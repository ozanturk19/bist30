"""Faz 12 P1 — business_rules.py test suite (CPO-693)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_rules import (
    validate_change_pct,
    validate_price,
    validate_signal_consistency,
    validate_date_range,
    validate_stocks_list,
)
from datetime import date


# ── validate_change_pct ──────────────────────────────────────────────────────

def test_normal_change_ok():
    assert validate_change_pct("AKBNK", 2.5)["ok"] is True

def test_negative_change_ok():
    assert validate_change_pct("AKBNK", -3.1)["ok"] is True

def test_zero_change_ok():
    assert validate_change_pct("AKBNK", 0.0)["ok"] is True

def test_glyho_anomal():
    r = validate_change_pct("GLYHO", 28.4)
    assert r["ok"] is False and r["flag"] == "ANOMAL"

def test_selec_anomal():
    r = validate_change_pct("SELEC", -15.2)
    assert r["ok"] is False and r["flag"] == "ANOMAL"

def test_exact_limit_ok():
    assert validate_change_pct("THYAO", 10.5)["ok"] is True

def test_just_over_limit_fail():
    assert validate_change_pct("THYAO", 10.51)["ok"] is False

def test_null_change_pct_fail():
    assert validate_change_pct("TICKER", None)["ok"] is False


# ── validate_price ───────────────────────────────────────────────────────────

def test_valid_price():
    assert validate_price("AKBNK", 45.2)["ok"] is True

def test_zero_price_fail():
    assert validate_price("AKBNK", 0)["ok"] is False

def test_negative_price_fail():
    assert validate_price("AKBNK", -1.5)["ok"] is False

def test_none_price_fail():
    assert validate_price("AKBNK", None)["ok"] is False

def test_small_valid_price():
    assert validate_price("AKBNK", 0.01)["ok"] is True


# ── validate_signal_consistency ──────────────────────────────────────────────

def test_al_with_signal_price_ok():
    assert validate_signal_consistency("THYAO", "AL", 85.5)["ok"] is True

def test_al_without_signal_price_fail():
    r = validate_signal_consistency("THYAO", "AL", None)
    assert r["ok"] is False and r["flag"] == "MISSING_SIGNAL_PRICE"

def test_sat_without_signal_price_ok():
    assert validate_signal_consistency("THYAO", "SAT", None)["ok"] is True

def test_bekle_without_signal_price_ok():
    assert validate_signal_consistency("THYAO", "BEKLE", None)["ok"] is True

def test_none_signal_ok():
    assert validate_signal_consistency("THYAO", None, None)["ok"] is True


# ── validate_date_range ──────────────────────────────────────────────────────

def test_today_date_ok():
    assert validate_date_range("AKBNK", date.today().isoformat())["ok"] is True

def test_past_date_ok():
    assert validate_date_range("AKBNK", "2026-06-01")["ok"] is True

def test_future_date_fail():
    r = validate_date_range("AKBNK", "2027-01-01")
    assert r["ok"] is False and r["flag"] == "FUTURE_DATE"

def test_none_date_ok():
    assert validate_date_range("AKBNK", None)["ok"] is True

def test_turkish_format_past_date_ok():
    assert validate_date_range("AKBNK", "22.06.2026")["ok"] is True

def test_turkish_format_future_date_fail():
    r = validate_date_range("AKBNK", "01.07.2027")
    assert r["ok"] is False and r["flag"] == "FUTURE_DATE"


# ── validate_stocks_list integration ────────────────────────────────────────

HEALTHY_TICKERS = [
    {"ticker": "AKBNK", "price": 45.2,  "change_pct": 1.5,   "signal": "AL",    "signal_price": 44.0,  "signal_date": "2026-06-23"},
    {"ticker": "THYAO", "price": 85.5,  "change_pct": -0.8,  "signal": "SAT",   "signal_price": None,  "signal_date": "2026-06-20"},
    {"ticker": "SISE",  "price": 32.1,  "change_pct": 2.1,   "signal": "BEKLE", "signal_price": None,  "signal_date": None},
    {"ticker": "KCHOL", "price": 120.0, "change_pct": 0.5,   "signal": "AL",    "signal_price": 119.0, "signal_date": "2026-06-23"},
    {"ticker": "SAHOL", "price": 55.7,  "change_pct": -1.2,  "signal": "BEKLE", "signal_price": None,  "signal_date": None},
]

def test_healthy_tickers_pass():
    result = validate_stocks_list(HEALTHY_TICKERS)
    assert result["errors"] == [], f"Unexpected errors: {result['errors']}"
    assert result["failed_tickers"] == []

def test_glyho_selec_sentinel():
    anomalous = [
        {"ticker": "GLYHO", "price": 85.0, "change_pct": 28.4,  "signal": "AL",  "signal_price": 80.0, "signal_date": "2026-06-23"},
        {"ticker": "SELEC", "price": 45.0, "change_pct": -15.2, "signal": "SAT", "signal_price": None, "signal_date": "2026-06-23"},
    ]
    result = validate_stocks_list(anomalous)
    assert "GLYHO" in result["failed_tickers"]
    assert "SELEC" in result["failed_tickers"]

def test_negative_price_caught():
    bad = [{"ticker": "BADCO", "price": -5.0, "change_pct": 1.0, "signal": "BEKLE", "signal_price": None, "signal_date": None}]
    result = validate_stocks_list(bad)
    assert "BADCO" in result["failed_tickers"]

def test_al_missing_signal_price_caught():
    bad = [{"ticker": "MISSP", "price": 10.0, "change_pct": 2.0, "signal": "AL", "signal_price": None, "signal_date": None}]
    result = validate_stocks_list(bad)
    assert "MISSP" in result["failed_tickers"]


# ── runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_normal_change_ok, test_negative_change_ok, test_zero_change_ok,
        test_glyho_anomal, test_selec_anomal, test_exact_limit_ok,
        test_just_over_limit_fail, test_null_change_pct_fail,
        test_valid_price, test_zero_price_fail, test_negative_price_fail,
        test_none_price_fail, test_small_valid_price,
        test_al_with_signal_price_ok, test_al_without_signal_price_fail,
        test_sat_without_signal_price_ok, test_bekle_without_signal_price_ok,
        test_none_signal_ok,
        test_today_date_ok, test_past_date_ok, test_future_date_fail, test_none_date_ok,
        test_healthy_tickers_pass, test_glyho_selec_sentinel,
        test_negative_price_caught, test_al_missing_signal_price_caught,
    ]
    passed = failed_list = 0
    fail_names = []
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✓ {t.__name__}")
        except AssertionError as e:
            fail_names.append(t.__name__)
            print(f"  ✗ {t.__name__}: {e}")
    print(f"\n{'='*55}")
    print(f"Result: {passed}/{len(tests)} passed")
    if fail_names:
        print(f"FAILED: {', '.join(fail_names)}")
        raise SystemExit(1)
    print("ALL TESTS PASSED ✅")
