# -*- coding: utf-8 -*-
"""T2.2 C sinifi DOGRULAMA — pre-deploy, render bazli, POZITIF KONTROLLU.

Kanit disiplini:
  K-A  Mevcut 16 adopter icin _header.html ciktisi ONCE == SONRA (BIREBIR).
       Payda elle yazilmaz: '_header.html' include eden sablonlardan turetilir.
  K-B  hisseler.html: yeni cikti == ESKI inline header (BIREBIR, davranis korundu).
  K-C  blog_article.html: more-menu 0 -> 12 oge (BUG duzeltmesi, KASITLI degisim),
       ve kaybolan tek sey display:none olan olu .header-right sarmalayicisi.
  K-D  POZITIF KONTROL: kosul gercekten atesleniyor mu? (yanlis deger verildiginde
       link GORUNMELI, dogru degerde GORUNMEMELI)
  K-E  hdr_self HIC verilmemisken render patlamiyor ve link VAR (varsayilan davranis).
  K-F  KOR NOKTA KANITI: `request` Flask'te Jinja global'idir; `request is not defined`
       ASLA dogru olmaz ve istek baglami disinda `request.endpoint` RuntimeError atar.
       Bu yuzden guard request'e DEGIL, parametreye baglandi.
"""
import io
import re
import subprocess
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = sys.argv[1] if len(sys.argv) > 1 else "HEAD"

SELF_RE = re.compile(r'<a href="/hisseler" role="menuitem">')
MENU_RE = re.compile(r'<div class="bp-nav-more-menu" role="menu">(.*?)</div>\s*</div>', re.S)


def git_show(path):
    return subprocess.run(
        ["git", "show", "%s:%s" % (BASE, path)],
        capture_output=True, text=True, check=True,
    ).stdout


def env_from_str(src, name="_header.html"):
    e = Environment(loader=FileSystemLoader("templates"),
                    autoescape=select_autoescape(["html"]))
    return e.from_string(src)


new_env = Environment(loader=FileSystemLoader("templates"),
                      autoescape=select_autoescape(["html"]))
new_tpl = new_env.get_template("_header.html")
old_tpl = env_from_str(git_show("templates/_header.html"))

# --- payda: _header.html'i include eden sablonlar (yorumlar SIYRILIR) ---------
YORUM = re.compile(r"{#.*?#}", re.S)
import glob  # noqa: E402

adopters = []
for f in sorted(glob.glob("templates/*.html")):
    if f.endswith("_header.html"):
        continue
    s = YORUM.sub("", io.open(f, encoding="utf-8").read())
    if "include '_header.html'" in s:
        adopters.append(f.split("/")[-1][:-5])

# t22_header_harness.py ile ayni parametre tablosu + bu turda eklenen 2 sablon
PARAMS = {
    "tarama": {}, "blog": {}, "gucu_yuksek": {}, "kategori": {}, "metodoloji": {},
    "portfolio": {}, "blog_article": {},
    "abd_tarama": {"hdr_title": "__EMOJI__ __TITLE__", "hdr_title_tag": "div",
                   "hdr_sub": "Supertrend · ADX · EMA Sinyal Tarayıcısı"},
    "bilanco_takvimi": {"hdr_title": "\U0001f4c5 Bilanço Takvimi",
                        "hdr_sub": "Veriler yükleniyor…", "hdr_sub_id": "lastUpdate"},
    "gizlilik": {"hdr_title": "\U0001f512 Gizlilik Politikası"},
    "gundem": {"hdr_title": "Piyasa Gündem Merkezi", "hdr_sub": "Yükleniyor…",
               "hdr_sub_id": "updatedAt"},
    "hakkinda": {"hdr_title": "Hakkında"},
    "iletisim": {"hdr_title": "\U0001f4ec İletişim"},
    "karsilastir": {"hdr_title": "Hisse Karşılaştırma", "hdr_sub": "2-4 hisseyi seçin",
                    "hdr_sub_id": "compareSubtitle"},
    "sinyal_performans": {"hdr_title": "Sinyal Performans Analizi"},
    "varlik": {"hdr_trailing_include": "_header_asset_price.html"},
    "yasal": {"hdr_title": "⚖️ Yasal Uyarı & SPK Bildirimi"},
    "hisseler": {"hdr_title": "Tüm BIST Hisseleri", "hdr_self": "/hisseler"},
}

fail = []
eksik_param = [a for a in adopters if a not in PARAMS]
if eksik_param:
    fail.append("PAYDA: parametre tablosunda olmayan adopter: %s" % eksik_param)
print("PAYDA  _header.html include eden sablon : %d  (%s)" % (len(adopters), ", ".join(adopters)))
print()

# --- K-A: mevcut adopterlerde cikti DEGISMEDI --------------------------------
ka_ok = 0
for name in adopters:
    if name in ("hisseler",):
        continue  # K-B'de ayri olculuyor
    p = PARAMS.get(name, {})
    o = old_tpl.render(**p)
    n = new_tpl.render(**p)
    if o == n:
        ka_ok += 1
    else:
        fail.append("K-A %s: cikti DEGISTI (delta=%d bayt)" % (name, len(n) - len(o)))
