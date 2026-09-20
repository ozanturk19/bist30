#!/usr/bin/env python3
"""Sablon stil guard'i — T1.7 format-lint v2'nin ikinci parcasi.

`tools/css-token-guard.py` YALNIZ `static/css/*.css` dosyalarini denetliyor (2 dosya).
Oysa T1.5 migrasyonundan sonra sablonlarin icinde 2339 adet `var(--bp-*)` kullanimi var
ve bunlarin hicbiri hicbir kapida denetlenmiyordu. Iki kusur sinifi olculdu ve
bu guard tam olarak ikisini kapatir:

K-A  TANIMSIZ var()  — BLOKLAYICI, taban 0
     Bir sayfada kullanilan token o sayfada gorunur DEGILSE deger sessizce
     ilk-deger/bos'a duser. Tarayici hata vermez, HTTP 200 doner, grep dosyanin
     icinde token adini BULUR. Tek kirmizi olcut getComputedStyle'di; bu guard onu
     statik olarak, deploy'dan ONCE yapar.
     Kapsam kurali: CSS ozel ozellikleri DOM uzerinden miras alinir, DOSYALAR
     ARASINDA DEGIL. Bir sablonun `:root`unda tanimli token BASKA sablonu kurtarmaz.
     Bu yuzden denetim SAYFA BAZINDADIR (global css + o sayfanin kendi tanimlari +
     her sayfaya giren kabuk partial'lari).
     Bugunku taban: 27/27 sayfada 0 tanimsiz — guard bugun YESIL, yani kirmiziya
     donduren sey bundan sonraki bir REGRESYONDUR.

K-B  KANONIK-DEGERLI HAM HEX — RATCHET, bloklamaz ama ARTAMAZ
     Token'i olan bir rengin ham hex yazimi (`#f85149` yerine `var(--bp-sat)`).
     Bugun 506 occurrence var; hepsini bir gecede cevirmek GORSEL REGRESYON riski
     tasir (T1.5b olcumu: 601 adayin yalnizca 112'si kosulsuz guvenli). Bu yuzden
     mutlak yasak degil, KADEMELI KAPI: dosya basina sayim ARTARSA hata.
     Yani mevcut borc bloklamaz, YENI borc bloklar. Master Program §7'nin
     "once yeni commit'lere zorunlu, sonra geriye donuk" tavsiyesi budur.

     Ratchet dosyasi token IMZASINI da saklar: `tokens.css`e yeni bir token
     eklenince kanonik deger kumesi buyur ve sayimlar sablon degismeden artabilir.
     O durum ayri bir mesajla raporlanir — sucu sablona atmaz.

     T1.7 GENISLETME (15.08.2026, DEV-2): kapsam su ana kadar YALNIZ
     templates/*.html + kabuk partial'lariydi — `blog_content.py` ve
     `static/css/*.css` (tokens.css disinda) HICBIR guard'da yoktu. Olculdu:
     `blog_content.py` blog makalelerinin ic HTML'inde 578 kanonik-degerli ham
     hex tasiyor (`style="border-top:1px solid #30363d"` gibi inline stiller —
     GitHub-legacy paletin templates/ disindaki, hicbir S1/S7/T1.5 turunda
     GORULMEMIS bir kopyasi); `page-info-panel.css` 2 tane tasiyor (#b8c3ff =
     --bp-brand). Ikisi de EK_HEX_DOSYALARI'na baseline'la eklendi — mevcut
     borc bloklanmiyor (578 sayisi kendisi bir HATA degil, bir olcum), yalniz
     ARTISI artik yakalaniyor. Migrasyon (inline style -> class/token) ayri bir
     karar/is kalemi — bu guard yalniz GORUNURLUK katıyor.

     CPO-1673 GENISLETME (20.09.2026): CPO'nun bulgusu ("/gundem" rozetinde
     metin `rgb(0,226,144)`, zemin `rgba(63,185,80,...)` — token'la CELISEN
     eski GitHub-dark yesili) HEX_RE'nin YALNIZ `#rrggbb` sozdizimini yakalayip
     `rgb()/rgba()` fonksiyon notasyonunu HIC gormedigini ortaya cikardi — dosya
     turu (CSS/HTML) fark etmezdi, EK_HEX_DOSYALARI zaten static/css/**.css'i
     tasiyordu (CPO'nun "CSS taranmiyor" teshisi bu yuzden yanlisti, dogru kok
     neden regex'in renk SOZDIZIMI kapsamiydi). `kanonik_rgb_haritasi()` eklendi:
     hem `--x-rgb: r,g,b;` bilesen tanimlari hem hex->rgb donusumu ile ayni
     kanonik degerin `rgb()/rgba()` literal karsiligini da K-B'ye katar.
     Olculdu: genisletme 298 occurrence'a cikardi (eskiden gorulmeyen 33 yeni
     rgb/rgba literal, cogu blog_content.py+hisse.html+sektor_harita.html) —
     mevcut borc yine bloklanmadi, `--baseline` ile tavana alindi; YENI rgb/rgba
     kacisi bundan sonra FAIL verir.

K-E  OLU PALET LITERALI — RATCHET, bloklamaz ama ARTAMAZ (CPO, 20.09.2026)

     K-B'nin YAPISAL kor noktasi: K-B yalniz KANONIK-DEGERLI literalleri sayar,
     yani bugun bir token'in degerine ESIT olanlari. Urun eski bir paletten
     (GitHub-dark + Tailwind) kanonik palete gectiginde ESKI degerler hicbir
     token'a esit olmaz — ve tam bu yuzden K-B onlari HIC GORMEZ. Sayim dusuyor
     gorunur, oysa gorsel kusur olculmeyen sinifta duruyordur.

     Olculdu (20.09.2026, CPO): bilanco_takvimi + temettu_takvimi sayfalarinda
     14 adet Tailwind blue-500 (`rgba(59,130,246,...)`) — filtre dugmesinin
     KENARI kanonik periwinkle (`var(--bp-brand)`) iken ZEMINI eski maviydi,
     yani ayni ogenin iki yarisi iki ayri paletten boyaniyordu. Ayni iki sayfada
     "Guclu Trend" sayaci `#3fb950` (eski GitHub yesili) ile boyaniyordu, oysa
     AYNI SATIRDAKI "Trend Bozuldu" sayaci `.bp-sat-text` token sinifini
     kullaniyordu. K-B bu 20 occurrence'in HICBIRINI raporlamiyordu.

     Olcut: OLU_PALET haritasindaki her deger (hex + rgb()/rgba() literal
     karsiligi) sayilir. Denylist'e yalniz KANONIK HALEFI BELGELI degerler
     girer — "token'i olmayan renk" (ornek grafik EMA99 altini #e3b341) bu
     kapinin konusu DEGILDIR, o K-B'nin/ayri bir kararin isidir. Savunma:
     bir deger sonradan yeniden kanoniklesirse (tokens.css'e girerse)
     denylist'ten OTOMATIK dusulur, yanlis-pozitif uretmez.

K-C  SABLON-YEREL :root — RATCHET, bloklamaz ama ARTAMAZ (T9.4-d, bkz. yerel_root_sayim())

K-D  BOS catch{} — RATCHET, bloklamaz ama ARTAMAZ (T9.4)
     `catch(e){}` / `catch(_) {}` / `catch{}` — hata sessizce yutulur, ne log ne
     kullaniciya bildirim. Master Program T9.4'un istedigi "bos catch{} yasak"
     BLOKLAYICI olarak uygulanamaz: olculdu (14.08.2026), 16 sayfa sablonunda
     halihazirda 70 occurrence var (cogu localStorage/opsiyonel-widget savunma
     kodu, gercek hata degil). K-B/K-C ile ayni gerekce: mevcut borc bloklamaz,
     YENI borc bloklar.

     T1.7 GENISLETME (15.08.2026, DEV-2): kapsam su ana kadar YALNIZ sayfa
     sablonlariydi — `static/*.js` + `static/js/*.js` (9 dosya) HICBIR guard'da
     yoktu, T7.4'un "bos catch{} kapatildi" iddiasi templates/ disindaki gercek
     JS dosyalarini hic kapsamiyordu. Olculdu: 4 dosyada (bp-search.js x8,
     learning-mode.js x1, stale-banner.js x1, page-info-panel.js x1) toplam 11
     occurrence — hepsi ayni sinif (localStorage/opsiyonel-fetch savunma kodu).
     EK_CATCH_DOSYALARI'na baseline'la eklendi, mevcut borc bloklanmiyor.

     BILINEN SINIRLAR (Workflow adversarial-review, 14.08.2026, regex izole test
     edildi): (1) yorum-only govde (`catch(e){/* ignore */}`) YAKALANMAZ — kacis
     yolu, ratchet'i "yorum ekleyerek" atlatmak mumkun; (2) string/template
     literal icindeki "catch(e) {}" alt dizesi YANLIS POZITIF uretebilir; (3)
     `.catch(() => {})` gibi ok-fonksiyonlu Promise-catch yakalanmazken
     `.catch(function(e){})` yakalanir — tutarsiz; (4) catch parametresinde ic
     ice parantez varsa (`catch({x = f()})`) tespit tamamen kaybolur. Hepsi
     duz-regex yaklasiminin bilinen bedeli (K-B/K-C'nin ayni sinif kusurlarina
     benzer); bir sonraki turda tokenizer/negatif-lookbehind ile daraltilabilir,
     bugun BLOKLAYICI degil cunku guard zaten BLOKLAYICI degil, RATCHET.

Kullanim:
    python3 tools/style-guard.py             # denetle (deploy kapisi)
    python3 tools/style-guard.py --baseline  # ratchet'i bugunku duruma sabitle
    python3 tools/style-guard.py --verbose   # dosya bazinda tam tablo
Cikis: 0 = temiz, 1 = ihlal (deploy engellenmeli)
"""
import json
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL_DIR = ROOT / "templates"
CSS_DIR = ROOT / "static" / "css"
RATCHET = ROOT / "tools" / "style_guard_ratchet.json"

