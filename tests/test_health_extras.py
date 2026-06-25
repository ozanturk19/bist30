"""Paket 4 — Health Endpoint Extras test suite"""

import os
import sys
import time
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from _health_extras import (
    _compute_uptime_sec,
    _compute_cache_age_min,
    _compute_subprocess_pool_pending,
    _compute_ohlc_count_aggregate,
    _compute_stocks_cached_count,
    _get_app_version,
    _extend_health_payload,
)


# ── _compute_uptime_sec ───────────────────────────────────────────────────────

def test_uptime_monotone():
    """Uptime increases over time (sleep 0.15s > 0.1s rounding step)."""
    startup = time.time() - 100
    u1 = _compute_uptime_sec(startup)
    time.sleep(0.15)
    u2 = _compute_uptime_sec(startup)
    assert u2 > u1


def test_uptime_approximate():
    """Uptime ≈ elapsed seconds."""
    startup = time.time() - 60
    u = _compute_uptime_sec(startup)
    assert 59.0 <= u <= 61.0


# ── _compute_cache_age_min ────────────────────────────────────────────────────

def test_cache_age_min_correct():
    """cache_age_min returns correct minutes."""
    ts = time.time() - 120  # 2 minutes ago
    age = _compute_cache_age_min(ts)
    assert 1.9 <= age <= 2.1


def test_cache_age_min_none():
    """cache_ts=None → returns None."""
    assert _compute_cache_age_min(None) is None


# ── _compute_subprocess_pool_pending ─────────────────────────────────────────

def test_subprocess_pool_mock_5():
    """Mock executor with qsize=5 returns 5."""
    mock_exec = MagicMock()
    mock_exec._work_queue.qsize.return_value = 5
    assert _compute_subprocess_pool_pending(mock_exec) == 5


def test_subprocess_pool_none_returns_zero():
    """executor=None → returns 0."""
    assert _compute_subprocess_pool_pending(None) == 0


def test_subprocess_pool_safe_on_exception():
    """Exception in qsize → returns 0 (safe wrapper)."""
    mock_exec = MagicMock()
    mock_exec._work_queue.qsize.side_effect = AttributeError("no queue")
    assert _compute_subprocess_pool_pending(mock_exec) == 0


# ── _get_app_version ──────────────────────────────────────────────────────────

def test_app_version_constant():
    """Version string is constant '0.1.0'."""
    assert _get_app_version() == "0.1.0"


def test_app_version_stable():
    """Version string does not change between calls."""
    assert _get_app_version() == _get_app_version()


# ── _compute_ohlc_count_aggregate ─────────────────────────────────────────────

def test_ohlc_count_aggregate_sum():
    """Sum of ohlc_count across stocks."""
    stocks = {
        "THYAO": {"ohlc_count": 250},
        "GARAN": {"ohlc_count": 300},
        "AKBNK": {"ohlc_count": 150},
    }
    assert _compute_ohlc_count_aggregate(stocks) == 700


def test_ohlc_count_aggregate_empty():
    """Empty stocks → 0."""
    assert _compute_ohlc_count_aggregate({}) == 0


def test_ohlc_count_aggregate_missing_key():
    """Stocks without ohlc_count are skipped."""
    stocks = {
        "THYAO": {"ohlc_count": 200},
        "GARAN": {"ticker": "GARAN"},  # no ohlc_count
    }
    assert _compute_ohlc_count_aggregate(stocks) == 200


# ── _extend_health_payload ────────────────────────────────────────────────────

def test_extend_health_payload_backwards_compat():
    """Existing fields in base are preserved unchanged."""
    base = {"status": "ok", "custom_field": "preserved"}
    startup = time.time() - 60
    result = _extend_health_payload(base, startup_ts=startup)
    assert result["status"] == "ok"
    assert result["custom_field"] == "preserved"


def test_extend_health_payload_six_new_fields():
    """All 6 new fields are present in result."""
    base = {"status": "ok"}
    startup = time.time() - 60
    result = _extend_health_payload(base, startup_ts=startup)
    for field in ("uptime_sec", "cache_age_min", "subprocess_pool_pending",
                  "ohlc_count_aggregate", "stocks_cached_count", "app_version"):
        assert field in result, f"Missing field: {field}"


def test_extend_health_payload_no_mutation():
    """Base dict is not mutated."""
    base = {"status": "ok"}
    startup = time.time() - 60
    _extend_health_payload(base, startup_ts=startup)
    assert "uptime_sec" not in base


def test_extend_health_payload_stocks_cached_count():
    """stocks_cached_count reflects number of stocks passed."""
    base = {}
    startup = time.time() - 60
    stocks = {"THYAO": {"ohlc_count": 250}, "GARAN": {"ohlc_count": 300}}
    result = _extend_health_payload(base, startup_ts=startup, stocks=stocks)
    assert result["stocks_cached_count"] == 2
