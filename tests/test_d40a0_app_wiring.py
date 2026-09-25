"""D-40a0: app.py ince baglanti — KAP kaydi varsa /fundamentals alanlari aciklanan veriden."""
import gzip
import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import app  # noqa: E402
import kap_financials as kf  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_fin")


def _thyao_record():
    with gzip.open(os.path.join(FIX, "fr_1565996.html.gz"), "rt", encoding="utf-8") as f:
        rep = kf.build_report(f.read(), {"idx": 1565996, "fy": 2025, "period": 4, "publish": None}, "THYAO")
    return kf.build_record("THYAO", [rep])


def test_fundamentals_kap_kayitla_ve_kayitsiz(monkeypatch):
    rec = _thyao_record()
    monkeypatch.setattr(kf, "load_record", lambda t, base_dir=None: rec if t == "THYAO" else None)
    monkeypatch.setitem(app._cache, "data", [{"ticker": "THYAO", "price": 292.5}])
    yahoo = {"revenue_growth": 20.5, "net_debt_to_ebitda": 0.14, "dividend_yield": 2.28,
             "market_cap": {"value": 4.0e11, "currency": "TRY"}}
    out = app._fundamentals_kap("THYAO", yahoo)
    assert out["revenue_growth"] == 28.18 and out["net_debt_to_ebitda"] == 2.68
    assert out["dividend_yield"] == 0.0 and out["kap"]["flags"]["yabanci_para"] == "USD"
    other = app._fundamentals_kap("TUPRS", yahoo)
    assert other["revenue_growth"] is None and other["net_debt_to_ebitda"] == 0.14
    assert app._fundamentals_kap("THYAO", {}) == {}
