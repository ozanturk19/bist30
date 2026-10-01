"""D-59: app.py ince baglanti -- /api/kesfet, /api/kesfet/<liste>, /kesfet SSR, sitemap, llms.txt."""
import gzip
import json
import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import app  # noqa: E402
import kap_financials as kf  # noqa: E402
import kesfet  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_temel_v2")


def _rec(t):
    with gzip.open(os.path.join(FIX, t + ".json.gz"), "rt", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def evren(monkeypatch):
    """6 hisse ayni rafineri kaydiyla (ayni kova, farkli fiyat) + GARAN."""
    tup, gar = _rec("TUPRS"), _rec("GARAN")
    prices = {"TUPRS": 397.0, "AYGAZ": 200.0, "PETKM": 240.0, "SASA": 450.0, "ALKIM": 600.0, "GUBRF": 700.0,
              "GARAN": 133.9}
    monkeypatch.setattr(kf, "load_record", lambda t, base_dir=None: gar if t == "GARAN" else
                        (tup if t in prices else None))
    monkeypatch.setitem(app._cache, "data", [
        {"ticker": t, "price": p, "signal": "BEKLE", "bar_date": "01.10.2026"} for t, p in prices.items()]
        + [{"ticker": "XU030", "price": 1.0}])
    monkeypatch.setattr(app, "_get_sector", lambda t: "Bankacılık" if t == "GARAN" else "Kimya, Petrol ve Plastik")
    monkeypatch.setattr(app, "_financial_health_cache", {t: {"data": {"borsapusula_skoru": 55}} for t in prices})
    monkeypatch.setitem(app._KESFET, "ts", 0.0)
    monkeypatch.setitem(app._KESFET, "data", None)
    return prices


def test_api_kesfet_ozet_ve_tek_liste(evren):
    c = app.app.test_client()
    r = c.get("/api/kesfet")
    assert r.status_code == 200
    j = r.get_json()
    assert [x["slug"] for x in j["listeler"]] == [kesfet.SLUG[k] for k in kesfet.LISTS]
    assert j["tarih"] == "2026-10-01" and [x["kural"] for x in j["kurallar"]] == [kesfet.KURAL[k] for k in kesfet.LISTS]
    r = c.get("/api/kesfet/sektorune-gore-ucuz")
    v = r.get_json()
    assert r.status_code == 200 and v["anahtar"] == "sektorune_gore_ucuz"
    assert [x["ticker"] for x in v["satirlar"]] == ["AYGAZ", "PETKM"]       # ucuz ve ikisi de ortanca alti
    assert v["satirlar"][0]["degerleme"] == "ucuz" and v["satirlar"][0]["bp"] == 55
    assert c.get("/api/kesfet/sektorune_gore_ucuz").get_json()["slug"] == "sektorune-gore-ucuz"
    assert c.get("/api/kesfet/yok").status_code == 404


def test_onbellek_ve_soguk_acilis(evren, monkeypatch):
    calls = []
    real = kesfet.build

    def spy(*a, **k):
        calls.append(1)
        return real(*a, **k)
    monkeypatch.setattr(kesfet, "build", spy)
    a = app._kesfet_lists()
    b = app._kesfet_lists()
    assert a is b and len(calls) == 1            # 10 dk onbellek
    monkeypatch.setitem(app._cache, "data", [])
    monkeypatch.setitem(app._KESFET, "ts", 0.0)
    monkeypatch.setitem(app._KESFET, "data", None)
    empty = app._kesfet_lists()
    assert all(v == [] for v in empty["listeler"].values()) and app._KESFET["data"] is None   # bos evren yazilmaz


def test_kesfet_sayfasi_sablon_varsa_ssr_yoksa_404(evren):
    c = app.app.test_client()
    if not app._tpl_ready("kesfet.html"):
        assert c.get("/kesfet").status_code == 404
        assert c.get("/kesfet/kaliteli-makul").status_code == 404
        assert "/kesfet" not in c.get("/llms.txt").get_data(as_text=True)
        return
    r = c.get("/kesfet/sektorune-gore-ucuz")
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and "AYGAZ" in html and kesfet.SORU["sektorune_gore_ucuz"] in html
    assert c.get("/kesfet").status_code == 200
    r = c.get("/kesfet/sektorune_gore_ucuz")
    assert r.status_code == 301 and r.headers["Location"].endswith("/kesfet/sektorune-gore-ucuz")
    assert c.get("/kesfet/yok").status_code == 404
    assert "https://borsapusula.com/kesfet/istikrarli-temettu" in c.get("/llms.txt").get_data(as_text=True)
    app._sitemap_cache.clear()
    sm = c.get("/sitemap.xml").get_data(as_text=True)
    assert "/kesfet/sektorune-gore-ucuz</loc>" in sm and "/kesfet</loc>" not in sm   # kök kanonik değil


def test_metodoloji_kural_cumleleri_baglamda(monkeypatch):
    seen = {}
    monkeypatch.setattr(app, "render_template", lambda name, **ctx: seen.update(ctx) or "ok")
    app.metodoloji()
    assert [x["kural"] for x in seen["kesfet_kurallari"]] == [kesfet.KURAL[k] for k in kesfet.LISTS]
