"""
Faz 12 P1 — Data Quality Validator: Anomaly Detection
CPO-693: Z-score price anomaly + volume spike detection
"""

import math
import logging

logger = logging.getLogger(__name__)

DEFAULT_ZSCORE_THRESHOLD = 3.0
DEFAULT_VOLUME_SPIKE_RATIO = 10.0
MIN_HISTORY_LEN = 2


def _mean_std(values):
    """Compute (mean, std) for a list of floats. Returns (None, None) if insufficient data."""
    clean = [v for v in values if v is not None and isinstance(v, (int, float)) and not math.isnan(v)]
    if len(clean) < MIN_HISTORY_LEN:
        return None, None
    n = len(clean)
    mean = sum(clean) / n
    variance = sum((x - mean) ** 2 for x in clean) / n
    std = math.sqrt(variance)
    return mean, std


def z_score_check(ticker, today_val, history, threshold=DEFAULT_ZSCORE_THRESHOLD, field="price"):
    """
    Z-score anomaly: |today - mean_5d| / std_5d > threshold.

    today_val: float — today's value
    history:   list[float | None] — recent historical values (5 days typical)
    Returns error dict or None if ok / insufficient data.
    """
    if today_val is None or (isinstance(today_val, float) and math.isnan(today_val)):
        return None
    mean, std = _mean_std(history)
    if mean is None:
        return None
    if std == 0.0:
        return None
    z = abs(float(today_val) - mean) / std
    if z > threshold:
        err = {
            "ok": False, "flag": "Z_SCORE_ANOMALY",
            "ticker": ticker, "field": field,
            "today": float(today_val), "mean": round(mean, 4),
            "std": round(std, 4), "z_score": round(z, 3),
            "threshold": threshold,
            "msg": f"{field} z={z:.2f} > {threshold} (mean={mean:.3f}, std={std:.3f})",
        }
        logger.warning("ANOMALY %s: %s z=%.2f threshold=%.1f", ticker, field, z, threshold)
        return err
    return None


def volume_spike(ticker, today_vol, vol_history, spike_ratio=DEFAULT_VOLUME_SPIKE_RATIO):
    """
    Volume spike: today_vol / avg_5d_vol > spike_ratio.

    Returns error dict or None if ok / insufficient data.
    """
    if today_vol is None or (isinstance(today_vol, float) and math.isnan(today_vol)):
        return None
    mean, _ = _mean_std(vol_history)
    if mean is None or mean == 0.0:
        return None
    ratio = float(today_vol) / mean
    if ratio > spike_ratio:
        err = {
            "ok": False, "flag": "VOLUME_SPIKE",
            "ticker": ticker,
            "today_vol": float(today_vol), "avg_vol": round(mean, 0),
            "ratio": round(ratio, 2), "spike_ratio": spike_ratio,
            "msg": f"volume {today_vol:.0f} = {ratio:.1f}x avg {mean:.0f}",
        }
        logger.warning("ANOMALY %s: VOLUME_SPIKE ratio=%.1f threshold=%.1f", ticker, ratio, spike_ratio)
        return err
    return None


def validate_stock_anomaly(stock):
    """
    Run anomaly checks for a single stock dict.

    Expected keys (all optional):
      ticker, today_price, price_history (list),
      today_volume, volume_history (list)

    Returns list[dict] — empty = no anomalies found.
    """
    ticker = stock.get("ticker", "UNKNOWN")
    errors = []

    r = z_score_check(ticker, stock.get("today_price"), stock.get("price_history", []))
    if r:
        errors.append(r)

    r = volume_spike(ticker, stock.get("today_volume"), stock.get("volume_history", []))
    if r:
        errors.append(r)

    return errors


def compute_stock_anomaly_score(stock, threshold=2.0):
    """Compute UI anomaly score for a single stock. Returns {score, flag, reason}.
    Uses lower threshold than DQV alerting (2.0 vs 3.0) for UI badge display.
    """
    ticker = stock.get("ticker", "UNKNOWN")
    r = z_score_check(ticker, stock.get("today_price"), stock.get("price_history", []),
                      threshold=threshold)
    if r:
        return {"score": r["z_score"], "flag": True,
                "reason": f"z-score {r['z_score']}σ (son 5g std'den sapma)"}
    return {"score": 0.0, "flag": False, "reason": ""}


def validate_anomalies_list(stocks_with_history):
    """
    Run anomaly detection across all stocks.

    stocks_with_history: list[dict] — each has ticker + today_price/volume + histories

    Returns: {"total": N, "errors": [...], "failed_tickers": [...]}
    """
    all_errors = []
    for s in stocks_with_history:
        all_errors.extend(validate_stock_anomaly(s))

    failed = list({e["ticker"] for e in all_errors})
    if all_errors:
        logger.warning(
            "ANOMALY: %d anomalies across %d tickers: %s",
            len(all_errors), len(failed), failed,
        )
    return {"total": len(stocks_with_history), "errors": all_errors, "failed_tickers": failed}
