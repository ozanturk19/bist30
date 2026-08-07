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


def derive_adx_label(adx):
    """ADX değerinden tek kaynaklı trend-gücü etiketi (Site Contract v1.2).

    Eşikler: <18 Zayıf · 18-25 Orta · 25-40 Güçlü · >=40 Çok Güçlü.
    CPO-1196 D0 #4: önceden aynı eşik 6 farklı yüzeyde 6 farklı sayı ile
    tanımlıydı (app.py 3 yer + tarama/hisse/karsilastir/metodoloji şablonları).
    Bu fonksiyon tek kaynak; çağıranlar kendi eşiğini tanımlamaz.
    """
    try:
        a = float(adx)
    except (TypeError, ValueError):
        return "Zayıf"
    if a >= 40:
        return "Çok Güçlü"
    if a >= 25:
        return "Güçlü"
    if a >= 18:
        return "Orta"
    return "Zayıf"


# ── T1.1 (CPO-1321 FAZ 1) — kanonik sözlük evi ──────────────────────────────
# derive_adx_label ile aynı desen: bu 4 sözlük artık tek kaynak. Önceden aynı
# etiketler app.py'de N kez ve 10+ şablonda ayrı ayrı (bazen tutarsız) tanımlıydı.
# T1.2 (CPO-1321): SIGNAL_LABELS['SAT'] eski SAT etiketinden "Trend Bozuldu"ya
# app.py, business_rules.py, blog_content.py, manifest.json ve 18 şablonda
# tek commit'te yeniden adlandırıldı (bkz. tests/test_cpo1321_faz1_t1_2_trend_bozuldu_rename.py).

SIGNAL_LABELS = {
    "AL": "Güçlü Trend",
    "SAT": "Trend Bozuldu",
    "BEKLE": "Yatay",
}

# Kod → görünen ad. Kısa form (gundem/karsilastir/tarama şablonlarındaki
# çoğunluk) kanonik alındı. templates/index.html:5592 farklı, uzun-form bir
# eşleme kullanıyor (örn. "✓ İdeal giriş bölgesi") — bu sapma T1.3/T1.8
# sözlük-tekilleştirme adımında index.html'in kısa forma geçirilmesiyle kapanacak.
ENTRY_QUALITY_LABELS = {
    "IDEAL": "İdeal",
    "IYI": "İyi",
    "DIKKATLI": "Dikkatli",
    "UZAK": "Uzak",
}

# app.py:1753-1767'deki signal_bars eşiklerinin görünen adları (renk kodları
# ayrı tutuldu, bunlar salt metin sözlüğü).
SIGNAL_AGE_LABELS = {
    "TAZE": "Taze",
    "GELISIYOR": "Gelişiyor",
    "OLGUNLASIYOR": "Olgunlaşıyor",
    "OLGUN": "Olgun",
}


def derive_signal_age_label(signal_bars, signal=None):
    """signal_bars eşiğinden tek kaynaklı sinyal-yaşı etiketi (app.py:1753-1767 ile aynı eşik).

    signal="BEKLE" veya signal_bars=None ise etiket yok (None döner) — mevcut davranışla birebir.
    """
    if signal == "BEKLE" or signal_bars is None:
        return None
    try:
        b = float(signal_bars)
    except (TypeError, ValueError):
        return None
    if b <= 3:
        return SIGNAL_AGE_LABELS["TAZE"]
    if b <= 7:
        return SIGNAL_AGE_LABELS["GELISIYOR"]
    if b <= 15:
        return SIGNAL_AGE_LABELS["OLGUNLASIYOR"]
    return SIGNAL_AGE_LABELS["OLGUN"]


# Hacim etiketleri — iki ayrı ölçüt aynı sözlükte, çağıran hangisini istediğini
# anahtarla seçer. CONFIRMED = vol_confirmed booleanının (signal_vol_ratio>=1.7,
# app.py:1652) görünen adı, HIGH/VERY_HIGH = hisse.html:3420'deki ayrı vr eşiği
# (>=3 çok yüksek) — iki ölçüt birbirini geçersiz kılmaz, farklı bağlamlarda kullanılır.
VOLUME_LABELS = {
    "CONFIRMED": "Hacim Onaylı",
    "HIGH": "Yüksek Hacim",
    "VERY_HIGH": "Çok Yüksek Hacim",
}


def derive_volume_label(vol_ratio):
    """vol_ratio eşiğinden tek kaynaklı hacim-büyüklük etiketi (hisse.html:3420 ile aynı eşik)."""
    try:
        vr = float(vol_ratio)
    except (TypeError, ValueError):
        return None
    return VOLUME_LABELS["VERY_HIGH"] if vr >= 3 else VOLUME_LABELS["HIGH"]
