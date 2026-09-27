#!/bin/bash
# ARSIV (C-39b, 27.09): eski 46 adimli orkestrator. 11.10.2026 sonrasi silinir.
# scripts/pre-deploy-check.sh
# CPO-359 Pre-Deploy Tier 0 — Otomatik audit önceki deploy.
# Adımlar (C-39a, 27.09: 82 -> 46): 7 grup adımı (G1 Sözdizimi, G2 Renk/token,
# G3 Kabuk/asset, G4 Yayımlanan metin, G5 Sayı/biçim, G6 Etkileşim, G8 Kullanıcı
# verisi) + 39 tekil kapı (8-46; C-39b bunları da gruplara taşır).
# Exit 0: tüm geçer / Exit 1: en az 1 fail
#
# Kullanım: ./scripts/pre-deploy-check.sh

set -e
FAIL=0
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Pre-Deploy Check (CPO-359 Tier 0) ==="
echo ""

# -- C-39a (27.09): kapi 1-41 + kapi 84 (K-DR) 7 GRUP ADIMINA birlesti ---------
# Karar tablosu: ~/ops/plans/2026-09-23-denetim/kanit/gate_table.md. Kurallar
# (betikler) AYNEN kalir, koşucu yeniden yazilmadi; yalniz adim sayisi azaldi.
# Grup icinde her kural ayri kosar; biri kirmiziysa grup FAIL olur ve kuralin
# adi + ciktisinin sonu basilir (sessiz gecis yok -- enjeksiyon kaniti:
# ~/ops/plans/shots/C-39a/enjeksiyon.txt). Kaldirilan: 7 lint_scope (KALDIR).
# Tek grup kosmak: PREDEPLOY_GROUP=renk bash tools/pre-deploy-check.sh
# Grup girdisi: "etiket|komut" (komut alt kabukta calisir).
gate_group() {
  local key="$1" name="$2"; shift 2
  if [ -n "${PREDEPLOY_GROUP:-}" ] && [ "$PREDEPLOY_GROUP" != "$key" ]; then return 0; fi
  echo ""
  echo "$name..."
  local bad=0 item label cmd out
  for item in "$@"; do
    label="${item%%|*}"; cmd="${item#*|}"
    if ! out=$(eval "$cmd" 2>&1); then
      echo "  ✗ $label KIRIK. Detay: $cmd"
      echo "$out" | tail -15 | sed 's/^/      /'
      bad=$((bad + 1))
    fi
  done
  if [ "$bad" = "0" ]; then
    echo "  ✓ $name: $# kural PASS"
  else
    FAIL=$((FAIL + 1))
  fi
}

# KALICI_KURALLAR: pre-commit ile ayni liste (CPO-1584), senkron tutulmali.
KK_AUDIT_FILES="templates/hisse.html templates/karsilastir.html templates/ozet.html templates/sektor_harita.html templates/tarama.html templates/hisseler.html templates/index.html templates/portfolio.html templates/gundem.html templates/metodoloji.html templates/blog.html templates/blog_article.html templates/takvim.html templates/harita_gun.html"

gate_group sozdizimi "G1 Sozdizimi" \
  "Jinja parse|python3 tools/_predeploy_jinja_check.py" \
  "Python compile (tum *.py)|git ls-files '*.py' | python3 -c 'import ast,sys;[ast.parse(open(f,encoding=\"utf-8\").read(),f) for f in sys.stdin.read().split()]'" \
  "node-syntax-check|python3 tools/node-syntax-check.py" \
  "K-BE global-collision-check|python3 tools/global-collision-check.py"

gate_group renk "G2 Renk/token" \
  "CSS token guard|python3 tools/css-token-guard.py static/css/*.css" \
  "style-guard|python3 tools/style-guard.py" \
  "K-G state-order-check|python3 tools/state-order-check.py" \
  "K-I contrast-check|python3 tools/contrast-check.py" \
  "K-K da-override-check|python3 tools/da-override-check.py" \
  "K-AP canon-conflict-check|python3 tools/canon-conflict-check.py" \
  "K-BG js-palette-check|python3 tools/js-palette-check.py" \
  "K-BO volume-axis-color-check|python3 tools/volume-axis-color-check.py"

