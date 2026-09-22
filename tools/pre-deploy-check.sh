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
echo "1/73 Jinja parse..."
if python3 "$(dirname "$0")/_predeploy_jinja_check.py"; then
  echo "  ✓ Jinja parse OK"
else
  echo "  ✗ Jinja parse FAIL"
  FAIL=$((FAIL + 1))
fi

# 2. Python compile
echo ""
echo "2/73 Python compile (app.py)..."
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
echo "3/73 KALICI_KURALLAR audit..."
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
echo "4/73 format-lint (CPO-1180 K6)..."
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
echo "5/73 CSS token guard (CPO-1349)..."
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
echo "6/73 style-guard (T1.7: sablon ici var()/ham hex/yerel :root/bos catch ratchet)..."
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
echo "7/73 lint_scope ratchet (T9.4: sablon sayisi daralma dedektoru)..."
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
echo "8/73 node-syntax-check (DEV2-T-MOBOVF-1: sablon-ici JS sozdizimi)..."
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
echo "9/73 state-order-check (K-G: durum kurali varyantin ALTINDA olmali)..."
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
echo "10/73 contrast-check (K-I: ayni kuralda bg+fg WCAG kontrasti)..."
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
echo "11/73 cachebust-check (K-J: ?v= referansi diskteki hash ile ayni mi)..."
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
echo "12/73 legal-text-sync-check (K-H: hukuki metin <-> 'Son guncelleme' senkronu)..."
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
echo "13/73 da-override-check (K-K: .da-* bildirimini kisayolla silme)..."
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
echo "14/73 canon-conflict-check (K-AP: kanonik kaynak <-> sayfa-yerel kopya)..."
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
echo "15/73 glyph-canon-check (K-AQ: rozet glifi <-> kanonik anlam)..."
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
echo "16/73 threshold-sync-check (K-AR: bant esigi kopyalari <-> business_rules)..."
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
echo "17/73 nav-label-canon-check (K-AS: gezinme etiketi kanonu)..."
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
echo "18/73 tooltip-canon-check (K-AT: ipucu mekanizmasi kanonu)..."
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
echo "19/73 sort-canon-check (K-AV: siralama kontrolu durum kanonu)..."
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
echo "20/73 newtab-canon-check (K-AW: yeni sekme uyarisi kanonu)..."
if python3 tools/newtab-canon-check.py; then
  echo "  ✓ newtab-canon-check PASS"
else
  echo "  ✗ K-AW KIRIK: yeni sekmeyi adinda soylemeyen baglanti ya da isaretsiz dis hedef (ya da kapsam dustu)."
  echo "    Detay için: python3 tools/newtab-canon-check.py"
  FAIL=$((FAIL + 1))
fi

# 21. autorefresh-canon-check (K-AX, CPO 21.09.2026) -- PERIYODIK YENILEME
# ODAK KANONU. /portfolio 60 saniyede bir `tbody.innerHTML` ile tum satirlari
# basdan yaziyordu; satirlarin icinde "✎ duzenle" / "✕ kaldir" dugmeleri var.
# Klavye kullanicisi bir dugmeye gelip duraksarsa dugme YOK EDILIYOR, odak
# <body>'ye dusuyor: Enter islemiyor, Tab belgenin EN BASINDAN basliyor -- ve
# 60 saniyede bir tekrarliyor. Canli olcum: 5 sayfa / 6 zamanlayici / 529 oge
# risk altinda (bilanco takvimi 190, sektor haritasi 164 -- sonuncusu 2
# DAKIKADA bir). Ekranda gorsel fark ve konsolda hata YOK; fare kullanicisi
# fark etmiyor, bu yuzden 20 tur denetimden gecti. WCAG 2.2.2 (A) + 2.4.3 (A).
# Kapi: icerigini innerHTML ile yeniden yazan her periyodik handler
# bpPreserveFocus uzerinden gecmeli. Geciskenlik derinligi 1 (fetchLive yazmaz,
# cagirdigi render() yazar). Muafiyet YOK: sablonda tanimsiz handler sessizce
# gecmez, paylasilan makro serit ise ayrica olculur (yalniz <span> uretmeli).
# Taban SIFIR, pozitif kontrol 13/13 (takma ad sokulunce) + 4/4 (ciplak handler).
echo ""
echo "21/73 autorefresh-canon-check (K-AX: periyodik yenileme odak kanonu)..."
if python3 tools/autorefresh-canon-check.py; then
  echo "  ✓ autorefresh-canon-check PASS"
else
  echo "  ✗ K-AX KIRIK: sarmalanmamis periyodik icerik yenileyici (odaktaki oge yok edilir)."
  echo "    Detay için: python3 tools/autorefresh-canon-check.py"
  FAIL=$((FAIL + 1))
fi

echo ""
# 22. sticky-anchor-check (K-AY, CPO 21.09.2026) -- YAPISKAN CAPA KANONU.
#     Ust kabugun olcusu (makro serit 32 + header 60 + 2*safe-area-inset) 13
#     ayri yerde ELLE yaziliydi; UCU header'in kendi inset payini saymiyordu.
#     Centikli telefonda (PWA) /hisse sekme seridi header'in altinda TAMAMEN,
#     /tarama + /karsilastir thead'leri bir inset kadar kayboluyordu -- masaustunde
#     inset=0 oldugu icin 20+ tur denetimden gorunmeden gecti. Olcu artik
#     shared.css'te tek kaynak: var(--bp-anchor-macro|header).
echo "22/73 sticky-anchor-check (K-AY: yapiskan capa kanonu)..."
if python3 tools/sticky-anchor-check.py; then
  echo "  ✓ sticky-anchor-check PASS"
else
  echo "  ✗ K-AY KIRIK: kabuk olcusu elle yazilmis yapiskan capa (centikli cihazda kayar)."
  echo "    Detay için: python3 tools/sticky-anchor-check.py"
  FAIL=$((FAIL + 1))
fi

echo ""
# 23. safearea-layer-check (K-AZ, CPO 21.09.2026) -- GUVENLI ALAN KAPSAM KANONU.
#     PWA/standalone'da (viewport-fit=cover) icerik centigin ve ev gostergesinin
#     ALTINA cizilir. Arama modalinin tam ekran mobil varyanti ile /blog
#     .read-progress bunu oymuyordu: arama kutusu + ✕ kapat %100, ilerleme
#     cubugu %100 guvensiz bolgedeydi. Masaustunde inset=0 oldugu icin gorunmedi.
echo "23/73 safearea-layer-check (K-AZ: guvenli alan kapsam kanonu)..."
if python3 tools/safearea-layer-check.py; then
  echo "  ✓ safearea-layer-check PASS"
else
  echo "  ✗ K-AZ KIRIK: centik/ev gostergesi altinda kalan sabit katman."
  echo "    Detay için: python3 tools/safearea-layer-check.py"
  FAIL=$((FAIL + 1))
fi

echo ""
# 24. tr-decimal-input-check (K-BA, CPO 21.09.2026) -- TURKCE ONDALIK GIRDI KANONU.
#     /tarama'nin dort fiyat alani type="number"di. Turkce konusan kullanici
#     "12,50" yazinca tarayici virgulu SESSIZCE siliyor, input.value "1250"
#     oluyor -- validity.valid hala true, badInput false, hicbir hata yok.
#     Canli olcum: 216 hisse -> 5, filtre cipi guvenle "Min 1250 ₺" diyordu.
#     Ayni hata portfolio.html "Alis ₺" alaninda DAHA ONCE bulunup orada
#     duzeltilmisti; /tarama fix'i miras almamisti -- kapi ucuncu kopyayi onler.
echo "24/73 tr-decimal-input-check (K-BA: TR ondalik girdi kanonu)..."
if python3 tools/tr-decimal-input-check.py; then
  echo "  ✓ tr-decimal-input-check PASS"
else
  echo "  ✗ K-BA KIRIK: ondalik kabul eden alan type=\"number\" (TR virgulu sessizce silinir)."
  echo "    Detay için: python3 tools/tr-decimal-input-check.py"
  FAIL=$((FAIL + 1))
fi

echo "25/73 tr-calendar-day-check (K-BD: TR takvim gunu kanonu)..."
if python3 tools/tr-calendar-day-check.py; then
  echo "  ✓ tr-calendar-day-check PASS"
else
  echo "  ✗ K-BD KIRIK: \"bugun\" degeri UTC'den/yerel saatten turetiliyor."
  echo "    Detay için: python3 tools/tr-calendar-day-check.py"
  FAIL=$((FAIL + 1))
fi

echo "26/73 global-collision-check (K-BE: kuresel ad cakismasi)..."
if python3 tools/global-collision-check.py; then
  echo "  ✓ global-collision-check PASS"
else
  echo "  ✗ K-BE KIRIK: sablon, yukledigi paylasilan dosyanin ust duzey adini eziyor."
  echo "    Detay için: python3 tools/global-collision-check.py"
  FAIL=$((FAIL + 1))
fi

echo "27/73 js-palette-check (K-BG: JS paleti <-> tokens.css, RATCHET)..."
if python3 tools/js-palette-check.py; then
  echo "  ✓ js-palette-check PASS"
else
  echo "  ✗ K-BG KIRIK: JS icinde token'a baglanmamis ham renk ARTTI."
  echo "    Detay için: python3 tools/js-palette-check.py"
  FAIL=$((FAIL + 1))
fi

echo "28/73 copy-promise-check (K-BH: \"kopyala\" vaadi = kopyalanan sey)..."
if python3 tools/copy-promise-check.py; then
  echo "  ✓ copy-promise-check PASS"
else
  echo "  ✗ K-BH KIRIK: \"baglantiyi kopyala\" diyen kontrol panoya URL DEGIL baska bir sey yaziyor."
  echo "    Detay için: python3 tools/copy-promise-check.py"
  FAIL=$((FAIL + 1))
fi

# K-BI (21.09): "Yuklendi! N pozisyon" -- buluttan yukleme, ZATEN VAR oldugu
# icin EKLENMEYEN kayitlari da eklenmis sayiyordu (gelen listenin uzunlugundan
# sayiyordu). Ayni isi yapan dosya-ice-aktarma yolu DOGRU sayiyordu: ayni is
# icin iki kanon. Kapi, portfoye ekleme yapan her yolun ortak
# `_pfMergePositions()` kanonundan gectigini ve kullaniciya gosterilen sayinin
# gelen listenin uzunlugundan turetilMEdigini olcer.
echo "29/73 merge-report-check (K-BI: birlestirme sayimi = gercekten eklenen)..."
if python3 tools/merge-report-check.py; then
  echo "  ✓ merge-report-check PASS"
else
  echo "  ✗ K-BI KIRIK: portfoy birlestirme ya kanonu atliyor ya da sayiyi gelen listenin uzunlugundan turetiyor."
  echo "    Detay için: python3 tools/merge-report-check.py"
  FAIL=$((FAIL + 1))
fi

# K-BJ (21.09): portfoye pozisyon YAZAN dort yol vardi, sayisal olcut UC ayri
# yerde ve IKI ayri yazimda kopyalanmisti; hisse detay hizli-eklemesi ise hic
# dogrulamiyordu ve _hibCurrentPrice() fiyat okunamadiginda 0 donup o 0'i
# MALIYET olarak yaziyordu (cost=0 -> pozisyonun tam degeri "kar" gorunur,
# toplam K/Z kutusu sisirilir). CSV disa aktarimi da ayni K/Z'yi tablo
# render'inin aksine korumasizca hesapliyordu ("Infinity"/"NaN" hucreler).
echo "30/73 position-validation-check (K-BJ: pozisyon sayisal dogrulamasi tek kanon)..."
if python3 tools/position-validation-check.py; then
  echo "  ✓ position-validation-check PASS"
else
  echo "  ✗ K-BJ KIRIK: pozisyon olcutu yeniden yazilmis ya da dogrulanmamis fiyat portfoye yaziliyor."
  echo "    Detay için: python3 tools/position-validation-check.py"
  FAIL=$((FAIL + 1))
fi

