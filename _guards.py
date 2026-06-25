"""Daemon Corruption Guard — Phase 3 #2 Paket 5
Pure validation functions, no global state or side effects.
"""

import json
from datetime import datetime, timezone, timedelta


def _is_valid_fundamentals(data: dict) -> tuple[bool, str]:
    """Returns (is_valid, reason). Validates fundamentals cache data."""
    required = {"ticker", "last_price", "PE_ratio", "EPS", "market_cap"}
    missing = required - data.keys()
    if missing:
        return False, f"missing required keys: {sorted(missing)}"

    if not isinstance(data["last_price"], (int, float)):
        return False, f"last_price must be numeric, got {type(data['last_price']).__name__}"

    if data["EPS"] is None:
        return False, "EPS is null"

    if data["market_cap"] is not None and data["market_cap"] < 0:
        return False, f"market_cap is negative: {data['market_cap']}"

    return True, "ok"


def _is_valid_chart(data: dict) -> tuple[bool, str]:
    """Returns (is_valid, reason). Validates OHLC chart cache data."""
    required = {"ticker", "ohlc_count", "ohlc"}
    missing = required - data.keys()
    if missing:
        return False, f"missing required keys: {sorted(missing)}"

    if data["ohlc_count"] < 100:
        return False, f"ohlc_count {data['ohlc_count']} < 100 minimum"

    ohlc = data["ohlc"]
    if not isinstance(ohlc, list) or len(ohlc) == 0:
        return False, "ohlc is empty or not a list"

    prev_t = None
    for entry in ohlc:
        t = entry.get("t")
        if t is not None:
            if prev_t is not None and t <= prev_t:
                return False, f"timestamps not ascending: {t} <= {prev_t}"
            prev_t = t

    for entry in ohlc:
        for field in ("o", "h", "l", "c"):
            val = entry.get(field)
            if val is not None and val < 0:
                return False, f"negative OHLC value: {field}={val}"

    if "volume_array" in data:
        va = data["volume_array"]
        if not isinstance(va, list) or len(va) == 0:
            return False, "volume_array is empty"

    return True, "ok"


def _is_valid_macro(data: dict, max_age_hours: int = 24) -> tuple[bool, str]:
    """Returns (is_valid, reason). Validates macro index cache data."""
    if not data or "XU030" not in data:
        return False, "missing required key: XU030"

    xu030 = data["XU030"]
    if xu030 is None:
        return False, "XU030 is null"

    if isinstance(xu030, dict):
        if "last_price" not in xu030:
            return False, "XU030 nested dict missing last_price"
    elif not isinstance(xu030, (int, float)):
        return False, f"XU030 invalid type: {type(xu030).__name__}"

    if "USDTRY" in data:
        usdtry = data["USDTRY"]
        if not isinstance(usdtry, (int, float)):
            return False, f"USDTRY must be numeric, got {type(usdtry).__name__}: {usdtry!r}"

    if "timestamp" in data:
        try:
            ts = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - ts
            if age > timedelta(hours=max_age_hours):
                return False, f"stale data: {age.total_seconds() / 3600:.1f}h old (max {max_age_hours}h)"
        except (ValueError, TypeError) as e:
            return False, f"invalid timestamp: {e}"

    return True, "ok"


def _is_valid_disk_cache(raw) -> tuple[bool, str]:
    """Returns (is_valid, reason). raw can be str (JSON string) or dict."""
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return False, f"JSONDecodeError: {e}"
    elif isinstance(raw, dict):
        data = raw
    else:
        return False, f"unexpected input type: {type(raw).__name__}"

    version = data.get("version")
    if version is not None and not str(version).startswith("3."):
        return False, f"SchemaMismatch: version {version!r} expected 3.x"

    if "data" not in data:
        return False, "InvalidData: missing 'data' field"

    if data["data"] is None:
        return False, "InvalidData: 'data' is null"

    if not isinstance(data["data"], dict):
        return False, f"InvalidData: 'data' must be dict, got {type(data['data']).__name__}"

    cache_key = data.get("cache_key", "")
    if isinstance(cache_key, str) and cache_key.startswith("hisse_"):
        if "chart" not in data["data"]:
            return False, "InvalidData: hisse cache missing 'chart' in data"

    return True, "ok"
