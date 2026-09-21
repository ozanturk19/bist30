#!/bin/bash
# scripts/pre-deploy-check.sh
# CPO-359 Pre-Deploy Tier 0 — Otomatik audit önceki deploy.
# Adımlar:
# 1. Jinja parse
# 2. KALICI_KURALLAR audit
# 3. Python compile
# 4. format-lint (CPO-1180 K6)
# 5. CSS token guard (CPO-1349 §1 madde-1)
# 6. style-guard (T1.7 — K-A/K-B/K-C/K-D)
# 7. lint_scope ratchet (T9.4 — bkz. asagidaki not)
# 8. node-syntax-check (DEV2-T-MOBOVF-1 / CPO-DEV2-011 onerisi — bkz. asagidaki not)
# 12. legal-text-sync-check (K-H — hukuki metin/tarih senkronu, CPO 20.09.2026)
# Exit 0: tüm geçer / Exit 1: en az 1 fail
#
# Kullanım: ./scripts/pre-deploy-check.sh

set -e
FAIL=0
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Pre-Deploy Check (CPO-359 Tier 0) ==="
echo ""

# 1. Jinja parse
echo "1/20 Jinja parse..."
if python3 "$(dirname "$0")/_predeploy_jinja_check.py"; then
  echo "  ✓ Jinja parse OK"
else
  echo "  ✗ Jinja parse FAIL"
  FAIL=$((FAIL + 1))
fi

# 2. Python compile
echo ""
echo "2/20 Python compile (app.py)..."
if python3 -c "import ast;ast.parse(open('app.py').read())" 2>/dev/null; then
  echo "  ✓ app.py compile OK"
else
  echo "  ✗ app.py compile FAIL"
  FAIL=$((FAIL + 1))
fi

# 3. KALICI_KURALLAR audit
# CPO-1584 (11.09): eskiden SADECE templates/hisse.html taranıyordu — diğer
# 14 şablon (tarama/sektör-harita/index/portfolio/gundem/... dahil) hiç
# kontrol edilmiyordu, push-time gate commit-time gate'le (.githooks/
# pre-commit, aynı gün genişletildi) tutarsızdı. Liste ikisinde de senkron
# tutulmalı.
echo ""
echo "3/20 KALICI_KURALLAR audit..."
KK_AUDIT_FILES="templates/hisse.html templates/karsilastir.html templates/ozet.html templates/sektor_harita.html templates/tarama.html templates/hisseler.html templates/index.html templates/portfolio.html templates/gundem.html templates/metodoloji.html templates/blog.html templates/blog_article.html templates/temettu_takvimi.html templates/bilanco_takvimi.html"
KK_FAIL=0
for f in $KK_AUDIT_FILES; do
  if ! ./tests/audit/kalici-kurallar-check.sh "$f" > /dev/null 2>&1; then
    echo "  ✗ KK ihlali: $f. Detay için ./tests/audit/kalici-kurallar-check.sh $f çalıştır."
    KK_FAIL=$((KK_FAIL + 1))
  fi
done
if [ "$KK_FAIL" = "0" ]; then
  echo "  ✓ KK $(echo $KK_AUDIT_FILES | wc -w | tr -d ' ') dosya PASS"
else
  FAIL=$((FAIL + 1))
fi

# 4. format-lint
echo ""
echo "4/20 format-lint (CPO-1180 K6)..."
if ./tools/format-lint.sh > /dev/null 2>&1; then
  echo "  ✓ format-lint PASS"
else
  echo "  ✗ format-lint ihlal var. Detay için ./tools/format-lint.sh çalıştır."
  FAIL=$((FAIL + 1))
fi