# T1.7 GENISLETME (15.08.2026) — K-B'nin templates/ disina taan EK dosyalari.
# tokens.css HARIC: o token'larin TANIM kaynagi, kendi hex'i "borc" degil.
EK_HEX_DOSYALARI = [ROOT / "blog_content.py"] + \
    [f for f in sorted(CSS_DIR.glob("*.css")) if f.name != "tokens.css"] + \
    [f for f in sorted((CSS_DIR / "pages").glob("*.css"))]
# T2.5 GENISLETME (18.08.2026) - inline <style> bloklari static/css/pages/*.css'e
# TASINDI (bp-critical-css HARIC). Ust satir olmadan bu dosyalardaki ham hex
# K-B'de HIC GORUNMEZ - T2.2'nin ayni dersi (yukarida KABUK_PARTIALS notu),
# borc denetlenmeyen bir klasore tasinmis olurdu.

# T1.7 GENISLETME (15.08.2026) — K-D'nin templates/ disina taan EK dosyalari.
EK_CATCH_DOSYALARI = sorted((ROOT / "static").glob("*.js")) + \
    sorted((ROOT / "static" / "js").glob("*.js"))

# Her sayfaya fiilen giren kabuk partial'lari: buradaki tanimlar tum sayfalarda gecerli.
# T2.2: _header.html + _header_asset_price.html EKLENDI. Eklenmeden once
# 16 sayfanin kanonik header-i HICBIR kapida denetlenmiyordu ve ratchet
# toplami 491->475 dusmus gorunuyordu — borc ODENMEDI, denetlenmeyen bir
# dosyaya TASINDI. Bu satir olmadan K-A/K-B kapsam iddiasi sahtedir.
KABUK_PARTIALS = ("_base.html", "_head.html", "_header.html",
                  "_header_asset_price.html")

