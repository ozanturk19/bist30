"""D-60 (C-59): app.py ince baglanti -- /hisse/<T>/bilanco · /gelir-tablosu · /nakit-akis, Temel sekmesi
baglantisi, sitemap, llms.txt. Sablon (finansal_tablo.html) C-59 arayuz dalinda: burada render_template
yakalanir; sablon yoksa uc 404 verir (arka uc once deploy edilebilir)."""
import gzip
import json
import os
import shutil
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import app  # noqa: E402
import kap_financials as kf  # noqa: E402
import kap_tablolar as kt  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_tablolar")


def _rec(t):
    with gzip.open(os.path.join(FIX, "rec_%s.json.gz" % t), "rt", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def ortam(monkeypatch, tmp_path):
    recs = {"THYAO": _rec("THYAO"), "GARAN": _rec("GARAN")}
    raw = tmp_path / "raw"
    raw.mkdir()
    for i in (1565996, 1552588):
        shutil.copy(os.path.join(FIX, "raw_%s.html.gz" % i), str(raw / ("%s.html.gz" % i)))
    monkeypatch.setattr(kf, "load_record", lambda t, base_dir=None: recs.get(t))
    monkeypatch.setattr(kt, "RAW_DIR", str(raw))
    monkeypatch.setattr(kt, "CACHE_DIR", FIX)                          # fixture onbellegi (imza ayni)
    monkeypatch.setattr(kt, "_atomic_write_json", lambda p, o: None)    # testte diske yazilmaz
    seen = {}

    def fake_render(name, **ctx):
        seen["name"], seen["ctx"] = name, ctx
        return "ok:" + name
    monkeypatch.setattr(app, "render_template", fake_render)
    monkeypatch.setattr(app, "_tpl_ready", lambda name: True)
    return seen


def test_uc_sayfa_ssr_baglami(ortam):
    c = app.app.test_client()
    for slug, soru in (("bilanco", "bilançosu"), ("gelir-tablosu", "gelir tablosu"), ("nakit-akis", "nakit akışı")):
        r = c.get("/hisse/THYAO/" + slug)
        assert r.status_code == 200 and ortam["name"] == "finansal_tablo.html"
        ft = ortam["ctx"]["ft"]
        assert ft["slug"] == slug and ft["ticker"] == "THYAO" and ft["soru"].endswith(soru + " nasıl?")
        assert ortam["ctx"]["canonical"] == "https://borsapusula.com/hisse/THYAO/" + slug
        assert ft["yillik"]["sutunlar"][0]["rapor"] == 1565996
    assert c.get("/hisse/GARAN/bilanco").status_code == 200 and ortam["ctx"]["ft"]["sablon"] == "banka"


def test_yonlendirme_ve_404(ortam, monkeypatch):
    c = app.app.test_client()
    r = c.get("/hisse/thyao/bilanco")
    assert r.status_code == 301 and r.headers["Location"].endswith("/hisse/THYAO/bilanco")
    assert c.get("/hisse/XU030/bilanco").status_code == 404           # endeks
    assert c.get("/hisse/ZZZZZ/bilanco").status_code == 404           # evren disi
    assert c.get("/hisse/THYAO/ozkaynak").status_code == 404          # tablo adi yok
    monkeypatch.setattr(kf, "load_record", lambda t, base_dir=None: None)
    assert c.get("/hisse/THYAO/bilanco").status_code == 404           # kayit yok
    monkeypatch.setattr(app, "_tpl_ready", lambda name: name != "finansal_tablo.html")
    monkeypatch.setattr(kf, "load_record", lambda t, base_dir=None: _rec("THYAO"))
    assert c.get("/hisse/THYAO/bilanco").status_code == 404           # sablon henuz yok


def test_temel_sekmesi_baglantilari(ortam, monkeypatch):
    assert [b["href"] for b in app._finansal_tablo_baglantilari("THYAO")] == [
        "/hisse/THYAO/bilanco", "/hisse/THYAO/gelir-tablosu", "/hisse/THYAO/nakit-akis"]
    assert app._finansal_tablo_baglantilari("SAHOL") == []
    monkeypatch.setattr(app, "_tpl_ready", lambda name: False)
    assert app._finansal_tablo_baglantilari("THYAO") == []


def test_sitemap_ve_llms(ortam, monkeypatch):
    c = app.app.test_client()
    monkeypatch.setattr(app, "_sitemap_cache", {})
    sm = c.get("/sitemap.xml").get_data(as_text=True)
    son = max(_rec("THYAO")["reports"], key=lambda r: (r["fy"], r["period"]))["publish"][:10]
    assert "<loc>https://borsapusula.com/hisse/THYAO/bilanco</loc><lastmod>%s</lastmod>" % son in sm
    assert "/hisse/THYAO/nakit-akis</loc>" in sm and "/hisse/GARAN/bilanco</loc>" in sm
    assert "/hisse/XU030/bilanco" not in sm
    txt = c.get("/llms.txt").get_data(as_text=True)
    assert "/hisse/{TICKER}/gelir-tablosu" in txt and txt.index("Finansal tablolar") < txt.index("## Metodoloji")