# K-BK (21.09): `/api/data` soguk baslangicta (her `systemctl restart` sonrasi)
# HTTP 200 + gecerli JSON + {"stocks": [], "loading": true} doner. Alti
# tuketiciden DORDU `loading` alanini hic okumuyordu ve bos listeyi KESIN
# HUKUMLU "veri yok" diye sunuyordu: ana sayfa dort bolume "Su an gosterilecek
# hisse verisi yok." (tek atislik yukleme, tekrar-dene yok), 404 aramasi
# "THYAO ile eslesen bir hisse bulunamadi", portfoy "borsadan cekilmis
# olabilir - ... veya pozisyonu KALDIRIN" (veri kaybina yol acan tavsiye),
# hisse detayi "giris analizi hesaplanamadi, veri yetersiz". Kanon
# static/bp-search.js:151 -- bu dali yazili gerekcesiyle ele alan TEK yerdi.
echo "31/73 api-data-loading-guard (K-BK: bos liste != veri yok)..."
if python3 tools/api-data-loading-guard.py; then
  echo "  ✓ api-data-loading-guard PASS"
else
  echo "  ✗ K-BK KIRIK: bir /api/data tuketicisi bos listeyi 'veri yok' diye sunuyor, `loading` okunmuyor."
  echo "    Detay için: python3 tools/api-data-loading-guard.py"
  FAIL=$((FAIL + 1))
fi

# K-BM (21.09): /portfolio, `bp_portfolio` kaydini parse edemedigi ya da dizi
# olmadigini gordugu her durumda bellegi `[]` yapip "Portföyünüz boş." diyordu;
# ham kayit hala tarayicidaydi, ama kullanici bunu gercek bos portfoy sanip tek
# pozisyon ekleyince ilk save() ham kaydi KALICI eziyordu. Ayni is icin ikinci
# kanon (hisse.html:togglePortfolio) islemi iptal edip "mevcut verin korundu"
# diyordu -- zayif kanon veri kaybettiriyordu. Kapi, kullanici verisi tutan her
# localStorage parse yolunda catch'in ya ham kaydi yedeklemesini ya islemi iptal
# etmesini sart kosar; yeniden uretilebilir onbellek anahtarlari muaftir.
echo "32/73 local-data-guard (K-BM: bozuk yerel kayit sessizce silinmemeli)..."
if python3 tools/local-data-guard.py; then
  echo "  ✓ local-data-guard PASS"
else
  echo "  ✗ K-BM KIRIK: bozuk bir yerel kayit sessizce sifirlaniyor (kullanici verisi kaybi riski)."
  echo "    Detay için: python3 tools/local-data-guard.py"
  FAIL=$((FAIL + 1))
fi

# K-BN (21.09): site EOD-only (app.py background_refresh, CPO-1508/1512: gunde
# BIR kez, 18:10+ TR) ama UC yuzey kullaniciya alt-gunluk tazelik vaat ediyordu:
# /yasal (HUKUKI sayfa) "~15 dakika gecikmeli olabilir", fiyat gosteren 12
# sayfanin footer rozeti "BIST resmi yayin gecikmesi yaklasik 15 dakika",
# hisse.html tazelik cipi 'BIST ~15dk gecikmeli'. CANLI KANIT: 21.09 Pzt 09:07
# TR'de servis edilen veri updated_at=18.09 18:14 = ~63 SAAT eskiydi.
# /hakkinda, /metodoloji, /tarama, /gundem, index dogrusunu soyluyordu -> tek
# is icin iki kanon. Kapi ayrica KENDI PREMISE'ini olcer: app.py'den EOD imzasi
# kaybolursa PASS/FAIL vermez, "cadence degismis" diye duser.
echo "33/73 eod-freshness-claim-check (K-BN: gosterilen fiyatin tazelik vaadi)..."
if python3 tools/eod-freshness-claim-check.py; then
  echo "  ✓ eod-freshness-claim-check PASS"
else
  echo "  ✗ K-BN KIRIK: bir yuzey EOD-only mimaride olmayan bir tazelik vaat ediyor."
  echo "    Detay için: python3 tools/eod-freshness-claim-check.py"
  FAIL=$((FAIL + 1))
fi

# 34. volume-axis-color-check (K-BO, CPO 21.09.2026) -- HACIM YON-BAGIMSIZ
# bir buyukluktur (cokuste de yuksek cikar). --bp-al/--bp-sat ile boyaninca,
# ayni satirdaki "Sinyal" sutunu / ayni karttaki seg-al cubugu o rengi zaten
# YON anlaminda kullandigi icin kullanici hacmi "olumlu" okuyordu. Emsal ayni
# depoda yaziliydi (tarama.css .trend-label, ADX/BTCIM 10.09) ama kardes RVOL
# hucresine uygulanmamisti. Ikinci sinif: hacim ekseninin kanonik rengi
# --bp-volume; --bp-gold/--bp-accent-yellow odunc alinmasi ayni kavrami
# uc renge boluyordu (21.09'da 4 yuzey/10 ihlal, pozitif kontrol 49ae8c6).
echo "34/73 volume-axis-color-check (K-BO: hacim ekseni yon rengiyle boyanamaz)..."
if python3 tools/volume-axis-color-check.py; then
  echo "  ✓ volume-axis-color-check PASS"
else
  echo "  ✗ K-BO KIRIK: hacim ekseni yabanci bir eksenin rengiyle boyaniyor."
  echo "    Detay için: python3 tools/volume-axis-color-check.py"
  echo "    Pozitif kontrol: python3 tools/volume-axis-color-check.py --ref 49ae8c6"
  FAIL=$((FAIL + 1))
fi

# 35. direction-zero-check (K-BP, CPO 21.09.2026) -- DEGISIM SIFIRSA YON
# RENGI YOKTUR. Yesil "yukselis", kirmizi "dusus", "+" kazanc vaadidir; 0
# bunlarin hicbiri degil. Sitede iki kanon vardi: `x > 0 ? AL : x < 0 ? SAT :
# NOTR` (/tarama, /gundem, /sektor-harita) ve `x >= 0 ? AL : SAT` (/karsilastir,
# /portfolio, /ozet, /hisse, anasayfa serit, blog widget). 21.09 canli kanit:
# ALARK/DOAS/ARCLK/CEMTS/ISMEN change_pct=0 -> /tarama "0,00%" GRI,
# /karsilastir "+0,00%" YESIL. /portfolio'da daha sik: pozisyon guncel
# fiyattan eklendiginde K/Z TAM SIFIRDIR ve "+0,00 ₺" YESIL yaziliyordu.
# Pozitif kontrol (fix oncesi agac): 27 ihlal / 9 dosya.
# K-CC (22.09.2026) eki: kapi 22.09'da "OK" derken anasayfada/ozette ON canli
# ihlal duruyordu. Uc kor nokta kapatildi -- (D) satir-ici Jinja kosulu
# `{{ A if x >= 0 else B }}`, (E) kosulsuz isaretli bicim `'%+.2f'|format(x)`
# ("+0,00"), (F) degiskene atanan kararin ADIYLA takibi (yakinlik penceresi
# dolayli degiskeni goremiyordu). Canli kanit: /ozet'te 21 adet "+0,0%",
# biri YESIL sc-ret-pos; anasayfa sektor mozaiginde Ulasim ve Telekom
# (skor 0) YESIL zemin + YUKARI ok + "+0 skor".
echo "35/73 direction-zero-check (K-BP+K-CC: 0 bir yonle ayni kefeye konamaz)..."
if python3 tools/direction-zero-check.py; then
  echo "  ✓ direction-zero-check PASS"
else
  echo "  ✗ K-BP KIRIK: degismeyen bir deger yon rengi/isareti aliyor."
  echo "    Detay için: python3 tools/direction-zero-check.py"
  echo "    Pozitif kontrol: python3 tools/direction-zero-check.py --ref 00d37b9  (K-CC: 10 ihlal)"
  FAIL=$((FAIL + 1))
fi

# 36. stop-level-canon-check (K-BQ, CPO 21.09.2026) -- "STOP" BIR YON
# IDDIASIDIR. `sl_level` Supertrend bandinin guncel degeridir, sinyal yonunden
# bagimsiz HER hissede hesaplanir; long-only bir urunde ona "Stop" demek ancak
# band fiyatin ALTINDAYKEN anlamlidir. 21.09 canli olcum (/api/data, 217 hisse):
# sl_level > price olan **197** hisse (72/72 SAT + 125/138 BEKLE). MARTI: fiyat
# 2,01 ₺ iken "Hap Bilgi" -> "Stop Seviyesi 2,74 ₺" (%36 YUKARIDA), ayni sayfa
# iki satir yukarida "Net sinyal olmadigi icin tanimli bir giris bolgesi yok"
# diyordu. /karsilastir ayni alani ZATEN dogru adlandirmisti ("Supertrend
# Seviyesi" + "acik bir pozisyonun stopu anlamina gelmez") -- /hisse emsali
# miras almamisti. Alt-etiket de band fiyatin ustundeyken "ST destegi" diyordu.
# Pozitif kontrol (fix oncesi agac): 7 ihlal / hisse.html.
echo "36/73 stop-level-canon-check (K-BQ: 'Stop' yon iddiasidir)..."
if python3 tools/stop-level-canon-check.py; then
  echo "  ✓ stop-level-canon-check PASS"
else
  echo "  ✗ K-BQ KIRIK: sl_level yuzeyinde 'stop'/'destek'/'direnc' kosulsuz iddia ediliyor."
  echo "    Detay için: python3 tools/stop-level-canon-check.py"
  echo "    Pozitif kontrol: python3 tools/stop-level-canon-check.py --ref 14248ef"
  FAIL=$((FAIL + 1))
fi

# 37. indicator-precision-check (K-BR, CPO 22.09.2026) -- ESIK TASIYAN
# GOSTERGE TAM SAYIYA YUVARLANAMAZ. ADX'in 25 esigi urunun sinyal kuralidir.
# `|int` ASAGI KESER: ISDMR ADX 25,9 iken /hisse checklist'i "✓ ADX 25 --
# Güçlü trend (eşik: 25)" basiyordu ("kil payi gecti" diye okunur), ayni
# sayfanin Hap Bilgi'si `|round|int` ile "26", indikator paneli "25,9"
# diyordu -- AYNI SAYI UC GOSTERIM. Anasayfa spotlight'inda SSR (`|round(0)`)
# ile CSR (`Math.round`) ayni karti ciziyordu. Canli: int!=round olan 91
# hisse, ADX 25,0-25,9 bandinda 14 hisse. Site kanonu ZATEN 1 ondalikti
# (/tarama, /karsilastir) -- sapan /hisse SSR + anasayfa spotlight'ti.
# Pozitif kontrol (fix oncesi agac): 13 ihlal.
echo "37/73 indicator-precision-check (K-BR: ADX/RSI 1 ondalik kanonu)..."
if python3 tools/indicator-precision-check.py; then
  echo "  ✓ indicator-precision-check PASS"
else
  echo "  ✗ K-BR KIRIK: ADX/RSI tam sayiya yuvarlaniyor (esik 25 ile cakisir)."
  echo "    Detay için: python3 tools/indicator-precision-check.py"
  echo "    Pozitif kontrol: python3 tools/indicator-precision-check.py --ref 6c4d5f8"
  FAIL=$((FAIL + 1))
fi

# 38. indicator-panel-canon-check (K-BS, CPO 22.09.2026) -- GOSTERGE PANELI
# TEK AGIZDAN KONUSUR. Uc sinif, ucu de canli dogrulandi (22.09):
#   A) CPO-1665 rozetin metnini/isaretini otoriter kaynaga (signalData.indicators)
#      tasidi, KARDES alan `techDetail` chart ozetinde (`s.st_bull`) kaldi ->
#      /hisse/TAVHL rozet "Trend Yonu -- ↓ Dusus" derken hemen altindaki
#      teknik satir "Supertrend(10,3): LONG" basiyordu (tarayici olcumu).
#   B) K-BO ihlali SINIF ADI uzerinden hayatta kalmisti: hacim rozeti
#      `ind-bull` (= --bp-al yukselis yesili) kullaniyordu, kapi 34 yalniz
#      token/ham-hex ariyordu. vol_ratio >= 3 olan 4 hissenin DORDU DE BEKLE,
#      ikisi o gun dusmus (SASA -1,70% - USAK -3,85%).
#   C) `rsi_zone` sinyalden BAGIMSIZ turetilir; "Ideal Giris Penceresi" tasiyan
#      46 hissenin 45'i AL DEGIL (FROTO/MGROS/MAVI SAT). Rengi CPO-DEV2-031/033
#      notrlemisti, KELIMELER kalmisti.
# Pozitif kontrol (fix oncesi agac): 5 ihlal / 2 dosya, uc sinifin hepsi.
echo "38/73 indicator-panel-canon-check (K-BS: rozet ve teknik satir tek kaynak)..."
if python3 tools/indicator-panel-canon-check.py; then
  echo "  ✓ indicator-panel-canon-check PASS"