COMMENT_RE = re.compile(r"{#.*?#}", re.S)
TANIM_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")
VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
HEX_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b")
TOKEN_DEGER_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*(#[0-9A-Fa-f]{3,8})\s*;")
BOS_CATCH_RE = re.compile(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}")

# CPO-1673 (20.09.2026): K-B'nin HEX_RE'si YALNIZ `#rrggbb` sozdizimini yakaliyordu.
# CPO'nun bulgusundaki her iki deger de (rozet metni `rgb(0,226,144)`, zemin
# `rgba(63,185,80,...)`) FONKSIYON notasyonundaydi — dosya CSS mi HTML mi oldugu
# fark etmezdi, K-B ikisini de hicbir zaman goremezdi. Gercek kok neden bu, "CSS
# dosyalari taranmiyor" degil (EK_HEX_DOSYALARI zaten static/css/**.css'i tasiyor,
# asagidaki kanonik_rgb_haritasi() da ayni CSS dosyalarini okur). Bu yuzden K-B'yi
# `rgb()/rgba()` literal renklerini de kapsayacak sekilde genisletiyoruz: deger,
# bir token'in hex karsiligina veya `--x-rgb: r, g, b;` bilesen tanimina esitse
# sayilir. `var(--bp-al-rgb)` gibi degisken kullanimlari sayiya GIRMEZ (regex
# yalniz sayisal literal yakalar).
RGB_LITERAL_RE = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*[,)]")
TOKEN_RGB_DEGER_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*;")

