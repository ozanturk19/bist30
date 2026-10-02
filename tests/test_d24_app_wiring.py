"""D-24: app.py ince baglanti -- /api/takvim, /takvim, eski takvim uclari ve 301'ler."""
import json
import os
import sys
from datetime import datetime

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import app  # noqa: E402
import takvim  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "takvim", "kap_fin_ornek.json")


@pytest.fixture
def ortam(monkeypatch, tmp_path):
    with open(FIX, encoding="utf-8") as f:
        recs = json.load(f)["records"]
    for t, rec in recs.items():
        (tmp_path / ("%s.json" % t)).write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(takvim, "KAP_DIR", str(tmp_path))
    stocks = [{"ticker": t, "price": 100.0, "change_pct": 0.5, "signal": "BEKLE", "borsapusula_skoru": 55}
              for t in sorted(recs)] + [{"ticker": "XU030", "price": 1.0}]
    monkeypatch.setitem(app._cache, "data", stocks)
    monkeypatch.setattr(app, "get_earnings_data", lambda: {"estimates": {"THYAO": "2099-01-01"}})
    app._takvim_cache.update(ts=0.0, day=None, data=None)
    yield recs
    app._takvim_cache.update(ts=0.0, day=None, data=None)


def test_api_takvim(ortam):
    r = app.app.test_client().get("/api/takvim")
    assert r.status_code == 200
    p = r.get_json()
    today = datetime.now(app._TZ_TR).date().isoformat()
    assert p["schema"] == 1 and p["kapsam"] == len(ortam) and p["kap_kayit"] == len(ortam)
    ds = [e["date"] for e in p["events"]]
    assert ds == sorted(ds) and all(d >= today for d in ds)
    assert {e["kind"] for e in p["events"]} <= {"bilanco", "temettu", "makro"}
    assert all(e["date_kind"] in ("kesin", "tahmini") for e in p["events"])
    assert "XU030" not in json.dumps(p)
    assert p["counts"]["all"] == len(p["events"])
    if today <= "2026-09-30":
        tu = [e for e in p["events"] if e["kind"] == "temettu" and e["ticker"] == "TUPRS"][0]
        assert tu["brut_tl"] == 6.7469533 and tu["yield_pct"] == 6.75 and tu["pay_date"] == "2026-10-02"


def test_api_temettu_takvimi_eski_bicim(ortam):
    p = app.app.test_client().get("/api/temettu-takvimi").get_json()
    rows = {r["ticker"]: r for r in p["stocks"]}
    assert "EREGL" not in rows or rows["EREGL"]["next_ex_date"] is None
    assert {"ticker", "next_ex_date", "last_div_date", "last_div_amount", "next_div_amount"} <= set(rows["TUPRS"])
    if datetime.now(app._TZ_TR).date().isoformat() <= "2026-09-30":
        assert rows["TUPRS"]["next_div_amount"] == 6.7469533 and rows["TUPRS"]["last_div_amount"] == 10.3799282
        assert "LKMNH" in rows and "NTHOL" in rows  # BIST30 disi da var


def test_eski_uclar_ve_yonlendirmeler(ortam):
    c = app.app.test_client()
    r = c.get("/api/bilanco-takvimi")
    assert r.status_code == 301 and r.headers["Location"].endswith("/api/takvim")
    assert c.get("/api/bilanco-mini").status_code == 200
    ec = c.get("/api/economic-calendar").get_json()
    assert all("date" in e and "event" in e for e in ec["upcoming"])
    ready = os.path.exists(os.path.join(ROOT, "templates", "takvim.html"))
    b, t, k = c.get("/bilanco-takvimi"), c.get("/temettu-takvimi"), c.get("/takvim")
    if ready:  # C-36 sablonu yayinda
        assert b.status_code == 301 and b.headers["Location"].endswith("/takvim?tur=bilanco")
        assert t.status_code == 301 and t.headers["Location"].endswith("/takvim?tur=temettu")
        assert k.status_code == 200 and "Takvim" in k.get_data(as_text=True)
    else:     # arka uc once deploy edildiyse eski sayfalar kalir, /takvim 404 (500 yok)
        assert b.status_code == 200 and t.status_code == 200 and k.status_code == 404


def test_eski_disk_bicimi_duzlesir():
    old = {"periods": [{"stocks": [{"ticker": "THYAO", "date": "2026-11-05"},
                                   {"ticker": "TUPRS", "date": "yaklaşık"}]}], "updated_at": "x"}
    assert app._earnings_flat_from_periods(old) == {"estimates": {"THYAO": "2026-11-05"}, "updated_at": "x"}


def test_sitemap_takvim():
    body = app.app.test_client().get("/sitemap.xml").get_data(as_text=True)
    assert "/takvim</loc>" in body and "/bilanco-takvimi</loc>" not in body


def test_takvim_ssr_baglam_yoksa_sablon_bos_durumla(monkeypatch, ortam):
    if not os.path.exists(os.path.join(ROOT, "templates", "takvim.html")):
        pytest.skip("C-36 sablonu yok (arka uc tek basina)")
    monkeypatch.setattr(app, "_takvim_payload", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    r = app.app.test_client().get("/takvim")
    assert r.status_code == 200