else
  echo "  ✗ K-BS KIRIK: rozet/teknik satir ayri kaynaktan okuyor, hacim yon"
  echo "    rengiyle boyaniyor ya da rsi_zone kanondan gecmiyor."
  echo "    Detay icin: python3 tools/indicator-panel-canon-check.py"
  echo "    Pozitif kontrol: python3 tools/indicator-panel-canon-check.py --ref 9a92c9d"
  FAIL=$((FAIL + 1))
fi

# 39. innerhtml-sibling-check (K-BT, CPO 22.09.2026) -- BIR innerHTML YAZIMI
# KARDES BIR BILESENI YOK ETMEMELI. `el.innerHTML = ...` kabin TUM cocuklarini
# siler; icinde JS'in baska yerde doldurdugu bir id varsa o bilesen DOM'dan
# kalkar ve dolduran kod SESSIZCE hicbir sey yapmaz (getElementById null doner,
# guard yuzunden hata da atilmaz). CANLI VAKA (22.09): "Hacim Profili" paneli
# #entryAnalysisGrid'in ucuncu cocuguydu; renderEntryAnalysis()'in "aktif
# sinyal yok" dali grid'i placeholder ile eziyordu -> BEKLE olan 138/217
# hissede panelin markup'i Ozet sekmesinde DOM'da bile yoktu, oysa `rvol` ve
# `signal_vol_ratio` 217/217 hissede DOLU. Hacim YON-BAGIMSIZ bir buyukluk
# (K-BO): sinyali olmayan hissede en anlamli oldugu yer orasiydi. Ayni sinif
# daha once iki kez P1 uretti (K-U pozisyon silme, K-AF marquee icerigi).
# Muafiyetler (dosya, KAP, COCUK) uclusudur -- kap bazli olsa kapi kendi
# bulgusuna kor kalirdi. Pozitif kontrol: 5 ihlal (hp* id'leri).
echo "39/73 innerhtml-sibling-check (K-BT: innerHTML kardes bileseni yok etmemeli)..."
if python3 tools/innerhtml-sibling-check.py; then
  echo "  ✓ innerhtml-sibling-check PASS"
else
  echo "  ✗ K-BT KIRIK: bir innerHTML yazimi, JS ile doldurulan bir kardesi kapsiyor"
  echo "    (ya da bir muafiyet bayatladi / bir sablon olculemedi)."
  echo "    Detay icin: python3 tools/innerhtml-sibling-check.py"
  echo "    Pozitif kontrol: python3 tools/innerhtml-sibling-check.py --ref 3ced203"
  FAIL=$((FAIL + 1))
fi

# ── 40: K-BU — GOSTERILEN SAYI INSAN-OKUR ETIKETTEN AYRISTIRILMAZ ──────────
# Backend bir gostergeyi hem ham sayi (`adx: 25.9`) hem de INSAN icin
# yuvarlanmis metin (`indicators.adx.label` = "ADX 26") olarak servis eder.
# /gundem'in kart render'i ikincisini parse edip `.toFixed(1)` ile basiyordu:
# islem kaybi kurtarmaz, yuvarlanmis degere SAHTE ondalik ekler ("26,0").
# AYNI SAYFANIN SSR makrosu "25,9" basiyordu ve grid innerHTML ile bastan
# yazildigi icin CSR, SSR'in DOGRU sayisini YANLISLA EZIYORDU.
# CANLI (22.09, /api/gundem): 7/7 kartta SSR != CSR; ISDMR 25,9->26,0 ve
# BIMAS 25,1->25,0 urunun ADX 25 ESIGINE cakisiyor.
# ⛔ K-BR kapisi (37) bunu GORMEDI: o kapi `|int`/`Math.round`/`.toFixed(0)`
# YAZIMLARINI arar; buradaki kayip backend'de olmus, frontend'e hazir
# yuvarlanmis METIN olarak gelmisti. Bir kanon kapisi yalnizca ARADIGI
# KANALDA korur (K-BO token kapisi <-> K-BS sinif-adi kanali ile ayni aile).
# Muaf: `.value` (form girdisi) ve `dataset`/`data-*` (makine-okur tasiyici).
echo "40/73 label-derived-number-check (K-BU: sayi etiketten ayristirilmaz)..."
if python3 tools/label-derived-number-check.py; then
  echo "  ✓ label-derived-number-check PASS"
else
  echo "  ✗ K-BU KIRIK: kullaniciya gosterilen bir sayi, sunum metninden"
  echo "    (label/textContent/innerHTML) geri ayristiriliyor."
  echo "    Kanon: ham alani oku (s.adx), bicimi bp-format.js bpIndNum'dan al."
  echo "    Detay icin: python3 tools/label-derived-number-check.py"
  echo "    Pozitif kontrol: python3 tools/label-derived-number-check.py --ref 422db78"
  FAIL=$((FAIL + 1))
fi

# ── 41: K-BV — PARA OLCEGI KISALTMASI TEK KANONDAN GELIR ──────────────────
# AYNI buyukluk sitede UC ayri yazimla basiliyordu; ikisi AYNI SEKMEDE:
#   /hisse Temel kartlari + /karsilastir -> "197,98 Mrd₺" (2 ondalik, boslukSUZ)
#   /hisse Temel sekmesi Ciro/Net Kar grafigi -> "180,4 Mr ₺" (1 ondalik,
#     boslukLU, T basamagi YOK) -- ayni kartin 40 piksel altinda
#   /portfolio -> "M₺"/"K₺", milyar ve trilyon basamagi HIC yok
#     (1,2 milyarlik portfoy "1.200,00 M₺" yaziyordu)
# CANLI (22.09, 7/7 hisse): ASELS karti "197,98 Mrd₺" <-> grafik "180,4 Mr ₺";
# TUPRS kartta "1,03 T₺" iken grafik trilyonu bilmedigi icin "916,8 Mr ₺".
# Grafikteki metin aria-label/data-tip'e de gidiyordu: ekran okuyucu "Mr" duyar.
# ⛔ 49. ders: kapi YAZIMA degil DEGERIN KAYNAGINA bagli -- A deseni olcek
# BOLMESINI (1e6/1e9/1e12) arar, B deseni backend'in zaten olcekledigi
# durumda elle yazilan birim dizgesini. HTML'de yalnizca <script> taranir,
# metodoloji.html'deki "5 Mn ₺" PROZA ihlal degildir.
echo "41/73 money-scale-canon-check (K-BV: para olcegi kisaltmasi tek kanon)..."
if python3 tools/money-scale-canon-check.py; then
  echo "  ✓ money-scale-canon-check PASS"
else
  echo "  ✗ K-BV KIRIK: para olcegi (Mn/Mrd/T) ikinci bir yerde olceklendi"
  echo "    ya da birim kisaltmasi elle yazildi."
  echo "    Kanon: bp-format.js bpMoneyCompact(v, {sym, frac})"
  echo "    Detay icin: python3 tools/money-scale-canon-check.py"
  echo "    Pozitif kontrol: python3 tools/money-scale-canon-check.py --ref 26ed4f1"
  FAIL=$((FAIL + 1))
fi

# -- 42: K-BW -- SATIR-ICI `style=` ICINDE CIPLAK RENK OLAMAZ ---------------
# Rengi denetleyen IKI kapi vardi ve `#ff7875` IKISININ DE ARASINDAN gecti:
#   style-guard      -> yalniz static/css/*.css
#   js-palette-check -> JS dosyalari + sablonlarin <script> bloklari
# templates/hisse.html:139 ise UCUNCU kanaldi -- HTML attribute'u:
#   <span style="color:#ff7875">(BLACK DOWN TRIANGLE) Bozuldu</span>
# `#ff7875` tokens.css'te HIC YOK (kanonik --bp-sat = #f85149) ve bu rozet
# CANLI 72/217 hisse sayfasinda basiliyordu; ayni sayfadaki diger her SAT
# yuzeyi token'dan geliyordu. Ayni taramada 2 ihlal daha cikti:
# hisse.html:3827 `#b8b8c0` (kardes satir K-P'de --bp-text2'ye gecmisti,
# bu satir atlanmis) ve _analytics.html:62 KVKK kabul dugmesi `#0e0e12`
# (token'in kopyasi; blogun geri kalani zaten var(--x,#yedek) yaziyordu).
echo "42/73 inline-style-hex-check (K-BW: satir-ici renk token'dan gelir)..."
if python3 tools/inline-style-hex-check.py; then
  echo "  ✓ inline-style-hex-check PASS"
else
  echo "  ✗ K-BW KIRIK: sablon satir-ici style= icinde ciplak renk var."
  echo "    Kanon: var(--bp-x) ya da var(--bp-x, #yedek)."
  echo "    Detay icin: python3 tools/inline-style-hex-check.py"
  echo "    Pozitif kontrol: python3 tools/inline-style-hex-check.py --ref 4dc34f6"
  FAIL=$((FAIL + 1))
fi

# -- 43: K-BX -- TEMEL ANALIZ KARTI: BIRIM VE BAND SOZLESMESI --------------
# `/hisse` Temel sekmesindeki kart ayni sayiyi UC yerde kullanir: gosterilen
# METIN, RENK ve alt ETIKET. 22.09'da bu ucluden ikisi iki AYRI sinifta
# koptu:
#   BIRIM -- yfinance `debtToEquity` YUZDE doner (THYAO 89,39 = 0,89x;
#     OTKAR 869,17 = 8,69x). Kart yuzdeyi dogrudan "x" (kat) basip esikleri
#     (2 / 1) ORAN gibi uyguluyordu. CANLI: D/E dolu 94 hissenin 85'i
#     kirmizi "Yuksek"; dogru cevrimde 80'i yesil "Dusuk" -- kart borcsuz
#     sirketleri asiri borclu ilan ediyordu. Backend'in kendi akil-sagligi
#     tavani da bunu soyluyordu: _FUND_SANITY ust siniri 2000 (2000 KAT yok,
#     %2000 = 20x var).
#   BAND -- Beta kartinda RENK 0,7/1,3 esigini, ETIKET 1,0 esigini
#     kullaniyordu: canli 62 beta kartinin 11'inde renk ile yazi farkli
#     bandi soyluyordu (KAREL 0,99 notr renk + "Dusuk volatilite").
# Kapi alan ADINA bakmaz: (A) kartin kendi birim iddiasi (`x`/soneksiz)
# ile backend'in uretebilecegi tavani karsilastirir, (B) renk ve etiket
# esik KUMELERININ esitligini arar.
echo "43/73 fundamental-card-band-check (K-BX: temel kart birim/band)..."
if python3 tools/fundamental-card-band-check.py; then
  echo "  ✓ fundamental-card-band-check PASS"
else
  echo "  ✗ K-BX KIRIK: temel analiz kartinda birim ya da band sapmasi var."
  echo "    Kanon: metin = renk = etiket ayni ifade ve ayni band kumesi."
  echo "    Detay icin: python3 tools/fundamental-card-band-check.py"
  echo "    Pozitif kontrol: python3 tools/fundamental-card-band-check.py --ref e7cb2cf"
  FAIL=$((FAIL + 1))
fi

# -- 44: K-BY -- SABLONDA PALET DISI RENK (KANAL BAGIMSIZ) ------------------
# Sitede rengi denetleyen UC kapi vardi ve her biri BIR kanali taniyordu:
#   style-guard (css govdesi) · js-palette-check (<script>) ·
#   inline-style-hex-check (satir-ici `style=`).
# 22.09 olcumu: hisse.html hero kartinin rengi UCUNDE DE degildi. Once bir
# Jinja degiskenine yaziliyordu -- {% set _hc='#16a34a' %} -- ve ancak 40
# satir asagida style="--hero-accent:{{ _hc }}" ile enterpole ediliyordu;
# kapi 42 orada yalniz `{{ _hc }}` gorur. DOKUZ hex, hicbiri tokens.css'te
# yok, CANLI 217 hisse sayfasinin 79'unda basiliyordu -- ayni sayfanin her
# diger AL/SAT yuzeyi --bp-al/--bp-sat okurken. Ayni tur BESINCI kanali da
# buldu: index.html hero-art'inda SVG sunum oznitelikleri
# (fill="#ff37d8", stop-color="#1fe0ff") -- ustelik AYNI SVG'nin 3 dairesi
# zaten fill="var(--bp-art-violet)" idi, oge YARI goc etmisti.
# ⛔ 52. ders geregi bu kapi KANAL SAYMAZ. Kural tek ve yapisal: yorumlar
# cikarildiktan sonra sablonda gecen her renk hex'i tokens.css'te TANIMLI
# olmalidir. Muafiyetler de yapisal: akromatik (r==g==b) notrler ve baska
# sirketin marka rengi. Token DEGERININ yedek olarak yazilmasi
# (`var(--bp-border,#2a2a2c)`, `_tok('--bp-al','#00e290')`) K-BG'de bilerek
# kurulan kalip; kapsam disi.
echo "44/73 template-color-channel-check (K-BY: renk kanaldan bagimsiz token'dan gelir)..."
if python3 tools/template-color-channel-check.py; then
  echo "  ✓ template-color-channel-check PASS"