# ── K-E: OLU PALET (CPO, 20.09.2026) ────────────────────────────────────────
# deger -> (kanonik halef, neden). YALNIZ halefi belgeli degerler; "token'i
# olmayan renk" buraya GIRMEZ. Anahtarlar kucuk harf hex.
OLU_PALET = {
    "#58a6ff": ("--bp-brand", "eski GitHub-dark mavi"),
    "#1f6feb": ("--bp-brand", "eski GitHub mavi vurgu"),
    "#70b1ff": ("--bp-brand", "eski GitHub mavi (acik ton)"),
    "#3b82f6": ("--bp-brand", "Tailwind blue-500"),
    "#1d4ed8": ("--bp-brand", "Tailwind blue-700"),
    "#3fb950": ("--bp-al", "eski GitHub yesili"),
    "#8b949e": ("--bp-text3", "eski GitHub grisi (mavi tonlu)"),
    "#c9d1d9": ("--bp-text2", "eski GitHub metin rengi"),
    "#e6edf3": ("--bp-text", "eski GitHub parlak metin"),
    "#0d1117": ("--bp-bg", "eski GitHub zemin"),
    "#161b22": ("--bp-surface", "eski GitHub yuzey"),
}
# K-E kapsami: K-B'nin dosyalari + gercek JS dosyalari (tooltip/toast gibi
# kullaniciya GORUNEN renkleri orada uretiliyor). VENDOR dosyasi haric —
# lightweight-charts.min.js ucuncu parti, kendi paleti bizim kararimiz degil.
OLU_PALET_VENDOR = {"lightweight-charts.min.js"}


def olu_palet_haritasi(harita):
    """Bugun kanonik OLMAYAN olu degerler -> {hex, (r,g,b)} kumeleri.

    Savunma: bir deger sonradan tokens.css'e girerse (yeniden kanoniklesirse)
    denylist'ten otomatik duser — guard'in kendisi yanlis-pozitif uretemez.
    """
    hexler, rgbler = {}, {}
    for val, (halef, neden) in OLU_PALET.items():
        if val in harita:                      # yeniden kanoniklesmis, olu degil
            continue
        h = val.lstrip("#")
        hexler[val] = (halef, neden)
        rgbler[(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))] = (halef, neden)
    return hexler, rgbler


# K-E yanlis-pozitif savunmasi: bir olu degeri ANLATAN yorum ("#1f6feb'ten kanonik
# token'a gecirildi") kusur DEGILDIR — sayilirsa taban sonsuza kadar sisik kalir ve
# ayni dosyadaki GERCEK bir regresyonu maskeler. Blok yorumlari (/* */, {# #},
# <!-- -->) olcumden cikarilir. `//` satir yorumu BILEREK cikarilmaz: `https://`
# icindeki cift-egik onu yanlis kesip kodun yarisini olcum disi birakirdi.
YORUM_RE = re.compile(r"/\*.*?\*/|{#.*?#}|<!--.*?-->", re.S)


def olu_palet_say(metin, hexler, rgbler):
    metin = YORUM_RE.sub(" ", metin)
    n = 0
    for h in HEX_RE.findall(metin):
        if h.lower() in hexler:
            n += 1
    for r, g, b in RGB_LITERAL_RE.findall(metin):
        if (int(r), int(g), int(b)) in rgbler:
            n += 1
    return n


sys.path.insert(0, str(ROOT / "tools"))
try:
    from lint_scope import sayfa_sablonlari
except ImportError:                                    # pragma: no cover
    sayfa_sablonlari = None


def _oku(p):
    return p.read_text(encoding="utf-8", errors="replace")


def global_tanimlar():
    """static/css/*.css + her sayfaya giren kabuk partial'larinin tanimladigi token'lar."""
    toks = set()
    for f in sorted(CSS_DIR.glob("*.css")):
        toks |= set(TANIM_RE.findall(_oku(f)))
    for n in KABUK_PARTIALS:
        p = TPL_DIR / n
        if p.exists():
            toks |= set(TANIM_RE.findall(_oku(p)))
    return toks


def kanonik_hex_haritasi():
    """deger -> [token adlari].  Yalnizca dogrudan hex ATANAN token'lar."""
    m = {}
    for f in sorted(CSS_DIR.glob("*.css")):
        for tok, val in TOKEN_DEGER_RE.findall(_oku(f)):
            m.setdefault(val.lower(), set()).add(tok)
    return {k: sorted(v) for k, v in m.items()}


