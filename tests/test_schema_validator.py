"""Faz 12 P1 — schema_validator.py test suite (CPO-693)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_validator import validate_api_data, validate_api_macro, validate_api_hisse_chart, validate_schema


# ── /api/data ────────────────────────────────────────────────────────────────

VALID_DATA = {
    "stocks": [
        {"ticker": "AKBNK", "price": 45.2, "change_pct": 1.5, "signal": "AL",
         "signal_price": 44.0, "signal_date": "2026-06-23"},
    ],
    "updated_at": "23.06.2026 10:30:00",
    "loading": False,
    "sectors": ["Bankacılık", "Sanayi"],
    "xu100_spark": [14000.0, 14050.0, 14020.0],
    "data_quality": "fresh",
    "stocks_age_s": 120,
    "refreshing": False,
}

def test_api_data_valid():
    r = validate_api_data(VALID_DATA)
    assert r["ok"] is True

def test_api_data_missing_stocks():
    data = {k: v for k, v in VALID_DATA.items() if k != "stocks"}
    r = validate_api_data(data)
    assert r["ok"] is False and r["flag"] == "SCHEMA_ERROR"

def test_api_data_missing_xu100_spark():
    data = {k: v for k, v in VALID_DATA.items() if k != "xu100_spark"}
    r = validate_api_data(data)
    assert r["ok"] is False and r["flag"] == "SCHEMA_ERROR"

def test_api_data_stocks_not_array():
    data = {**VALID_DATA, "stocks": "not-an-array"}
    r = validate_api_data(data)
    assert r["ok"] is False and r["flag"] == "SCHEMA_ERROR"

def test_api_data_invalid_data_quality():
    data = {**VALID_DATA, "data_quality": "unknown_value"}
    r = validate_api_data(data)
    assert r["ok"] is False and r["flag"] == "SCHEMA_ERROR"

def test_api_data_loading_true_empty_stocks():
    data = {**VALID_DATA, "loading": True, "stocks": []}
    r = validate_api_data(data)
    assert r["ok"] is True

def test_api_data_stock_ticker_required():
    data = {**VALID_DATA, "stocks": [{"price": 45.2}]}  # no ticker
    r = validate_api_data(data)
    assert r["ok"] is False and r["flag"] == "SCHEMA_ERROR"

def test_api_data_null_price_ok():
    data = {**VALID_DATA, "stocks": [{"ticker": "AKBNK", "price": None}]}
    r = validate_api_data(data)
    assert r["ok"] is True

def test_api_data_null_stocks_age_ok():
    data = {**VALID_DATA, "stocks_age_s": None}
    r = validate_api_data(data)
    assert r["ok"] is True

def test_api_data_extra_fields_ok():
    data = {**VALID_DATA, "extra_unknown_field": "value"}
    r = validate_api_data(data)
    assert r["ok"] is True  # additionalProperties: true


# ── /api/macro ───────────────────────────────────────────────────────────────

VALID_MACRO = {
    "items": [{"symbol": "XU100", "price": 14250.5, "change": 0.5}],
    "cached": True,
    "stale": False,
}

def test_api_macro_valid():
    r = validate_api_macro(VALID_MACRO)
    assert r["ok"] is True

def test_api_macro_missing_items():
    data = {"cached": True}
    r = validate_api_macro(data)
    assert r["ok"] is False and r["flag"] == "SCHEMA_ERROR"

def test_api_macro_missing_cached():
    data = {"items": []}
    r = validate_api_macro(data)
    assert r["ok"] is False and r["flag"] == "SCHEMA_ERROR"

def test_api_macro_empty_items_ok():
    data = {"items": [], "cached": True}
    r = validate_api_macro(data)
    assert r["ok"] is True

def test_api_macro_wrong_cached_type():
    data = {**VALID_MACRO, "cached": "yes"}
    r = validate_api_macro(data)
    assert r["ok"] is False and r["flag"] == "SCHEMA_ERROR"


# ── /api/hisse/<ticker>/chart ────────────────────────────────────────────────

VALID_CHART_READY = {
    "chart": {"summary": {"signal": "AL"}, "ohlc": []},
    "updated_at": "23.06.2026 10:30:00",
    "loading": False,
}

VALID_CHART_LOADING = {
    "chart": None,
    "loading": True,
    "reason": "cache_miss_read_only_mode",
}

def test_api_chart_valid_ready():
    r = validate_api_hisse_chart(VALID_CHART_READY)
    assert r["ok"] is True

def test_api_chart_valid_loading():
    r = validate_api_hisse_chart(VALID_CHART_LOADING)
    assert r["ok"] is True

def test_api_chart_missing_loading():
    data = {"chart": None}
    r = validate_api_hisse_chart(data)
    assert r["ok"] is False and r["flag"] == "SCHEMA_ERROR"

def test_api_chart_wrong_loading_type():
    data = {**VALID_CHART_READY, "loading": "false"}
    r = validate_api_hisse_chart(data)
    assert r["ok"] is False and r["flag"] == "SCHEMA_ERROR"


# ── Generic validate_schema ──────────────────────────────────────────────────

def test_unknown_schema_not_found():
    r = validate_schema({}, "nonexistent_schema_xyz")
    assert r["ok"] is False and r["flag"] == "SCHEMA_FILE_NOT_FOUND"

def test_schema_name_in_result():
    r = validate_api_data(VALID_DATA)
    assert r.get("schema") == "api_data"


# ── runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_api_data_valid, test_api_data_missing_stocks,
        test_api_data_missing_xu100_spark, test_api_data_stocks_not_array,
        test_api_data_invalid_data_quality, test_api_data_loading_true_empty_stocks,
        test_api_data_stock_ticker_required, test_api_data_null_price_ok,
        test_api_data_null_stocks_age_ok, test_api_data_extra_fields_ok,
        test_api_macro_valid, test_api_macro_missing_items,
        test_api_macro_missing_cached, test_api_macro_empty_items_ok,
        test_api_macro_wrong_cached_type,
        test_api_chart_valid_ready, test_api_chart_valid_loading,
        test_api_chart_missing_loading, test_api_chart_wrong_loading_type,
        test_unknown_schema_not_found, test_schema_name_in_result,
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