else
  echo "  ✗ K-BY KIRIK: sablonda paletin disindan bir renk uretiliyor."
  echo "    Kanon: renk YALNIZ tokens.css'ten gelir -- kanal fark etmez."
  echo "    Detay icin: python3 tools/template-color-channel-check.py"
  echo "    Pozitif kontrol: python3 tools/template-color-channel-check.py --ref 5053319"
  FAIL=$((FAIL + 1))
fi

# ── K-BZ (22.09): KOKEN ROZETI, ALTINDAKI ICERIGIN KOKENINI SOYLER ──────────
# Canli 22.09 /hisse/<T> "AI Analiz": `#sigExplainBadge` SSR'da kosulsuz
# "Gemini AI" yaziyordu; altindaki govde ise SSR'in KURAL-TABANLI 3-kriter
# checklist'iydi. Yani yanit gelene kadar -- ve hata / "veri yok" dallarinin
# TAMAMINDA -- rozet yapay zeka iddia ederken metin bir Python sablonuydu.
# Kapi yazimi degil KENDISINI arar (ders 52): saglayici adi gecen her SSR
# metni bulunur, JS tarafindan yeniden yazilabiliyor VE SSR'da gorunuyorsa
# ihlaldir. `#newsSource` ayni sayfada ayni saglayici adini tasir ama kabi
# `display:none` oldugu icin ihlal DEGIL -- muafiyet degil, olcum sonucu.
echo "45/73 provenance-badge-check (K-BZ: koken rozeti <-> govdenin gercek kaynagi)..."
if python3 tools/provenance-badge-check.py; then
  echo "  ✓ provenance-badge-check PASS"
else
  echo "  ✗ K-BZ KIRIK: koken rozeti, yanit gelmeden saglayici adi iddia ediyor."
  echo "    Detay icin: python3 tools/provenance-badge-check.py"
  echo "    Pozitif kontrol: python3 tools/provenance-badge-check.py --ref 9c63d9f"
  FAIL=$((FAIL + 1))
fi

# ── K-CA (22.09): GORUNEN BIR ORAN, YANINDA YAZAN SAYIYLA AYNI KAYNAKTAN GELIR ─
# Canli 22.09: /hisse "Risk / Ödül" kartinin CUBUGU `|cur-sl|` vs `|tp2-cur|`
# ile ciziliyordu; TP2 = cur + 3 x risk oldugu icin oran cebirsel olarak HER
# ZAMAN 3,0 -- rr_signal'i olan 55 hissenin 55'inde bar tipatip 25%/75%. Ayni
# kartta, cubugun HEMEN ALTINDA, ayni etiket altinda rr_signal "13,25x" (TKFEN)
# / "0,34x" (MAVI) yaziyordu. /karsilastir ise "Risk/Ödül (R/R)" satirini
# `rr_ratio`dan okuyordu: o alan 79/79 hissede tipatip 2.0, yani karsilastirma
# sayfasinda hicbir seyi ayirt etmeyen bir sutun. CPO-DEV2-045 ayni totolojiyi
# `rr_now` SAYISINDAN silmisti, BARI ve bu satiri birakmisti (ders 56).
# Kapi uc ekseni birden olcer: (A) sabit alanin tuketimi, (B) cubuk genisliginin
# bagimsiz hesabi, (C) 1:N ankrasi olmadan basilan oran.
echo "46/73 rr-canon-check (K-CA: cubuk da sayi da rr_signal'den)..."
if python3 tools/rr-canon-check.py; then
  echo "  ✓ rr-canon-check PASS"
else
  echo "  ✗ K-CA KIRIK: gorunen R/R, yaninda yazan sayidan baska bir seyi gosteriyor."
  echo "    Detay icin: python3 tools/rr-canon-check.py"
  echo "    Pozitif kontrol: python3 tools/rr-canon-check.py --ref 6c4eac2"
  FAIL=$((FAIL + 1))
fi

# ── K-CB (22.09): BEYAN EDILEN PENCERE, GOSTERILEN VERIYLE AYNI OLMALI ──────
# Canli 22.09: /hisse grafiginin GORUNEN sure etiketi bar sayisindan DINAMIK
# turetiliyordu ("2 Yıl" / "N İşlem Günü") ve kodun yanindaki not "yanlis bir
# '2 Yil' iddiasi hicbir an ekranda durmaz" diyordu -- ama AYNI ogenin
# `aria-label`i SSR'da SABIT "2 yıl" yaziyor, hic guncellenmiyordu. DSTKF
# (405 bar / 592 takvim gunu): goren kullanici "405 İşlem Günü", ekran
# okuyucu "2 yıl". /portfolio'da ayni hata dizeyle kurulan adin icindeydi:
# "Son 30 gün" -- veri `ohlc.slice(-30)`, yani 30 SEANS (~42 takvim gunu) ve
# AYNI dilim /hisse'de "Son 30 seans" diye etiketleniyordu. Ayrica RSI bolge
# adi UC yazimdaydi (frontend "Nötr bölge" · backend "Nötr Bölge (RSI 45-60)"
# · /metodoloji bu adi HIC bilmiyor, kosulsuz "İdeal Giriş Penceresi" diyordu;
# canli 46 hissenin 45'i AL DEGIL). Kapi dort ekseni olcer: (A) oznitelikte
# donmus pencere iddiasi, (B) bar esiginin ikinci kopyasi, (C) belgelenmemis
# bolge adi, (D) dizeyle kurulan erisilebilir adda literal pencere.
echo "47/73 window-claim-check (K-CB: pencere beyani <-> cizilen veri)..."
if python3 tools/window-claim-check.py; then
  echo "  ✓ window-claim-check PASS"
else
  echo "  ✗ K-CB KIRIK: ekranda yazan pencere/bolge adi, gosterilen veriyle ayni degil."
  echo "    Detay icin: python3 tools/window-claim-check.py"
  echo "    Pozitif kontrol: python3 tools/window-claim-check.py --ref 4bd1ea0"
  FAIL=$((FAIL + 1))
fi

# 48. export-parity-check (K-CC, CPO 22.09.2026) -- INDIRILEN DOSYA,
# EKRANDAKI SAYIYI VERMELI. /tarama CSV'si "Hacim Orani"ni 1 ondalikla
# yaziyordu, ekran 2 ondalik basiyordu: 22.09 canli olcumde 217 hissenin
# 195'inde sayi FARKLI, 14 hisse sayfanin KENDI bandini (>=1,5 "Yuksek
# hacim") karsi tarafa geciyordu; vol_ratio TAM 0 olan 5 hissede falsy
# kontrol hucreyi BOSALTIYOR, "Giris Kalitesi" ham makine kodu (UZAK)
# basiyordu -- ekranda ayni deger "Kovalama". /portfolio K/Z %'si ekranda
# 1, CSV'de 2 ondaliktir ve ISARETSIZDIR. Dort eksen: P1 hassasiyet,
# P2 falsy-sifir, P3 `|| 0`, P4 ham makine kodu.
echo "48/73 export-parity-check (K-CC: disa aktarim <-> ekran ayni sayi/ad)..."
if python3 tools/export-parity-check.py; then
  echo "  ✓ export-parity-check PASS"
else
  echo "  ✗ K-CC KIRIK: indirilen dosya ekrandakinden baska bir sayi/ad veriyor."
  echo "    Detay icin: python3 tools/export-parity-check.py"
  echo "    Pozitif kontrol: python3 tools/export-parity-check.py --ref 00d37b9"
  FAIL=$((FAIL + 1))
fi

# 49. relative-time-anchor-check (K-CD, CPO 22.09.2026) -- "BUGUN"/"DUN"
# OKUYUCUNUN TAKVIMINDEN OKUNUR. /ozet'in hisse kartlari goreli yasi ARSIV
# gunune gore uretiyordu (`signal_age_text(historical_date)`, bug-hunt r27):
# 22.09 canli olcumde otomatik son-islem-gunu geri donusunde AYNI OGEDE
# "Bugün · 21.09.2026" yaziyordu -- 21 kart; /ozet/2026-09-18'de
# "Bugün · 18.09.2026" x7 ve "Dün · 17.09.2026" x4. Sayfanin geri kalani
# (baslik, "... olustu" cipi, ust bant, <title>, meta) arsiv modunda MUTLAK
# tarihe cevrilmisti, yalniz bu iki satir atlanmisti. Uc eksen: A1 goreli-yas
# filtresine referans-gun argumani, A2 referans-gun dalinda indexical sozcuk
# literali (sozcukler business_rules.SIGNAL_DATE_LABELS'tan okunur), A3 ayni
# yeniden-capalamanin JS yazimi (bpSignalDateLabel(..., ...)).
echo "49/73 relative-time-anchor-check (K-CD: goreli zaman <-> okuyucunun takvimi)..."
if python3 tools/relative-time-anchor-check.py; then
  echo "  ✓ relative-time-anchor-check PASS"
else
  echo "  ✗ K-CD KIRIK: \"Bugun/Dun\" okuyucunun bugunu disinda bir gune capalanmis."
  echo "    Detay icin: python3 tools/relative-time-anchor-check.py"
  echo "    Pozitif kontrol: python3 tools/relative-time-anchor-check.py --ref 7c7788f"
  FAIL=$((FAIL + 1))
fi

# 50. intraday-claim-check (K-CE, CPO 22.09.2026) -- MIMARI EOD-ONLY OLDUGU
# HALDE 6 YUZEY "GUN ICI"/"ANLIK" DIYORDU. /api/data CPO-1508/1512/1703 ile
# gunde TEK kez, kapanistan sonra yazilir; change_pct her zaman TAMAMLANMIS
# gunun kapanis-kapanis degisimidir. Site bunu /yasal ve /hakkinda'da yazili
# olarak BEYAN ediyor ("fiyatlar gercek zamanli DEGILDIR ... son kapanis") --
# ve ayni /hakkinda sayfasi 62 satir yukarida "anlik deger" vaat ediyordu.
# Canli ihlaller: anasayfa serit etiketi "Gün İçi En Çok Hareket Edenler"
# (AYNI SAYFA ayni alani "Son kapanışta ne oldu?" diye adlandiriyordu) +
# /portfolio meta/og/twitter x3 "anlık değer" + /hakkinda "anlık değer".
# Sozluk mimari olarak IMKANSIZ iddialardan olusur, muafiyet ANLAM kuralidir
# (ayni parcada "degildir/retire edildi/kaldirildi" varsa iddia degil beyandir).
echo "50/73 intraday-claim-check (K-CE: EOD-only mimaride gun-ici/canli iddia)..."
if python3 tools/intraday-claim-check.py; then
  echo "  ✓ intraday-claim-check PASS"
else
  echo "  ✗ K-CE KIRIK: EOD-only veriye gun-ici/gercek-zamanli iddia yapiliyor."
  echo "    Detay icin: python3 tools/intraday-claim-check.py"
  echo "    Pozitif kontrol: git show HEAD~1:templates/index.html > /tmp/pc.html && python3 tools/intraday-claim-check.py /tmp/pc.html"
  FAIL=$((FAIL + 1))
fi