def kanonik_rgb_haritasi():
    """(r,g,b) -> [token adlari] — CPO-1673 genisletmesi.

    Iki kaynaktan beslenir: (1) `--x-rgb: r, g, b;` seklinde dogrudan bilesen
    tanimlayan token'lar (rgba() alfa-kompozisyonu icin var, ornek --bp-al-rgb),
    (2) kanonik_hex_haritasi()'ndeki hex degerlerin RGB'ye cevrilmis hali — boylece
    `#00e290` icin hem `#00e290` hem `rgb(0,226,144)` ayni token'a kanonik sayilir.
    """
    m = {}
    for f in sorted(CSS_DIR.glob("*.css")):
        for tok, r, g, b in TOKEN_RGB_DEGER_RE.findall(_oku(f)):
            m.setdefault((int(r), int(g), int(b)), set()).add(tok)
    for hexval, toklar in kanonik_hex_haritasi().items():
        h = hexval.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            rgb = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            m.setdefault(rgb, set()).update(toklar)
    return {k: sorted(v) for k, v in m.items()}


def sayfalar():
    if sayfa_sablonlari is not None:
        return sayfa_sablonlari()
    return [f for f in sorted(TPL_DIR.glob("*.html"))
            if not f.name.startswith("_") and ".bak" not in f.name]


def hex_say(metin, harita, rgbharita=None):
    # 20.09 CPO: K-B de blok yorumlarini olcum disi birakir. K-E bu savunmayi
    # kurulusundan beri tasiyordu (bkz. YORUM_RE notu), K-B tasimiyordu —
    # yapisal olarak AYNI kusur: gecmis bir fix'i ANLATAN yorum ("deger
    # `rgba(124,92,255,.12)` literaliyle yaziliyordu") kusur olarak sayiliyor,
    # ratchet tavani sisik kaliyor ve ayni dosyadaki GERCEK bir regresyonu
    # maskeliyordu. Canli olcum: /ozet'in literali token'a cevrildi, ozet.css
    # sayimi yine de 1'de kaldi — tek kaynagi fix'i anlatan yorumdu.
    metin = YORUM_RE.sub(" ", metin)
    n = 0
    for h in HEX_RE.findall(metin):
        hl = h.lower()
        if len(hl) in (4, 7, 9) and hl in harita:
            n += 1
    if rgbharita:
        for r, g, b in RGB_LITERAL_RE.findall(metin):
            if (int(r), int(g), int(b)) in rgbharita:
                n += 1
    return n


