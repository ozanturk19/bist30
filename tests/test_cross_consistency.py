"""Faz 12 P1 — cross_consistency.py test suite (CPO-693)"""

import sys
import os
import math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cross_consistency import (
    compare_price_across_endpoints,
    validate_data_vs_chart,
    validate_stocks_cross_consistency,
)


# ── compare_price_across_endpoints ──────────────────────────────────────────

def test_same_price_ok():
    errs = compare_price_across_endpoints("AKBNK", {"api_data": 45.2, "api_chart": 45.2})
    assert errs == []

def test_within_tolerance_ok():
    # 0.44% diff — within 0.5%
    errs = compare_price_across_endpoints("AKBNK", {"api_data": 45.20, "api_chart": 45.00})
    assert errs == []

def test_at_exact_tolerance_ok():
    # exactly 0.5% — boundary, should pass (not strictly greater)
    base = 100.0
    other = base * (1 - 0.005)  # = 99.5 — exactly 0.5%
    errs = compare_price_across_endpoints("THYAO", {"api_data": base, "api_chart": other})
    assert errs == []

def test_just_over_tolerance_fail():
    # 0.51% diff
    base = 100.0
    other = base * (1 - 0.0051)  # = 99.49 — 0.51%
    errs = compare_price_across_endpoints("THYAO", {"api_data": base, "api_chart": other})
    assert len(errs) == 1 and errs[0]["flag"] == "CROSS_INCONSISTENCY"

def test_large_discrepancy_fail():
    errs = compare_price_across_endpoints("SISE", {"api_data": 32.0, "api_chart": 30.0})
    assert len(errs) == 1
    assert errs[0]["pct_diff"] > 0.5

def test_none_skipped():
    # When chart price is None — no comparison, no error
    errs = compare_price_across_endpoints("KCHOL", {"api_data": 120.0, "api_chart": None})
    assert errs == []

def test_all_none_ok():
    errs = compare_price_across_endpoints("SAHOL", {"api_data": None, "api_chart": None})
    assert errs == []

def test_zero_price_flagged():
    errs = compare_price_across_endpoints("BADCO", {"api_data": 0.0, "api_chart": 45.0})
    assert len(errs) == 1 and errs[0]["flag"] == "ZERO_PRICE_FOR_COMPARISON"

def test_three_sources_two_inconsistent():
    # api_data=100, api_chart=99 (ok), api_macro=95 (fail vs data + chart)
    errs = compare_price_across_endpoints(
        "AKBNK",
        {"api_data": 100.0, "api_chart": 99.6, "api_macro": 95.0},
    )
    flags = [e["flag"] for e in errs]
    assert all(f == "CROSS_INCONSISTENCY" for f in flags)
    assert len(errs) == 2  # data vs macro + chart vs macro

def test_three_sources_all_consistent():
    errs = compare_price_across_endpoints(
        "AKBNK",
        {"api_data": 100.0, "api_chart": 100.1, "api_macro": 99.8},
    )
    assert errs == []

def test_nan_price_skipped():
    errs = compare_price_across_endpoints(
        "TICKER",
        {"api_data": float("nan"), "api_chart": 45.0},
    )
    assert errs == []


# ── validate_data_vs_chart ───────────────────────────────────────────────────

def test_data_vs_chart_ok():
    errs = validate_data_vs_chart("THYAO", 85.5, 85.4)
    assert errs == []

def test_data_vs_chart_fail():
    errs = validate_data_vs_chart("THYAO", 85.5, 80.0)
    assert len(errs) == 1 and errs[0]["flag"] == "CROSS_INCONSISTENCY"

def test_data_vs_chart_none_chart_cache_miss():
    errs = validate_data_vs_chart("THYAO", 85.5, None)
    assert len(errs) == 1 and errs[0]["flag"] == "CACHE_MISS"

def test_data_vs_chart_eregl_drift_flagged():
    # Gerçek dünya: monthly close 5.28, actual price 40.08 — bedelsiz/konsolidasyon drift
    errs = validate_data_vs_chart("EREGL", 40.08, 5.28)
    assert len(errs) == 1 and errs[0]["flag"] == "CROSS_INCONSISTENCY"
    assert errs[0]["pct_diff"] > 80


# ── validate_stocks_cross_consistency ───────────────────────────────────────

STOCKS = [
    {"ticker": "AKBNK", "price": 45.20},
    {"ticker": "THYAO", "price": 85.50},
    {"ticker": "SISE",  "price": 32.10},
]

def test_all_stocks_consistent():
    charts = {"AKBNK": 45.18, "THYAO": 85.46, "SISE": 32.08}
    result = validate_stocks_cross_consistency(STOCKS, charts)
    assert result["errors"] == []
    assert result["failed_tickers"] == []
    assert result["checked"] == 3

def test_one_stock_inconsistent():
    charts = {"AKBNK": 44.00, "THYAO": 85.46, "SISE": 32.08}
    result = validate_stocks_cross_consistency(STOCKS, charts)
    assert "AKBNK" in result["failed_tickers"]
    assert "THYAO" not in result["failed_tickers"]

def test_missing_chart_for_ticker():
    # SISE not in charts_map → chart=None → CACHE_MISS (yeni davranış)
    charts = {"AKBNK": 45.18, "THYAO": 85.46}  # SISE missing
    result = validate_stocks_cross_consistency(STOCKS, charts)
    assert any(e["flag"] == "CACHE_MISS" and e["ticker"] == "SISE" for e in result["errors"])

def test_both_none_not_counted():
    stocks = [{"ticker": "GHOST", "price": None}]
    charts = {"GHOST": None}
    result = validate_stocks_cross_consistency(stocks, charts)
    assert result["checked"] == 0
    assert result["errors"] == []

def test_total_count():
    charts = {"AKBNK": 45.18, "THYAO": 85.46, "SISE": 32.08}
    result = validate_stocks_cross_consistency(STOCKS, charts)
    assert result["total"] == 3


# ── runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_same_price_ok, test_within_tolerance_ok, test_at_exact_tolerance_ok,
        test_just_over_tolerance_fail, test_large_discrepancy_fail,
        test_none_skipped, test_all_none_ok, test_zero_price_flagged,
        test_three_sources_two_inconsistent, test_three_sources_all_consistent,
        test_nan_price_skipped,
        test_data_vs_chart_ok, test_data_vs_chart_fail,
        test_data_vs_chart_none_chart_cache_miss, test_data_vs_chart_eregl_drift_flagged,
        test_all_stocks_consistent, test_one_stock_inconsistent,
        test_missing_chart_for_ticker, test_both_none_not_counted, test_total_count,
    ]
    passed = 0
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
