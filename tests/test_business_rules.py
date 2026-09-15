"""Faz 12 P1 — business_rules.py test suite (CPO-693)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_rules import (
    validate_change_pct,
    validate_price,
    validate_signal_consistency,
    validate_date_range,
    validate_stocks_list,
    derive_adx_label,
    derive_rsi_zone,
    derive_ema_deadband,
)
from datetime import date


# ── validate_change_pct ──────────────────────────────────────────────────────

def test_normal_change_ok():
    assert validate_change_pct("AKBNK", 2.5)["ok"] is True

def test_negative_change_ok():
    assert validate_change_pct("AKBNK", -3.1)["ok"] is True

def test_zero_change_ok():
    assert validate_change_pct("AKBNK", 0.0)["ok"] is True

def test_glyho_anomal():
    r = validate_change_pct("GLYHO", 28.4)
    assert r["ok"] is False and r["flag"] == "ANOMAL"

def test_selec_anomal():
    r = validate_change_pct("SELEC", -15.2)
    assert r["ok"] is False and r["flag"] == "ANOMAL"

def test_exact_limit_ok():
    assert validate_change_pct("THYAO", 10.5)["ok"] is True

def test_just_over_limit_fail():
    assert validate_change_pct("THYAO", 10.51)["ok"] is False

def test_null_change_pct_fail():
    assert validate_change_pct("TICKER", None)["ok"] is False


# ── validate_price ───────────────────────────────────────────────────────────

def test_valid_price():
    assert validate_price("AKBNK", 45.2)["ok"] is True

def test_zero_price_fail():
    assert validate_price("AKBNK", 0)["ok"] is False

def test_negative_price_fail():
    assert validate_price("AKBNK", -1.5)["ok"] is False

def test_none_price_fail():
    assert validate_price("AKBNK", None)["ok"] is False

def test_small_valid_price():
    assert validate_price("AKBNK", 0.01)["ok"] is True


# ── validate_signal_consistency ──────────────────────────────────────────────

def test_al_with_signal_price_ok():
    assert validate_signal_consistency("THYAO", "AL", 85.5)["ok"] is True

def test_al_without_signal_price_fail():
    r = validate_signal_consistency("THYAO", "AL", None)
    assert r["ok"] is False and r["flag"] == "MISSING_SIGNAL_PRICE"

def test_sat_without_signal_price_fail():
    r = validate_signal_consistency("THYAO", "SAT", None)
    assert r["ok"] is False and r["flag"] == "MISSING_SIGNAL_PRICE"

def test_bekle_without_signal_price_ok():
    assert validate_signal_consistency("THYAO", "BEKLE", None)["ok"] is True

def test_none_signal_ok():
    assert validate_signal_consistency("THYAO", None, None)["ok"] is True


# ── validate_date_range ──────────────────────────────────────────────────────

def test_today_date_ok():
    assert validate_date_range("AKBNK", date.today().isoformat())["ok"] is True

def test_past_date_ok():
    assert validate_date_range("AKBNK", "2026-06-01")["ok"] is True

def test_future_date_fail():
    r = validate_date_range("AKBNK", "2027-01-01")
    assert r["ok"] is False and r["flag"] == "FUTURE_DATE"

def test_none_date_ok():
    assert validate_date_range("AKBNK", None)["ok"] is True

def test_turkish_format_past_date_ok():
    assert validate_date_range("AKBNK", "22.06.2026")["ok"] is True

def test_turkish_format_future_date_fail():
    r = validate_date_range("AKBNK", "01.07.2027")
    assert r["ok"] is False and r["flag"] == "FUTURE_DATE"


# ── validate_stocks_list integration ────────────────────────────────────────

HEALTHY_TICKERS = [
    {"ticker": "AKBNK", "price": 45.2,  "change_pct": 1.5,   "signal": "AL",    "signal_price": 44.0,  "signal_date": "2026-06-23"},
    {"ticker": "THYAO", "price": 85.5,  "change_pct": -0.8,  "signal": "SAT",   "signal_price": 87.0,  "signal_date": "2026-06-20"},
    {"ticker": "SISE",  "price": 32.1,  "change_pct": 2.1,   "signal": "BEKLE", "signal_price": None,  "signal_date": None},
    {"ticker": "KCHOL", "price": 120.0, "change_pct": 0.5,   "signal": "AL",    "signal_price": 119.0, "signal_date": "2026-06-23"},
    {"ticker": "SAHOL", "price": 55.7,  "change_pct": -1.2,  "signal": "BEKLE", "signal_price": None,  "signal_date": None},
]

def test_healthy_tickers_pass():
    result = validate_stocks_list(HEALTHY_TICKERS)
    assert result["errors"] == [], f"Unexpected errors: {result['errors']}"
    assert result["failed_tickers"] == []

def test_glyho_selec_sentinel():
    anomalous = [
        {"ticker": "GLYHO", "price": 85.0, "change_pct": 28.4,  "signal": "AL",  "signal_price": 80.0, "signal_date": "2026-06-23"},
        {"ticker": "SELEC", "price": 45.0, "change_pct": -15.2, "signal": "SAT", "signal_price": None, "signal_date": "2026-06-23"},
    ]
    result = validate_stocks_list(anomalous)
    assert "GLYHO" in result["failed_tickers"]
    assert "SELEC" in result["failed_tickers"]

def test_negative_price_caught():
    bad = [{"ticker": "BADCO", "price": -5.0, "change_pct": 1.0, "signal": "BEKLE", "signal_price": None, "signal_date": None}]
    result = validate_stocks_list(bad)
    assert "BADCO" in result["failed_tickers"]

def test_al_missing_signal_price_caught():
    bad = [{"ticker": "MISSP", "price": 10.0, "change_pct": 2.0, "signal": "AL", "signal_price": None, "signal_date": None}]
    result = validate_stocks_list(bad)
    assert "MISSP" in result["failed_tickers"]


# ── derive_adx_label (CPO-1196 D0 #4 — tek kaynaklı ADX eşiği) ────────────────

def test_adx_label_zayif():
    assert derive_adx_label(17.9) == "Zayıf"

def test_adx_label_orta_lower_bound():
    assert derive_adx_label(18) == "Orta"

def test_adx_label_orta_upper_bound():
    assert derive_adx_label(24.9) == "Orta"

def test_adx_label_guclu_lower_bound():
    assert derive_adx_label(25) == "Güçlü"

def test_adx_label_guclu_upper_bound():
    assert derive_adx_label(39.9) == "Güçlü"

def test_adx_label_cok_guclu():
    assert derive_adx_label(40) == "Çok Güçlü"

def test_adx_label_none_defaults_zayif():
    assert derive_adx_label(None) == "Zayıf"

def test_adx_label_invalid_defaults_zayif():
    assert derive_adx_label("n/a") == "Zayıf"


# ── derive_rsi_zone (CPO-1656 — tek kaynaklı RSI bölge eşiği) ─────────────────
# TUPRS RSI=70.6 örneği: /hisse ve /api/data bunu "Dikkatli" gösterirken
# /karsilastir kendi bağımsız >70 mantığıyla "(Aşırı Alım)" gösteriyordu.
# Aşağıdaki sınır testleri derive_rsi_zone'un kanonik (<70 Dikkatli, >=80
# Aşırı Alım) eşiğini kilitler.

def test_rsi_zone_asiri_satim():
    assert derive_rsi_zone(29.9) == "Aşırı Satım"

def test_rsi_zone_dip_toparlanma_lower_bound():
    assert derive_rsi_zone(30) == "Dip Toparlanması"

def test_rsi_zone_ideal_giris_lower_bound():
    assert derive_rsi_zone(45) == "İdeal Giriş Penceresi"

def test_rsi_zone_trend_guclenior_lower_bound():
    assert derive_rsi_zone(60) == "Trend Güçleniyor"

def test_rsi_zone_dikkatli_lower_bound():
    assert derive_rsi_zone(70) == "Dikkatli"

def test_rsi_zone_dikkatli_upper_bound_tuprs_ornegi():
    assert derive_rsi_zone(70.6) == "Dikkatli"  # karsilastir eskiden "(Aşırı Alım)" derdi

def test_rsi_zone_asiri_alim_lower_bound():
    assert derive_rsi_zone(80) == "Aşırı Alım"

def test_rsi_zone_none_returns_none():
    assert derive_rsi_zone(None) is None

def test_rsi_zone_invalid_returns_none():
    assert derive_rsi_zone("n/a") is None


# ── derive_ema_deadband (CPO-1656 EK YANIT Seçenek B — UI-only rozet) ─────────
# ISCTR canlı örneği (CPO-1656): EMA12=13.4147/EMA99=13.4293, fark %0.109 —
# eşiğin (%0.15) altında, "kararsızlık bölgesi" True olmalı.

def test_ema_deadband_isctr_ornegi_true():
    diff_pct, deadband = derive_ema_deadband(13.4147, 13.4293)
    assert diff_pct == 0.109
    assert deadband is True

def test_ema_deadband_uzak_degerler_false():
    diff_pct, deadband = derive_ema_deadband(121, 104)
    assert deadband is False
    assert diff_pct > 0.15

def test_ema_deadband_esik_altinda_true():
    diff_pct, deadband = derive_ema_deadband(100.10, 100.0)
    assert deadband is True

def test_ema_deadband_esikte_false():
    # tam %0.15 -> strict < kullanılır, eşitlik deadband SAYILMAZ
    diff_pct, deadband = derive_ema_deadband(100.15, 100.0)
    assert diff_pct == 0.15
    assert deadband is False

def test_ema_deadband_none_input():
    diff_pct, deadband = derive_ema_deadband(None, 100)
    assert diff_pct is None
    assert deadband is False

def test_ema_deadband_invalid_input():
    diff_pct, deadband = derive_ema_deadband("n/a", 100)
    assert diff_pct is None
    assert deadband is False

def test_ema_deadband_zero_e99():
    diff_pct, deadband = derive_ema_deadband(10, 0)
    assert diff_pct is None
    assert deadband is False

def test_ema_deadband_does_not_affect_bull_bear_comparison():
    # Sinyal motorunun e12>e99/e12<e99 karşılaştırması bu fonksiyondan
    # BAĞIMSIZ kalmalı — deadband True olsa bile yön karşılaştırması aynı.
    e12, e99 = 13.4147, 13.4293
    _, deadband = derive_ema_deadband(e12, e99)
    assert deadband is True
    assert (e12 > e99) is False  # e12 < e99, yön hâlâ net (sadece fark küçük)


# ── runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_normal_change_ok, test_negative_change_ok, test_zero_change_ok,
        test_glyho_anomal, test_selec_anomal, test_exact_limit_ok,
        test_just_over_limit_fail, test_null_change_pct_fail,
        test_valid_price, test_zero_price_fail, test_negative_price_fail,
        test_none_price_fail, test_small_valid_price,
        test_al_with_signal_price_ok, test_al_without_signal_price_fail,
        test_sat_without_signal_price_fail, test_bekle_without_signal_price_ok,
        test_none_signal_ok,
        test_today_date_ok, test_past_date_ok, test_future_date_fail, test_none_date_ok,
        test_healthy_tickers_pass, test_glyho_selec_sentinel,
        test_negative_price_caught, test_al_missing_signal_price_caught,
        test_adx_label_zayif, test_adx_label_orta_lower_bound, test_adx_label_orta_upper_bound,
        test_adx_label_guclu_lower_bound, test_adx_label_guclu_upper_bound, test_adx_label_cok_guclu,
        test_adx_label_none_defaults_zayif, test_adx_label_invalid_defaults_zayif,
        test_rsi_zone_asiri_satim, test_rsi_zone_dip_toparlanma_lower_bound,
        test_rsi_zone_ideal_giris_lower_bound, test_rsi_zone_trend_guclenior_lower_bound,
        test_rsi_zone_dikkatli_lower_bound, test_rsi_zone_dikkatli_upper_bound_tuprs_ornegi,
        test_rsi_zone_asiri_alim_lower_bound, test_rsi_zone_none_returns_none,
        test_rsi_zone_invalid_returns_none,
        test_ema_deadband_isctr_ornegi_true, test_ema_deadband_uzak_degerler_false,
        test_ema_deadband_esik_altinda_true, test_ema_deadband_esikte_false,
        test_ema_deadband_none_input, test_ema_deadband_invalid_input,
        test_ema_deadband_zero_e99, test_ema_deadband_does_not_affect_bull_bear_comparison,
    ]
    passed = failed_list = 0
    fail_names = []
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✓ {t.__name__}")
        except AssertionError as e:
            fail_names.append(t.__name__)
            print(f"  ✗ {t.__name__}: {e}")
    print(f"\n{'='*55}")
    print(f"Result: {passed}/{len(tests)} passed")
    if fail_names:
        print(f"FAILED: {', '.join(fail_names)}")
        raise SystemExit(1)
    print("ALL TESTS PASSED ✅")
