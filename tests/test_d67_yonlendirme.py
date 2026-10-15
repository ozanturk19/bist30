"""D-67: yönlendirme ve iç bağlantı hijyeni + XU030/XU100 + /hisseler endeks bağlamı + blog og:image.

Yerel (py3.9): seo_yonlendirme.py, Python'un ürettiği HTML'deki iç bağlantılar (blog_content,
haber_gundem) ve app.py kaynağı. VPS (py3.10+): uçlar Flask test istemcisiyle.
"""
import ast
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import seo_yonlendirme as sy  # noqa: E402

PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
APP = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()


def _seed():
    with open(os.path.join(ROOT, "universe_seed.json"), encoding="utf-8") as f:
        return json.load(f)


def _app_literal(name):
    for n in ast.parse(APP).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and getattr(n.targets[0], "id", None) == name:
            return ast.literal_eval(n.value)
    raise AssertionError(name)


def test_endeks_sayfasi():
    assert sy.ENDEKS_SAYFASI == {"XU030": "/hisseler#bist30", "XU100": "/hisseler#bist100"}


def test_donem_etiketi_ceyrek_tr_saatiyle():
    assert sy.donem_etiketi("2026-10-12T04:00:03+0000") == "Ekim–Aralık 2026"
    assert sy.donem_etiketi("2026-09-30T22:30:00+0000") == "Ekim–Aralık 2026"   # 01.10 01:30 TR
    assert sy.donem_etiketi("2026-09-24T07:55:21+0300") == "Temmuz–Eylül 2026"
    assert sy.donem_etiketi("2027-01-01T04:00:00+0000") == "Ocak–Mart 2027"
    assert sy.donem_etiketi("2026-05-04T07:00:00+0300") == "Nisan–Haziran 2026"
    assert sy.donem_etiketi(None) is None and sy.donem_etiketi("dün") is None


def test_hisseler_endeks_universe_uyeligi():
    u = _seed()
    evren = [t for t in _app_literal("BIST100") if t not in ("XU030", "XU100")]
    he = sy.hisseler_endeks(u, evren, {"AKBNK": "Akbank T.A.Ş."})
    assert he["donem"] == sy.donem_etiketi(u["generated_at"])
    assert [t for t, _ in he["bist30"]] == sorted(u["indices"]["XU030"]) and len(he["bist30"]) == 30
    assert [t for t, _ in he["bist100"]] == sorted(u["indices"]["XU100"]) and len(he["bist100"]) == 100
    assert ("AKBNK", "Akbank T.A.Ş.") in he["bist30"] and he["eksik"] == []
    # sayfası olmayan üye bağlantı listesine girmez, `eksik`te görünür
    he = sy.hisseler_endeks(u, [t for t in evren if t != "THYAO"], {})
    assert "THYAO" not in [t for t, _ in he["bist30"]] and he["eksik"] == ["THYAO"]
    assert sy.hisseler_endeks({}, evren, {}) is None
    assert sy.hisseler_endeks({"indices": u["indices"]}, evren, {}) is None       # dönem okunamıyor


def _yonlenen_yollar():
    redirects = _app_literal("REDIRECTS")
    yollar = set(redirects)
    # 301/302 dönen diğer rotalar: /bulten, /harita (son güne 302), /sektor-karsilastir, eski takvimler
    yollar |= {"/bulten", "/harita", "/sektor-karsilastir", "/bilanco-takvimi", "/temettu-takvimi"}
    return redirects, yollar


def test_python_html_ic_baglantilari_kanonik():
    _, yollar = _yonlenen_yollar()
    files = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    files = [f for f in files if not f.startswith(("attic/", "tests/", "tools/", "research/"))]
    pat = re.compile(r'''href=\\?["'](/[^"'\\]*)|"href":\s*"(/[^"]*)"|\]\((/[^)\s]*)\)''')
    bad = []
    for f in files:
        src = open(os.path.join(ROOT, f), encoding="utf-8").read()
        for m in pat.finditer(src):
            u = next(g for g in m.groups() if g is not None)
            yol = u.split("#", 1)[0].split("?", 1)[0] or "/"
            if yol in yollar or "?tab=" in u or re.match(r"^/hisse/(XU030|XU100)\b", u):
                bad.append((f, u))
    assert bad == []


def test_app_kaynagi():
    redirects, _ = _yonlenen_yollar()
    assert redirects["/gucu-yuksek"] == "/tarama"
    for hedef in redirects.values():                      # tablo hedefleri parametresiz/kanonik
        assert "?signal=" not in hedef and "?tab=" not in hedef
    sp = re.search(r"def stock_page\(ticker\):(.*?)render_template\(", APP, re.S).group(1)
    assert sp.index("seo_yonlendirme.ENDEKS_SAYFASI.get(ticker.upper())") < sp.index("ticker != ticker.upper()")
    sk = re.search(r"def sektor_karsilastir\(\):(.*?)\n\n\n", APP, re.S).group(1)
    assert 'redirect("/sektor-harita", code=301)' in sk and "tab=compare" not in sk
    for fn in ("blog_index", "blog_article"):
        body = re.search(r"def %s\((.*?)\n\n\n" % fn, APP, re.S).group(1)
        assert "og_image_url=_blog_og_image_url(" in body, fn
    hh = re.search(r"def hisseler_hub\(\):(.*?)\n\n\n", APP, re.S).group(1)
    assert "hisseler_endeks=hisseler_endeks" in hh


@PY310
def test_app_yonlendirmeler():
    import app
    c = app.app.test_client()
    for yol, hedef in (("/hisse/XU030", "/hisseler#bist30"), ("/hisse/XU100", "/hisseler#bist100"),
                       ("/hisse/xu030", "/hisseler#bist30"), ("/gucu-yuksek", "/tarama"),
                       ("/sektor-karsilastir?s=Banka&s=Enerji", "/sektor-harita")):
        r = c.get(yol)
        assert r.status_code == 301 and r.headers["Location"].endswith(hedef), (yol, r.headers.get("Location"))


@PY310
def test_app_hisseler_endeks_ve_blog_og(monkeypatch):
    import app
    seen = {}
    monkeypatch.setattr(app, "render_template", lambda name, **ctx: seen.update(ctx, _name=name) or "ok")
    c = app.app.test_client()
    assert c.get("/hisseler").status_code == 200
    he = seen["hisseler_endeks"]
    idx = (app.UNIVERSE.get("indices") or {})
    evren = set(app.BIST100) - app.INDEX_TICKERS
    assert len(he["bist30"]) == len(set(idx["XU030"]) & evren) and len(he["bist100"]) == len(set(idx["XU100"]) & evren)
    assert re.match(r"^(Ocak–Mart|Nisan–Haziran|Temmuz–Eylül|Ekim–Aralık) 20\d\d$", he["donem"])
    art = app._get_blog_cache()[0][0]
    c.get("/blog/" + art["slug"])
    gun = (art.get("updated") or art["date"]).replace("-", "")
    assert seen["og_image_url"] == "/og-image.png?d=" + gun
    c.get("/blog")
    assert re.match(r"^/og-image\.png\?d=\d{8}$", seen["og_image_url"])
