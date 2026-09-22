#!/usr/bin/env python3
"""tools/head-meta-check.py -- KAPI 57 (K-CL): <head> META KANALI + OG GORSELI

56 kapinin hicbiri `<head>` icindeki META DEGERLERINI ve `/og-image.*`
rotalarinin CIZDIGI METNI bir kanal olarak okumuyordu:

  * kapi 50 (`intraday-claim-check`) yalniz `templates/**.html` -- ama
    desenleri "canlı fiyat|hisse veri|borsa veri" ile SINIRLI;
    "canlı güncelleme" desene HIC takilmiyordu.
  * kapi 52 (`app-published-text-check`) `app.py`'nin yayimlanan metnini
    okuyor -- ama kurallari sozluk (Premium/💎/skor adi), tazelik DEGIL.
  * kapi 53/54/55/56 JS / manifest / robots / sitemap kanallari.

Oysa `<head>`, urunun EN GENIS DAGITIMLI metnidir: Google snippet'i,
WhatsApp/X/LinkedIn onizleme karti, AI motorlarinin ozet girdisi. Ve
`og:image` bir METIN YUZEYIDIR: PIL ile 1200x630 PNG'ye yazilan 8 dize.

K-CL'DE BULUNAN 4 IHLAL (canli olculdu 22.09 09:3x)
----------------------------------------------------
1) **"Algoritmik, ücretsiz, canlı güncelleme"** -- her iki og-image
   rotasinda. Mimari EOD-only; `blog_content.py:919` SSS'i AYNEN
   "gün içi canlı takip sunmaz" diyor. Urunun kendi SSS'i ile onizleme
   kartinin sloganı BIREBIR CELISIYORDU. Cift korluk: yanlis kanal
   (kapi 50 .html tarar) VE yanlis desen (RE_CANLI "güncelleme"yi almaz).

2) **`216` sayisinin altinda "BIST100 HİSSE"** -- `_og_image_stats()`
   `total`'i XU030 haric TUM takip evreni olarak sayiyor (canli: 216).
   BIST100 100 hissedir; sitenin kendi kanonu 8 sablonda "BIST100 +
   ek hisseler". Etiket sayidigi kumeden DAR bir endeksi adlandiriyordu.

3) **Alt baslikta `{today_s}` = `datetime.now()`** -- veri bir onceki
   EOD turundan gelir. Olculdu: gorsel "22.09.2026" yazarken
   `/api/data.updated_at` = "21.09.2026 18:22". Gunun ~22 saatinde yalan.
   AYRICA `og:image` URL'i versiyonsuz; Facebook/WhatsApp/X karti URL'e
   gore onbellekler -> DOGRU tarih bile onbellekte KALICI yalana doner
   (86. ders). Cozum: tarihi tumuyle kaldir.

4) **`templates/hisse.html:17` `<meta name="keywords"> ... al sat`** --
   217 hisse sayfasinin tamaminda. AL-SAT terimi Ozan'in KALICI yasagi
   (09.09, SPK konumlanmasi). `tests/audit/kalici-kurallar-check.sh` K3
   yalniz 3 sabit ifadeyi ariyor (`>AL Sinyalleri<`, `ORTA|GÜÇLÜ|ZAYIF
   SAT`, `al mı sat`) -- " al sat," hicbirine uymuyordu. Hafizadaki
   "K3 kapsami DAR" uyarisinin somut karsiligi.

KURALLAR
--------
R1  Meta degerlerinde ve og-image metninde gun-ici/canli tazelik iddiasi
    olamaz (EOD-only mimari, K-CE kanonu).
R2  Meta degerlerinde ve og-image metninde AL-SAT sozlugu olamaz (kalici).
R3  og-image metni render-zamani tarihi (`datetime.now()` turevi)
    BASAMAZ -- URL versiyonsuz oldugu icin platform onbelleginde donar.
R4  Indekslenebilir sablon (robots noindex YOK) canonical + og:title +
    og:description + og:image TASIMALI.
R5  Sablonlarin ilan ettigi og:image:width/height, rotanin GERCEKTEN
    urettigi tuval olculeriyle ayni olmali (89. ders: iki alan ayni
    olguyu anlatiyorsa birbirine karsi olcul).
R6  `/og-image.svg` ve `/og-image.png` AYNI metin kumesini yayinlamali --
    tek urun, tek kanon. (Merceğin tekrar eden P1'i: "ayni is icin iki
    kanon basli basina bulgudur".)
R7  og-image'daki KISA etiketler (<=25 karakter, sayilarin altina cizilen
    kutu etiketleri) bir endeks adi (`BIST<sayi>`) TASIYAMAZ -- sayilan
    kume XU030 haric TUM evren. Kapi kor kalmasin diye `_og_image_stats`
    hala bu kumeyi saydigi da dogrulanir (R7a).

Kullanim:
    python3 tools/head-meta-check.py
    python3 tools/head-meta-check.py --verbose
    python3 tools/head-meta-check.py --ref ee2a473   # 7 ihlal beklenir (R1x2/R2/R3x2/R7x2)
"""
import ast
import re
import xml.dom.minidom
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- R1
# Kapi 50'nin desenleri + bu turda bulunan bosluk ("canlı güncelleme").
# "gün içinde" sure zarfidir, "anlık kayıt/görüntü/kare" snapshot'tir.
RE_INTRADAY = [
    (re.compile(r"gün[\s\-]?içi(?!nde)", re.I), "gün içi"),
    (re.compile(r"anlık\s+(?!kayıt|kaydı|kaydını|görüntü|görüntüsü|kare|karesi)"
                r"[a-zçğıöşü]", re.I), "anlık <finansal isim>"),
    (re.compile(r"gerçek\s+zamanlı", re.I), "gerçek zamanlı"),
    (re.compile(r"canlı\s+(fiyat|veri|borsa|hisse|güncelle|takip|akış|yayın)", re.I),
     "canlı <veri/güncelleme/takip>"),
    (re.compile(r"(sürekli|aralıksız|kesintisiz)\s+güncelle", re.I), "sürekli güncelleme"),
    (re.compile(r"\b7\s*/\s*24\b"), "7/24"),
]

