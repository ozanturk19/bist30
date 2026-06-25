"""SLA Tracker Helpers — SPEC-016 Pre-Implementation
Standalone helpers for /api/sla endpoint.
No app.py dependency — integration is ~5dk post-Pzt cutover.
"""

import json
import subprocess
from typing import Optional


# ── Nginx 5xx ────────────────────────────────────────────────────────────────

def _count_nginx_5xx(window_hours: int = 24) -> int:
    """Count nginx 5xx responses in the current access log.

    Uses awk field 9 (status code). Returns -1 on any error.
    Note: window_hours is advisory — counts current log file, not a strict time window.
    """
    try:
        result = subprocess.run(
            ["awk", "$9~/^5/{c++} END{print c+0}", "/var/log/nginx/access.log"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        count_str = result.stdout.strip()
        return int(count_str) if count_str.isdigit() else 0
    except Exception:
        return -1


# ── Data Freshness ────────────────────────────────────────────────────────────

def _compute_sla_freshness(stocks_age_s: float, threshold_s: float = 1800) -> dict:
    """Classify data freshness into TAZE / STALE / CRITICAL.

    Thresholds:
      TAZE     — age < threshold_s (default 30dk)
      STALE    — threshold_s <= age < threshold_s * 2
      CRITICAL — age >= threshold_s * 2
    """
    age_s = float(stocks_age_s)
    if age_s < threshold_s:
        status = "TAZE"
    elif age_s < threshold_s * 2:
        status = "STALE"
    else:
        status = "CRITICAL"
    return {
        "age_s": round(age_s),
        "age_min": round(age_s / 60, 1),
        "threshold_s": threshold_s,
        "status": status,
    }


# ── Smoke Result ─────────────────────────────────────────────────────────────

_DEFAULT_SMOKE_RESULT_PATH = "/var/log/bist30-smoke-last.json"

# Expected file format (JSON):
# {"pass": 6, "total": 6, "ts": "2026-06-25 09:47", "result": "PASS"}


def _compute_sla_smoke(last_smoke_result_path: Optional[str] = None) -> dict:
    """Parse last smoke result file → PASS / WARN / FAIL.

    Returns graceful default if file is missing (result=None).
    """
    path = last_smoke_result_path or _DEFAULT_SMOKE_RESULT_PATH
    try:
        with open(path, "r") as f:
            data = json.load(f)
        passed = int(data.get("pass", 0))
        total = int(data.get("total", 6))
        ts = data.get("ts", "")
        raw_result = str(data.get("result", "")).upper()
        if raw_result == "PASS":
            result = "PASS"
        elif raw_result == "WARN":
            result = "WARN"
        else:
            result = "FAIL"
        return {"pass": passed, "total": total, "ts": ts, "result": result}
    except FileNotFoundError:
        return {"pass": None, "total": None, "ts": None, "result": None}
    except Exception:
        return {"pass": None, "total": None, "ts": None, "result": "FAIL"}


# ── Payload Builder ───────────────────────────────────────────────────────────

def _build_sla_payload(
    stocks_age_s: float,
    smoke_result_path: Optional[str] = None,
) -> dict:
    """Build the full /api/sla response dict from the three SLA labels."""
    return {
        "freshness": _compute_sla_freshness(stocks_age_s),
        "smoke": _compute_sla_smoke(smoke_result_path),
        "nginx_5xx_24h": _count_nginx_5xx(),
    }
