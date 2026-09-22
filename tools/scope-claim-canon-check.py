#!/usr/bin/env python3
"""KAPI 80 -- K-DN: SAYFANIN KENDI VERI KUMESI ICIN YAPTIGI KAPSAM IDDIASI.

KANAL: her sablonun `<title>` / `og:title` / `twitter:title` /
`description` uclusu ve `<h1>` -- yani sayfanin "ben neyi kapsiyorum"
cumlesini kurdugu yerler. 79 kapinin hicbiri bunlari BIRBIRIYLE
karsilastirmiyordu (kapi 57 head-meta'nin VARLIGINI olcer, icerigini degil).

BULDUGU (K-DN, canli 22.09 -- /temettu-takvimi):
  backend `_dividend_refresh_impl` ornegi `BIST30_LITERAL` (app.py, hiz/
  rate-limit gerekcesi) -> API 28 hisse donuyordu. Sayfanin GORUNUR her
  yuzeyi ise BIST GENELINI vaat ediyordu:
     <title>  "... BIST Temettü Tarihleri ve Tutarları"
     <h1>     "BIST Temettü (Ex-Temettü) Takvimi"
     cip      "Toplam Hisse" -> 28   (sitenin evreni 217)
  Dogru kapsami soyleyen TEK yer `meta description` ("BIST30
  şirketlerinin...") idi -- yani kullaniciya GORUNMEYEN yer. Kardes sayfa
  /bilanco-takvimi ayni kabukta 216 hisse servis ediyor, dolayisiyla site
  icinde gezen kullanici icin iki takvim ayni evreni kapsiyormus gibi
  duruyordu.

IKI KURAL
  R1 (tek kanon): bir sablonun kapsam iddialari AYNI SINIFTAN olmalidir.
     Sinif: "DAR" = BIST30 anilmis; "GENEL" = BIST/BIST100 anilmis, 30 yok.
     Ayni sablonda ikisi birden -> ihlal. (Gercek regresyon: `--ref 509c33a`)
  R2 (gorunurluk): kapsam iddiasi DAR ise, ayni sinif GORUNUR GOVDEDE de
     gecmelidir. Yalnizca <head> meta'sinda -- ya da yalnizca `sr-only` bir
     baslikta -- dogru olmak, EKRANA BAKAN kullaniciya yalan soylemeye devam
     etmektir; K-DN'in cekirdegi tam olarak buydu (dogru kapsami soyleyen tek
     yer `meta description` idi).

OLCUM NOTLARI
  * 77. ders (yorumlar yayimlanmaz): Jinja `{# #}`, HTML `<!-- -->` ve
    `<script>` bloklari R2'nin govde metninden DUSURULUR. Aksi halde bu
    dosyanin en ustundeki aciklama yorumu bile kapiyi gecirirdi.
  * `class="sr-only"` ogeler de DUSURULUR: ekran okuyucuya soylenen kapsam
    GORSEL kullaniciya soylenmis sayilmaz. (/temettu-takvimi'nin h1'i sr-only
    -- R2 onu kanit kabul etseydi K-DN bulgusunun yarisi kapiyi gecerdi.)
  * `meta name="keywords"` MUAF: SEO anahtar listesi sayfanin veri kumesi
    hakkinda bir iddia degil, arama terimi kovasidir (index.html "BIST100
    sinyalleri, BIST30 teknik analiz" ikisini birden tasir ve bu dogrudur).
  * "BIST 30"/"BIST-30"/"BIST30" ve "BIST 100"/"BIST100" yazimlarinin hepsi
    yakalanir (164. ders: kapi hatanin YAZIMINI degil kendisini aramali).

Kullanim: python3 tools/scope-claim-canon-check.py [--verbose] [--ref GIT_REF]
          python3 tools/scope-claim-canon-check.py --self-test
Cikis: ihlal varsa 1.
"""
import re, sys, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL  = ROOT / "templates"

RE_DAR   = re.compile(r"BIST[\s\-]?30\b")
RE_GENEL = re.compile(r"\bBIST(?:[\s\-]?100)?\b(?![\s\-]?30)")

RE_TITLE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
RE_H1    = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.S | re.I)
RE_META  = re.compile(
    r"""<meta\s+[^>]*?(?:name|property)\s*=\s*["'](?P<key>[^"']+)["'][^>]*?"""
    r"""content\s*=\s*["'](?P<val>[^"']*)["']""", re.I)