gate_group kabuk "G3 Kabuk/asset" \
  "sw_manifest (elle ?v= 0)|python3 tools/sw_manifest.py" \
  "K-AS nav-label-canon-check|python3 tools/nav-label-canon-check.py" \
  "K-AY sticky-anchor-check|python3 tools/sticky-anchor-check.py" \
  "K-AZ safearea-layer-check|python3 tools/safearea-layer-check.py" \
  "K-DR overflow-guard-canon-check (kapi 84)|python3 tools/overflow-guard-canon-check.py"

gate_group metin "G4 Yayimlanan metin" \
  "KALICI_KURALLAR audit|for f in \$KK_AUDIT_FILES; do ./tests/audit/kalici-kurallar-check.sh \"\$f\" >/dev/null 2>&1 || { echo \"KK ihlali: \$f\"; exit 1; }; done" \
  "K-H legal-text-sync-check|python3 tools/legal-text-sync-check.py" \
  "K-AQ glyph-canon-check|python3 tools/glyph-canon-check.py" \
  "K-BN eod-freshness-claim-check|python3 tools/eod-freshness-claim-check.py"

gate_group sayi "G5 Sayi/bicim kanonu" \
  "format-lint (K6)|./tools/format-lint.sh" \
  "K-AR threshold-sync-check|python3 tools/threshold-sync-check.py" \
  "K-BA tr-decimal-input-check|python3 tools/tr-decimal-input-check.py" \
  "K-BD tr-calendar-day-check|python3 tools/tr-calendar-day-check.py" \
  "K-BP direction-zero-check|python3 tools/direction-zero-check.py" \
  "K-BQ stop-level-canon-check|python3 tools/stop-level-canon-check.py" \
  "K-BR indicator-precision-check|python3 tools/indicator-precision-check.py" \
  "K-BS indicator-panel-canon-check|python3 tools/indicator-panel-canon-check.py" \
  "K-BU label-derived-number-check|python3 tools/label-derived-number-check.py" \
  "K-BV money-scale-canon-check|python3 tools/money-scale-canon-check.py"

gate_group etkilesim "G6 Etkilesim sozlesmesi" \
  "K-AT tooltip-canon-check|python3 tools/tooltip-canon-check.py" \
  "K-AV sort-canon-check|python3 tools/sort-canon-check.py" \
  "K-AW newtab-canon-check|python3 tools/newtab-canon-check.py" \
  "K-AX autorefresh-canon-check|python3 tools/autorefresh-canon-check.py" \
  "K-BT innerhtml-sibling-check|python3 tools/innerhtml-sibling-check.py"

# E2E->KALDIR adaylari: Playwright e2e yazilana kadar kural olarak KALIR.
gate_group veri "G8 Kullanici verisi (e2e oncesi)" \
  "K-BH copy-promise-check|python3 tools/copy-promise-check.py" \
  "K-BI merge-report-check|python3 tools/merge-report-check.py" \
  "K-BJ position-validation-check|python3 tools/position-validation-check.py" \
  "K-BK api-data-loading-guard|python3 tools/api-data-loading-guard.py" \
  "K-BM local-data-guard|python3 tools/local-data-guard.py"

if [ -n "${PREDEPLOY_GROUP:-}" ]; then
  [ "$FAIL" = "0" ] && exit 0 || exit 1
fi

echo ""
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
echo "8/46 inline-style-hex-check (K-BW: satir-ici renk token'dan gelir)..."
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
echo "9/46 fundamental-card-band-check (K-BX: temel kart birim/band)..."
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
echo "10/46 template-color-channel-check (K-BY: renk kanaldan bagimsiz token'dan gelir)..."
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
echo "11/46 provenance-badge-check (K-BZ: koken rozeti <-> govdenin gercek kaynagi)..."
if python3 tools/provenance-badge-check.py; then
  echo "  ✓ provenance-badge-check PASS"
else
  echo "  ✗ K-BZ KIRIK: koken rozeti, yanit gelmeden saglayici adi iddia ediyor."
  echo "    Detay icin: python3 tools/provenance-badge-check.py"
  echo "    Pozitif kontrol: python3 tools/provenance-badge-check.py --ref 9c63d9f"
  FAIL=$((FAIL + 1))
fi

