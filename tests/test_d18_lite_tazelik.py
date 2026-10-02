"""D-18 — /api/hisse/<t>/lite'a 4 tazelik alanı (last_fresh_ts, data_quality, stale_reason, close_status).

Alanlar /api/data ve SSR ssr_signal ile aynı stock sözlüğünden gelir; hisse sayfası /api/data'dan
çıkınca (C-25c) "Güncellenmiyor" rozeti ve kapanış günü bunlarla kurulur. VPS (py3.10+).
"""
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
FIELDS = ("last_fresh_ts", "data_quality", "stale_reason", "close_status")


def test_lite_source_lists_the_four_fields():
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    m = re.search(r"def api_hisse_lite\(.*?_resp = safe_json", src, re.S)
    assert m
    for f in FIELDS:
        assert '"%s":' % f in m.group(0), f


@PY310
def test_lite_returns_freshness_fields_from_cache():
    import app
    c = app.app.test_client()
    row = app._enrich_stock({"ticker": "THYAO", "price": 1.0, "change_pct": 0.0})
    row.update({"last_fresh_ts": 1789139651, "data_quality": "stale",   # _enrich_stock last_fresh_ts'i ezer
                "stale_reason": "unknown", "close_status": "resmi"})
    with app._lock:
        _old = list(app._cache["data"])
        app._cache["data"] = [row]
    try:
        r = c.get("/api/hisse/THYAO/lite")
        assert r.status_code == 200
        st = r.get_json()["stock"]
        assert st["last_fresh_ts"] == 1789139651
        assert st["data_quality"] == "stale"
        assert st["stale_reason"] == "unknown"
        assert st["close_status"] == "resmi"
        # taze/alansız kayıtta anahtar vardır, değer None (istemci tek biçim görür)
        with app._lock:
            app._cache["data"] = [app._enrich_stock({"ticker": "THYAO", "price": 1.0, "change_pct": 0.0})]
        st = c.get("/api/hisse/THYAO/lite").get_json()["stock"]
        assert all(f in st for f in FIELDS)
        assert st["data_quality"] != "stale" and not st["stale_reason"]
    finally:
        with app._lock:
            app._cache["data"] = _old