# ---------------------------------------------------------------- R2
# Ozan 09.09 (kalici): "AL-SAT terimlerini hic bir zaman kullanmayacagiz".
RE_ALSAT = [
    (re.compile(r"\bal[\s\-]sat\b", re.I), "al sat / al-sat"),
    (re.compile(r"\bal\s+mı\s+sat\b", re.I), "al mı sat"),
    (re.compile(r"\b(al|sat)\s+sinyal(i|leri)\b", re.I), "AL/SAT sinyali"),
    (re.compile(r"\b(ORTA|GÜÇLÜ|ZAYIF)\s+SAT\b"), "ORTA/GÜÇLÜ/ZAYIF SAT"),
]

# ---------------------------------------------------------------- R4
REQUIRED_META = [
    ('rel="canonical"', re.compile(r'rel=["\']canonical["\']')),
    ("og:title", re.compile(r'property=["\']og:title["\']')),
    ("og:description", re.compile(r'property=["\']og:description["\']')),
    ("og:image", re.compile(r'property=["\']og:image["\']')),
]
RE_NOINDEX = re.compile(r'name=["\']robots["\'][^>]*noindex', re.I)

# ---------------------------------------------------------------- R8
# CPO-1767 madde 1: og gorselinin ICERIGI her EOD turunda degisiyor ama URL
# sabitti (/og-image.png); Facebook/WhatsApp/X karti URL'e gore onbellekler,
# kart ILK taramanin fotografinda donuyordu. Kanon: `{{ og_image_url }}`
# (app.py `_inject_og_image_url` -> `?d=YYYYMMDD`, EOD veri tarihinden).
# Bu kural SABIT yazimi arar -- R3 gibi metni degil, URL'in kendisini.
RE_STATIC_OG_URL = re.compile(r"/og-image\.(?:png|svg)(?![?\w])")
RE_OG_CANON = re.compile(r"\{\{\s*og_image_url\s*\}\}")

# Meta DEGERI tasiyan satirlar (yalniz `content="..."` ve <title>).
RE_META_CONTENT = re.compile(
    r'<meta\s+(?:name|property)=["\'](?P<key>[^"\']+)["\'][^>]*?'
    r'content=["\'](?P<val>[^"\']*)["\']', re.I)
