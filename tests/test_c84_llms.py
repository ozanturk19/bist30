"""C-84: llms.txt yenileme — her adres doğrudan 200, güncelleme saati, kapsam, skor ağırlıkları,
3 örnek finansal tablo adresi, /hisseler#bist30 çapası, "nasıl alıntılanır" satırı; hisse
sayfası için JS'e kalmış vaat (grafik, bildirim listesi) yok; ürün dili yasakları.

Yerel (py3.9): gövde app.py kaynağından (kapı 55 ile aynı ayıklama) okunur, yer tutucular
seo_yonlendirme.yer_tutucu_doldur ile canlıdaki değerlerle doldurulur. VPS (py3.10+): /llms.txt
ucu ve metindeki her adres Flask test istemcisiyle doğrudan 200.
"""
import ast
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import kesfet  # noqa: E402
import seo_yonlendirme as sy  # noqa: E402
import temel_skor_v2  # noqa: E402

PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
APP = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
URL = re.compile(r"https://borsapusula\.com(/[^\s\"'\)\]}<>,;]*)")
YASAK = re.compile(r"\b(AL|SAT|BEKLE)\b|[Üü]cretsiz|ÜCRETSİZ|sinyal servisi|\b[Bb]ugün|\b[Dd]ün\b|[Hh]edef|"
                   r"kâr al|\bTP\d")


def _body():
    m = re.search(r'def llms_txt\(\):(.*?)\n    return Response', APP, re.S)
    return re.search(r'body\s*=\s*"""(.*?)"""', m.group(1), re.S).group(1)


def _yer(bulten="2026-10-14", harita="2026-10-14"):
    return {
        "[[KAPSAM]]": "233 şirket; BIST 100 endeksinin tüm üyeleri dahil",
        "[[TEMEL]]": ", ".join("%s %%%d" % (temel_skor_v2.AXIS_LABELS[k].lower(), w)
                               for k, w in temel_skor_v2.WEIGHTS.items()),
        "[[KESFET]]": ", ".join("[%s](https://borsapusula.com/kesfet/%s)" % (kesfet.BASLIK[k], kesfet.SLUG[k])
                                for k in kesfet.LISTS),
        "[[SON_HARITA]]": harita, "[[SON_BULTEN]]": bulten,
    }


def _redirects():
    for n in ast.parse(APP).body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "REDIRECTS":
            return ast.literal_eval(n.value)


def test_icerik_kabul_olcutleri():
    t = sy.yer_tutucu_doldur(_body(), _yer())
    assert "[[" not in t
    assert "yaklaşık 18:45'te (Türkiye saati, UTC+3)" in t                       # güncelleme saati
    assert "Kapsam: 233 şirket; BIST 100 endeksinin tüm üyeleri dahil" in t        # kapsam
    assert "BorsaPusula Skoru (0-100) = 0,60 × Temel skor + 0,40 × trend payı" in t
    assert "kalite %30, değerleme %20, büyüme %20, bilanço sağlığı %20, temettü %10" in t
    assert "## Nasıl alıntılanır?" in t and "rakamın ait olduğu tarih" in t
    urls = URL.findall(t)
    assert not [u for u in urls if "{" in u]          # kalıp ({TICKER}) tam adres olarak yazılmaz
    for u in ("/hisse/THYAO/bilanco", "/hisse/ASELS/gelir-tablosu", "/hisse/BIMAS/nakit-akis",
              "/hisseler#bist30", "/hisseler#bist100", "/sitemap.xml", "/harita/2026-10-14",
              "/bulten/2026-10-14", "/bulten/arsiv", "/kesfet/istikrarli-temettu"):
        assert u in urls, u
    yon = set(_redirects()) | {"/harita", "/bulten", "/kesfet", "/sektor-karsilastir"}
    for u in urls:
        assert u.split("#")[0].split("?")[0].rstrip("/") not in yon or u == "/", u      # 301/302 yok
    hisse = next(ln for ln in t.split("\n") if ln.startswith("- Hisse sayfası:"))
    assert "grafik" not in hisse.lower() and "bildirim" not in hisse.lower()          # JS'e kalmış vaat yok
    assert not YASAK.search(t), YASAK.search(t)


def test_dolmayan_yer_tutucu_satiri_duser():
    t = sy.yer_tutucu_doldur(_body(), dict(_yer(bulten=None, harita=None), **{"[[TEMEL]]": None, "[[KESFET]]": None}))
    assert "[[" not in t and "/bulten/" not in t and "/harita/" not in t and "/kesfet/" not in t
    assert "Temel skor (0-100)" not in t and "- [Şirket bildirimleri]" in t
    assert sy.yer_tutucu_doldur("a [[X]]\nb\nc [[Y]]", {"[[X]]": "1", "[[Y]]": ""}) == "a 1\nb"


@PY310
def test_llms_ucu_her_adres_dogrudan_200():
    import app
    c = app.app.test_client()
    r = c.get("/llms.txt")
    assert r.status_code == 200 and r.mimetype == "text/plain"
    t = r.get_data(as_text=True)
    assert "[[" not in t and t.count("- [Haberler]") == 1
    for u in sorted(set(URL.findall(t))):
        yol = u.split("#")[0]
        rr = c.get(yol)
        assert rr.status_code == 200, (yol, rr.status_code, rr.headers.get("Location"))
