"""
Faz 12 P1 — Data Quality Validator: Business Rules
CPO-693: BIST-specific business rule validation for stock data
"""

import math
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)

# BIST circuit breaker: ±10% günlük limit
BIST_DAILY_LIMIT_PCT = 10.5
MIN_PRICE = 0.01


def validate_change_pct(ticker, change_pct):
    """BIST ±10% tavan kuralı — split/corporate action anomali detection."""
    if change_pct is None or (isinstance(change_pct, float) and math.isnan(change_pct)):
        return {"ok": False, "flag": "ANOMAL_NULL_CHANGE_PCT", "ticker": ticker, "value": change_pct}
    if abs(change_pct) > BIST_DAILY_LIMIT_PCT:
        return {
            "ok": False,
            "flag": "ANOMAL",
            "ticker": ticker,
            "value": change_pct,
            "msg": f"change_pct {change_pct:.2f}% BIST %10 tavan ihlali",
        }
    return {"ok": True, "ticker": ticker, "value": change_pct}


def validate_price(ticker, price, field="price"):
    """Fiyat geçerliliği: pozitif, not None, not NaN."""
    if price is None:
        return {"ok": False, "flag": "NULL_PRICE", "ticker": ticker, "field": field}
    if isinstance(price, float) and (math.isnan(price) or math.isinf(price)):
        return {"ok": False, "flag": "NAN_PRICE", "ticker": ticker, "field": field, "value": price}
    try:
        if float(price) <= 0:
            return {"ok": False, "flag": "NEGATIVE_PRICE", "ticker": ticker, "field": field, "value": price}
    except (TypeError, ValueError):
        return {"ok": False, "flag": "INVALID_PRICE", "ticker": ticker, "field": field, "value": price}
    return {"ok": True, "ticker": ticker, "field": field, "value": price}


def validate_signal_consistency(ticker, signal, signal_price):
    """AL sinyali için signal_price zorunlu."""
    if signal and signal.upper() == "AL":
        if signal_price is None or (isinstance(signal_price, float) and math.isnan(signal_price)):
            return {
                "ok": False,
                "flag": "MISSING_SIGNAL_PRICE",
                "ticker": ticker,
                "signal": signal,
                "msg": "signal=AL ama signal_price=None",
            }
    return {"ok": True, "ticker": ticker, "signal": signal}


def validate_date_range(ticker, signal_date):
    """Sinyal tarihi bugün veya geçmişte olmalı (future date = veri hatası)."""
    if signal_date is None:
        return {"ok": True, "ticker": ticker}
    try:
        if isinstance(signal_date, str):
            s = signal_date[:10]
            # DD.MM.YYYY (uygulama formatı) veya ISO YYYY-MM-DD her ikisini destekle
            try:
                sd = datetime.strptime(s, "%d.%m.%Y").date()
            except ValueError:
                sd = datetime.strptime(s, "%Y-%m-%d").date()
        elif isinstance(signal_date, datetime):
            sd = signal_date.date()
        elif isinstance(signal_date, date):
            sd = signal_date
        else:
            return {"ok": False, "flag": "INVALID_DATE", "ticker": ticker, "error": f"unknown type {type(signal_date)}"}
        today = date.today()
        if sd > today:
            return {
                "ok": False,
                "flag": "FUTURE_DATE",
                "ticker": ticker,
                "signal_date": str(sd),
                "today": str(today),
            }
    except Exception as e:
        return {"ok": False, "flag": "INVALID_DATE", "ticker": ticker, "error": str(e)}
    return {"ok": True, "ticker": ticker, "signal_date": str(sd)}


def validate_stock(stock_dict):
    """
    Bir hissenin tüm business rule'larını çalıştır.
    Returns: list[dict] — boş liste = tümü geçti
    """
    ticker = stock_dict.get("ticker", "UNKNOWN")
    errors = []

    r = validate_change_pct(ticker, stock_dict.get("change_pct"))
    if not r["ok"]:
        logger.warning("BRV_FAIL %s: %s change_pct=%s", ticker, r["flag"], stock_dict.get("change_pct"))
        errors.append(r)

    r = validate_price(ticker, stock_dict.get("price"))
    if not r["ok"]:
        logger.warning("BRV_FAIL %s: %s price=%s", ticker, r["flag"], stock_dict.get("price"))
        errors.append(r)

    r = validate_signal_consistency(ticker, stock_dict.get("signal"), stock_dict.get("signal_price"))
    if not r["ok"]:
        logger.warning("BRV_FAIL %s: %s signal=%s", ticker, r["flag"], stock_dict.get("signal"))
        errors.append(r)

    r = validate_date_range(ticker, stock_dict.get("signal_date"))
    if not r["ok"]:
        logger.warning("BRV_FAIL %s: %s signal_date=%s", ticker, r["flag"], stock_dict.get("signal_date"))
        errors.append(r)

    return errors


def validate_stocks_list(stocks):
    """
    Tüm hisse listesini validate et.
    Returns: {"total": N, "errors": [...], "failed_tickers": [...]}
    """
    all_errors = []
    for s in stocks:
        errs = validate_stock(s)
        all_errors.extend(errs)

    failed = list({e["ticker"] for e in all_errors})
    if all_errors:
        logger.warning("BRV: %d violations across %d tickers: %s",
                       len(all_errors), len(failed), failed)

    return {"total": len(stocks), "errors": all_errors, "failed_tickers": failed}
