"""DEV-1034/CPO-1020 — stale-fallback tier carry-over fix.

Root cause (Pzt 06.07 + tekrar Sal 07.07): _refresh_data_impl() prev_cache
fallback `dict(_ps)` blind-copy yapıyordu — signal_strength >= 75 olan bir
ticker yfinance'tan veri alamayıp stale fallback'e düşerse, tier alanı asla
yeniden hesaplanmıyordu (eski tier_score bazlı veya önceki döngüden kalma
değerde sonsuza kadar donuyordu). fd62ef4 (analyze() tier migrasyonu) canlı
kodda doğru çalışıyordu — bug bu ikinci, kopyalanan yolda gizliydi.

Fix: tier banı `_derive_tier()` adlı tek bir yardımcıya taşındı, hem
analyze() hem stale-fallback bloğu aynı fonksiyonu çağırıyor — artık
carried-over signal_strength'ten tier yeniden türetiliyor, iki kopya
mantık birbirinden sapamaz.

Bu testler kod tabanını statik olarak inceler (regex) ve `_derive_tier`
fonksiyonunu izole exec ile davranış olarak doğrular — sunucu/3.10+ import
gerektirmez (feedback_local_mac_no_python310).
"""
import os
import re

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _extract_function_body(src, func_name):
    pattern = rf"def {func_name}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


def _load_derive_tier():
    src = _read_app()
    body = _extract_function_body(src, "_derive_tier")
    assert body, "_derive_tier() bulunamadı"
    ns = {}
    exec(body, ns)
    return ns["_derive_tier"]


def test_analyze_uses_derive_tier_helper():
    src = _read_app()
    body = _extract_function_body(src, "analyze")
    assert body, "analyze() bulunamadı"
    assert "_derive_tier(signal, signal_strength, low_liquidity, earnings_warning)" in body, (
        "analyze() tier atamasını _derive_tier() üzerinden yapmalı — bant mantığı "
        "iki yerde tekrarlanırsa (DEV-1034) birbirinden sapabilir"
    )


def test_stale_fallback_rederives_tier():
    src = _read_app()
    body = _extract_function_body(src, "_refresh_data_impl")
    assert body, "_refresh_data_impl() bulunamadı"
    assert '_fallback["tier"] = _derive_tier(' in body, (
        "stale fallback bloğu tier'ı _derive_tier() ile yeniden hesaplamalı — "
        "aksi halde signal_strength >= 75 olan stale ticker sonsuza kadar eski "
        "tier'da donar (DEV-1034/CPO-1020 kök nedeni)"
    )
    fallback_idx = body.index('_fallback = dict(_ps)')
    tier_fix_idx = body.index('_fallback["tier"] = _derive_tier(')
    append_idx = body.index("results.append(_fallback)")
    assert fallback_idx < tier_fix_idx < append_idx, (
        "tier yeniden hesaplama dict(_ps) kopyasından SONRA, results.append'ten "
        "ÖNCE olmalı — sırasız olursa eski tier append edilir"
    )


def test_derive_tier_bands_match_compose_score_thresholds():
    derive_tier = _load_derive_tier()
    assert derive_tier("AL", 75, False, False) == "premium"
    assert derive_tier("AL", 60, False, False) == "plus"
    assert derive_tier("AL", 40, False, False) == "standart"
    assert derive_tier("AL", 39, False, False) is None
    assert derive_tier("BEKLE", 90, False, False) is None


def test_derive_tier_demote_on_risk_flags():
    derive_tier = _load_derive_tier()
    # tek risk bayrağı: bir kademe düşür
    assert derive_tier("AL", 78, True, False) == "plus"
    assert derive_tier("AL", 78, False, True) == "plus"
    # iki risk bayrağı: iki kademe düşür
    assert derive_tier("AL", 78, True, True) == "standart"
    # standart'tan iki kademe düşerse tier kaybolur (None), hata fırlatmaz
    assert derive_tier("AL", 45, True, True) is None


def test_derive_tier_handles_falsy_signal_strength_without_crash():
    derive_tier = _load_derive_tier()
    assert derive_tier("AL", 0, False, False) is None
    assert derive_tier(None, 0, False, False) is None
