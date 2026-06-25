"""Paket 1 — api_stale Alert test suite"""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from _alerts import _check_api_stale, _format_alert_md, _should_alert_telegram


# ── _check_api_stale ──────────────────────────────────────────────────────────

def test_stale_5min_no_alert():
    """Stale +5min < threshold 10min → no alert."""
    ts = time.time() - 5 * 60
    assert _check_api_stale(ts, market_open=True, threshold_min=10) is None


def test_stale_15min_market_open_alert():
    """Stale +15min + market_open=True → ALERT dict."""
    ts = time.time() - 15 * 60
    alert = _check_api_stale(ts, market_open=True, threshold_min=10)
    assert alert is not None
    assert alert["level"] == "CRITICAL"
    assert alert["type"] == "api_stale"
    assert alert["age_min"] >= 14.9


def test_stale_15min_market_closed_no_alert():
    """Stale +15min + market_open=False → no alert (seans dışı normal)."""
    ts = time.time() - 15 * 60
    assert _check_api_stale(ts, market_open=False, threshold_min=10) is None


def test_cache_ts_none_no_alert():
    """cache_ts=None → no alert."""
    assert _check_api_stale(None, market_open=True) is None


def test_stale_just_below_threshold_no_alert():
    """Stale 9.9min < threshold 10min → no alert (boundary)."""
    ts = time.time() - 9.9 * 60
    assert _check_api_stale(ts, market_open=True, threshold_min=10) is None


def test_stale_alert_contains_age_and_threshold():
    """ALERT dict contains age_min and threshold_min fields."""
    ts = time.time() - 20 * 60
    alert = _check_api_stale(ts, market_open=True, threshold_min=10)
    assert alert is not None
    assert "age_min" in alert
    assert alert["threshold_min"] == 10
    assert alert["age_min"] >= 19.9


# ── _format_alert_md ──────────────────────────────────────────────────────────

def test_format_alert_md_schema():
    """ALERT line contains level, type, age_min and red indicator."""
    alert = {"level": "CRITICAL", "type": "api_stale", "age_min": 15.3, "threshold_min": 10}
    line = _format_alert_md(alert)
    assert "CRITICAL" in line
    assert "api_stale" in line
    assert "15.3" in line
    assert "🔴" in line


def test_format_alert_md_unknown_type():
    """Unknown alert type → generic fallback line with level."""
    alert = {"level": "WARNING", "type": "unknown_type"}
    line = _format_alert_md(alert)
    assert "🔴" in line
    assert "WARNING" in line


# ── _should_alert_telegram ────────────────────────────────────────────────────

def test_telegram_no_prior_alert_should_send():
    """No prior alert → should send."""
    alert = {"level": "CRITICAL", "type": "api_stale", "age_min": 15.0, "threshold_min": 10}
    assert _should_alert_telegram(alert, last_alert_ts=None) is True


def test_telegram_cooldown_active_no_send():
    """Within 5min cooldown → should NOT send."""
    alert = {"level": "CRITICAL", "type": "api_stale", "age_min": 15.0, "threshold_min": 10}
    recent_ts = time.time() - 2 * 60  # 2 minutes ago
    assert _should_alert_telegram(alert, last_alert_ts=recent_ts, cooldown_min=5) is False


def test_telegram_cooldown_expired_should_send():
    """Past 5min cooldown → should send."""
    alert = {"level": "CRITICAL", "type": "api_stale", "age_min": 15.0, "threshold_min": 10}
    old_ts = time.time() - 6 * 60  # 6 minutes ago
    assert _should_alert_telegram(alert, last_alert_ts=old_ts, cooldown_min=5) is True


def test_telegram_empty_alert_no_send():
    """Empty alert dict → no send."""
    assert _should_alert_telegram({}) is False
