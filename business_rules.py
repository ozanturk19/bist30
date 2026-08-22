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
    try:
        cp = float(change_pct)
    except (TypeError, ValueError):
        return {"ok": False, "flag": "INVALID_CHANGE_PCT", "ticker": ticker, "value": change_pct}
    if abs(cp) > BIST_DAILY_LIMIT_PCT:
        return {
            "ok": False,
            "flag": "ANOMAL",
            "ticker": ticker,
            "value": change_pct,
            "msg": f"change_pct {cp:.2f}% BIST %10 tavan ihlali",
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
    if isinstance(signal, str) and signal.upper() == "AL":
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
        today = _today_tr()
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
# çoğunluk) kanonik alındı. templates/index.html eskiden farklı, uzun-form bir
# eşleme kullanıyordu (örn. "✓ İdeal giriş bölgesi") — bu sapma r41'de (22.08,
# commit fd4d9f5) index.html'in kısa forma geçirilmesiyle kapatıldı.
ENTRY_QUALITY_LABELS = {
    "IDEAL": "İdeal",
    "IYI": "İyi",
    "DIKKATLI": "Dikkatli",
    "UZAK": "Uzak",
}

# ── CPO-1335 — göreli tarih etiketi kanonik türetimi ────────────────────────
# KUSUR: "Bugün"/"Dün" etiketi iki DONMUŞ eksenden türetiliyordu:
#   (a) signal_bars — veri setindeki bar sayısı. Ticker o gün tazelenmezse son
#       bar dünün barıdır, dolayısıyla bars=1 "bugün" demek değildir. Canlı
#       kanıt 08.08.2026 (payda 215): bars=1 hem 07.08 hem 06.08 signal_date'ine
#       düşüyordu; bars=2 -> 06.08 ve 05.08; bars=3 -> 04.08 ve 05.08. Sapma tek
#       tip DEĞİL — "hepsini bir gün geri al" düzeltmesi işe yaramaz.
#   (b) is_new_signal — analyze() içinde (signal_date == today_str) olarak
#       hesaplanıp payload'a donduruluyor (app.py:1635). Ticker tazelenmezse
#       eski günün True'su taşınıyor: RYSAS is_new_signal=True, signal_date=
#       06.08, ölçüm günü 08.08 → anasayfa hero'su "bugün güçlü trende geçti"
#       diyordu. Bu alan analyze()'ın (DEV1 alanı) çıktısı; BURADA
#       DEĞİŞTİRİLMİYOR, yalnız TÜKETİM tarafı artık ona güvenmiyor.
#
# KANONİK EKSEN: signal_date — payload'da 215/215 dolu, "DD.MM.YYYY", gerçek bar
# tarihinden türer (app.py:1619/1623). Etiket GERÇEK bugünle (Europe/Istanbul)
# karşılaştırılarak OKUMA/RENDER ANINDA üretilir.
#
# Tarih bilinmiyorsa etiket ÜRETİLMEZ (None) — çağıran nötr bir şey basmalı,
# ASLA "Bugün"e düşmemeli (eski `bars || 1` deseninin tuzağı buydu).
#
# JS aynası: static/bp-format.js (bpSignalDateLabel) — eşikler birebir aynı,
# tests/test_cpo1335_signal_date_label.py ikisini birlikte kilitler.

SIGNAL_DATE_LABELS = {
    "TODAY": "Bugün",
    "YESTERDAY": "Dün",
}

_TZ_TR_NAME = "Europe/Istanbul"


def _today_tr():
    """Europe/Istanbul takvim günü. zoneinfo yoksa sistem yerel gününe düşer."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(_TZ_TR_NAME)).date()
    except Exception as e:
        logger.warning(
            "BRV: zoneinfo/tzdata Europe/Istanbul kullanilamiyor (%s), sistem yerel gunune dusuluyor",
            e,
        )
        return date.today()


def parse_signal_date(signal_date):
    """"DD.MM.YYYY" -> date. Ayrıştırılamazsa None — varsayım YOK."""
    if isinstance(signal_date, datetime):
        return signal_date.date()
    if isinstance(signal_date, date):
        return signal_date
    if not isinstance(signal_date, str):
        return None
    try:
        return datetime.strptime(signal_date.strip(), "%d.%m.%Y").date()
    except (ValueError, TypeError):
        return None


def signal_date_age_days(signal_date, today=None):
    """signal_date ile bugün arasındaki TAKVİM GÜNÜ farkı. Bilinmiyorsa None.

    Pozitif = geçmiş, 0 = bugün, negatif = gelecek (savunma amaçlı ele alınır).
    """
    sd = parse_signal_date(signal_date)
    if sd is None:
        return None
    ref = today if today is not None else _today_tr()
    if isinstance(ref, datetime):
        ref = ref.date()
    if not isinstance(ref, date):
        return None
    return (ref - sd).days


def is_signal_from_today(signal_date, today=None):
    """Sinyal GERÇEKTEN bugüne mi ait.

    Donmuş `is_new_signal` bayrağı yerine bunu kullan — o bayrak analiz anında
    hesaplanıp donuyor, bayat ticker'da eski günün değerini taşıyor.
    """
    return signal_date_age_days(signal_date, today) == 0


def derive_signal_date_label(signal_date, today=None):
    """Kanonik göreli tarih etiketi.

    bugün -> "Bugün" · dün -> "Dün" · daha eski VEYA gelecek -> gerçek tarih
    ("DD.MM.YYYY"). Tarih ayrıştırılamazsa None döner; çağıran nötr bir şey
    basmalı, "Bugün"e DÜŞMEMELİ.
    """
    age = signal_date_age_days(signal_date, today)
    if age is None:
        return None
    if age == 0:
        return SIGNAL_DATE_LABELS["TODAY"]
    if age == 1:
        return SIGNAL_DATE_LABELS["YESTERDAY"]
    sd = parse_signal_date(signal_date)
    return sd.strftime("%d.%m.%Y")


def derive_signal_date_key(signal_date, today=None):
    """Rozet/renk sınıfı için ayrık anahtar: today / yesterday / older / unknown.

    static/bp-format.js:bpSignalDateKey() ile birebir aynı.
    """
    age = signal_date_age_days(signal_date, today)
    if age is None:
        return "unknown"
    if age == 0:
        return "today"
    if age == 1:
        return "yesterday"
    return "older"