# 46: rr-canon-check (K-CA) C-52 (24.09) ile emekli -- R/R hicbir yuzeyde yok;
# yasak kapi 76 R3'te (signal-rule-canon-check RE_BANNED).

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
echo "12/46 window-claim-check (K-CB: pencere beyani <-> cizilen veri)..."
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
echo "13/46 export-parity-check (K-CC: disa aktarim <-> ekran ayni sayi/ad)..."
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
# literali (sozcukler kapi dosyasinda sabit), A3 ayni
# yeniden-capalamanin JS yazimi (bpSignalDateLabel(..., ...)).
echo "14/46 relative-time-anchor-check (K-CD: goreli zaman <-> okuyucunun takvimi)..."
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
echo "15/46 intraday-claim-check (K-CE: EOD-only mimaride gun-ici/canli iddia)..."
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
echo "16/46 blog-claim-check (K-CF: blog govdesi icerik-dogruluk kanonu)..."
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
echo "17/46 app-published-text-check (K-CG: app.py yayimlanan metin kanonu)..."
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
echo "18/46 static-js-text-check (K-CH: paylasilan JS yayimlanan metin kanonu)..."
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
# (sw_manifest, eski cachebust-check) -- o da metni degil ikon hash'ini. Oysa manifest'in metni
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
echo "19/46 manifest-text-check (K-CI: PWA manifest yayimlanan metin + URL sozu)..."
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
echo "20/46 crawler-channel-check (K-CJ: robots/llms/humans/security + JSON-LD)..."
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
echo "21/46 sitemap-claim-check (K-CK: changefreq <-> lastmod <-> EOD mimarisi)..."
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
echo "22/46 head-meta-check (K-CL: <head> meta kanali + og gorseli)..."
if python3 tools/head-meta-check.py; then
  echo "  ✓ head-meta-check PASS"
else
  echo "  ✗ K-CL KIRIK: <head> meta kanali ya da og gorseli kanon disi iddia tasiyor."
  echo "    Detay icin: python3 tools/head-meta-check.py --verbose"
  echo "    Pozitif kontrol: python3 tools/head-meta-check.py --ref ee2a473  # 7 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

echo "23/46 glossary-where-check (K-CM: sozlugun \"nerede gorulur\" vaadi)..."
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
echo "24/46 score-claim-check (K-CN: Teknik Güç Skoru bilesen iddiasi)..."
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
echo "25/46 delivery-timing-claim-check (K-CO: teslimat anindaligi vaadi)..."
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
echo "26/46 tab-visibility-canon-check (K-CP: sekme gorunurlugu tek kanon)..."
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
echo "27/46 url-state-param-check (K-CQ: URL durum parametresi korunumu)..."
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
echo "28/46 form-url-state-check (K-CS: form durumu <-> adres cubugu tur-gidisi)..."
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
echo "29/46 url-state-owner-check (K-CT: adres cubugunun tek sahibi)..."
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
echo "30/46 client-server-state-owner-check (K-CU: sunucu durumunun istemcideki sahibi)..."
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
echo "31/46 privacy-claim-flow-check (K-CV: gizlilik beyani <-> veri akisi)..."
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
echo "32/46 score-band-canon-check (K-CW: skor bandinin renk+ad kanonu)..."
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
echo "33/46 dynamic-tip-canon-check (K-CX: durum degisince data-tip de guncellenmeli)..."
if python3 tools/dynamic-tip-canon-check.py; then
  echo "  ✓ dynamic-tip-canon-check PASS"
else
  echo "  ✗ K-CX KIRIK: aciklama fare-only `title` kanalina yaziliyor, [data-tip] donuk kaliyor."
  echo "    Pozitif kontrol: python3 tools/dynamic-tip-canon-check.py --self-test  # 11/11 beklenir"
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
echo "34/46 canon-css-dup-check (K-CY: kanonik CSS'i JS enjeksiyonu ezemez)..."
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
echo "35/46 brand-wordmark-canon-check (K-CZ: marka sozcuk-isareti tek token)..."
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
echo "36/46 py-palette-check (K-DB: Python kanali <-> tokens.css, SIFIR sarti)..."
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
echo "37/46 index-ticker-channel-check (K-DC: endeks/hisse kanal envanteri)..."
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
echo "38/46 long-only-surface-check (K-DE: long-only sunum kapisi)..."
if python3 tools/long-only-surface-check.py; then
  echo "  ✓ long-only-surface-check PASS"