# 51. blog-claim-check (K-CF, CPO 22.09.2026) -- YAPISAL BOSLUK: blog_content.py
# 7371 satir / ~130 makale tasiyor ama 68 kapidan YALNIZ style-guard.py onu
# aciyordu (o da salt renk icin). Sonuc, 22.09 canli olcumunde 13 ihlal:
#   * /metodoloji'de K-CB/CPO-1745 ile RETIRE EDILEN kanon blogda KOSULSUZ
#     yasiyordu ("RSI 45-60: İdeal Giriş Penceresi" -- urun bu adi artik
#     yalniz Guclu Trend sinyalinde basiyor, aksi halde "Nötr Bölge");
#   * evren sayisi 5 yerde 214'te donmustu (canli /api/data = 217);
#   * EOD-only urun "makro ticker bandi USD/TRY kurunu ANLIK gosterir" diyordu;
#   * var olmayan iki sey vaat ediliyordu: "/sinyal-performans" sayfasi (301 ->
#     /tarama, gecmis performans yok) ve ana sayfada "BIST30 filtresi" (hic yok);
#   * /gucu-yuksek "Güçlü Momentum" diye adlandiriliyordu (kanonik ad: Tarama).
# Besi de FAQPage JSON-LD'ye basiliyordu -- yani Google zengin sonuclarina.
# Olcum: dosya `ast` ile ayristirilir, YALNIZ string literalleri taranir (Python
# yorumlari otomatik disarida kalir, markdown `#` basliklari korunur -- 56. ders)
# ve kural CUMLE granulerliginde isler (koca makale govdesinde bir yerde gecen
# "Güçlü Trend" 40 satir asagidaki kosulsuz cumleyi muaf yapmasin -- 43. ders).
echo "51/73 blog-claim-check (K-CF: blog govdesi icerik-dogruluk kanonu)..."
if python3 tools/blog-claim-check.py; then
  echo "  ✓ blog-claim-check PASS"
else
  echo "  ✗ K-CF KIRIK: blog govdesi urunun kanonu/kapsami/sayfalariyla celisiyor."
  echo "    Detay icin: python3 tools/blog-claim-check.py"
  echo "    Pozitif kontrol: git show HEAD~1:blog_content.py > /tmp/pc_blog.py && python3 tools/blog-claim-check.py /tmp/pc_blog.py"
  FAIL=$((FAIL + 1))
fi

# 52. app-published-text-check (K-CG, CPO 22.09.2026) -- 76. DERSIN IKINCI
# UYGULAMASI: kapi 50 yalniz templates/, kapi 51 yalniz blog_content.py tarar.
# Oysa urunun kullaniciya BASTIGI metnin bir bolumu app.py'de yasiyor --
# e-posta govdeleri, e-posta KONU satirlari, SSS/JSON-LD ureteci ve AI prompt
# sozlugu. Bu kanal 51 kapinin HICBIRININ girdi kumesinde degildi ve 22.09
# olcumunde 17 ihlal tasiyordu:
#   * /profil kullaniciya "⭐ Sadece Hacim Onaylı" diye SECTIRIYOR, ayni
#     tercihten uretilen mail "💎 Premium Sinyal Değişimi" KONUSUYLA geliyordu;
#   * rozet 💎, urunun kendi /metodoloji sayfasinda "Yüksek Skor" (Teknik Güç
#     Skoru 70+) demek ve o sayfa "⭐ Hacim Onaylı ile KARISTIRILMAMALI" diye
#     acikca uyariyor -- mail tam da o karisikligi ogretiyordu;
#   * "Premium" sozcugu CPO-DEV2-053/055 ile paywall cagrisimi yuzunden emekli
#     edilmisti, site uydu, e-posta kanali eski sozlukte dondu (10 yerde);
#   * hos geldin maili "2-yıllık backtest performans raporu" vaat ediyordu --
#     /backtest ve /sinyal-performans 301 ile /tarama'ya gider, /hakkinda bu
#     ozelligi "🔚 retire edildi, güncel bir arayüzü yok" diye isaretliyor;
#   * SSS JSON-LD skoru "sinyal skoru" diye adlandiriyordu (kanon: Teknik Güç
#     Skoru -- ayni sayfa 4 yerde oyle yaziyor).
# Olcum: `ast` ile YALNIZ string literalleri (77. ders); docstring'ler ve
# serbest string bloklari YAYIMLANMADIGI icin haric tutulur, boylece yorum
# bagisikligi bedavaya gelir. Veri anahtarlari (only_premium, mail_pref
# degeri "premium") tam-esitlikle muaf -- beyaz liste anahtari satir numarasi
# DEGIL, dizenin kendisidir.
echo "52/73 app-published-text-check (K-CG: app.py yayimlanan metin kanonu)..."
if python3 tools/app-published-text-check.py; then
  echo "  ✓ app-published-text-check PASS"
else
  echo "  ✗ K-CG KIRIK: app.py'nin kullaniciya bastigi metin kanon disi."
  echo "    Detay icin: python3 tools/app-published-text-check.py"
  echo "    Pozitif kontrol: mkdir -p /tmp/pc52/tools; git show HEAD~1:app.py > /tmp/pc52/app.py; cp tools/app-published-text-check.py /tmp/pc52/tools/; python3 /tmp/pc52/tools/app-published-text-check.py"
  FAIL=$((FAIL + 1))
fi

# 53. static-js-text-check (K-CH, CPO 22.09.2026) -- 76. DERSIN UCUNCU
# UYGULAMASI + 83. DERS. Kapi 50 yalniz `templates/`, 51 yalniz
# `blog_content.py`, 52 yalniz `app.py` okuyor; glyph/legal/nav kanon kapilari
# da yalniz `templates/`. Yani TARAYICIYA INEN paylasilan JS (`static/**/*.js`)
# hicbir metin kapisinin girdisinde DEGILDI. Sonuc: "Premium" 22.08'de emekli
# edildi, sablonlardan temizlendi, e-posta kanali K-CG'de kapatildi -- ve
# sozcuk `static/learning-mode.js` icinde yasamaya devam etti; urunun
# yayimlanan TUM metninde kalan TEK canli ornek oydu. Ayni dosya RSI 45-60
# bandini KOSULSUZ "ideal giris penceresi" diye tanimliyordu (canli: bantta
# 46 hisse, 45'i Guclu Trend DEGIL -> ekran "Notr Bolge" derken sozluk tersini
# soyluyordu).
# Olcum: elle yazilmis JS tarayicisi ile YALNIZ dize literalleri (77. ders) --
# yorumlar ve regex literalleri atilir, cunku repo'nun olcum notlari emekli
# terimleri bilerek anar. Veri anahtarlari tam-esitlikle muaf (K-BD dersi).
echo "53/73 static-js-text-check (K-CH: paylasilan JS yayimlanan metin kanonu)..."
if python3 tools/static-js-text-check.py; then
  echo "  ✓ static-js-text-check PASS"
else
  echo "  ✗ K-CH KIRIK: static/*.js'in kullaniciya bastigi metin kanon disi."
  echo "    Detay icin: python3 tools/static-js-text-check.py --verbose"
  echo "    Pozitif kontrol: mkdir -p /tmp/pc53/tools/../static; git show HEAD~1:static/learning-mode.js > /tmp/pc53/static/learning-mode.js; cp tools/static-js-text-check.py /tmp/pc53/tools/; python3 /tmp/pc53/tools/static-js-text-check.py"
  FAIL=$((FAIL + 1))
fi

# K-CI (22.09) -- 76/83. DERSIN DORDUNCU UYGULAMASI: PWA MANIFEST'I
# `static/manifest.json` 53 kapidan YALNIZ BIRI tarafindan okunuyordu
# (cachebust-check) -- o da metni degil ikon hash'ini. Oysa manifest'in metni
# kullaniciya ISLETIM SISTEMI KABUGUNDA ulasir: yukleme diyalogu, ana ekran
# adi, uzun basinca acilan kisayol menusu. 3 ihlal bulundu:
#   1) "Güçlü Trend Sinyalleri" kisayolu /?filter=al'a gidiyordu -- `filter`
#      diye bir parametre urunde HIC var olmadi (canli: /?filter=al ile /
#      byte-ozdes). Gercek hedef /tarama?signal=AL: olculdu 7 satir %100 AL.
#   2) orientation:"portrait-primary" -- WCAG SC 1.3.4; ayrica shared.css'in
#      K-AY yatay blogunu (olculdu: 812x375'te header relative, alt nav 52px)
#      yuklu kullanici icin ULASILAMAZ kiliyordu.
#   3) /ozet kisayolu "Bugünkü sinyal özeti" derken sayfa "Dün · 21.09.2026".
# ⛔ KANAL FARKI: sablonda "Bugün" Jinja ile tazelenebilir (K-CD'nin cozumu);
#    manifest STATIK JSON -- orada indexical sozcuk hicbir kosulla kurtarilamaz.
echo "54/73 manifest-text-check (K-CI: PWA manifest yayimlanan metin + URL sozu)..."
if python3 tools/manifest-text-check.py; then
  echo "  ✓ manifest-text-check PASS"
else
  echo "  ✗ K-CI KIRIK: PWA manifest'i kanon disi metin ya da tuketicisiz URL tasiyor."
  echo "    Detay icin: python3 tools/manifest-text-check.py --verbose"
  echo "    Pozitif kontrol: git stash -- static/manifest.json && git checkout 8ff9ad5 -- static/manifest.json && python3 tools/manifest-text-check.py  # 3 ihlal beklenir (R1/R2/R4)"
  FAIL=$((FAIL + 1))
fi

# K-CJ (22.09) -- 76/83. DERSIN BESINCI UYGULAMASI: TARAYICI/AI-MOTOR KANALI
# /robots.txt · /llms.txt · /humans.txt · /security.txt ve sablonlardaki 27
# JSON-LD blogu 54 kapidan HICBIRI tarafindan okunmuyordu. Bu kanalin
# okuyucusu insan degil MAKINE (Googlebot, GPTBot, ClaudeBot, PerplexityBot,
# ve JSON-LD'yi HTML govdesinden daha guvenilir sayan cevap motorlari) --
# buradaki bir yalan kullaniciya siteyi HIC ACMADAN once ulasir. 4 ihlal:
#   1) robots.txt: `Disallow: /admin/` SADECE `User-agent: *` grubundaydi.
#      REP (RFC 9309 §2.2.1) bir tarayiciya YALNIZ en ozel eslesen grubu
#      uygulatir -- 13 adli grup (Googlebot/Bingbot/Yandex/GPTBot/ClaudeBot/
#      PerplexityBot dahil) o satiri HIC gormuyordu. Kural VARDI, uygulandigi
#      kume yanlisti.
#   2) robots.txt: `Crawl-delay: 5` dosyanin SONUNDA, `User-agent: DotBot` +
#      `Disallow: /` grubunun icindeydi. Yorumu genel niyet ("for politeness")
#      diyor, gruplama satir sirasina gore oldugu icin direktif yalnizca
#      DotBot'a aitti -- ve o grup zaten tumden bloke, yani ISLEVSIZDI.
#   3) humans.txt: "açık kaynaklı metodoloji" -- agacta tek bir kamuya acik
#      depo baglantisi yok. /metodoloji kurallari YAYINLIYOR: bu "seffaf"tir,
#      "acik kaynak" DEGILDIR. Ayni cumlenin "Backtest ile HER ZAMAN
#      dogrulanan" mutlagi da /yasal ile celisiyordu.
#   4) humans.txt: `Components: ... Chart.js` -- olculdu, urunde 0 eslesme
#      (grafik katmani tumuyle lightweight-charts). Gecis artigi.
# ⛔ 84. DERSIN TEKRARI: kapinin ILK yazimi R3 desenini "acik kaynak" diye
#    yazdi ve gercek ihlali ("açık kaynaklı") KACIRDI -- `tr_fold` yalniz
#    i/I ailesini katlar, ç/ğ/ö/ş/ü KALIR. Pozitif kontrol olmasa kapi
#    bos "OK" derdi. Es-yazim taranmadan bir dedektor dogrulanmis sayilmaz.
echo "55/73 crawler-channel-check (K-CJ: robots/llms/humans/security + JSON-LD)..."
if python3 tools/crawler-channel-check.py; then
  echo "  ✓ crawler-channel-check PASS"
else
  echo "  ✗ K-CJ KIRIK: tarayici/AI-motor kanali kanon disi iddia ya da olu kural tasiyor."
  echo "    Detay icin: python3 tools/crawler-channel-check.py --verbose"
  echo "    Pozitif kontrol: python3 tools/crawler-channel-check.py --ref bdc6013  # 16 ihlal beklenir (R1x13/R2/R3/R4)"
  FAIL=$((FAIL + 1))
fi

