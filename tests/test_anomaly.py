"""Faz 12 P1 — anomaly.py test suite (CPO-693)"""

import sys
import os
import math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anomaly import z_score_check, volume_spike, validate_stock_anomaly, validate_anomalies_list


# ── z_score_check ────────────────────────────────────────────────────────────

# history: mean=10.0, std≈0.707 → z>3 means today > 12.12 or < 7.88
HISTORY_5D = [9.5, 10.0, 10.2, 9.8, 10.5]  # mean≈10.0, std≈0.346

def test_normal_price_no_anomaly():
    r = z_score_check("AKBNK", 10.1, HISTORY_5D)
    assert r is None

def test_price_4std_above_anomaly():
    # mean≈10.0, std≈0.346 → z=4 means today≈11.384
    r = z_score_check("AKBNK", 11.4, HISTORY_5D)
    assert r is not None and r["flag"] == "Z_SCORE_ANOMALY"

def test_price_below_threshold_ok():
    # z just below 3
    r = z_score_check("AKBNK", 11.0, HISTORY_5D)
    # mean≈10.0, std≈0.346, z=(11.0-10.0)/0.346≈2.89 < 3
    assert r is None

def test_none_today_skipped():
    r = z_score_check("AKBNK", None, HISTORY_5D)
    assert r is None

def test_nan_today_skipped():
    r = z_score_check("AKBNK", float("nan"), HISTORY_5D)
    assert r is None

def test_empty_history_skipped():
    r = z_score_check("AKBNK", 45.0, [])
    assert r is None

def test_single_history_skipped():
    r = z_score_check("AKBNK", 45.0, [44.0])
    assert r is None

def test_constant_history_no_anomaly():
    # std=0 → skip (division by zero protection)
    r = z_score_check("AKBNK", 50.0, [10.0, 10.0, 10.0, 10.0, 10.0])
    assert r is None

def test_z_score_result_fields():
    r = z_score_check("THYAO", 15.0, HISTORY_5D)
    assert r is not None
    assert "z_score" in r and "mean" in r and "std" in r and "threshold" in r

def test_custom_threshold():
    # With threshold=2.0, z≈2.89 should trigger
    r = z_score_check("AKBNK", 11.0, HISTORY_5D, threshold=2.0)
    assert r is not None and r["flag"] == "Z_SCORE_ANOMALY"

def test_history_with_none_values():
    # None in history is filtered out
    r = z_score_check("AKBNK", 10.1, [9.5, None, 10.2, 9.8, 10.5])
    assert r is None  # still normal


# ── volume_spike ─────────────────────────────────────────────────────────────

VOL_HISTORY = [3_000_000, 3_200_000, 2_900_000, 3_100_000, 3_050_000]  # avg≈3_050_000

def test_normal_volume_ok():
    r = volume_spike("AKBNK", 3_500_000, VOL_HISTORY)
    assert r is None

def test_volume_15x_spike():
    r = volume_spike("AKBNK", 50_000_000, VOL_HISTORY)
    assert r is not None and r["flag"] == "VOLUME_SPIKE"

def test_volume_exactly_10x_ok():
    avg = sum(VOL_HISTORY) / len(VOL_HISTORY)
    exactly_10x = avg * 10.0
    r = volume_spike("AKBNK", exactly_10x, VOL_HISTORY)
    assert r is None  # not strictly greater than 10

def test_volume_just_over_10x_spike():
    avg = sum(VOL_HISTORY) / len(VOL_HISTORY)
    just_over = avg * 10.01
    r = volume_spike("AKBNK", just_over, VOL_HISTORY)
    assert r is not None and r["flag"] == "VOLUME_SPIKE"

def test_none_volume_skipped():
    r = volume_spike("AKBNK", None, VOL_HISTORY)
    assert r is None

def test_empty_volume_history_skipped():
    r = volume_spike("AKBNK", 5_000_000, [])
    assert r is None

def test_zero_avg_volume_skipped():
    r = volume_spike("AKBNK", 5_000_000, [0, 0, 0])
    assert r is None

def test_volume_spike_result_fields():
    r = volume_spike("THYAO", 50_000_000, VOL_HISTORY)
    assert r is not None
    assert "ratio" in r and "avg_vol" in r and "spike_ratio" in r


# ── validate_stock_anomaly / validate_anomalies_list ────────────────────────

def test_clean_stock_no_anomalies():
    stock = {
        "ticker": "AKBNK",
        "today_price": 10.1,
        "price_history": HISTORY_5D,
        "today_volume": 3_200_000,
        "volume_history": VOL_HISTORY,
    }
    errs = validate_stock_anomaly(stock)
    assert errs == []

def test_stock_with_price_anomaly():
    stock = {
        "ticker": "ANOMAL",
        "today_price": 15.0,
        "price_history": HISTORY_5D,
        "today_volume": 3_000_000,
        "volume_history": VOL_HISTORY,
    }
    errs = validate_stock_anomaly(stock)
    flags = [e["flag"] for e in errs]
    assert "Z_SCORE_ANOMALY" in flags

def test_stock_with_volume_spike():
    stock = {
        "ticker": "VSPIKED",
        "today_price": 10.0,
        "price_history": HISTORY_5D,
        "today_volume": 50_000_000,
        "volume_history": VOL_HISTORY,
    }
    errs = validate_stock_anomaly(stock)
    flags = [e["flag"] for e in errs]
    assert "VOLUME_SPIKE" in flags

def test_validate_anomalies_list_summary():
    stocks = [
        {
            "ticker": "CLEAN",
            "today_price": 10.1, "price_history": HISTORY_5D,
            "today_volume": 3_200_000, "volume_history": VOL_HISTORY,
        },
        {
            "ticker": "BAD",
            "today_price": 15.0, "price_history": HISTORY_5D,
            "today_volume": 50_000_000, "volume_history": VOL_HISTORY,
        },
    ]
    result = validate_anomalies_list(stocks)
    assert result["total"] == 2
    assert "BAD" in result["failed_tickers"]
    assert "CLEAN" not in result["failed_tickers"]


# ── runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_normal_price_no_anomaly, test_price_4std_above_anomaly,
        test_price_below_threshold_ok, test_none_today_skipped,
        test_nan_today_skipped, test_empty_history_skipped,
        test_single_history_skipped, test_constant_history_no_anomaly,
        test_z_score_result_fields, test_custom_threshold,
        test_history_with_none_values,
        test_normal_volume_ok, test_volume_15x_spike,
        test_volume_exactly_10x_ok, test_volume_just_over_10x_spike,
        test_none_volume_skipped, test_empty_volume_history_skipped,
        test_zero_avg_volume_skipped, test_volume_spike_result_fields,
        test_clean_stock_no_anomalies, test_stock_with_price_anomaly,
        test_stock_with_volume_spike, test_validate_anomalies_list_summary,
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
