"""Health Endpoint Extras — Phase 3 #2 Paket 4
Pure helper functions for /api/health extended payload (6 new fields).
No global state. Integration: call _extend_health_payload() in /api/health handler.
"""

import time
from typing import Any, Optional

_APP_VERSION = "0.1.0"


def _compute_uptime_sec(startup_ts: float) -> float:
    """Returns seconds elapsed since startup_ts (UNIX timestamp)."""
    return round(time.time() - startup_ts, 1)


def _compute_cache_age_min(last_refresh_ts: Optional[float]) -> Optional[float]:
    """Returns minutes since last refresh, or None if ts is None."""
    if last_refresh_ts is None:
        return None
    return round((time.time() - last_refresh_ts) / 60, 2)


def _compute_subprocess_pool_pending(executor: Any = None) -> int:
    """Returns pending task count from executor work queue, or 0 on any failure."""
    if executor is None:
        return 0
    try:
        return executor._work_queue.qsize()
    except Exception:
        return 0


def _compute_ohlc_count_aggregate(stocks: dict) -> int:
    """Returns sum of ohlc_count across all cached stock entries."""
    total = 0
    for stock_data in stocks.values():
        if isinstance(stock_data, dict):
            count = stock_data.get("ohlc_count")
            if isinstance(count, int):
                total += count
    return total


def _compute_stocks_cached_count(stocks: dict) -> int:
    """Returns number of stocks present in the cache dict."""
    return len(stocks)


def _get_app_version() -> str:
    """Returns application version string."""
    return _APP_VERSION


def _check_health_loop_stall(now: float, last_tick_ts: float, threshold_s: float = 15) -> Optional[float]:
    """Returns the gap in seconds if it exceeds threshold_s, else None.

    Pure/stateless — caller owns last_tick_ts persistence and logging.
    CPO-1068 (b) — forensic-only stall detection for _health_snapshot_loop.
    """
    gap = now - last_tick_ts
    return gap if gap > threshold_s else None


def _extend_health_payload(
    base: dict,
    startup_ts: float,
    last_refresh_ts: Optional[float] = None,
    executor: Any = None,
    stocks: Optional[dict] = None,
) -> dict:
    """Returns base payload with 6 extra health fields merged in.
    Does not mutate base. Backwards-compatible — existing keys preserved.

    Added fields: uptime_sec, cache_age_min, subprocess_pool_pending,
    ohlc_count_aggregate, stocks_cached_count, app_version.
    """
    _stocks = stocks or {}
    extras = {
        "uptime_sec": _compute_uptime_sec(startup_ts),
        "cache_age_min": _compute_cache_age_min(last_refresh_ts),
        "subprocess_pool_pending": _compute_subprocess_pool_pending(executor),
        "ohlc_count_aggregate": _compute_ohlc_count_aggregate(_stocks),
        "stocks_cached_count": _compute_stocks_cached_count(_stocks),
        "app_version": _get_app_version(),
    }
    return {**base, **extras}