# K-CK (22.09) -- SITEMAP DE BIR IDDIA METNIDIR
# K-CJ tarayici kanalini kapatti ama o kanalin EN COK OKUNAN dosyasini
# (/sitemap.xml) disarida birakti: sitemap statik metin degil, URETILIYOR.
# Yine de her <url> girdisi iki ayri iddia tasir -- <changefreq> "ne siklikta
# degisir" ve <lastmod> "en son ne zaman degisti" -- ve bunlar birbirini VE
# mimariyi dogrulamak zorundadir. 3 ihlal (canli sitemap'te olculdu):
#   1) `/` -> changefreq "hourly". Mimari EOD-only (K-CE kanonu). Kapi 50
#      SABLONLARI tariyor, uretilen XML'i degil -- ayni gun-ici iddiasi bu
#      kanalda hayatta kalmisti.
#   2) /portfolio + /karsilastir: changefreq "monthly" ama lastmod varsayilani
#      `today` -- girdi HER GUN "bugun degisti" derken ayni satirda "ayda bir
#      degisir" diyordu. Canli: 413 URL'nin 238'i bugunun tarihini tasiyordu.
#      Google guvenilmez lastmod'da alani TUMDEN yok sayar; yani celiski
#      gercekten gunluk degisen 217 /hisse/* girdisinin sinyalini de zehirliyordu.
#   3) /bilanco-takvimi + /temettu-takvimi: ayni celiski, ama burada DOGRU
#      taraf lastmod'du (yuk her EOD turunda yeniden uretiliyor) -- "weekly"
#      duzeltildi.
echo "56/73 sitemap-claim-check (K-CK: changefreq <-> lastmod <-> EOD mimarisi)..."
if python3 tools/sitemap-claim-check.py; then
  echo "  ✓ sitemap-claim-check PASS"
else
  echo "  ✗ K-CK KIRIK: sitemap girdisi kendi tazelik iddiasiyla ya da mimariyle celisiyor."
  echo "    Detay icin: python3 tools/sitemap-claim-check.py --verbose"
  echo "    Pozitif kontrol: python3 tools/sitemap-claim-check.py --ref e7a9221  # 6 ihlal beklenir (R1 + R2x5)"
  echo "                     python3 tools/sitemap-claim-check.py --ref 4d9af15  # 1 ihlal beklenir (R5)"
  FAIL=$((FAIL + 1))
fi

# K-CL (22.09) -- <head> META KANALI + OG GORSELI
# 56 kapinin hicbiri `<head>` icindeki META DEGERLERINI ve `/og-image.*`
# rotalarinin CIZDIGI METNI bir kanal olarak okumuyordu. Oysa <head> urunun
# EN GENIS DAGITIMLI metnidir (Google snippet, WhatsApp/X/LinkedIn onizleme
# karti, AI motorlarinin ozet girdisi) ve og:image bir METIN YUZEYIDIR.
# 4 ihlal (canli olculdu 22.09 09:3x):
#   1) Her iki og-image rotasi "Algoritmik, ücretsiz, canlı güncelleme"
#      diyordu. Mimari EOD-only; blog_content.py:919 SSS'i AYNEN "gün içi
#      canlı takip sunmaz" diyor -- urun kendi SSS'iyle celisiyordu.
#      CIFT KORLUK: yanlis kanal (kapi 50 yalniz .html tarar) VE yanlis
#      desen (kapi 50'nin RE_CANLI'si "canlı güncelleme"yi hic almaz).
#   2) `216` sayisinin altinda "BIST100 HİSSE". _og_image_stats() XU030
#      haric TUM evreni sayiyor; BIST100 100 hissedir. Etiket, saydigi
#      kumeden DAR bir endeksi adlandiriyordu (kanon: "BIST100 + ek hisseler").
#   3) Alt baslikta datetime.now() tarihi: gorsel "22.09.2026" yazarken
#      /api/data.updated_at "21.09.2026 18:22" idi -- gunun ~22 saatinde
#      yalan. Ustelik og:image URL'i versiyonsuz, platform karti URL'e gore
#      onbellekler: DOGRU tarih bile onbellekte kalici yalana doner (86. ders).
#   4) templates/hisse.html:17 keywords "... al sat" -- 217 hisse sayfasinda,
#      Ozan'in KALICI AL-SAT yasagi (09.09, SPK konumlanmasi). K3 yalniz 3
#      sabit ifade ariyor; " al sat," hicbirine uymuyordu.
# ⛔ 85/57. DERSIN TEKRARI: kapinin ILK yazimi og-image govdesini regex ile
#    ayristirdi ve @limiter.limit satirinda KESTI -> 0 dize, kapi "OK" dedi
#    ve HICBIR SEY olcmedi. Ayristirma `ast`e cevrildi, --verbose ayristirilan
#    dize sayisini basiyor. R5'in ilk yazimi da sentetigi YESIL GECIRDI
#    (iki farkli tuval uretiliyorken "ilan kumede var" diye) -- sertlestirildi.
echo "57/73 head-meta-check (K-CL: <head> meta kanali + og gorseli)..."
if python3 tools/head-meta-check.py; then
  echo "  ✓ head-meta-check PASS"
else
  echo "  ✗ K-CL KIRIK: <head> meta kanali ya da og gorseli kanon disi iddia tasiyor."
  echo "    Detay icin: python3 tools/head-meta-check.py --verbose"
  echo "    Pozitif kontrol: python3 tools/head-meta-check.py --ref ee2a473  # 7 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

echo "58/73 glossary-where-check (K-CM: sozlugun \"nerede gorulur\" vaadi)..."
if python3 tools/glossary-where-check.py; then
  echo "  ✓ glossary-where-check PASS"
else
  echo "  ✗ K-CM KIRIK: /metodoloji sozlugu urunde olmayan bir yuzeyi vaat ediyor."
  echo "    Detay icin: python3 tools/glossary-where-check.py --verbose"
  echo "    Pozitif kontrol: python3 tools/glossary-where-check.py --ref HEAD  # fix oncesi 3 ihlal"
  FAIL=$((FAIL + 1))
fi

# 59. K-CN (22.09) — "Teknik Güç Skoru"nun BILESEN IDDIASI + kosullu ad vaadi.
#   compose_score() kesin: ADX+gunluk hacim orani+Teyit+RSI. Supertrend/EMA
#   skora HIC girmez (onlar sinyalin YONUNU uretir). 22.09'da 4 yuzey celisti:
#   index hero "Supertrend, ADX ve EMA12/99'u tek bir Teknik Güç Skoru'nda
#   birlestiriyoruz"; hisse.html gauge "Supertrend + ADX + hacim teyidi"
#   (AYNI SAYFA 645'te dogru listeyi yaziyordu); index vitrin "hacim teyidi"
#   Hacim(25p)+Teyit(10p) iki bileseni tek ada eritiyordu; hisse.html:2856
#   RSI tooltip'i "45-60 ideal giris penceresi"ni KOSULSUZ yaziyordu — K-CH
#   ve CPO-1769 bu iddiayi iki kanalda kapatmisti ama bu kopya
#   `ideal giri\u015f` diye yazildigi icin iki kapi da dizeyi HIC GORMEDI.
# ⛔ POZITIF KONTROL KAPIYI DUZELTTI (85. dersin tekrari): kapinin ilk yazimi
#    HTML etiketlerini siliyordu, 4 bulgunun 3'u ise data-tip ATTRIBUTE'unda
#    yasiyordu -> --ref HEAD 4 yerine 1 ihlal buldu. Attribute metni artik
#    etiket silinmeden once ayri blok olarak cikariliyor.
echo "59/73 score-claim-check (K-CN: Teknik Güç Skoru bilesen iddiasi)..."
if python3 tools/score-claim-check.py; then
  echo "  ✓ score-claim-check PASS"
else
  echo "  ✗ K-CN KIRIK: skorun bilesen listesi compose_score() ile celisiyor."
  echo "    Detay icin: python3 tools/score-claim-check.py --verbose"
  echo "    Pozitif kontrol: python3 tools/score-claim-check.py --ref 29147f3  # 4 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 60. K-CO (22.09) — TESLIMAT/TEPKI ANINDALIGI + tercih adi paritesi.
#   Kapi 50 VERININ gun-ici olup olmadigini olcer ("anlik fiyat", "gercek
#   zamanli"). Urunun ikinci zamanlama sozu -- NE ZAMAN HABER ALACAKSIN --
#   59 kapinin hicbirinin sozlugunde yoktu. Mimari EOD-only: sinyal degisimi
#   gunde TEK kez, kapanis sonrasi EOD turunda tespit edilir (app.py:3973 /
#   4412, _eod_fetch_trigger_ready_after = 18:10 TR). Yani "aninda mail"
#   mimari olarak "gunde bir kez" demektir. K-CO'da 3 kanalda 6 yuzey:
#   /profil iki tercih etiketi, hosgeldin maili iki cumle (app.py),
#   /gizlilik tercih sayimi, /metodoloji "rozet bu gecisi ANINDA yansitir".
#   R2 ayrica "ayni is icin iki kanon" mercegi: kullanicinin /profil'de
#   GORDUGU dort tercih adi, tercihlerin sayildigi her yuzeyde ayni yazilmali
#   (/gizlilik "sadece premium" diyordu -- hicbir ekranda gecmeyen VERI
#   ANAHTARI nesirde tercih adi gibi sunulmustu).
# ⛔ POZITIF KONTROL KAPIYI 2 KEZ DUZELTTI (85. ders):
#    (a) `anında` kelime sinirsiz taranince "or|anında", "yan|ında",
#        "veritaban|ında" 3 sahte pozitif verdi -- Turkce "-ında" eki.
#    (b) R2'nin ilk yazimi her "(a,b,c)" grubunu sayim sandi: rgba(184,195,
#        255,0.06) sahte pozitifti. Sayim artik >=3 HARFLI oge ister.
echo "60/73 delivery-timing-claim-check (K-CO: teslimat anindaligi vaadi)..."
if python3 tools/delivery-timing-claim-check.py; then
  echo "  ✓ delivery-timing-claim-check PASS"
else
  echo "  ✗ K-CO KIRIK: urun EOD-only mimaride 'aninda' teslimat vaat ediyor."
  echo "    Detay icin: python3 tools/delivery-timing-claim-check.py --verbose"
  echo "    Pozitif kontrol: python3 tools/delivery-timing-claim-check.py --self-test"
  FAIL=$((FAIL + 1))
fi

# KAPI 61 — K-CP (22.09): sekme/panel gorunurlugunde TEK KANON.
#   /hisse'de UC yer ayni karari veriyordu: applyTab'in `data-tab-content`
#   dongusu (gercek kanon) · ALL_PANELS/SHOW_FOR_TAB ID listesi (eksik ve
#   etkisiz ikinci kanon) · renderEntryAnalysis()'in "aktif sekme ozet degilse
#   DOKUNMA ve RETURN" erken cikisi. Ucuncusu, IIFE'nin applyTab(initial)'den
#   SONRA calistigini gormuyordu: ?tab=ai (ya da localStorage `bp_hisse_tab`)
#   ile acilan sayfada grid HIC doldurulmuyor, kullanici Ozet'e gecince bolum
#   goruntuye alinip BOS kaliyordu. Canli 22.09 BIMAS (AL + entry_quality):
#   ?tab=ozet -> eqBadge 45 / rrBar 228 / rrLevels 1632 karakter;
#   ?tab=ai -> Ozet'e gecince UCU DE 0.
# ⛔ POZITIF KONTROL KAPIYI 2 KEZ DUZELTTI (85. ders):
#    (a) R1 ilk yazimi `.style.display !== 'none'` OKUMASINI da yazim sandi.
#    (b) R1 ilk yazimi degiskeni 4 satirlik pencerede ariyordu: gercek uc
#        ihlali (2486/2499/2511) KACIRDI, buna karsilik kendi aciklama
#        YORUMUNDAKI ornegi ihlal sandi. Simdi yorumlar bosaltiliyor ve
#        degisken->ID bagi akis sirali izleniyor (--ref HEAD -> 7 ihlal).
echo "61/73 tab-visibility-canon-check (K-CP: sekme gorunurlugu tek kanon)..."
if python3 tools/tab-visibility-canon-check.py; then
  echo "  ✓ tab-visibility-canon-check PASS"
else
  echo "  ✗ K-CP KIRIK: sekme panelinin gorunurlugu applyTab disindan yonetiliyor."
  echo "    Detay icin: python3 tools/tab-visibility-canon-check.py --verbose"
  echo "    Pozitif kontrol: python3 tools/tab-visibility-canon-check.py --self-test"
  echo "    Regresyon ornegi: python3 tools/tab-visibility-canon-check.py --ref 87c165e  # 7 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# KAPI 62 — K-CQ (22.09): URL durumunun COK-YAZARLI korunumu.