# Sayfanin KENDI veri kumesi hakkindaki iddiayi tasiyan meta anahtarlari.
META_SCOPE_KEYS = {
    "description", "og:description", "twitter:description",
    "og:title", "twitter:title",
}
# Muaf: arama terimi kovasi, sayfanin kapsam iddiasi degil (bkz. docstring).
META_EXEMPT = {"keywords"}

RE_JINJA_CMT  = re.compile(r"\{#.*?#\}", re.S)
RE_HTML_CMT   = re.compile(r"<!--.*?-->", re.S)
RE_SCRIPT     = re.compile(r"<script\b.*?</script>", re.S | re.I)
RE_HEAD_BLOCK = re.compile(r"\{%\s*block\s+head\s*%\}.*?\{%\s*endblock\s*%\}", re.S)
# <title>/<meta> tanimi geregi HEAD ogesidir -- `{% block head %}` sarmalayicisi
# olmayan parcalarda (self-test fixture'lari) da govdeden dusurulmeleri gerekir.
RE_HEAD_EL    = re.compile(r"<title\b.*?</title\s*>|<meta\b[^>]*>", re.S | re.I)
RE_TAG        = re.compile(r"<[^>]+>")
# Ekran okuyucuya ozel ogeler -- gorsel kullanici bunlari GORMEZ.
RE_SR_ONLY    = re.compile(
    r"""<(?P<t>[a-zA-Z0-9]+)\b[^>]*class\s*=\s*["'][^"']*\bsr-only\b[^"']*["'][^>]*>"""
    r"""(?:(?!</(?P=t)\b).)*?</(?P=t)\s*>""", re.S)


def _sinif(metin):
    """Metnin tasidigi kapsam siniflarini dondurur."""
    out = set()
    if RE_DAR.search(metin):
        out.add("DAR")
    if RE_GENEL.search(metin):
        out.add("GENEL")
    return out


def _iddialar(src):
    """(kaynak_adi, metin) ciftleri -- yalnizca kapsam iddiasi tasiyanlar."""
    found = []
    for m in RE_TITLE.finditer(src):
        found.append(("<title>", RE_TAG.sub(" ", m.group(1))))
    for m in RE_H1.finditer(src):
        found.append(("<h1>", RE_TAG.sub(" ", m.group(1))))
    for m in RE_META.finditer(src):
        key = m.group("key").lower()
        if key in META_EXEMPT or key not in META_SCOPE_KEYS:
            continue
        found.append(('meta[%s]' % key, m.group("val")))
    return [(k, v) for k, v in found if _sinif(v)]


def _govde_metni(src):
    """GORUNUR govde metni: head blogu, yorumlar, script ve sr-only dusurulur."""
    s = RE_HEAD_BLOCK.sub(" ", src)
    s = RE_HEAD_EL.sub(" ", s)
    s = RE_JINJA_CMT.sub(" ", s)
    s = RE_HTML_CMT.sub(" ", s)
    s = RE_SCRIPT.sub(" ", s)
    s = RE_SR_ONLY.sub(" ", s)
    s = RE_TAG.sub(" ", s)
    return s


def denetle(kaynak, verbose=False):
    """kaynak: {dosya_adi: icerik}. Ihlal listesi dondurur."""
    ihlaller = []
    for ad in sorted(kaynak):
        src = kaynak[ad]
        idd = _iddialar(src)
        if not idd:
            continue
        siniflar = set()
        for _, v in idd:
            siniflar |= _sinif(v)
        if verbose:
            print("  %-28s %s" % (ad, " ".join(sorted(siniflar))))
            for k, v in idd:
                print("      %-24s %s" % (k, v.strip()[:110]))
        # R1 -- tek kanon
        if siniflar == {"DAR", "GENEL"}:
            dar   = [k for k, v in idd if "DAR"   in _sinif(v)]
            genel = [k for k, v in idd if "GENEL" in _sinif(v)]
            ihlaller.append(
                "%s R1: ayni sayfa iki kapsam sinifi iddia ediyor -- "
                "DAR=%s vs GENEL=%s" % (ad, ",".join(dar), ",".join(genel)))
        # R2 -- gorunurluk
        if "DAR" in siniflar and not RE_DAR.search(_govde_metni(src)):
            ihlaller.append(
                "%s R2: kapsam DAR (BIST30) ama bunu yalniz <head> soyluyor; "
                "gorunur govdede (sr-only haric) kapsam ifadesi yok" % ad)
    return ihlaller


def _oku_disk():
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(TPL.glob("*.html"))}