print("K-A  mevcut adopter ciktisi ONCE==SONRA : %d/%d" % (ka_ok, len(adopters) - 1))

# --- K-B: hisseler.html davranisi KORUNDU ------------------------------------
old_hisseler = git_show("templates/hisseler.html")
old_hdr = re.search(r"<header\b.*?</header>", old_hisseler, re.S).group(0)
new_hdr = new_tpl.render(hdr_title="Tüm BIST Hisseleri", hdr_self="/hisseler")
kb = old_hdr == new_hdr
print("K-B  /hisseler yeni cikti == ESKI header : %s  (%d vs %d bayt)"
      % ("BIREBIR" if kb else "FARKLI", len(new_hdr), len(old_hdr)))
if not kb:
    i = next((k for k in range(min(len(old_hdr), len(new_hdr))) if old_hdr[k] != new_hdr[k]),
             min(len(old_hdr), len(new_hdr)))
    fail.append("K-B: off=%d old=%r new=%r" % (i, old_hdr[i:i + 90], new_hdr[i:i + 90]))

# --- K-C: blog_article more-menu 0 -> 12 -------------------------------------
old_ba = re.search(r"<header\b.*?</header>", git_show("templates/blog_article.html"), re.S).group(0)
new_ba = new_tpl.render()


def menu_oge_sayisi(html):
    m = MENU_RE.search(html)
    if not m:
        return None
    return len(re.findall(r'<a [^>]*role="menuitem"', m.group(1)))


o_n, n_n = menu_oge_sayisi(old_ba), menu_oge_sayisi(new_ba)
print("K-C  blog_article 'Daha' menusu ogesi    : %s -> %s" % (o_n, n_n))
if not (o_n == 0 and n_n == 12):
    fail.append("K-C: more-menu oge sayisi beklenen 0->12, olculen %s->%s" % (o_n, n_n))

o_links = set(re.findall(r'href="([^"]+)"', old_ba))
n_links = set(re.findall(r'href="([^"]+)"', new_ba))
print("K-C  link KUMESI  kaybolan=%s" % (sorted(o_links - n_links) or "YOK"))
print("K-C  link KUMESI  kazanilan=%s" % sorted(n_links - o_links))
if o_links - n_links:
    fail.append("K-C: blog_article'da link KAYBI: %s" % sorted(o_links - n_links))

o_txt = set(re.findall(r">([^<>{}]{2,40})</a>", old_ba))
kayip_metin = [t for t in o_txt if t not in new_ba]
print("K-C  kaybolan gorunur baglanti metni     : %s" % (kayip_metin or "YOK"))
if kayip_metin:
    fail.append("K-C: gorunur metin kaybi: %s" % kayip_metin)

# --- K-D: POZITIF KONTROL — kapi kor mu? -------------------------------------
d1 = len(SELF_RE.findall(new_tpl.render(hdr_self="/baska-sayfa")))
d2 = len(SELF_RE.findall(new_tpl.render(hdr_self="/hisseler")))
print("K-D  POZITIF KONTROL  hdr_self='/baska-sayfa' -> self-link %d (beklenen 1)" % d1)
print("K-D  POZITIF KONTROL  hdr_self='/hisseler'    -> self-link %d (beklenen 0)" % d2)
if (d1, d2) != (1, 0):
    fail.append("K-D: kosul KOR veya ters (%d,%d)" % (d1, d2))

# --- K-E: request TANIMSIZ iken guvenli varsayilan ---------------------------
try:
    e_n = len(SELF_RE.findall(new_tpl.render()))
    print("K-E  hdr_self VERILMEDI -> render OK, self-link %d (beklenen 1)" % e_n)
    if e_n != 1:
        fail.append("K-E: hdr_self yokken self-link %d" % e_n)
except Exception as exc:  # noqa: BLE001
    print("K-E  hdr_self VERILMEDI -> ISTISNA: %s" % exc)
    fail.append("K-E: parametresiz render PATLIYOR: %s" % exc)

# --- K-F: kor nokta kaniti — request tabanli guard NEDEN reddedildi ----------
import flask  # noqa: E402
_a = flask.Flask(__name__)
with _a.app_context():
    _g = _a.jinja_env.globals
    tanimli = "request" in _g
    try:
        _a.jinja_env.from_string("{{ request.endpoint }}").render()
        patlar = "HAYIR"
    except Exception as exc:  # noqa: BLE001
        patlar = type(exc).__name__
print("K-F  Flask jinja_env.globals icinde 'request' : %s  (yani `is not defined` ASLA dogru olmaz)"
      % ("VAR" if tanimli else "YOK"))
print("K-F  istek baglami DISINDA request.endpoint   : %s" % patlar)
if not tanimli or patlar == "HAYIR":
    fail.append("K-F: kor nokta kaniti uretilemedi (tanimli=%s patlar=%s)" % (tanimli, patlar))

print()
if fail:
    print("DOGRULAMA: RED (%d)" % len(fail))
    for f_ in fail:
        print("  ", f_)
    sys.exit(1)
print("DOGRULAMA: GECTI (K-A..K-F)")