#   /tarama'da URL'yi iki yazar yonetiyordu: `applyFilters()` filtre sozlugunden
#   SIFIRDAN kuruyordu (`location.pathname + '?' + params.toString()`), `tab` o
#   sozlukte olmadigi icin her cagri onu dusuruyordu; `switchTaramaTab()` ise
#   `set('tab')/delete('tab')` ile yaziyordu. Init akisi applyFilters -> sonra
#   searchParams.get('tab') oldugu icin sekme OKUNMADAN once siliniyordu.
#   Canli 22.09: `/tarama?tab=temel` -> URL `/tarama`, TEKNIK sekmesi acik
#   (aria-selected teknik:true), panelTemel display:none. Temel sekmesine
#   dogrudan baglanti (paylasilan link / yer imi) hic calismiyordu.
#   Enjeksiyon: yamasiz `?tab=temel&min_adx=30` -> ``; yamali -> `?tab=temel`.
# MUAFIYET ANLAM KURALIDIR (43. ders): "durum parametresi" olmak icin ad hem
#   searchParams.get ile OKUNMALI hem set/delete ile YAZILMALI -- boylece `?d=`
#   gibi salt-okunur/tek-yonlu parametreler kapsam disinda kalir.
echo "62/73 url-state-param-check (K-CQ: URL durum parametresi korunumu)..."
if python3 tools/url-state-param-check.py; then
  echo "  ✓ url-state-param-check PASS"
else
  echo "  ✗ K-CQ KIRIK: URL'yi sifirdan kuran yazar baska bir yazarin param'ini siliyor."
  echo "    Detay icin: python3 tools/url-state-param-check.py --verbose"
  echo "    Pozitif kontrol: python3 tools/url-state-param-check.py --self-test"
  echo "    Regresyon ornegi: python3 tools/url-state-param-check.py --ref 4ee0558  # 1 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# KAPI 64 (K-CS, 22.09) -- PAYLASILAN ADRES CUBUGU / FORM DURUMU TUR-GIDISI.
#   NOT: kapi 63 DEV1'e rezerve (CPO-1774'te teyit edildi), CPO 64'u aldi.
#   /tarama'da ayni adres cubugunu paylasan IKI form var, yalniz Teknik yaziyordu:
#   canli olcum 22.09 -> Temel'de Bant=Yesil + Sektor=Enerji + Sirala=Karlilik ile
#   2 sonuc kaliyor, adres hala `/tarama?tab=temel`; paylasilan link filtresiz aciliyor.
#   Ikinci bulgu: sekme-kor hidrasyon yabanci `sort` degerini <select>e yaziyordu,
#   eslesen <option> olmadigi icin tarayici degeri SESSIZCE "" yapiyor -- canli:
#   `/tarama?sort=temel_score` -> sortSel.value="", selectedIndex=-1, menu bos.
#   R1 yazma simetrisi · R2 <select> yutulmasi korumasi · R3 tur-gidis (yazilan
#   her parametre geri okunmali). MUAFIYET ANLAM KURALIDIR: kapsam "URLSearchParams
#   kurup fetch eden fonksiyon"; tek kuruculu sablonlar R1 disinda.
echo "63/73 form-url-state-check (K-CS: form durumu <-> adres cubugu tur-gidisi)..."
if python3 tools/form-url-state-check.py; then
  echo "  ✓ form-url-state-check PASS"
else
  echo "  ✗ K-CS KIRIK: bir formun durumu adrese yazilmiyor ya da geri okunmuyor."
  echo "    Pozitif kontrol: python3 tools/form-url-state-check.py --self-test   # 4/4 beklenir"
  echo "    Regresyon ornegi: python3 tools/form-url-state-check.py --ref d7c3782  # 3 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

echo ""
# KAPI 65 -- K-CT: adres cubugunun SAHIPLIGI (form-disi URL durumu).
#   Kapi 64'un kapsami "URLSearchParams kurup fetch eden fonksiyon" + "`.value`
#   ile forma yazan hidrator"; /sektor-harita durumunu FORM ALANIYLA degil
#   `aria-pressed` cipleriyle tasidigi icin o okuma yuzeyine HIC girmiyordu
#   (76/109. ders: dedektorun sekli yuzeyi secer).
#   Canli olculdu: Karsilastir'da 2 sektor sec -> Isi Haritasi'na don ->
#   adres `?tab=heatmap&s=Ulasim&s=Telekom` kaliyordu; o adres acildiginda
#   `loadSectors()` hic kosmadigi icin `_selected` [] geliyordu -- sayfa KENDI
#   URETTIGI olu derin baglantiyi paylastiriyordu. Ayrica tek sektorluk secim
#   adrese yaziliyor ama okuma esigine (`>= 2`) takilip geri okunmuyordu.
#   R1 tek yayimci · R2 tur-gidis · R3 `append` birikmesi · R4 sekme kapsami.
echo "64/73 url-state-owner-check (K-CT: adres cubugunun tek sahibi)..."
if python3 tools/url-state-owner-check.py; then
  echo "  ✓ url-state-owner-check PASS"
else
  echo "  ✗ K-CT KIRIK: adres cubugu iki yazarli ya da yazdigini geri okumuyor."
  echo "    Pozitif kontrol: python3 tools/url-state-owner-check.py --self-test  # 5/5 beklenir"
  echo "    Regresyon ornegi: python3 tools/url-state-owner-check.py --ref 5944a02  # 1 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

echo ""
# KAPI 66 -- K-CU: SUNUCUDA YASAYAN DURUMUN ISTEMCIDEKI SAHIBI.
#   Kapi 64/65 paylasilan yuzey olarak ADRES CUBUGUNU ele aliyordu; 111. dersin
#   ("paylasilan yuzeyin bir SAHIBI var mi") bir sonraki yuzeyi sunucuda tutulan
#   ve istemcide kopyasi bulunan durumdur (alarm/abonelik/tercih).
#   Canli olculdu (/hisse/<T> 🔔): dugmenin durumu YALNIZ localStorage'dan
#   okunuyordu, gercek e-posta alarmi sunucuda yasiyordu; `GET /api/user-alerts`
#   uretimde CANLI ama hicbir istemci yuzeyi onu OKUMUYORDU. Telefonda takibe
#   alinan hisse masaustunde "Bildirim al" gorunuyor, e-posta geliyor ama alarm
#   KAPATILAMIYORDU; tarayici verisi silinince kayit YETIM kaliyordu.
#   Harness pozitif kontrolu (eski kod): sunucuda kayitli + yerelde yok iken
#   tiklama POST gonderiyordu (kapatmak isterken ALIYORDU), ters durumda DELETE.
#   R1 yazma/okuma asimetrisi · R2 dallanma sahibi · R3 bos != bilinmiyor.
echo "65/73 client-server-state-owner-check (K-CU: sunucu durumunun istemcideki sahibi)..."
if python3 tools/client-server-state-owner-check.py; then
  echo "  ✓ client-server-state-owner-check PASS"
else
  echo "  ✗ K-CU KIRIK: sunucuda yasayan bir durum istemcide sahipsiz."
  echo "    Pozitif kontrol: python3 tools/client-server-state-owner-check.py --self-test  # 5/5 beklenir"
  echo "    Regresyon ornegi: python3 tools/client-server-state-owner-check.py --ref 2065e69  # 2 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

echo ""
# KAPI 67 -- K-CV: GIZLILIK BEYANI ILE GERCEK VERI AKISI ARASINDAKI KANON.
#   Kapi 66 "sunucuda yasayan durumun istemcideki SAHIBI var mi" diye soruyordu.
#   Ayni mercek bir kez daha kayar: kullanicinin verisi hakkinda SITENIN YAZILI
#   BEYANI da bir kanondur. Digerleri bozuldugunda UI yanlis gosterir; bu
#   bozuldugunda site KVKK kapsaminda YANLIS BEYANDA bulunur.
#   Canli olculdu (/gizlilik): "localStorage ... IZLEME LISTESI gibi yerel
#   ayarlari saklar ve SUNUCUYA GONDERILMEZ" deniyordu; oysa giris yapmis
#   kullanicida 🔔 dugmesi `POST /api/user-alerts/<T>` gonderiyor ve kayit
#   `subs[email]["alerts"][ticker]` olarak E-POSTAYLA ILISKILI sunucuda duruyor.
#   Ayni sayfa 20 satir yukarida "sunucuda saklanir" diyordu -> tek is icin iki
#   kanon. Ayrica izleme listesi YANLIS kanala (bulut sync) atfedilmisti (govde
#   `{positions}` -- izleme listesi orada yok), gercek kanal hic aciklanmamisti,
#   ve "tema tercihi" diye saklanan hicbir sey yoktu (site dark-only).
#   R1 toplama kanali beyan edilmeli (cift yonlu) · R2 yerel depo envanteri
#   cift yonlu + sunucuya aynalanan anahtar varken NITELENDIRILMEMIS mutlak
#   "sunucuya gonderilmez" iddiasi yasak.
echo "66/73 privacy-claim-flow-check (K-CV: gizlilik beyani <-> veri akisi)..."
if python3 tools/privacy-claim-flow-check.py; then
  echo "  ✓ privacy-claim-flow-check PASS"
else
  echo "  ✗ K-CV KIRIK: gizlilik metni gercek veri akisiyla celisiyor."
  echo "    Pozitif kontrol: python3 tools/privacy-claim-flow-check.py --self-test  # 5/5 beklenir"
  echo "    Regresyon ornegi: python3 tools/privacy-claim-flow-check.py --ref bd47ac4  # 5 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

echo ""
# KAPI 68 -- K-CW: TEKNIK GUC SKORU'NUN BANT KANONU (renk + ad).
#   Kapi 67 "yazili beyan <-> kod" kanonuna bakiyordu. Ayni mercek bir kez daha
#   kayar: SAYININ GORSEL SINIFLANDIRMASI da bir kanondur ve sessizce ikilesir.
#   Canli olculdu (22.09, getComputedStyle): ayni Teknik Guc Skoru anasayfada
#   ham skor esigine (70/56 -> --bp-al/--bp-volume/--bp-sat), /tarama ve
#   /hisse'de kanonik `tier` alanina (mor/periwinkle/notr) gore boyaniyordu --
#   ENERY 72 / TUPRS 62 / AYGAZ 49 / BIMAS 43'te 4/4 renk uyusmazligi. Dahasi
#   AL sinyalli hisselerin skoru SAT'in kanonik rengiyle (--bp-sat) boyaniyordu:
#   "en yuksek skorlar" izgarasinda 7 karttan 3'u KIRMIZI halka + YESIL "Guclu
#   Trend" rozeti tasiyordu. Bant ADLARI da ucuncu kanondu (lejant "Guclu/Orta/
#   Zayif" vs kanonik "Yuksek Skor/Orta Skor/rozetsiz") ve "Guclu" ayni sayfada
#   AL sinyalinin adiyla ayni kelime + ayni renkti (CPO-1682 cakismasi).
#   R1 tier dalinin rengi kanonik · R2 ham skor esiginden (56) bant rengi yasak
#   · R3 bant adi kanonik ("Guclu Sinyal" ve swatch yanindaki "Guclu/Zayif" yasak).
echo "67/73 score-band-canon-check (K-CW: skor bandinin renk+ad kanonu)..."
if python3 tools/score-band-canon-check.py; then
  echo "  ✓ score-band-canon-check PASS"
else
  echo "  ✗ K-CW KIRIK: ayni skor iki farkli bant sozlugune gore sunuluyor."
  echo "    Pozitif kontrol: python3 tools/score-band-canon-check.py --self-test  # 7/7 beklenir"
  echo "    Regresyon ornegi: python3 tools/score-band-canon-check.py --ref 9d347bf  # 4 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

