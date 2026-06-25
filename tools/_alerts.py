"""api_stale Alert — Phase 3 #2 Paket 1
Pure functions for API staleness detection and alert formatting.
No global state. Integration: call from background_refresh + ALERT.md append.
"""

import time
from typing import Optional


def _check_api_stale(
    cache_ts: Optional[float],
    market_open: bool,
    threshold_min: float = 10,
) -> Optional[dict]:
    """Returns alert dict if cache is stale during market hours, else None.

    cache_ts: UNIX timestamp of last successful cache refresh, or None.
    market_open: True when BIST is in session.
    threshold_min: minutes before considered stale (default 10).
    """
    if not market_open:
        return None
    if cache_ts is None:
        return None

    age_sec = time.time() - cache_ts
    age_min = age_sec / 60

    if age_min < threshold_min:
        return None

    return {
        "level": "CRITICAL",
        "type": "api_stale",
        "age_min": round(age_min, 1),
        "threshold_min": threshold_min,
        "cache_ts": cache_ts,
    }


def _format_alert_md(alert: dict) -> str:
    """Returns a red ALERT.md line for the given alert dict."""
    if alert.get("type") == "api_stale":
        return (
            f"🔴 ALERT [{alert['level']}] api_stale — "
            f"cache {alert['age_min']}dk eski (eşik: {alert['threshold_min']}dk)"
        )
    return f"🔴 ALERT [{alert.get('level', 'UNKNOWN')}] {alert.get('type', 'unknown')}"


def _should_alert_telegram(
    alert: dict,
    last_alert_ts: Optional[float] = None,
    cooldown_min: float = 5,
) -> bool:
    """Returns True if alert should be forwarded to Telegram.

    Enforces market_open guard (alert must exist) and cooldown window.
    last_alert_ts: UNIX timestamp of last Telegram alert sent, or None.
    cooldown_min: minimum minutes between Telegram alerts (default 5).
    """
    if not alert:
        return False

    if last_alert_ts is None:
        return True

    elapsed_sec = time.time() - last_alert_ts
    return elapsed_sec >= cooldown_min * 60
