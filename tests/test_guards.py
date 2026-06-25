"""Paket 5 — Daemon Corruption Guard test suite (19 fixture corpus)"""

import json
import os
import sys
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from _guards import (
    _is_valid_fundamentals,
    _is_valid_chart,
    _is_valid_macro,
    _is_valid_disk_cache,
)

CORPUS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tools", "test-fixtures", "corruption-corpus",
)


def _load(subdir: str, filename: str) -> dict:
    path = os.path.join(CORPUS, subdir, filename)
    with open(path) as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _load_raw(subdir: str, filename: str) -> str:
    path = os.path.join(CORPUS, subdir, filename)
    with open(path) as f:
        return f.read()


# ── Fundamentals corrupt (5 fixtures: F1-F5) ─────────────────────────────────

@pytest.mark.parametrize("filename", [
    "missing_pe_ratio.json",   # F1 — PE_ratio key absent
    "null_eps.json",           # F2 — EPS null
    "negative_market_cap.json", # F3 — market_cap < 0
    "string_price_type.json",  # F4 — last_price is str
    "empty_object.json",       # F5 — all fields absent
])
def test_fundamentals_corrupt(filename):
    data = _load("fundamentals-corrupt", filename)
    is_valid, reason = _is_valid_fundamentals(data)
    assert is_valid is False, f"{filename}: expected invalid — got valid (reason: {reason})"


# ── Chart corrupt (4 fixtures: C1-C4) ────────────────────────────────────────

@pytest.mark.parametrize("filename", [
    "low_ohlc_count.json",       # C1 — ohlc_count=42 < 100
    "empty_volume_array.json",   # C2 — volume_array=[]
    "mismatched_timestamps.json", # C3 — timestamps descending
    "negative_ohlc_value.json",  # C4 — OHLC < 0
])
def test_chart_corrupt(filename):
    data = _load("chart-corrupt", filename)
    is_valid, reason = _is_valid_chart(data)
    assert is_valid is False, f"{filename}: expected invalid — got valid (reason: {reason})"


# ── Macro corrupt (5 fixtures: M1-M5) ────────────────────────────────────────

@pytest.mark.parametrize("filename", [
    "xu030_null.json",         # M1 — XU030=null
    "usdtry_string_type.json", # M2 — USDTRY="38,42" str
    "missing_last_price.json", # M3 — XU030 nested, no last_price
    "stale_timestamp.json",    # M4 — timestamp 72h old
    "empty_macro.json",        # M5 — empty dict
])
def test_macro_corrupt(filename):
    data = _load("macro-corrupt", filename)
    is_valid, reason = _is_valid_macro(data)
    assert is_valid is False, f"{filename}: expected invalid — got valid (reason: {reason})"


# ── Disk-cache corrupt (5 fixtures: D1-D5) ───────────────────────────────────

def test_disk_cache_missing_data_field():
    # D1 — 'data' key absent
    data = _load("disk-cache-corrupt", "missing_data_field.json")
    is_valid, reason = _is_valid_disk_cache(data)
    assert is_valid is False, f"D1: expected invalid — got valid (reason: {reason})"


def test_disk_cache_json_parse_error():
    # D2 — truncated JSON string
    raw = _load_raw("disk-cache-corrupt", "json_parse_error.txt")
    is_valid, reason = _is_valid_disk_cache(raw)
    assert is_valid is False, f"D2: expected invalid — got valid (reason: {reason})"


@pytest.mark.parametrize("filename", [
    "partial_write.json",   # D3 — hisse cache missing 'chart'
    "wrong_version.json",   # D4 — version=1.0
    "empty_data_value.json", # D5 — data=null
])
def test_disk_cache_corrupt(filename):
    data = _load("disk-cache-corrupt", filename)
    is_valid, reason = _is_valid_disk_cache(data)
    assert is_valid is False, f"{filename}: expected invalid — got valid (reason: {reason})"


# ── True negatives (valid data must pass) ────────────────────────────────────

def test_valid_fundamentals():
    data = {
        "ticker": "AKBNK",
        "last_price": 42.50,
        "PE_ratio": 13.6,
        "EPS": 3.12,
        "market_cap": 180_000_000_000,
    }
    is_valid, reason = _is_valid_fundamentals(data)
    assert is_valid is True, f"valid fundamentals rejected: {reason}"


def test_valid_chart():
    data = {
        "ticker": "AKBNK",
        "ohlc_count": 150,
        "ohlc": [
            {"t": 1718000000, "o": 41.0, "h": 42.5, "l": 40.8, "c": 42.1, "v": 1200000},
            {"t": 1718086400, "o": 42.1, "h": 43.0, "l": 41.9, "c": 42.8, "v": 980000},
        ],
    }
    is_valid, reason = _is_valid_chart(data)
    assert is_valid is True, f"valid chart rejected: {reason}"


def test_valid_macro():
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    data = {
        "timestamp": now_ts,
        "XU030": 10245.80,
        "USDTRY": 38.42,
        "EURTRY": 41.85,
    }
    is_valid, reason = _is_valid_macro(data)
    assert is_valid is True, f"valid macro rejected: {reason}"


def test_valid_disk_cache_macro():
    data = {
        "ts": "2026-06-25T05:30:00Z",
        "version": "3.2",
        "cache_key": "macro_global",
        "data": {"XU030": 10245.80, "USDTRY": 38.42},
    }
    is_valid, reason = _is_valid_disk_cache(data)
    assert is_valid is True, f"valid macro cache rejected: {reason}"


def test_valid_disk_cache_hisse():
    data = {
        "ts": "2026-06-25T05:30:00Z",
        "version": "3.2",
        "cache_key": "hisse_AKBNK",
        "data": {
            "ticker": "AKBNK",
            "last_price": 42.50,
            "chart": [{"t": 1718000000, "o": 41.0, "h": 42.5, "l": 40.8, "c": 42.1}],
        },
    }
    is_valid, reason = _is_valid_disk_cache(data)
    assert is_valid is True, f"valid hisse cache rejected: {reason}"