RE_TITLE = re.compile(r"<title>(?P<val>.*?)</title>", re.S)

# Jinja ifadelerini metinden dusur -- degeri degil SABIT kopyayi tariyoruz.
RE_JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.S)


def _read(ref, relpath):
    if ref:
        return subprocess.run(["git", "show", f"{ref}:{relpath}"], cwd=ROOT,
                              capture_output=True, text=True).stdout
    return (ROOT / relpath).read_text(encoding="utf-8")


def _route_body(app_src, route):
    """`@app.route(route)` ile suslenmis fonksiyonun KAYNAK GOVDESI.

    ⛔ 85/57. dersin tekrari: kapinin ILK yazimi bunu regex ile
    `(?=\n@app\.route|\n@?def\s)` diye yazdi ve govdeyi `@limiter.limit`
    satirinda KESTI -- 0 dize ayristi, kapi "OK" dedi ve HICBIR SEY olcmedi.
    Bu yuzden ayristirma `ast` ile yapilir ve `--verbose` ayristirilan dize
    SAYISINI basar (sifir gorulunce kapi kor demektir).
    """
    try:
        tree = ast.parse(app_src)
    except SyntaxError:
        return ""
    lines = app_src.splitlines(keepends=True)
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if (isinstance(dec, ast.Call) and dec.args
                    and isinstance(dec.args[0], ast.Constant)
                    and dec.args[0].value == route):
                return "".join(lines[node.lineno - 1:node.end_lineno])
    return ""


def _svg_texts(body):
    """SVG <text ...>GOVDE</text> govdeleri.

    K-DB (22.09): govdedeki IC ETIKETLER (<tspan fill=...>) SOYULUR. Marka
    sozcuk-isareti `<text>Borsa<tspan>Pusula</tspan></text>` olarak yazilir --
    soyulmazsa R6 bu yuzeyi PNG'deki "BorsaPusula" ile hic eslestiremez ve
    kapi kendi isaretleme bicimi yuzunden sahte-pozitif uretir."""
    out = []
    for t in re.findall(r"<text\b[^>]*>(.*?)</text>", body, re.S):
        out.append(re.sub(r"<[^>]+>", "", t).strip())
    return out


def _png_texts(body):
    """draw.text(...) ve (x, "sayi", "ETIKET", renk) tuple'larindaki insan metni."""
    out = []
    for m in re.finditer(r"draw\.text\(\s*\([^)]*\)\s*,\s*f?[\"'](.*?)[\"']", body, re.S):
        out.append(m.group(1))
    # boxes = [(60, str(al_count), "▲ GÜÇLÜ TREND", "#3fb950"), ...]
    for m in re.finditer(r"\(\s*\d+\s*,\s*str\([^)]*\)\s*,\s*[\"'](.*?)[\"']", body):
        out.append(m.group(1))
    # for text, color in [("BIST", "#f0f6fc"), ("100", "#58a6ff"), ...]
    # -- baslik PNG tarafinda dongude cizilir; ILK yazim bunu KACIRDI ve R6
    #    3 sahte-pozitif uretti (57. ders: dar cikarim, muafiyeti beyan et).
    for m in re.finditer(r"\(\s*[\"'](.*?)[\"']\s*,\s*[\"']#[0-9a-fA-F]{3,8}[\"']\s*\)", body):
        out.append(m.group(1))
    # font_family / tuple icinde gecen renk kodlarini disla
    return [t.strip() for t in out if not t.startswith("#")]


def _og_title(app_src):
    """K-DB: baslik artik IKI rotada da `_OG_TITLE_PARTS`tan turuyor; rota
    govdesinde literal olarak GECMEZ. Modul sabitinden cozulur, boylece R6
    her iki yuzeyde de AYNI tek metni gorur."""
    m = re.search(r"_OG_TITLE_PARTS\s*=\s*\((.*?)\)\n", app_src, re.S)
    if not m:
        return None
    return "".join(re.findall(r'\("([^"]+)"\s*,\s*"[a-z0-9_]+"\)', m.group(1)))