else
  echo "  ✗ K-DE KIRIK: bir kanal Trend Bozuldu sinyalinde giris/hedef/R-R vaadi basiyor (ya da envanter bayat)."
  echo "    Self-test:       python3 tools/long-only-surface-check.py --self-test  # 14/14 beklenir"
  echo "    Pozitif kontrol: python3 tools/long-only-surface-check.py --ref 8b3f67b  # 25 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 74. tr-fold-canon-check (KAPI 75 -- K-DG)
#   TURKCE ARAMA KATLAMASI TEK KANONDAN MI? "ASCII klavyeyle yazilan sorgu
#   Turkce harfli adla eslessin" isi BES yerde ayri yazilmisti ve DORDU
#   farkliydi: bp-search.js/tarama tam katlama; karsilastir `ı`yi,
#   portfolio ş/ğ/ü/ö/ç'yi, blog HICBIR diyakritigi katlamiyordu.
#   CANLI OLCUM 22.09 (sablonlardan sokulen gercek govdeler, /api/stocks/list
#   216 ad): kanondan sapan ad karsilastir 49, portfolio 102, blog 124.
#   "turk hava yollari" ust aramada 1 sonuc, /karsilastir ve /blog'da 0.
#   /blog'da 91 kartin 86'sinin basliginda ASCII yazilinca bulunamayan en az
#   bir kelime vardi ("yonetim" 0 / kanon 10, "guclu" 0 / 8, "turkiye" 0 / 9)
#   -- ustelik "Risk Yonetimi" sayfanin KENDI kategori cipinin adi.
#   Kanon: static/bp-vocab.js `bpTrFold()`. Kapi kopyayi (R2), kirli delegeyi
#   (R3) ve bildirilmemis/yanlis siralanmis bagimliligi (R4/R5) yakalar.
echo "39/46 tr-fold-canon-check (K-DG: Turkce arama katlamasi tek kanon)..."
if python3 tools/tr-fold-canon-check.py; then
  echo "  ✓ tr-fold-canon-check PASS"
else
  echo "  ✗ K-DG KIRIK: bir yuzey kendi Turkce katlamasini yaziyor ya da bp-vocab.js bagimliligi bildirilmemis."
  echo "    Self-test:       python3 tools/tr-fold-canon-check.py --self-test  # 8/8 beklenir"
  echo "    Pozitif kontrol: python3 tools/tr-fold-canon-check.py --ref 684f16c  # 12 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 75. learning-mode-surface-check (KAPI 76 -- K-DH)
#   OGRENME MODU CAPASI OLAN HER SAYFA OZELLIGI YUKLUYOR MU? `.jargon-term`
#   capasini uc kaynak basiyor (sablon, `sigLabelTooltip()`, bp-vocab.js) ama
#   learning-mode.js YALNIZ 3 sayfada yukluydu. CANLI OLCUM 22.09 (render
#   sonrasi DOM): /bilanco-takvimi 46 capa, /temettu-takvimi 28, /karsilastir
#   4, /portfolio ve /sektor-harita da capali -- hicbirinde "?" cikmiyordu.
#   Kullanici /tarama'da modu aciyor (localStorage), sonraki sayfada ozellik
#   sessizce yok oluyordu (141. dersin ozellik bicimi: ISARET yayildi, MOTOR
#   yayilmadi). Ayrica ozelligin TEK kontrolu `@media (max-width:600px)
#   {header .bp-lm-toggle{display:none}}` ile mobilde tamamen gizliydi --
#   telefonda Ogrenme Modu hic acilamiyordu.
#   R1 capa->motor · R2 motor->capa (bayat yukleme) · R3 kontrol hicbir
#   kirilma noktasinda display:none olamaz · R4 olu sozluk anahtari UYARI ·
#   R5 kapsam tabani 6. Yorumlar soyulur (137. ders).
echo "40/46 learning-mode-surface-check (K-DH: Ogrenme Modu yuzey envanteri)..."
if python3 tools/learning-mode-surface-check.py; then
  echo "  ✓ learning-mode-surface-check PASS"
else
  echo "  ✗ K-DH KIRIK: jargon capasi basan bir sayfa Ogrenme Modu motorunu yuklemiyor (ya da kontrol gizlenmis)."
  echo "    Self-test:       python3 tools/learning-mode-surface-check.py --self-test  # 11/11 beklenir"
  echo "    Pozitif kontrol: python3 tools/learning-mode-surface-check.py --ref 1dd9684  # 6 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 76. signal-rule-canon-check (KAPI 77 -- K-DK)