echo ""
# NOT (K-CX, 22.09): asagidaki "n/68" etiketleri ILERLEME SAYACIDIR (kacinci
#   kapi calisti / toplam kac kapi var). Yorum basliklarindaki "KAPI 68 -- K-CW"
#   gibi numaralar ise KALICI KIMLIKTIR (commit mesajlari ve hafiza notlari onlara
#   atif yapar) ve yeniden numaralanmaz. Ikisi bilerek ayrilmistir: 63 kimligi
#   kullanimda degil, o yuzden en yuksek kimlik (69) toplam kapi sayisindan (68)
#   bir fazla. Bu satir yazilmadan once paydalar 60/61/62/68 diye dort kanona
#   bolunmustu ve operator "60/60 gecti" gorup 8 kapinin varligini kaciriyordu.
# KAPI 69 -- K-CX: DURUM DEGISINCE ERISILEBILIR KANAL DA GUNCELLENMELI.
#   K-AH (kapi 44 / title-tooltip-check.js) native `title=`i yasakladi: dokunmatikte
#   ve klavye ODAGINDA hic gosterilmez, kanonik kanal [data-tip] (bp-tooltip.js).
#   Ama o kapi `data-tip` VARLIGINI sahte-pozitif muafiyeti sayar -- TAZELIGINI
#   degil. Aciklamayi DURUMA gore yalnizca `el.title`a yazan bir eleman kapidan
#   gecer, fare kullanicisina guncel metni gosterir, dokunmatik/klavye
#   kullanicisina ACILIS metnini gostermeye devam eder.
#   Canli olculdu 22.09 (/hisse/ASELS, playwright, klavye odagi ile bp-tooltip'in
#   GERCEKTEN bastigi metin): buton "Takipte ✓" gosterirken tooltip "Sinyal
#   degisiminde bildirim al" diyordu -- YIKICI eylem (listeden cikarma) TERS
#   tarif ediliyordu. Bozuk portfoy kaydinda "kaydin okunamadi ... kurtarabilirsin"
#   uyarisi yalniz fare kanalindaydi, tooltip "Portfoye ekle / cikar" diyordu.
#   Ayrica 3 dal K-AH kosusunda HIC tetiklenmiyordu: anomali rozeti (canli
#   evrende flag 0/217), sinyal hata dali, AI kaynak rozeti (?tab=ai olmadan
#   display:none). Kusur yalniz CALISAN dalda gorunuyorsa, onu canli DOM'da
#   arayan kapi kordur -- bu yuzden kapi 69 STATIK olcer.
#   R1 runtime `el.title=` / setAttribute('title') yasak (document.title ve
#   iframe muaf; kanonik yazici `_bpTip`) · R2 ayni etikette title= + data-tip= yasak.
echo "68/73 dynamic-tip-canon-check (K-CX: durum degisince data-tip de guncellenmeli)..."
if python3 tools/dynamic-tip-canon-check.py; then
  echo "  ✓ dynamic-tip-canon-check PASS"
else
  echo "  ✗ K-CX KIRIK: aciklama fare-only `title` kanalina yaziliyor, [data-tip] donuk kaliyor."
  echo "    Pozitif kontrol: python3 tools/dynamic-tip-canon-check.py --self-test  # 9/9 beklenir"
  echo "    Kill-fix:        python3 tools/dynamic-tip-canon-check.py --kill-fix   # 2/2 beklenir"
  echo "    Regresyon ornegi: 0f9f2b6 agacinda 9 ihlal (hepsi hisse.html)"
  FAIL=$((FAIL + 1))
fi

# 69. canon-css-dup-check (KAPI 70 -- K-CY)
#   KANONIK CSS BLOGUNUN SAHIBI OLDUGU SECICIYI JS ENJEKTE ETTIGI CSS EZEMEZ.
#   Canli olculdu 22.09 (/tarama + /portfolio, getComputedStyle): ust nav'in
#   aktif ogesi `--bp-al` (AL SINYALI YESILI) ile boyaniyordu -- cunku
#   bp-search.js ayni nav stilinin ham-hex'li IKINCI kopyasini runtime'da
#   <head>'in sonuna enjekte ediyor, esit ozgullukte kaynak sirasindan
#   kazaniyordu. Sonuc: metin+zemin AL yesili, kenarlik brand, kanonik
#   Data-Art hapi (pill + rotate(-1deg)) 20 sayfanin HICBIRINDE render
#   edilmiyordu. Durum anahtari da ikilesmisti (`.active` vs `[aria-current]`).
#   Mevcut kapilarin HICBIRI goremezdi: style-guard/css-token-guard yalniz
#   static/css/*.css okur, js-palette-check ham hex SAYAR (tavanli) ama
#   "kimin kuralini eziyor" demez, da-override-check sablon->sablon bakar.
#   A = kanonigin DE bildirdigi kimlik ozelligini JS yeniden bildirmis
#   B = ayni taban icin ikinci durum anahtari. SIFIR sarti, ratchet YOK.
echo "69/73 canon-css-dup-check (K-CY: kanonik CSS'i JS enjeksiyonu ezemez)..."
if python3 tools/canon-css-dup-check.py; then
  echo "  ✓ canon-css-dup-check PASS"
else
  echo "  ✗ K-CY KIRIK: JS'ten enjekte edilen CSS kanonik bloğun kuralını eziyor."
  echo "    Pozitif kontrol: python3 tools/canon-css-dup-check.py --ref b4b8bcf  # 4 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 70. brand-wordmark-canon-check (KAPI 71 -- K-CZ)
#   MARKA SOZCUK-ISARETININ VURGULU YARISI TEK TOKEN'DAN BOYANIR.
#   Olculdu 22.09 (sablon+CSS envanteri): "Borsa|Pusula" wordmark'inin ikinci
#   yarisi UC AYRI kanondan boyaniyordu -- --bp-al (header SVG + footer, yani
#   20+ sayfanin HEPSI), --bp-brand (404/410/429/500; CPO-1558 ONCESI logo
#   gradyaninin rengi, goc orada yarim kalmis), --bp-accent-cyan (/hakkinda
#   hero; AYNI EKRANDA header logosu yesil, hero basligi camgobegi).
#   Ustelik --bp-al bu uründe ANLAM TASIR (AL sinyali): K-BO kurali "yon/sinyal
#   rengi yon tasimayan bir buyuklugu boyayamaz" -- marka adi yon tasimaz.
#   K-CY'nin (nav aktif ogesi --bp-al ile boyaniyordu) bir katman yukarisi.
#   SIFIR sarti, ratchet YOK. Cozulemeyen renk kaynagi da ihlaldir.
echo "70/73 brand-wordmark-canon-check (K-CZ: marka sozcuk-isareti tek token)..."
if python3 tools/brand-wordmark-canon-check.py; then
  echo "  ✓ brand-wordmark-canon-check PASS"
else
  echo "  ✗ K-CZ KIRIK: marka sözcük-işaretinin vurgulu yarısı kanon dışı bir renkten boyanıyor."
  echo "    Self-test:       python3 tools/brand-wordmark-canon-check.py --self-test  # 5/5 beklenir"
  echo "    Pozitif kontrol: python3 tools/brand-wordmark-canon-check.py --ref 8b3d756  # 7 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 71. py-palette-check (KAPI 72 -- K-DB)
#   PYTHON KANALINDAKI HER HAM HEX tokens.css'te BIR TOKEN DEGERI OLMALI.
#   22.09'a kadar UC palet kapisinin UCU de Python'u hic gormuyordu
#   (style-guard -> static/css, js-palette-check -> JS, template-color-channel
#   -> sablon). Oysa app.py urunun EN KAMUSAL gorselini uretiyor:
#   /og-image.png = 21 sablonun og:image'i (WhatsApp/X/Facebook onizlemesi)
#   VE manifest.json screenshots[wide] = Chrome PWA kurulum istemi.
#   Canli olcum 22.09 (1200x630 piksel sayimi): 12 renk, 11'i kanon disi --
#   kart bastan asagi GitHub koyu temasiyla boyaniyordu; tek esleseni
#   #f85149 (SAT) idi, yani AYNI GORSELDE yon cifti asimetrikti.
#   KRITIK AYRINTI: kanon kumesi okunurken tokens.css YORUMLARI SOYULUR --
#   7 renk YALNIZ yorumlarda geciyor (ornegin og kartinin grisi #8b949e);
#   soyulmazsa kapi kendi belgelendirmesiyle korlesirdi.
#   Muafiyet: tools/app_hex_exempt.json (e-posta govdesi, CPO-1782, DEV1
#   alani) -- DONDURULMUS, sadece kuculebilir; bayat girdi de FAIL verir.
echo "71/73 py-palette-check (K-DB: Python kanali <-> tokens.css, SIFIR sarti)..."
if python3 tools/py-palette-check.py; then
  echo "  ✓ py-palette-check PASS"
else
  echo "  ✗ K-DB KIRIK: Python kanalinda kanon disi ham hex (ya da bayat muafiyet / palet-token sapmasi)."
  echo "    Self-test:       python3 tools/py-palette-check.py --self-test  # 8/8 beklenir"
  echo "    Pozitif kontrol: python3 tools/py-palette-check.py --ref 5e864a7  # 33 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 72. index-ticker-channel-check (KAPI 73 -- K-DC)
#   "ENDEKS BIR HISSE DEGIL" KURALI HER KANALDA UYGULANIYOR MU?
#   app.py:11235 kurali 22.09'da DOKUZ ayri yerde ELLE tekrar ediliyordu ve
#   kanallarin bir kismi kurali hic gormemisti. En somut kusur 404 sayfasindaydi:
#   "Bunu mu demek istediniz?" kutusu ticker evrenini `/api/data`dan (217 kayit,
#   216'si hisse) kuruyordu -- kullanici "XU" yazinca urun ENDEKSI hisse diye
#   ONERIYORDU. Ustelik ayni fonksiyon iki evren donduruyordu: oturum onbellegi
#   yolu 216 (bp-search kanonu), fetch yolu 217. Kaynak `/api/stocks/list`
#   kanonuna gecirildi (289 KB -> 11,9 KB, `loading` yarisi yapisal olarak yok).
#   Envanter: tools/api_data_consumers.json -- /api/data fetch eden HER frontend
#   dosyasi `filtered` (endeks eler) ya da `keyed` (evren uretmez) diye
#   siniflandirilir; bildirilmemis YENI kanal da, artik fetch etmeyen BAYAT
#   girdi de FAIL verir.
#   Muafiyet: route_guard_exempt = /hisse/XU030 ve /karsilastir?tickers=...,XU030
#   (app.py mantigi = DEV1 alani, CPO-1783). DONDURULMUS, yalniz kuculebilir:
#   muaf route guard EKLERSE giris bayatlar ve kapi FAIL verir.
echo "72/73 index-ticker-channel-check (K-DC: endeks/hisse kanal envanteri)..."
if python3 tools/index-ticker-channel-check.py; then
  echo "  ✓ index-ticker-channel-check PASS"
else
  echo "  ✗ K-DC KIRIK: bir kanal endeks ticker'ini hisse gibi isliyor (ya da envanter bayat)."
  echo "    Self-test:       python3 tools/index-ticker-channel-check.py --self-test  # 12/12 beklenir"
  echo "    Pozitif kontrol: python3 tools/index-ticker-channel-check.py --ref 4905153  # 1 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 73. long-only-surface-check (KAPI 74 -- K-DE)
#   "TREND BOZULDU SINYALINDE GIRIS DEGERLENDIRMESI GOSTERILMEZ" KURALI
#   KANAL KANAL UYGULANIYOR MU? Kural /metodoloji'de YAZILI ("BorsaPusula
#   long-only bir urundur: 'ideal giris' ancak yonu yukari gosteren bir
#   sinyalin yaninda bir sey vaat eder" + "Trend Bozuldu sinyallerinde
#   hedef/stop yapisi ve R/R gosterilmez") ve /hisse (CPO-DEV2-052 #1, Ozan
#   karari) ile /karsilastir (_naForSat) uyguluyordu. 22.09 canli olcumu:
#   /tarama Sinyal=Trend Bozuldu filtresinde 72 satirin 35'i "Ideal"/"Iyi"
#   rozetini --bp-al YESILIYLE (rgb(0,226,144)) basiyordu; mobil kartta da 35;
#   CSV de oyle. Ayni hissenin kendi sayfasi ayni anda "somut giris/hedef
#   seviyesi bu sinyal tipinde gosterilmez" diyordu. /gundem karti da SAT'ta
#   "Kalite" + "R/R 1:N" basabiliyordu.
#   Envanter: tools/long_only_surfaces.json -- gated alanlari (entry_quality/
#   optimal_entry/rr_signal/tp1/tp2) EKRANA BASAN her kanal bildirilir;
#   bildirilmemis YENI kanal da, alani birakmis BAYAT girdi de FAIL.
#   Kapi komsuluk degil KAPSAM olcer: kapi ya ayni ifadede ya cevreleyen
#   blokta olmali (komsu satirdaki `isAl` kapi sayilmaz), yorumlar soyulur,
#   yerel degiskene alinan alan takma ad olarak izlenir.
echo "73/73 long-only-surface-check (K-DE: long-only sunum kapisi)..."
if python3 tools/long-only-surface-check.py; then
  echo "  ✓ long-only-surface-check PASS"
else
  echo "  ✗ K-DE KIRIK: bir kanal Trend Bozuldu sinyalinde giris/hedef/R-R vaadi basiyor (ya da envanter bayat)."
  echo "    Self-test:       python3 tools/long-only-surface-check.py --self-test  # 14/14 beklenir"
  echo "    Pozitif kontrol: python3 tools/long-only-surface-check.py --ref 8b3f67b  # 25 ihlal beklenir"
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