def denetle():
    gtok = global_tanimlar()
    harita = kanonik_hex_haritasi()
    rgbharita = kanonik_rgb_haritasi()
    imza = "%d:%s|%d" % (len(harita), ",".join(sorted(harita)[:8]), len(rgbharita))

    tanimsiz = {}
    hex_sayim = {}
    for f in sayfalar():
        txt = _oku(f)
        yerel = set(TANIM_RE.findall(txt))
        # T2.5 GENISLETME (18.08.2026) - sayfanin ONCEDEN kendi <style> icinde
        # tuttugu yerel :root/token tanimlari artik static/css/pages/<ad>.css'te.
        # Bu satir olmadan K-A o sayfanin KENDI TASIDIGI token'i bile 'tanimsiz'
        # sanir (yanlis-pozitif) - T2.2'deki KABUK_PARTIALS dersiyle ayni sinif.
        page_css = CSS_DIR / "pages" / (f.stem + ".css")
        if page_css.exists():
            yerel |= set(TANIM_RE.findall(_oku(page_css)))
        eksik = {}
        for tok in set(VAR_RE.findall(txt)):
            if tok not in gtok and tok not in yerel:
                eksik[tok] = len(re.findall(r"var\(\s*" + re.escape(tok), txt))
        if eksik:
            tanimsiz[f.name] = eksik
        hex_sayim[f.name] = hex_say(txt, harita, rgbharita)

    # ── KABUK PARTIAL'LARI DA TARA (T2.2 dersi) ─────────────────────────────
    # KABUK_PARTIALS su ana kadar YALNIZ global_tanimlar()'da kullaniliyordu,
    # yani partial'larin TANIMLADIGI token'lar biliniyor ama KULLANDIKLARI
    # var() ve icerdikleri ham hex HIC SAYILMIYORDU. Olculdu (09.08.2026):
    # _header.html 12 ham hex tasiyor, 1'i kanonik degerli (#b8c3ff = --bp-brand);
    # _head.html 4 tasiyor, 1'i kanonik (#0e0e12 = --bp-bg). Bunlar 16 ve 27
    # sayfaya giriyor ama ratchet'te GORUNMUYORLARDI. 065b6a6'da toplam 491->475
    # dustu; dususun bir kismi borcun ODENMESI degil, denetlenmeyen bir dosyaya
    # TASINMASIYDI. Partial'lar her sayfaya girdigi icin K-A'da yerel :root
    # kurtarmasi YOK — global tanimlara karsi olculurler (en siki olcut).
    for n in KABUK_PARTIALS:
        pf = TPL_DIR / n
        if not pf.exists():
            continue
        txt = COMMENT_RE.sub("", _oku(pf))     # dokuman blogu olcume girmez
        eksik = {}
        for tok in set(VAR_RE.findall(txt)):
            if tok not in gtok:
                eksik[tok] = len(re.findall(r"var\(\s*" + re.escape(tok), txt))
        if eksik:
            tanimsiz[n] = eksik
        hex_sayim[n] = hex_say(txt, harita, rgbharita)

    # ── EK HEX DOSYALARI (T1.7 genisletme, 15.08.2026) ──────────────────────
    # blog_content.py + static/css/*.css (tokens.css haric) — bunlar K-A
    # (tanimsiz var()) kapsamina GIRMEZ, cunku ikisi de CSS custom property
    # tuketen sayfa sablonu degil (biri Python string'i, digeri harici CSS
    # dosyasi zaten kendi var() kullanimini tokens.css'e karsi kendi icinde
    # gecerli kilar). Yalniz K-B (ham hex ratchet) icin sayilir — goruculuk,
    # migrasyon degil. Anahtar carpismasin diye ROOT-relative yol kullanilir.
    for f in EK_HEX_DOSYALARI:
        if not f.exists():
            continue
        ad = str(f.relative_to(ROOT))
        hex_sayim[ad] = hex_say(_oku(f), harita, rgbharita)

    # ── K-E: olu palet sayimi (CPO, 20.09.2026) ─────────────────────────────
    ohex, orgb = olu_palet_haritasi(harita)
    olu_sayim = {}
    kapsam = list(sayfalar()) + [TPL_DIR / n for n in KABUK_PARTIALS] + \
        list(EK_HEX_DOSYALARI) + list(EK_CATCH_DOSYALARI)
    gorulen = set()
    for f in kapsam:
        if not f.exists() or f.name in OLU_PALET_VENDOR:
            continue
        ad = f.name if f.parent == TPL_DIR else str(f.relative_to(ROOT))
        if ad in gorulen:
            continue
        gorulen.add(ad)
        n = olu_palet_say(_oku(f), ohex, orgb)
        if n:
            olu_sayim[ad] = n
    return gtok, harita, imza, tanimsiz, hex_sayim, olu_sayim


def yerel_root_sayim():
    """Sablon-yerel :root bloklarini say (T9.4-d).

    NEDEN BLOKLAYICI DEGIL RATCHET: CSS ozel ozellikleri DOM uzerinden miras
    alinir, DOSYALAR ARASINDA DEGIL. Bir sablonun kendi :root'u tokens.css'i
    o sayfada EZER ve hicbir arac bunu fark etmez — grep token adini bulur,
    tarayici hata vermez. Olculdu (09.08.2026): 4 sablonda yerel :root var ve
    tanimladiklari 13 token'in 11'i tokens.css'teki karsiligindan FARKLI degerde
    (ornek: --brand #1f6feb vs --bp-brand #b8c3ff; --text3 #484f58 = 2.09:1
    kontrast, FAZ 8'in P0 kalemi). Yani /tarama, /kripto, /abd-tarama fiilen
    BASKA BIR PALETLE render ediliyor. Bunu bu turda DUZELTMEDIM (gorsel karar,
    marka rengi Ozan'da) ama ARTMASINI engelliyorum.
    """
    from lint_scope import sayfa_sablonlari
    out = {}
    for f in sayfa_sablonlari():
        n = f.read_text(encoding="utf-8").count(":root")
        if n:
            out[f.name] = n
    return out


