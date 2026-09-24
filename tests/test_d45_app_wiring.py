"""D-45 app.py ince baglanti testleri (Flask test istemcisi). app.py 3.10+ ister: yerelde atlanir,
VPS venv'de kosar. Depo gecici klasore yonlendirilir; ag cagrisi yok."""
from __future__ import annotations

import json
import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import app as appmod  # noqa: E402
import kap_feed as kf  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "kap_feed")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    with open(os.path.join(FX, "kap_liste_ornek.json"), encoding="utf-8") as f:
        rows = json.load(f)
    uni = {"AHGAZ", "ASTOR", "EKGYO", "FORTE", "THYAO", "ULKER", "AKCNS", "LINK", "GARAN", "ESCOM", "MIATK", "ORGE"}
    st = kf.Store(str(tmp_path / "kap_feed"))
    st.merge([x for x in (kf.normalize(r, uni) for r in rows) if x])
    monkeypatch.setattr(appmod, "_KAP_STORE", st)
    # canli last_kap_cache.json'a dokunulmaz (VPS'te kosarken uretim onbellegi ezilmesin)
    monkeypatch.setattr(appmod, "_load_kap_cache_from_disk", lambda: None)
    monkeypatch.setattr(appmod, "_save_kap_cache_to_disk", lambda: None)
    monkeypatch.setattr(appmod, "_kap_cache", {})
    appmod.app.config["TESTING"] = True
    return appmod.app.test_client()


def test_api_haberler_paged_no_outbound_links(client):
    r = client.get("/api/haberler?adet=5")
    assert r.status_code == 200
    d = r.get_json()
    assert d["available"] and len(d["items"]) == 5 and d["routine_hidden"] > 0
    assert set(d["items"][0]) >= {"id", "date", "ticker", "class", "title", "onem", "rutin", "href"}
    assert "kap.org.tr" not in r.get_data(as_text=True)
    assert all(not x["rutin"] for x in d["items"])
    t = client.get("/api/haberler?tur=temettu").get_json()
    assert t["items"] and all(x["filter"] == "temettu" for x in t["items"])


def test_api_bildirim_and_404(client):
    r = client.get("/api/bildirim/1666965")
    assert r.status_code == 200
    d = r.get_json()
    assert d["item"]["ticker"] == "ASTOR" and "23 Eylül 2026" in d["item"]["summary"]
    assert "kap.org.tr" not in r.get_data(as_text=True)
    assert client.get("/api/bildirim/1").status_code == 404
    assert client.get("/api/bildirim/1648987").status_code == 404   # baska uyenin bildirimi akista yok


def test_stock_kap_same_source(client):
    r = client.get("/api/hisse/AHGAZ/kap")
    d = r.get_json()
    ids = [x["index"] for x in d["disclosures"]]
    assert 1625024 in ids and 1648987 not in ids
    assert all(not x["summary"].endswith("\n") and "?nin" not in x["summary"] for x in d["disclosures"])


def test_gundem_girdi_admin_only(client):
    assert client.get("/api/gundem-girdi").status_code in (403, 503)


def test_pages_fail_safe_without_templates(client):
    has = os.path.exists(os.path.join(ROOT, "templates", "haberler.html"))
    r = client.get("/haberler")
    assert r.status_code == (200 if has else 404)
    has_b = os.path.exists(os.path.join(ROOT, "templates", "bildirim.html"))
    r = client.get("/hisse/ASTOR/bildirim/1666965")
    assert r.status_code == (200 if has_b else 404)
    if has_b:
        assert client.get("/hisse/THYAO/bildirim/1666965").status_code == 301
        assert client.get("/hisse/ASTOR/bildirim/1").status_code == 404