def _norm(t):
    """Placeholder'lari dusur, bosluklari sikistir -- iki rotayi kiyaslamak icin."""
    t = re.sub(r"\{[^{}]*\}", "•", t)
    return re.sub(r"\s+", " ", t).strip()


def main():
    argv = sys.argv[1:]
    ref = argv[argv.index("--ref") + 1] if "--ref" in argv else None
    verbose = "--verbose" in argv
    out = []

    # ---------------- og-image rotalari ----------------
    app_src = _read(ref, "app.py")
    svg_body = _route_body(app_src, "/og-image.svg")
    png_body = _route_body(app_src, "/og-image.png")
    if not svg_body or not png_body:
        print("  [R0] og-image rotalari bulunamadi -- kapi kor, ayristirici guncellenmeli")
        return 1

    _title = _og_title(app_src)
    _t = [_title] if _title else []
    og_surfaces = [("/og-image.svg", svg_body, _svg_texts(svg_body) + _t),
                   ("/og-image.png", png_body, _png_texts(png_body) + _t)]

    for name, body, texts in og_surfaces:
        for t in texts:
            for rx, label in RE_INTRADAY:
                if rx.search(t):
                    out.append(("R1", name, f'"{t}" -> {label} (mimari EOD-only)'))
            for rx, label in RE_ALSAT:
                if rx.search(t):
                    out.append(("R2", name, f'"{t}" -> {label} (kalici yasak, 09.09)'))
            # R3: render-zamani tarihi basiliyor mu?
            if re.search(r"\{[^{}]*(today|now|tarih|date)[^{}]*\}", t, re.I):
                out.append(("R3", name,
                            f'"{t}" -> render-zamani tarihi basiyor; veri onceki EOD '
                            f"turundan gelir ve og:image URL'i versiyonsuz (platform "
                            f"onbelleginde kalici yalan)"))
            # R7: kisa kutu etiketi endeks adlandiramaz
            if len(t) <= 25 and re.search(r"BIST\s*\d+", t, re.I):
                out.append(("R7", name,
                            f'"{t}" -> kutu etiketi endeks adlandiriyor; sayilan kume '
                            f"XU030 haric TUM evren (kanon: 'BIST100 + ek hisseler')"))

    # R9 (K-DB, 22.09) -- /og-image.svg IYI-BICIMLI XML MI?
    #   Rota bir f-string ile elle kuruluyor; sablon motoru yok, dolayisiyla
    #   hicbir sey iyi-bicimliligi dogrulamiyordu. K-DB sirasinda tam da bu
    #   sinifta bir kusur URETILDI: aciklama yorumuna token adi yazildi ve
    #   XML yorumu ICINDE IKI TIRE YAN YANA gecemedigi icin belge bozuldu
    #   (olculdu: expat "not well-formed", satir 5). Tarayici bagislar, kati
    #   ayristirici (ve bazi paylasim onizleyicileri) bagislamaz.
    #   Kapi rotayi vekil sayilarla render edip ayristirir.
    try:
        _ns = {}
        _pal = app_src[app_src.index("_OG_PALETTE = {"):]
        exec(_pal[:_pal.index(chr(10) + "}" + chr(10)) + 3], _ns)
        _tp = app_src.index("_OG_TITLE_PARTS =")
        exec(app_src[_tp:app_src.index(chr(10), app_src.index("_OG_SUBTITLE", _tp)) + 1], _ns)
        _stat = "    al_count, sat_count, total, _today_unused = _og_image_stats()"
        _i = app_src.index(_stat, app_src.index('@app.route("/og-image.svg")'))
        _j = app_src.index("</svg>", _i) + len("</svg>") + 3   # + kapatan uclu tirnak
        _body = app_src[_i:_j].replace(
            _stat.strip(), "al_count, sat_count, total = 7, 72, 216")
        exec("def _r():" + chr(10) + _body + chr(10) + "    return svg" + chr(10), _ns)
        xml.dom.minidom.parseString(_ns["_r"]())
    except Exception as exc:
        out.append(("R9", "/og-image.svg",
                    "rota iyi-bicimli XML uretmiyor / ayristirilamadi: %s" % exc))

    # R7b (K-DB, 22.09) -- BIR KURAL, PARCA PARCA CIZILEN METNI GORMEZ.
    #   R7 ("kisa kutu etiketi endeks adlandiramaz") 22.09'a kadar HIC
    #   tetiklenmemisti, oysa tam da onun tarif ettigi kusur kartin BASLIGINDA
    #   duruyordu: "BIST100 Sinyal Paneli" -- ayni gorselin ucuncu kutusu
    #   "216 TAKIP EDILEN HISSE" diyordu (XU030 haric TUM evren). Kural
    #   gormedi cunku baslik UC AYRI parcadan ciziliyordu: ("BIST"),("100"),
    #   (" Sinyal Paneli") -- hicbir parca tek basina `BIST\s*\d+` degil.
    #   36. dersin ikizi: AYNI ISIN PARCALANMIS HALI AYRI BIR YAZIMDIR.
    #   Cozum: her yuzeyde ardisik parcalarin 2- ve 3-gram birlesimleri de
    #   ayni kurala sokulur. `len<=25` esigi korunur -- kanonik kapsam
    #   ifadesi ("BIST100 + ek hisseler", 21+ karakterlik cumle icinde)
    #   uzun oldugu icin tetiklenmez, kisa endeks etiketi tetiklenir.
    for name, body, texts in og_surfaces:
        frags = [t for t in texts if t]
        for n in (2, 3):
            for i in range(len(frags) - n + 1):
                joined = "".join(frags[i:i + n]).strip()
                if len(joined) <= 25 and re.search(r"BIST\s*\d+", joined, re.I):
                    out.append(("R7b", name,
                                f'"{joined}" -> PARCA PARCA cizilen baslik endeks '
                                f"adlandiriyor ({n} parca); sayilan kume XU030 haric "
                                f"TUM evren (kanon: 'BIST100 + ek hisseler')"))

    # R7a -- kapinin oncüllü hala gecerli mi (kapi kor kalmasin)
    stats = re.search(r"def _og_image_stats\(\):(.*?)(?=\n@|\ndef\s)", app_src, re.S)
    if not stats or 'ticker"] != "XU030"' not in stats.group(1):
        out.append(("R7a", "_og_image_stats",
                    "sayim kumesi degismis (XU030 haric tum evren degil) -- R7'nin "
                    "oncülü gecersiz, kural gozden gecirilmeli"))

    # R8a -- kapinin oncülü hala gecerli mi: sablonlarin bel bagladigi
    # `og_image_url` degiskenini app.py GERCEKTEN yayinliyor mu? Context
    # processor silinirse Jinja undefined -> og:image "https://borsapusula.com"
    # olur ve R8 (sabit URL arar) bunu GORMEZ -- kapi kor kalir.
    if "og_image_url=" not in app_src or "@app.context_processor" not in app_src:
        out.append(("R8a", "app.py",
                    "`og_image_url` context processor'u yok -- sablonlardaki "
                    "`{{ og_image_url }}` bos render edilir, R8 kor kalir"))

    # R6 -- iki rota AYNI metni yayinlamali.
    # BILEREK MUAF (57. ders -- muafiyeti dosyada ACIKCA beyan et):
    #   "📊"  : PNG'de bilerek YOK. Rotanin kendi yorumu: "mini bar-chart
    #           (emoji yerine, font-bagimsiz)" -- DejaVu emoji glifi tasimaz,
    #           PIL kutu cizerdi. Bu bir SUS tercihi, metin kanonu degil.
    #   "\u2022": sayi placeholder'inin normalize hali ({al_count} vs
    #           str(al_count)) -- DEGER, kopya degil.
    R6_EXEMPT = {"\U0001F4CA", "\u2022"}
    svg_set = {_norm(t) for t in og_surfaces[0][2] if _norm(t)} - R6_EXEMPT
    png_set = {_norm(t) for t in og_surfaces[1][2] if _norm(t)} - R6_EXEMPT
    for only, where in ((svg_set - png_set, "yalniz /og-image.svg"),
                        (png_set - svg_set, "yalniz /og-image.png")):
        for t in sorted(only):
            out.append(("R6", "og-image", f'"{t}" -> {where} (tek urun, tek kanon)'))

    # R5 -- ilan edilen olcu <-> uretilen tuval
    canvas = set()
    m = re.search(r'<svg width="(\d+)" height="(\d+)"', svg_body)
    if m:
        canvas.add((m.group(1), m.group(2)))
    m = re.search(r'Image\.new\(\s*["\']RGB["\']\s*,\s*\((\d+),\s*(\d+)\)', png_body)
    if m:
        canvas.add((m.group(1), m.group(2)))

    if len(canvas) > 1:
        out.append(("R5", "og-image",
                    f"iki rota FARKLI tuval uretiyor {sorted(canvas)} -- "
                    f"og:image:width/height tek bir olcuyu ilan edebilir"))

    # ---------------- sablonlar ----------------
    tpl_dir = ROOT / "templates"
    names = sorted(p.name for p in tpl_dir.glob("*.html") if not p.name.startswith("_"))
    n_meta = 0
    for fname in names:
        src = _read(ref, f"templates/{fname}")
        if not src:
            continue
        head = src[:src.find("{% endblock %}")] if "{% endblock %}" in src else src

        values = [(m.group("key"), m.group("val")) for m in RE_META_CONTENT.finditer(head)]
        tm = RE_TITLE.search(head)
        if tm:
            values.append(("title", tm.group("val")))

        for key, raw in values:
            n_meta += 1
            val = RE_JINJA.sub(" ", raw)
            for rx, label in RE_INTRADAY:
                if rx.search(val):
                    out.append(("R1", f"{fname}:{key}", f'"{val.strip()[:90]}" -> {label}'))
            for rx, label in RE_ALSAT:
                if rx.search(val):
                    out.append(("R2", f"{fname}:{key}",
                                f'"{val.strip()[:90]}" -> {label} (kalici yasak, 09.09)'))
            # ⛔ Kapinin ILK yazimi burada `raw not in {w for w, _ in canvas}`
            #    diyordu: iki rota FARKLI tuval uretse bile ilan edilen 1200
            #    kumede bulundugu icin sentetik ihlal YESIL GECTI. Olcum
            #    curuttu -- R5 artik TEK tuval bekler ve ciftle kiyaslar.
            if canvas and key in ("og:image:width", "og:image:height"):
                idx = 0 if key.endswith("width") else 1
                expect = {c[idx] for c in canvas}
                if raw not in expect or len(canvas) > 1:
                    out.append(("R5", f"{fname}:{key}",
                                f"ilan {raw}, rota(lar) {sorted(canvas)} uretiyor"))

        # R8 -- og gorseli URL'i SABIT olamaz (surumlu kanon zorunlu).
        # Yalniz meta degil TUM kaynak taranir: ayni gorsel JSON-LD
        # ImageObject.url'de de ilan ediliyor (blog_article) -- "ayni is icin
        # iki kanon" orada da dogar.
        for m in RE_STATIC_OG_URL.finditer(src):
            line = src[:m.start()].count("\n") + 1
            out.append(("R8", f"{fname}:{line}",
                        f'"{m.group(0)}" sabit/surumsuz og gorseli URL\'i -- kanon '
                        f"`{{{{ og_image_url }}}}` (platform onbellegi URL-bazli, "
                        f"kart ilk taramada donar)"))

        # R4 -- indekslenebilir sayfa zorunlu meta seti
        if not RE_NOINDEX.search(head):
            for label, rx in REQUIRED_META:
                if not rx.search(head):
                    out.append(("R4", fname, f"indekslenebilir ama {label} YOK"))

    if verbose:
        print(f"  tarandi: {len(names)} sablon / {n_meta} meta degeri, "
              f"og-image {len(svg_set)}+{len(png_set)} dize, tuval {sorted(canvas)}")
    if out:
        for rule, where, msg in out:
            print(f"  [{rule}] {where}: {msg}")
        print(f"  TOPLAM {len(out)} ihlal")
        return 1
    print(f"KAPI 57 OK — <head> meta kanali + og gorseli tutarli "
          f"({n_meta} meta degeri, {len(names)} sablon)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
