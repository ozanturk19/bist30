"""D-40a2: app.py ince baglanti -- /fundamentals Temel v2 alanlari (kap_temel_v2.extend)."""
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

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_temel_v2")


def _rec(t):
    with gzip.open(os.path.join(FIX, t + ".json.gz"), "rt", encoding="utf-8") as f:
        return json.load(f)


def test_fundamentals_temel_v2_kayitla_ve_kayitsiz(monkeypatch):
    rec = _rec("TUPRS")
    monkeypatch.setattr(kf, "load_record", lambda t, base_dir=None: rec if t == "TUPRS" else None)
    monkeypatch.setitem(app._cache, "data", [{"ticker": "TUPRS", "price": 397.0}])
    yahoo = {"pe_ratio": 11.7, "pb_ratio": 1.74, "roe": 17.6, "shares": 1926795598.0,
             "market_cap": {"value": 7.6e11, "currency": "TRY"}}
    out = app._fundamentals_temel_v2("TUPRS", app._fundamentals_kap("TUPRS", yahoo))
    assert out["kap_durum"] == "var" and out["kap"]["sablon"] == "sanayi"
    assert out["kap"]["degerleme_simdi"]["fk"] == 11.33 and out["kap"]["degerleme_simdi"]["pd_dd"] == 1.68
    assert "sektor_ortanca" in out
    other = app._fundamentals_temel_v2("GARAN", app._fundamentals_kap("GARAN", dict(yahoo)))
    assert other["kap_durum"] == "hazirlaniyor" and "kap" not in other
    assert app._fundamentals_temel_v2("TUPRS", {}) == {}
