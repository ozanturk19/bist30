"""
Faz 12 P1 — Data Quality Validator: Cross Consistency
CPO-693: Compare price data across /api/data, /api/hisse/X/chart, /api/macro
"""

import math
import logging
from itertools import combinations

logger = logging.getLogger(__name__)

DEFAULT_TOLERANCE_PCT = 0.5


def _compare_two_prices(ticker, price_a, price_b, source_a, source_b, tolerance_pct):
    """Compare two price values. Returns error dict or None if ok."""
    if price_a is None or price_b is None:
        return None
    if isinstance(price_a, float) and (math.isnan(price_a) or math.isinf(price_a)):
        return None
    if isinstance(price_b, float) and (math.isnan(price_b) or math.isinf(price_b)):
        return None
    try:
        fa, fb = float(price_a), float(price_b)
    except (TypeError, ValueError):
        return None
    if fa == 0.0:
        return {
            "ok": False, "flag": "ZERO_PRICE_FOR_COMPARISON",
            "ticker": ticker, "source_a": source_a, "price_a": fa,
        }
    pct_diff = abs(fa - fb) / fa * 100
    if pct_diff > tolerance_pct:
        return {
            "ok": False, "flag": "CROSS_INCONSISTENCY",
            "ticker": ticker,
            "source_a": source_a, "price_a": fa,
            "source_b": source_b, "price_b": fb,
            "pct_diff": round(pct_diff, 3),
            "tolerance_pct": tolerance_pct,
            "msg": (
                f"{source_a}={fa} vs {source_b}={fb}: "
                f"{pct_diff:.3f}% > tol {tolerance_pct}%"
            ),
        }
    return None


def compare_price_across_endpoints(ticker, prices_by_source, tolerance_pct=DEFAULT_TOLERANCE_PCT):
    """
    Compare prices from multiple sources for one ticker.

    prices_by_source: {source_name: price_or_None}
    e.g. {"api_data": 45.2, "api_chart": 45.1, "api_macro": None}

    Returns list of error dicts (empty = all consistent).
    Skips comparisons where either value is None/NaN.
    """
    errors = []
    sources = list(prices_by_source.items())
    for (name_a, price_a), (name_b, price_b) in combinations(sources, 2):
        err = _compare_two_prices(ticker, price_a, price_b, name_a, name_b, tolerance_pct)
        if err:
            logger.warning(
                "CROSS_INCONS %s: %s=%s vs %s=%s (%.3f%%)",
                ticker, name_a, price_a, name_b, price_b,
                err.get("pct_diff", 0),
            )
            errors.append(err)
    return errors


def validate_data_vs_chart(ticker, data_price, chart_last_close, tolerance_pct=DEFAULT_TOLERANCE_PCT):
    """Shorthand: /api/data price vs /api/hisse/X/chart last close."""
    if chart_last_close is None:
        return [{"ok": False, "flag": "CACHE_MISS", "ticker": ticker,
                 "source": "api_chart", "msg": "chart cache None — cross-check atlandı"}]
    return compare_price_across_endpoints(
        ticker,
        {"api_data": data_price, "api_chart": chart_last_close},
        tolerance_pct,
    )


def validate_stocks_cross_consistency(stocks, charts_map, tolerance_pct=DEFAULT_TOLERANCE_PCT):
    """
    Check all stocks for price consistency between /api/data and /api/hisse/X/chart.

    stocks:     list[dict] — each has 'ticker' and 'price'
    charts_map: dict[str, float | None] — {ticker: last_close_or_None}

    Returns: {"total": N, "checked": M, "errors": [...], "failed_tickers": [...]}
    """
    all_errors = []
    checked = 0
    for s in stocks:
        ticker = s.get("ticker", "UNKNOWN")
        data_price = s.get("price")
        chart_price = charts_map.get(ticker)
        if data_price is None and chart_price is None:
            continue
        checked += 1
        errs = validate_data_vs_chart(ticker, data_price, chart_price, tolerance_pct)
        all_errors.extend(errs)

    failed = list({e["ticker"] for e in all_errors})
    if all_errors:
        logger.warning(
            "CROSS: %d inconsistencies across %d tickers: %s",
            len(all_errors), len(failed), failed,
        )
    return {
        "total": len(stocks),
        "checked": checked,
        "errors": all_errors,
        "failed_tickers": failed,
    }