#   SINYAL URETIM KURALI HER KANALDA TAM MI ANLATILIYOR? Kod (app.py
#   `_bar_signal_fast`) DORT kosul isliyor: Supertrend yonu + ADX >= 25 +
#   DI yonu (dip>dim) + EMA12/EMA99. Kural BES kanalda anlatiliyordu ve
#   DI kosulunu YALNIZ /metodoloji'nin formul kutusu iceriyordu:
#   /hakkinda formul kutusu 3 kosul, /hisse AL/SAT checklist'i 3 madde +
#   "3/3 kriter uyumlu" (JS rozet tooltip'i de "3 kriter"), blog "uclu
#   filtre sistemi ... Ucu ayni anda" -- USTELIK ayni yazidaki AL listesi
#   4 madde sayarken paragrafi "su uc kriter" diyordu. /metodoloji'nin
#   KENDI TL;DR'i da ana formul kutusuyla celisiyordu (3 kosul yaziyordu).
#   CANLI OLCUM 22.09 (/api/data): 4/4 AL hissesinde DI+ > DI-, 87 SAT'in
#   86'sinda DI- > DI+ -- kosul gercekten sinyali belirliyor.
#   R1 kural beyani DI'yi anmali (blok = gercek yayim birimi, komsuluk
#   DEGIL) · R2 "3/uc kriter|kosul" sayimi yanlis (4 kosul var; GOSTERGE
#   sayimi 3'tur ve serbesttir). Yorumlar soyulur: HTML/Jinja/JS/py (137.
#   ders). Baslik alanlari (title/og:title) muaf, description TARANIR.
echo "41/46 signal-rule-canon-check (K-DK: sinyal kurali tek kanon)..."
if python3 tools/signal-rule-canon-check.py; then
  echo "  ✓ signal-rule-canon-check PASS"
else
  echo "  ✗ K-DK KIRIK: sinyal kuralini anlatan bir yuzey DI kosulunu atliyor ya da kosul sayimi yanlis."
  echo "    Self-test:       python3 tools/signal-rule-canon-check.py --self-test  # 30/30 beklenir"
  echo "    Pozitif kontrol: python3 tools/signal-rule-canon-check.py --ref a2fc59e  # 30 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 77. fundamental-field-presentation-check (KAPI 78 -- K-DL)
#   TEMEL ALANIN SUNUM SOZLESMESI.
#   R1 ISARETLI YUZDE: seviye yuzdeleri ('%' ONDE, Turkce yazim) negatif
#   degerde `'%' + (-3.5).toFixed(1)` = **"%-3,5"** uretiyordu -- eksi
#   isareti yuzde isaretiyle rakamin ARASINDA. CANLI 22.09 (217/217):
#   en az bir negatif yuzde tasiyan 148 hisse (%68). Ayni yanlis yazim /hisse
#   Temel kartinda ve /karsilastir ROE satirinda BAGIMSIZ iki kez
#   duruyordu. Kural alan ADINA degil YAPIYA bakar: '%' ardindan
#   HESAPLANMIS bir ifade (toFixed/aritmetik/parseFloat) gelemez, ciplak
#   degisken serbest, kanonik bicimleyici (bpPctLevel/bpFormatPct/
#   pct_text) serbest.
#   R2 KAYNAKSIZ ALAN: `f.beta` BIST'e gore olculmus degil -- sitenin
#   kendi 494 gunluk verisiyle olcum: ISCTR kart 0,20 / olculen 1,21;
#   GARAN 0,51 / 1,15; AKBNK 0,69 / 1,29. Canli dagilim: beta dolu 128
#   hissenin 96'si "Piyasa alti hareket", 5'i "ustu" -- endeksin kendi
#   agir hisselerinde imkansiz. Alan XU030'a gore hesaplanana dek
#   (CPO-1787) gosterilmez.
echo "42/46 fundamental-field-presentation-check (K-DL: isaretli yuzde + kaynaksiz alan)..."
if python3 tools/fundamental-field-presentation-check.py; then
  echo "  ✓ fundamental-field-presentation-check PASS"