def bos_catch_sayim():
    """Bos catch{} bloklarini say (T9.4).

    `catch(e){}` hatayi sessizce yutar: ne konsola log ne kullaniciya bildirim.
    Cogu vaka mesru (localStorage/opsiyonel-widget savunma kodu) ama BLOKLAYICI
    yapmak bugunku ~26 sayfadaki mevcut borcu bir gecede kirar. K-B/K-C ile ayni
    desen: mevcut borc dokunulmaz, YENI catch{} eklenmesi engellenir.
    """
    from lint_scope import sayfa_sablonlari
    out = {}
    for f in sayfa_sablonlari():
        n = len(BOS_CATCH_RE.findall(f.read_text(encoding="utf-8", errors="replace")))
        if n:
            out[f.name] = n
    # T1.7 genisletme (15.08.2026): static/*.js + static/js/*.js — gercek JS
    # dosyalari, templates/ icindeki inline <script> degil. Anahtar carpismasin
    # diye ROOT-relative yol kullanilir.
    for f in EK_CATCH_DOSYALARI:
        if not f.exists():
            continue
        n = len(BOS_CATCH_RE.findall(f.read_text(encoding="utf-8", errors="replace")))
        if n:
            out[str(f.relative_to(ROOT))] = n
    return out


def main(argv):
    verbose = "--verbose" in argv
    gtok, harita, imza, tanimsiz, hex_sayim, olu_sayim = denetle()
    # K-A (tanimsiz var()) yalniz gercek sayfa sablonlarini kapsar; K-B (ham
    # hex) artik EK_HEX_DOSYALARI (blog_content.py + harici css) ile de
    # genisledigi icin hex_sayim ile K-A'nin sayfa sayisi ARTIK AYNI DEGIL.
    toplam_sayfa = len(sayfalar()) + len(KABUK_PARTIALS)
    toplam_hex_dosya = len(hex_sayim)

    if "--baseline" in argv:
        RATCHET.write_text(json.dumps(
            {"_not": "T1.7 style-guard ratchet — kanonik-degerli ham hex, dosya basina TAVAN. "
                     "Sayim yalniz DUSEBILIR; artis deploy'u bloklar. Yeni token eklenince "
                     "token_imzasi degisir ve bu dosya --baseline ile yenilenir. "
                     "'dosyalar' anahtari sayfa sablonlarini + EK_HEX_DOSYALARI'ni "
                     "(blog_content.py, harici css) birlikte tasir.",
             "token_imzasi": imza,
             "dosyalar": dict(sorted(hex_sayim.items())),
             "yerel_root": dict(sorted(yerel_root_sayim().items())),
             "bos_catch": dict(sorted(bos_catch_sayim().items())),
             "olu_palet": dict(sorted(olu_sayim.items()))},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print("baseline yazildi: %d dosya (K-B), toplam %d kanonik-degerli ham hex; "
              "K-E olu palet: %d dosya / %d occurrence"
              % (toplam_hex_dosya, sum(hex_sayim.values()),
                 len(olu_sayim), sum(olu_sayim.values())))
        return 0

    hata = 0
    print("style-guard  (kapsam: %d sayfa sablonu / %d dosya K-B, %d kanonik token degeri)"
          % (toplam_sayfa, toplam_hex_dosya, len(harita)))

    # ── K-A: tanimsiz var() — BLOKLAYICI ────────────────────────────────────
    if tanimsiz:
        hata = 1
        print("  KIRIK  K-A tanimsiz var(): %d sayfada" % len(tanimsiz))
        for ad in sorted(tanimsiz):
            for tok, n in sorted(tanimsiz[ad].items()):
                print("         %-28s %-24s %d kullanim" % (ad, tok, n))
        print("         Bu token o sayfada GORUNUR degil; deger sessizce bosa duser.")
        print("         Tarayici hata vermez, HTTP 200 doner, grep token adini BULUR.")
    else:
        print("  TEMIZ  K-A tanimsiz var(): %d/%d sayfada 0" % (toplam_sayfa, toplam_sayfa))

    # ── K-B: ham hex ratchet — ARTAMAZ ──────────────────────────────────────
    try:
        ratchet = json.loads(RATCHET.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("  ATLANDI K-B ham hex ratchet: %s yok — once `--baseline` calistirin." % RATCHET.name)
        print("         (Bu bir SESSIZ ATLAMA degil: acikca raporlanir ve deploy'u bloklamaz,")
        print("          ama kapinin bu yarisi devrede DEGILDIR.)")
        return hata

    taban = ratchet.get("dosyalar", {})
    artan = []
    for ad, n in sorted(hex_sayim.items()):
        t = taban.get(ad)
        if t is None:
            if n > 0:
                artan.append((ad, 0, n, "YENI DOSYA"))
        elif n > t:
            artan.append((ad, t, n, ""))
    if ratchet.get("token_imzasi") != imza:
        print("  UYARI  K-B: kanonik token kumesi DEGISTI (tokens.css'e token eklendi/cikarildi).")
        print("         Sayimlar sablon degismeden kayabilir — dogruladiktan sonra `--baseline`.")
    if artan:
        hata = 1
        print("  KIRIK  K-B ham hex ARTTI: %d dosya" % len(artan))
        for ad, t, n, not_ in artan:
            print("         %-28s %d -> %d  %s" % (ad, t, n, not_))
        print("         Token'i olan renk ham hex yazilmis. `var(--bp-*)` kullanin.")
        print("         Mevcut borc bloklamaz; YENI borc bloklar (kademeli kapi).")
    else:
        toplam = sum(hex_sayim.values())
        tt = sum(taban.values())
        print("  TEMIZ  K-B ham hex ratchet: %d occurrence (taban %d, artis yok)" % (toplam, tt))

    # ── K-C: sablon-yerel :root ratchet — ARTAMAZ ───────────────────────────
    yr = yerel_root_sayim()
    yr_taban = ratchet.get("yerel_root")
    if yr_taban is None:
        print("  ATLANDI K-C yerel :root: ratchet'te taban yok — `--baseline` calistirin.")
    else:
        yr_artan = [(ad, yr_taban.get(ad, 0), n) for ad, n in sorted(yr.items())
                    if n > yr_taban.get(ad, 0)]
        if yr_artan:
            hata = 1
            print("  KIRIK  K-C sablon-yerel :root ARTTI: %d dosya" % len(yr_artan))
            for ad, t, n in yr_artan:
                print("         %-28s %d -> %d" % (ad, t, n))
            print("         Yerel :root tokens.css'i O SAYFADA sessizce ezer.")
            print("         Yeni token TANIMI tokens.css'e; sayfaya DEGIL.")
        else:
            print("  TEMIZ  K-C yerel :root: %d sablon (taban %d, artis yok)"
                  % (sum(yr.values()), sum(yr_taban.values())))

    # ── K-D: bos catch{} ratchet — ARTAMAZ ──────────────────────────────────
    bc = bos_catch_sayim()
    bc_taban = ratchet.get("bos_catch")
    if bc_taban is None:
        print("  ATLANDI K-D bos catch{}: ratchet'te taban yok — `--baseline` calistirin.")
    else:
        bc_artan = [(ad, bc_taban.get(ad, 0), n) for ad, n in sorted(bc.items())
                    if n > bc_taban.get(ad, 0)]
        if bc_artan:
            hata = 1
            print("  KIRIK  K-D bos catch{} ARTTI: %d dosya" % len(bc_artan))
            for ad, t, n in bc_artan:
                print("         %-28s %d -> %d" % (ad, t, n))
            print("         catch bloğu hatayi sessizce yutuyor. En az console.warn/log ekleyin.")
            print("         Mevcut borc bloklamaz; YENI borc bloklar (kademeli kapi).")
        else:
            print("  TEMIZ  K-D bos catch{}: %d occurrence (taban %d, artis yok)"
                  % (sum(bc.values()), sum(bc_taban.values())))

    # ── K-E: olu palet ratchet — ARTAMAZ ────────────────────────────────────
    op_taban = ratchet.get("olu_palet")
    if op_taban is None:
        print("  ATLANDI K-E olu palet: ratchet'te taban yok — `--baseline` calistirin.")
    else:
        ohex, _orgb = olu_palet_haritasi(harita)
        op_artan = [(ad, op_taban.get(ad, 0), n) for ad, n in sorted(olu_sayim.items())
                    if n > op_taban.get(ad, 0)]
        if op_artan:
            hata = 1
            print("  KIRIK  K-E olu palet ARTTI: %d dosya" % len(op_artan))
            for ad, t, n in op_artan:
                print("         %-28s %d -> %d" % (ad, t, n))
            print("         Eski paletten (GitHub-dark/Tailwind) bir renk yazilmis.")
            print("         Halefleri: " + ", ".join(
                "%s->%s" % (v, ohex[v][0]) for v in sorted(ohex)))
            print("         K-B bu sinifi YAPISAL OLARAK goremez (deger hicbir token'a esit degil).")
        else:
            print("  TEMIZ  K-E olu palet: %d occurrence (taban %d, artis yok)"
                  % (sum(olu_sayim.values()), sum(op_taban.values())))

    if verbose:
        print("\n  %-32s %6s %6s" % ("dosya", "hex", "taban"))
        for ad, n in sorted(hex_sayim.items(), key=lambda kv: -kv[1]):
            print("  %-32s %6d %6s" % (ad, n, taban.get(ad, "-")))

    return hata


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