# 5. CSS token guard (CPO-1349 §1 madde-1)
# 08.08.2026: tokens.css yorumu icindeki kaza yorum-kapatma dizisi ikinci :root
# blogunun TAMAMINI dusurdu; 10/10 olcek token-i canlida TANIMSIZDI. Dosya HTTP 200
# donuyordu, boyutu dogruydu, grep iceride buluyordu. Elle calistirilan bir arac bir
# sonraki kazada yok hukmundedir -- kapiya baglandi.
echo ""
echo "5/20 CSS token guard (CPO-1349)..."
if python3 tools/css-token-guard.py static/css/*.css > /dev/null 2>&1; then
  echo "  ✓ CSS token guard PASS"
else
  echo "  ✗ CSS token guard FAIL. Detay: python3 tools/css-token-guard.py static/css/*.css"
  FAIL=$((FAIL + 1))
fi

echo ""
# 6. style-guard (T1.7) — css-token-guard YALNIZ static/css/*.css (2 dosya) bakiyor;
# sablonlarin icindeki ~2300 var(--bp-*) kullanimi HICBIR kapida denetlenmiyordu.
# K-A tanimsiz var() BLOKLAYICI (taban 0), K-B/K-C/K-D ratchet (yalniz dusebilir).
echo "6/20 style-guard (T1.7: sablon ici var()/ham hex/yerel :root/bos catch ratchet)..."
if python3 tools/style-guard.py > /dev/null 2>&1; then
  echo "  ✓ style-guard PASS"
else
  echo "  ✗ style-guard ihlal var. Detay için: python3 tools/style-guard.py --verbose"
  FAIL=1
fi

# 7. lint_scope ratchet (T9.4) — tools/lint_scope.py --check ZATEN YAZILMISTI
# (T1.7, 08.08.2026) ama HICBIR gate script'i cagirmiyordu; format-lint.sh yalniz
# bayraksiz modu (sablon listesi turetmek icin) kullaniyordu. Sonuc: sablon sayisi
# 27'den 26'ya dustugunde (abd_tarama.html kaldirildi, f9e4ac8) ratchet KIRIK
# duruma gecti ama hicbir deploy bunu raporlamadi — "YAZILMIS ama BAGLANMAMIS"
# sinifinin kendisi, 8f6006f'in kapattigi iki guard'la AYNI hastalik. Bagliyoruz.
echo ""
echo "7/20 lint_scope ratchet (T9.4: sablon sayisi daralma dedektoru)..."
if python3 tools/lint_scope.py --check > /dev/null 2>&1; then
  echo "  ✓ lint_scope PASS"
else
  echo "  ✗ lint_scope kapsam daraldi/dedektor kirik. Detay için: python3 tools/lint_scope.py --check"
  FAIL=$((FAIL + 1))
fi

# 8. node-syntax-check (DEV2-T-MOBOVF-1) -- T7.4'de (8a00386) hisse.html'deki
# tek-tirnak template-literal hatasi TUM inline <script> bloklarini kirdi
# (SyntaxError), ama Jinja parse / python compile / format-lint / CSS token
# guard / style-guard / lint_scope 7 katinin HICBIRI bunu yakalamadi -- hepsi
# Jinja/Python katmanina bakiyor, saf JS sozdizimine degil. Deploy-sonrasi
# canli konsolda yakalanip duzeltilmisti. Bu adim AYNI SINIF hatayi deploy-
# ONCESI yakalar (Jinja {{ }}/{% %} soyulup node --check ile dogrulanir,
# 31/31 mevcut sablonda 0 yanlis-pozitif dogrulanmistir).
echo ""
echo "8/20 node-syntax-check (DEV2-T-MOBOVF-1: sablon-ici JS sozdizimi)..."
if python3 tools/node-syntax-check.py > /dev/null 2>&1; then
  echo "  ✓ node-syntax-check PASS"
else
  echo "  ✗ node-syntax-check FAIL. Detay için: python3 tools/node-syntax-check.py"
  FAIL=$((FAIL + 1))
fi

# 9. state-order-check (K-G, CPO 20.09.2026) -- `:hover` bir SOZDE-SINIFTIR,
# yani `.a:hover` ile `.a.b` ozgulluk bakimindan ESITTIR; esitlikte karari
# KAYNAK SIRASI verir. Durum kurali varyant bilesiklerinin USTUNDE yazilirsa
# varyantin da tanimladigi her ozellik icin SESSIZCE olur -- ne tarayici
# uyarir, ne yukaridaki 8 kattan biri gorur (hepsi degere/token'a/sozdizimine
# bakar, CASCADE'e degil), ne de grep "kural var" demekten oteye gider.
# Olculen bedel (443d0c5): /bilanco-takvimi 46 kartin 29'unda, /temettu 28'in
# 4'unde marka rengi hover cercevesi HIC uygulanmiyordu. Taban SIFIR; kasitli
# ciftler tool icindeki GOZDEN_GECIRILMIS_KASITLI'de GEREKCESIYLE yazilidir.
echo ""
echo "9/20 state-order-check (K-G: durum kurali varyantin ALTINDA olmali)..."
if python3 tools/state-order-check.py > /dev/null 2>&1; then
  echo "  ✓ state-order-check PASS"
else
  echo "  ✗ K-G KIRIK: bir durum kurali (:hover/:focus/:active) esit ozgullukteki"
  echo "    varyantinin ALTINDA kaliyor. Detay için: python3 tools/state-order-check.py"
  FAIL=$((FAIL + 1))
fi

# 10. contrast-check (K-I, CPO 20.09.2026) -- ayni kuralda hem zemin hem metin
# rengi yaziliysa WCAG 2.1 kontrasti hesaplanir (AA: 4.5:1, buyuk metin 3:1).
# NEDEN AYRI KAPI: /404 arama butonu `background:var(--bp-brand)` uzerine
# `color:#fff` yaziyordu -> 1.71:1, canlida aylarca durdu. Ustteki 9 katin
# HICBIRI goremezdi: css-token-guard renkle ilgilenmez; style-guard K-B yalniz
# KANONIK-DEGERLI ham hex sayar (#fff'in token'i yok, gorunmez); K-E olu palet
# denylist'idir (#fff orada degil). Ve bulgu aslinda bir YAZIM meselesi
# degildi -- kanonik token yazilsa da ihlal surerdi; olculmesi gereken sey
# renklerin KENDISI. Taban SIFIR (77 cift). Kapsam siniri ve pozitif kontrol
# kaydi tool'un docstring'inde.
echo ""
echo "10/20 contrast-check (K-I: ayni kuralda bg+fg WCAG kontrasti)..."
if python3 tools/contrast-check.py > /dev/null 2>&1; then
  echo "  ✓ contrast-check PASS"
else
  echo "  ✗ K-I KIRIK: bir kuralda zemin+metin cifti WCAG AA esiginin altinda."
  echo "    Detay için: python3 tools/contrast-check.py --verbose"
  FAIL=$((FAIL + 1))
fi

# 11. cachebust-check (K-J, CPO 20.09.2026) -- her `/static/...?v=<md5-8>`
# referansi diskteki dosyanin gercek hash'iyle ESLESMEK zorunda. Iki ayri
# sessiz basarisizligi kapatir: (1) static/sw.js precache listesi ile
# templates/offline.html'in ELLE tasidigi hash'ler kopmustu -> `caches.match`
# query string'i anahtarin parcasi saydigi icin /offline tam da ise
# yarayacagi anda STILSIZ aciliyordu; (2) CSS degisip sablondaki ?v=
# guncellenmezse Cloudflare ESKI dosyayi servis eder, deploy "basarili"
# gorunur ama fix canliya CIKMAZ. Ustteki 10 kat dosyanin ICINE bakar,
# hicbiri REFERANSA bakmaz. Taban SIFIR (118 referans). Elle artirilan
# surum etiketleri (?v=75, ?v=4, ?v=20260915A) kasitli kapsam disi.
echo ""
echo "11/20 cachebust-check (K-J: ?v= referansi diskteki hash ile ayni mi)..."
if python3 tools/cachebust-check.py > /dev/null 2>&1; then
  echo "  ✓ cachebust-check PASS"
else
  echo "  ✗ K-J KIRIK: bir cache-bust referansi bayat -> canliya eski dosya gider."
  echo "    Detay için: python3 tools/cachebust-check.py"
  FAIL=$((FAIL + 1))
fi

# 12. legal-text-sync-check (K-H, CPO 20.09.2026) -- hukuki sayfalarin <main>
# DUZ METNI degistiyse "Son guncelleme" tarihi de degismek ZORUNDA. 20.09'da
# olculdu: /gizlilik Eylul'de yeni veri kategorileri + yeni ucuncu taraflar
# kazanmisti, /yasal sinyal/gecikme ifadelerini degistirmisti, ikisi de hala
# "Agustos 2026" diyordu. Tarih, sayfanin kendi "degisiklikler burada
# duyurulacaktir" sozunun kullaniciya gorunen TEK kanitidir (KVKK m.10).
# Ustteki 11 kat KODA bakar (sozdizimi/token/hex/kontrast/cascade/referans);
# bu bulgu kodda degil, iki METIN alani arasindaki sozlesmede. Stil-only
# duzenlemeler metin hash'ini degistirmedigi icin kapiyi TETIKLEMEZ.
echo ""
echo "12/20 legal-text-sync-check (K-H: hukuki metin <-> 'Son guncelleme' senkronu)..."
if python3 tools/legal-text-sync-check.py; then
  echo "  ✓ legal-text-sync-check PASS"
else
  echo "  ✗ K-H KIRIK: hukuki metin degisti ama 'Son guncelleme' tarihi donmus kaldi."
  echo "    Detay için: python3 tools/legal-text-sync-check.py"
  FAIL=$((FAIL + 1))
fi

# 13. da-override-check (K-K, CPO 21.09.2026) -- kanonik bir `.da-*` sinifinin
# bildirdigi LONGHAND, ayni ogeye uygulanan ve data-art.css'ten SONRA yuklenen
# bir sayfa kuralinda KISAYOLLA sifirlaniyor mu. 21.09'da kendi fix'im bunu
# uretti: `.da-select` ok isaretini `background-image` ile veriyor, /iletisim'in
# `.cf-input` kurali `background:` KISAYOLUNU kullaniyordu -> canlida
# `appearance:none` + ok YOK, yani hicbir gostergesi olmayan bir <select>.
# Ihlal TEK bir dosyada degil iki dosyanin KESISIMINDE; ustteki 12 katin
# hicbiri (token/hex/kontrast/cascade-sirasi/referans/metin) bunu goremez.
# Dogrudan longhand ezmesi KASITLI delta sayilir, kapsam disi. Taban SIFIR.
echo ""
echo "13/20 da-override-check (K-K: .da-* bildirimini kisayolla silme)..."
if python3 tools/da-override-check.py; then
  echo "  ✓ da-override-check PASS"
else
  echo "  ✗ K-K KIRIK: bir sayfa kurali kanonik .da-* bildirimini sessizce siliyor."
  echo "    Detay için: python3 tools/da-override-check.py"
  FAIL=$((FAIL + 1))
fi

# 14. canon-conflict-check (K-AP, CPO 21.09.2026) -- KANONIK kaynak (tokens.css
# + data-art.css + _bp_critical_css.html) ile sayfa-yerel kopya (pages/*.css +
# sablon ici <style>) AYNI SECICI + AYNI OZELLIK icin FARKLI deger yaziyor mu.
# Ezen katman kanonigin ALTINDA yuklendigi icin esit ozgullukte KAZANIR, yani
# o sayfa sessizce sitenin geri kalanindan AYRILIR. 21.09'da iki gercek kusuru
# boyle buldum: (1) `.header-search-btn` sinir rengi K-Y'de olculup
# duzeltilmisti ama fix yalniz bp-search.js'e uygulanmis, CSS katmani eski
# 1,34:1 degerde kalmisti (JS defer -> ilk boyada, JS duserse KALICI yanlis);
# (2) /temettu-takvimi `body{font-family}` kanonik Space Grotesk/Manrope yerine
# Inter yaziyordu -- 21 sayfanin 20'si bir yazi tipinde, o tek basina baskasinda.
# --* ozel ozellikleri ve yalniz bosluk farki kapsam disi. Taban SIFIR.
echo ""
echo "14/20 canon-conflict-check (K-AP: kanonik kaynak <-> sayfa-yerel kopya)..."
if python3 tools/canon-conflict-check.py; then
  echo "  ✓ canon-conflict-check PASS"
else
  echo "  ✗ K-AP KIRIK: bir sayfa kanonik kaynakla AYNI secici hakkinda FARKLI konusuyor."
  echo "    Detay için: python3 tools/canon-conflict-check.py"
  FAIL=$((FAIL + 1))
fi

# 15. glyph-canon-check (K-AQ, CPO 21.09.2026) -- ROZET GLIFI <-> KANONIK ANLAM.
# Bir glif site genelinde TEK bir sey demeli. 21.09'da 💎 ayni anda UC sey
# diyordu: (1) /tarama satir rozeti = Teknik Guc Skoru 70+, (2) /tarama filtre
# secenegi "💎 Premium" = hacim onayli (is_premium) -- canli olculdu: filtre
# 5 satir donduruyor ve 5'inde de 💎 YOK, (3) /hisse RSI<30 = "💎 Asiri Satim"
# -- canli: 217 hissenin 86'si su anda bu durumda (ornek /hisse/EMKEL,
# "Trend Bozuldu" hissesinde "RSI 10,9 💎 Asiri Satim"). Kanon: 💎 = skor bandi,
# ⭐ = Hacim Onayli. Taban SIFIR, pozitif kontrol 4/4.
echo ""
echo "15/20 glyph-canon-check (K-AQ: rozet glifi <-> kanonik anlam)..."
if python3 tools/glyph-canon-check.py; then
  echo "  ✓ glyph-canon-check PASS"
else
  echo "  ✗ K-AQ KIRIK: bir rozet glifi site genelinde BIRDEN FAZLA sey diyor."
  echo "    Detay için: python3 tools/glyph-canon-check.py"
  FAIL=$((FAIL + 1))
fi

# 16. threshold-sync-check (K-AR, CPO 21.09.2026) -- BANT ESIGI KOPYALARI.
# business_rules.py:derive_adx_label kendi docstring'inde "app.py'nin
# ImportError-fallback'i ve hisse.html'in JS ilk-render fallback'i esikleri
# kendi kopyalarinda tutar (otomatik senkron kilidi YOK, elle esitlenmeli)"
# diyordu -- kod kendi kor noktasini yaziyla ilan ediyor ama kapisi yoktu.
# Bu kapi 4 katmani birden olcer: (1) app.py fallback, (2) sablon-ici JS
# merdiveni, (3) duz nesir ("40+ Cok Guclu, 25-40 Guclu..."), (4) \uXXXX
# kacisiyla yazilmis nesir (hisse.html RSI tooltip'i boyle). Taban SIFIR,
# 11 kod + 9 nesir esigi, pozitif kontrol 4/4 (dort katmanda da yakalandi).
# Kapsam tabani var: olculen esik sayisi duserse cikis kodu 2.
echo ""
echo "16/20 threshold-sync-check (K-AR: bant esigi kopyalari <-> business_rules)..."
if python3 tools/threshold-sync-check.py; then
  echo "  ✓ threshold-sync-check PASS"
else
  echo "  ✗ K-AR KIRIK: bir bant esigi kopyasi kanonikten sapti (ya da kapsam dustu)."
  echo "    Detay için: python3 tools/threshold-sync-check.py"
  FAIL=$((FAIL + 1))
fi

# 17. nav-label-canon-check (K-AS, CPO 21.09.2026) -- GEZINME ETIKETI KANONU.
# WCAG SC 3.2.4 + 2.5.3. Sitenin UC gezinme yuzeyi (masaustu nav+drawer /
# mobil alt nav+sheet / alt bilgi) ayni hedefi FARKLI adla aniyordu:
# /tarama "Tarama" vs "Hisse Tarayici", /sektor-harita "Sektorler" vs
# "Sektor Haritasi", /ozet "Ozet" vs "Gunluk Ozet", /bilanco-takvimi
# "Bilanco" vs "Bilanco Takvimi", /temettu-takvimi "Temettu" vs "Temettu
# Takvimi" -- kullanici alt bilgide baska, ust menude baska ad goruyordu.
# Kapi SABLON KAYNAGINI okur, canli DOM'u DEGIL: kapali drawer/sheet
# aria-hidden'dir ve canli dedektor (tools/link-purpose-check.js) onlari
# -- dogru olarak -- ekran okuyucuda yok sayar; iki takvim catismasi tam bu
# yuzden canli taramada GORUNMEDI. Taban SIFIR, 63 baglanti, kapsam tabani
# 55, pozitif kontrol 3/3 (ad uyusmazligi / SC 2.5.3 / logo adi).
echo ""
echo "17/20 nav-label-canon-check (K-AS: gezinme etiketi kanonu)..."
if python3 tools/nav-label-canon-check.py; then
  echo "  ✓ nav-label-canon-check PASS"
else
  echo "  ✗ K-AS KIRIK: bir gezinme etiketi kanonik addan sapti (ya da kapsam dustu)."
  echo "    Detay için: python3 tools/nav-label-canon-check.py"
  FAIL=$((FAIL + 1))
fi

# 18. tooltip-canon-check (K-AT, CPO 21.09.2026) -- IPUCU MEKANIZMASI KANONU.
# Sitede IKI paralel ipucu mekanizmasi vardi. Kanonik olan [data-tip] +
# static/js/bp-tooltip.js (hover + focus + tap-toggle + Escape + viewport
# kirpma + aria-describedby). Ikincisi tarama.css'teki
# `thead th[data-tooltip]:hover::after` idi: dokunmatikte HIC acilmiyor,
# :focus-within ise odaklanabilir cocugu olmayan iki baslikta (Temel Skor /
# BorsaPusula Skoru) hic tetiklenemiyordu -> skor FORMULU yalnizca fareyle
# okunabiliyordu (WCAG 1.4.13). Ustelik white-space:nowrap + max-width yok:
# 102px'lik basligin altinda 502px, en uzununda ~1000px tek satir.
# Kapi uc ekseni olcer: (1) CSS'te `content:attr(data-*)` ile kurulan ikinci
# mekanizma -- yalniz `.ind-help` beyaz listede (onun tap+Escape JS'i var);
# (2) [data-tip] tasiyan her oge klavyeyle odaklanabilir olmali -- <label>
# istisnasi KOSULLU, sardigi kontrol display:none ise dusut (gercek bulgu:
# `#importFileInput{display:none}` yuzunden "İçe Aktar" YALNIZCA fareyle
# calisiyordu, WCAG 2.1.1 A); (3) [data-tip] kullanan sablon bp-tooltip.js'i
# yuklemeli. Taban SIFIR, 72 kullanim, kapsam tabani 50, pozitif kontrol 4/4.
echo ""
echo "18/20 tooltip-canon-check (K-AT: ipucu mekanizmasi kanonu)..."
if python3 tools/tooltip-canon-check.py; then
  echo "  ✓ tooltip-canon-check PASS"
else
  echo "  ✗ K-AT KIRIK: ikinci bir ipucu mekanizmasi ya da yalniz-fare ipucu (ya da kapsam dustu)."
  echo "    Detay için: python3 tools/tooltip-canon-check.py"
  FAIL=$((FAIL + 1))
fi

# 19. sort-canon-check (K-AV, CPO 21.09.2026) -- SIRALAMA KONTROLU DURUM KANONU.
# /tarama'da iki kusur olculdu: (1) acilir menu option metinleri yonu SABIT
# iddia ediyordu ("Trend Gucu / ADX (Guclu -> Zayif)") ama yonu sutun basligi
# da cevirebiliyordu -- 2. tiklamadan sonra aria-sort=ascending + liste
# Zayif->Guclu + URL sort_dir=asc iken metin hala "Guclu -> Zayif" diyordu;
# (2) Temel sekmesinde sirali sutun tabloda HIC isaretlenmiyordu (10/10
# baslikta aria-sort yok) ve basliklar tiklanamiyordu -- ayni sayfada Teknik
# sekmesi ok + aria-sort gosteriyordu. Kapi: yon ibaresi tasiyan option
# data-label/data-desc/data-asc ile gercek yonden TUREMELI; siralanabilir
# baslik th.th-sortable + aria-sort + button.th-sort-btn kalibini izlemeli.
# Kapsam tabani 10 option / 10 baslik, pozitif kontrol 4/4.
echo ""
echo "19/20 sort-canon-check (K-AV: siralama kontrolu durum kanonu)..."
if python3 tools/sort-canon-check.py; then
  echo "  ✓ sort-canon-check PASS"
else
  echo "  ✗ K-AV KIRIK: sabit yon iddiasi ya da durumunu bildirmeyen siralanabilir baslik (ya da kapsam dustu)."
  echo "    Detay için: python3 tools/sort-canon-check.py"
  FAIL=$((FAIL + 1))
fi

# 20. newtab-canon-check (K-AW, CPO 21.09.2026) -- YENI SEKME UYARISI KANONU.
# 27 target=_blank baglantinin 18'i acilan yeni sekmeyi ERISILEBILIR ADINDA
# hic soylemiyordu; 4'u (makro/sirket haber kartlari) siteden CIKIP 3. parti
# alan adina gidiyordu ve gorsel isareti de yoktu. Ayni davranis dort ayri
# sekilde anlatiliyordu (sr-only / aria-label / yalniz aria-hidden ↗ / hicbir
# sey). Yeni sekmeden "geri" tusuyla donulemez -- uyarisizlik yon kaybidir
# (WCAG 3.2.5 / G201). Kapi: (A) her _blank baglantinin ADI "yeni sekmede
# acilir" tasimali -- aria-hidden kutusuna saklanamaz; (B) siteden CIKAN
# baglanti ayrica gorunur ↗ tasimali (ic hedefler TASIMAZ; ↗ = "siteden
# ayriliyorsun"). B'nin tek muafiyeti KARDES OK: ayni hedefi gosteren,
# 800 karakter icindeki baska bir baglanti oku zaten tasiyorsa.
# Kapsam tabani 20 baglanti, pozitif kontrol 7/7.
echo ""
echo "20/20 newtab-canon-check (K-AW: yeni sekme uyarisi kanonu)..."
if python3 tools/newtab-canon-check.py; then
  echo "  ✓ newtab-canon-check PASS"
else
  echo "  ✗ K-AW KIRIK: yeni sekmeyi adinda soylemeyen baglanti ya da isaretsiz dis hedef (ya da kapsam dustu)."
  echo "    Detay için: python3 tools/newtab-canon-check.py"
  FAIL=$((FAIL + 1))
fi

echo ""
if [ "$FAIL" = "0" ]; then
  echo "✅ Pre-deploy TÜM CHECK GEÇTİ — deploy izinli."
  exit 0
else
  echo "❌ $FAIL fail tespit edildi — deploy reddedildi."
  exit 1
fi