else
  echo "  ✗ K-DL KIRIK: '%' ardina hesaplanmis sayi yazilmis ya da kaynaksiz `beta` alani sunuluyor."
  echo "    Self-test:       python3 tools/fundamental-field-presentation-check.py --self-test  # 14/14 beklenir"
  echo "    Pozitif kontrol: python3 tools/fundamental-field-presentation-check.py --ref ccf2893  # 18 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 78. sector-peer-promise-check (KAPI 79 -- K-DM)
#   SEKTOR AKRANI VAADI AKRANIN VARLIGINA BAGLI OLMALI.
#   app.py siniflandirilamayan ticker'lara "Diğer" verir ve (CPO-1464 #3)
#   o kova icin `_sector_pool = []` yapar -- "ayni sektor" havuzu KASITLI
#   bos. Iki tuketici vardi: `related_stocks` bu bosalmayi dalliyordu,
#   hero'daki `compare_url` dugmesi DALLANMIYORDU. Canli 22.09: 11 hisse
#   (ADEL AGROT BJKAS DURDO FENER FMIZP FORMT GSRAY IEYHO KARTN MARTI)
#   icin dugme "Sektordeki diger hisselerle karsilastir" diye vaat ediyor,
#   href akransiz `/karsilastir?tickers=BJKAS` -- sayfa "en az 2 hisse"
#   bos durumuna dusuyordu. Kapi vaadin KOSULUNU arar, YAZISINI degil:
#   sektor iddiasi `{% if %}` icinde ve kosul compare_url'den TURETILMIS
#   bir bayraga bagli olmali (sektor ADINA degil -- 52/162. ders).
echo "43/46 sector-peer-promise-check (K-DM: sektor akrani vaadi)..."
if python3 tools/sector-peer-promise-check.py; then
  echo "  ✓ sector-peer-promise-check PASS"
else
  echo "  ✗ K-DM KIRIK: sektor akrani vaadi akranin varligina bagli degil."
  echo "    Self-test:       python3 tools/sector-peer-promise-check.py --self-test  # 10/10 beklenir"
  echo "    Pozitif kontrol: python3 tools/sector-peer-promise-check.py --ref 334d01c  # 2 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 79. scope-claim-canon-check (KAPI 80 -- K-DN)
#   SAYFANIN KENDI VERI KUMESI ICIN YAPTIGI KAPSAM IDDIASI TEK KANON OLMALI
#   VE GORUNUR OLMALI.
#   /temettu-takvimi backend'de `BIST30_LITERAL` orneklemiyle uretiliyor
#   (app.py `_dividend_refresh_impl`, hiz/rate-limit) -- canli 22.09: 28
#   hisse. Sayfanin GORUNUR her yuzeyi ise BIST genelini vaat ediyordu:
#   <title> "BIST Temettü Tarihleri", sr-only h1 "BIST Temettü ... Takvimi",
#   "Toplam Hisse" cipi (28). Dogru kapsami soyleyen TEK yer `meta
#   description` idi -- yani kullaniciya GORUNMEYEN yer. Kardes /bilanco-
#   takvimi ayni kabukta 216 hisse servis ediyor, iki takvim ayni evreni
#   kapsiyormus gibi duruyordu.
#   R1: bir sablonun kapsam iddialari (title/h1/og/twitter/description) ayni
#       siniftan olmali (DAR=BIST30 anilmis / GENEL=BIST|BIST100).
#   R2: iddia DAR ise GORUNUR govdede de gecmeli -- yorum, <script> ve
#       `sr-only` kanit sayilmaz (77. ders + K-DN'in cekirdegi).
echo "44/46 scope-claim-canon-check (K-DN: kapsam iddiasi tek kanon)..."
if python3 tools/scope-claim-canon-check.py; then
  echo "  ✓ scope-claim-canon-check PASS"
else
  echo "  ✗ K-DN KIRIK: sayfa kendi veri kumesi icin celisen ya da gorunmeyen kapsam iddiasi tasiyor."
  echo "    Self-test:       python3 tools/scope-claim-canon-check.py --self-test  # 10/10 beklenir"
  echo "    Pozitif kontrol: python3 tools/scope-claim-canon-check.py --ref 509c33a  # 2 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 80. hidden-write-target-check (KAPI 81 -- K-DO)