def _oku_ref(ref):
    out = {}
    names = subprocess.run(["git", "ls-tree", "--name-only", "%s:templates" % ref],
                           cwd=ROOT, capture_output=True, text=True).stdout.split()
    for n in names:
        if not n.endswith(".html"):
            continue
        r = subprocess.run(["git", "show", "%s:templates/%s" % (ref, n)],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode == 0:
            out[n] = r.stdout
    return out


SELF = [
    # (ad, kaynak, beklenen_ihlal_sayisi)
    ("temiz-genel",
     '<title>Bilanço — BIST Sonuç Tarihleri</title>'
     '<meta name="description" content="BIST şirketlerinin (BIST100 + ek hisseler) dönemleri.">'
     '<h1>BIST Bilanço Takvimi</h1><p>BIST şirketleri</p>', 0),
    ("temiz-dar",
     '<title>BIST30 Temettü Takvimi</title>'
     '<meta name="description" content="BIST30 şirketlerinin ex-temettü tarihleri.">'
     '<h1 class="sr-only">BIST30 Temettü Takvimi</h1>'
     '<p>Bu takvim BIST30 şirketlerini kapsar.</p>', 0),
    ("r1-gercek-hata (K-DN oncesi /temettu-takvimi)",
     '<title>Temettü Takvimi — BIST Temettü Tarihleri</title>'
     '<meta name="description" content="BIST30 şirketlerinin ex-temettü tarihleri.">'
     '<h1 class="sr-only">BIST Temettü Takvimi</h1><p>Yahoo Finance kaynaklı.</p>', 2),
    ("r2-yalniz-head + sr-only h1",
     '<title>BIST30 Temettü Takvimi</title>'
     '<meta name="description" content="BIST30 şirketleri.">'
     '<h1 class="sr-only">BIST30 Temettü Takvimi</h1><p>Yahoo Finance kaynaklı.</p>', 1),
    ("r2-yalniz-yorumda (77. ders)",
     '<title>BIST30 Temettü</title><h1 class="sr-only">BIST30 Temettü</h1>'
     '{# BIST30 kapsami burada anlatiliyor #}<p>Yahoo Finance.</p>', 1),
    ("r2-yalniz-script-icinde",
     '<title>BIST30 Temettü</title><h1 class="sr-only">BIST30 Temettü</h1>'
     '<script>var t = "BIST30 kapsam";</script><p>Yahoo.</p>', 1),
    ("keywords-muaf (index.html deseni)",
     '<title>BorsaPusula — BIST Sinyalleri</title>'
     '<meta name="keywords" content="BIST100 sinyalleri, BIST30 teknik analiz">'
     '<h1>BIST Sinyalleri</h1><p>BIST hisseleri</p>', 0),
    ("yazim-varyantlari (164. ders)",
     '<title>BIST 30 Temettü</title>'
     '<meta name="description" content="BIST-30 şirketleri.">'
     '<h1 class="sr-only">BIST Temettü</h1><p>BIST 30 kapsar</p>', 1),
    ("kapsam-iddiasi-yok",
     '<title>İletişim | BorsaPusula</title><h1>İletişim</h1><p>Bize yazın.</p>', 0),
    ("og-twitter-de-okunur",
     '<title>BIST30 Temettü</title>'
     '<meta property="og:title" content="BIST Temettü Takvimi">'
     '<h1 class="sr-only">BIST30 Temettü</h1><p>BIST30 kapsar</p>', 1),
]


def self_test():
    ok = 0
    for ad, src, bekle in SELF:
        n = len(denetle({ad: src}))
        dr = "PASS" if n == bekle else "FAIL"
        if n == bekle:
            ok += 1
        else:
            print("  %s %-44s bekleniyordu %d, cikti %d" % (dr, ad, bekle, n))
            for i in denetle({ad: src}):
                print("        -> %s" % i)
    print("self-test %d/%d" % (ok, len(SELF)))
    return 0 if ok == len(SELF) else 1


def main():
    args = sys.argv[1:]
    if "--self-test" in args:
        sys.exit(self_test())
    verbose = "--verbose" in args
    ref = None
    if "--ref" in args:
        ref = args[args.index("--ref") + 1]
    kaynak = _oku_ref(ref) if ref else _oku_disk()
    print("KAPI 80 -- kapsam iddiasi tek kanon (%s, %d sablon)"
          % (ref or "calisan agac", len(kaynak)))
    ihlaller = denetle(kaynak, verbose)
    for i in ihlaller:
        print("  IHLAL: %s" % i)
    print("  ihlal: %d" % len(ihlaller))
    sys.exit(1 if ihlaller else 0)


if __name__ == "__main__":
    main()
