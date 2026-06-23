"""Faz 12 P2.4 — DQV multi-tier alerting (monitoring-only, non-blocking)"""

import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ALERT_MD_PATH = os.environ.get("DQV_ALERT_PATH", "/root/bist30/ALERT.md")

# DQV event → tier (P0=critical/immediate, P1=hourly-summary)
DQV_TIER = {
    "DQV_BR":       "P1",
    "DQV_CROSS":    "P1",
    "DQV_ANOMALY":  "P1",
    "DQV_EMAIL_QA": "P1",
    "DQV_SV_DATA":  "P0",
    "DQV_SV_MACRO": "P0",
    "DQV_SV_CHART": "P0",
}


def emit_alert(event: str, detail: str = "", ticker: str = None, _sentry=None):
    """
    Non-blocking DQV alert. Tier derived from DQV_TIER (default P1).
    P0: ALERT.md append + logger.warning + sentry.capture_message(level='error')
    P1: ALERT.md append + logger.warning
    _sentry: sentry_sdk module if available, else None
    All exceptions swallowed — never raises.
    """
    try:
        tier = DQV_TIER.get(event, "P1")
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        ticker_tag = f"[{ticker}]" if ticker else ""
        line = f"[{ts}] {tier}{ticker_tag} {event}: {detail}"

        logger.warning("ALERT_%s %s%s: %s", tier, event, ticker_tag, detail)
        _append_alert_md(line)

        if tier == "P0" and _sentry is not None:
            try:
                _sentry.capture_message(
                    f"ALERT_P0 {event}{ticker_tag}: {detail}", level="error")
            except Exception as _se:
                logger.warning("Sentry P0 capture failed: %s", _se)
    except Exception as _e:
        logger.warning("emit_alert exception: %s", _e)


def _append_alert_md(line: str):
    try:
        with open(ALERT_MD_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as _e:
        logger.warning("ALERT.md append failed: %s", _e)