#   JS'IN YAZDIGI HEDEF KALICI GIZLI BIR AGACTA OLMAMALI.
#   `_bp_critical_css.html` anti-CLS kurali sarmalayiciyi gizliyor:
#     header > div:has(> .page-sub){display:none !important}
#   Bes sayfa VERI TAZELIK DAMGASINI tam oraya yaziyordu (gundem ·
#   sektor-harita · bilanco-takvimi · temettu-takvimi · karsilastir).
#   Canli olcum 22.09: #lastUpdate metni "Son güncelleme: 22.09.2026 07:50",
#   kutusu 0x0, parent display=none -- 13 saat eski veriyi isaret eden damga
#   kullaniciya HIC gorunmuyordu. Ustelik dugum role="status" aria-live
#   tasiyordu: display:none alt agaci a11y agacindan duser, yani canli bolge
#   ekran okuyucuya da duyurulmuyordu -- kanal IKI YONLU oluydu.
#   R1 sablon `hdr_sub`/`hdr_sub_id` gecmemeli · R2 anti-CLS kurali yerinde
#   durmali (gerekce cokerse kural gozden gecirilsin) · R3 JS'in yazdigi her
#   id sablonda tanimli olmali (damgayi <main>'e tasimayi unutma senaryosu).
echo "45/46 hidden-write-target-check (K-DO: gizli yazma hedefi)..."
if python3 tools/hidden-write-target-check.py; then
  echo "  ✓ hidden-write-target-check PASS"
else
  echo "  ✗ K-DO KIRIK: JS kalici gizli bir dugume yaziyor ya da hedef id yok."
  echo "    Self-test:       python3 tools/hidden-write-target-check.py --self-test  # 9/9 beklenir"
  echo "    Pozitif kontrol: python3 tools/hidden-write-target-check.py --ref 77f66e9  # 10 ihlal beklenir"
  FAIL=$((FAIL + 1))
fi

# 81. control-role-behavior-check (KAPI 82 -- K-DP)
#   BIR KONTROLUN ROLU ILE DAVRANISI AYNI SEYI SOYLEMELI.
#   /karsilastir "🔗 Linki Kopyala" bir <a href="."> idi; `.` bu sayfada ANA
#   SAYFAYA cozuluyordu (canli olcum: a.href == "https://borsapusula.com/").
#   Dugmenin tek isi "bu karsilastirmanin adresini ver"ken sag tik > "baglanti
#   adresini kopyala" / Ctrl+tik / orta tik VAADIN TAM TERSINI veriyordu;
#   ustelik <a href> SPACE ile etkinlesmez ve elemanin onkeydown'i yoktu ->
#   klavye kullanicisi hic kopyalayamiyordu. Kardesi (.compare-btn) zaten
#   gercek <button>'di: ayni satirda iki kanon (52. ders).
#   Ikinci sinif: /hisse'de iki <a href="#signalSummarySection"> onclick'inde
#   `return false` ile varsayilan FRAGMENT GEZINMESINI iptal ediyordu -- sekme
#   degisiyor ama tarayici hedefe ne kaydiriyor ne odak tasiyordu (olcum:
#   /hisse/GARAN'da hedef ekranin 2487px USTUNDE kaldi, location'da fragment
#   yoktu). `applyTab && applyTab(); return false` ifadesi applyTab TANIMSIZ
#   iken de iptal ediyordu: href'in yedek olma sebebi tam da ise yarayacagi
#   senaryoda yok ediliyordu.
#   R(A) <a>'nin href'i yer tutucu olamaz (`.`, `#`, bos, `javascript:`) ve
#   href'siz <a> onclick tasiyamaz -> <button type="button">.
#   R(B) gercek sayfa-ici capaya sahip <a>'nin satir-ici onclick'i varsayilani
#   IPTAL edemez (return false / preventDefault).
echo "46/46 control-role-behavior-check (K-DP: kontrol rolu = davranisi)..."
if python3 tools/control-role-behavior-check.py; then
  echo "  ✓ control-role-behavior-check PASS"
else
  echo "  ✗ K-DP KIRIK: bir <a> gezinmiyor ya da capasi gercekte sicramiyor."
  echo "    Pozitif kontrol: python3 tools/control-role-behavior-check.py --ref 61777f3  # 3 ihlal beklenir"
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
