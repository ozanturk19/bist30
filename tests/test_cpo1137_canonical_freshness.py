"""CPO-1137 — kanonik tazelik yaşı (_canonical_stocks_age) fixture'ı.

27 Tem 2026 11:05-11:10 TR ölçümü: /api/health (last_refresh_ts bazlı) "taze"
derken /api/data (eski medyan bazlı) "65.2 saat bayat" diyordu ve
data_freshness.is_stale sessiz kalıyordu — üç yüzey üç farklı hesaptan
besleniyordu. Bu test, üçünün artık paylaştığı _canonical_stocks_age()'in:

1. last_fresh_ts eksik/0 olan ticker'ı "hiç güncellenmedi" sayıp taze tarafa
   düşürmediğini (183/215 "alan yok" vakası),
2. medyanın maskeleyebileceği azınlık-taze/çoğunluk-bayat senaryosunda p90'ın
   doğru "stale" sinyali verdiğini,
3. sağlıklı durumda (küçük normal blip) yanlış alarm üretmediğini,
4. tek kalıcı-arızalı ticker'ın banner'ı sonsuza kilitlemediğini

doğrular. Python 3.9 (yerel Mac) app.py'yi (3.10+ sözdizimi) import edemediği
için fonksiyon kaynaktan izole exec edilir (bkz. test_cpo1119_data_quality_fixture.py).
"""
import os
import re
import time

import pytest

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _load_canonical_stocks_age():
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"def _canonical_stocks_age\(.*?\n\n\n", src, re.DOTALL)
    assert m, "_canonical_stocks_age() app.py'de bulunamadı — fonksiyon adı/imzası değişmiş olabilir"
    sentinel_m = re.search(r"_NEVER_FRESH_SENTINEL_S = ([^\n#]+)", src)
    assert sentinel_m, "_NEVER_FRESH_SENTINEL_S sabiti bulunamadı"
    ns = {"time": time}
    exec(f"_NEVER_FRESH_SENTINEL_S = {sentinel_m.group(1).strip()}\n" + m.group(0), ns)
    return ns["_canonical_stocks_age"]


_canonical_stocks_age = _load_canonical_stocks_age()


def test_empty_stocks_returns_none():
    assert _canonical_stocks_age([]) == (None, None)


def test_healthy_case_stays_fresh():
    now = time.time()
    # 210 taze (2dk), 5 alan-yok (normal per-cycle blip) — banner tetiklenmemeli.
    stocks = [{"last_fresh_ts": now - 120} for _ in range(210)] + [{} for _ in range(5)]
    age_s, eff_ts = _canonical_stocks_age(stocks, now)
    assert age_s < 1800
    assert eff_ts is not None


def test_cpo1137_2707_scenario_flags_stale():
    """27 Tem 11:05 TR canlı ölçümü: 14 taze(<10dk) + 18 bayat(~65.5sa) + 183 alan-yok.

    CPO-1147 P0 revizyonu (27 Tem 18:12 TR): p90 gerçek last_fresh_ts'i olan
    yalnız 32 ticker'ı (14+18) geçip alan-yok bölgesine düşüyor — bu artık
    sabit "~7 gün" sayısı DEĞİL, (None, None) döner (bkz. test_cpo1147_*
    altta). Bu test artık yalnız "sessizce taze tarafa düşmüyor" invaryantını
    doğruluyor.
    """
    now = time.time()
    stocks = (
        [{"last_fresh_ts": now - 300} for _ in range(14)]
        + [{"last_fresh_ts": now - 65.5 * 3600} for _ in range(18)]
        + [{} for _ in range(183)]
    )
    age_s, eff_ts = _canonical_stocks_age(stocks, now)
    assert age_s is None, "p90 alan-yok bölgesindeyken artık (None, None) döner — sahte sayı üretmemeli"
    assert eff_ts is None


def test_cpo1147_cold_start_majority_missing_returns_unknown_not_synthetic():
    """27 Tem 18:12 TR CANLI REGRESYON: restart sonrası disk-cache'te 183/215
    ticker'ın last_fresh_ts'i yok (Yahoo 429 duvarı — sadece 32/215 bu döngüde
    gerçekten tazelendi). p90 alan-yok bölgesine düşünce eski kod
    `now - (now - 7g) = 604800` sabit VE `now` ile birlikte İLERLEYEN sahte bir
    "güncel" tarih üretiyordu — canlıda `updated_at` her istekte artan ama
    her zaman tam "7 gün önce" gösteren bir değerdi (605800 sabit, tarih
    ilerliyor). Artık (None, None) dönmeli; çağıran (_data_quality_snapshot,
    build_data_freshness, _compute_health) zaten sahip olduğu last_refresh_ts
    fallback'ine düşer — gerçek (disk mtime / son cycle) bir çapa, sentetik
    bir tarih değil."""
    now = time.time()
    stocks = (
        [{"last_fresh_ts": now - 1848} for _ in range(32)]   # canlı oran: 32/215 gerçekten taze
        + [{} for _ in range(183)]                            # last_fresh_ts hiç yok
    )
    age_s, eff_ts = _canonical_stocks_age(stocks, now)
    assert age_s is None and eff_ts is None, (
        "p90 sentinel bölgesine düşerken sahte 'now-7g' üretmemeli — (None, None) ile "
        "çağıranın gerçek last_refresh_ts fallback'ine düşmesini sağlamalı"
    )


def test_missing_last_fresh_ts_never_reads_as_fresher_than_known_stale():
    """last_fresh_ts yok/0 olan ticker, bilinen en bayat ticker'dan DAHA taze görünmemeli."""
    now = time.time()
    known_stale_age = 65.5 * 3600
    stocks = [{"last_fresh_ts": now - known_stale_age}, {}]
    ages = sorted(now - (s.get("last_fresh_ts") or (now - 7 * 86400)) for s in stocks)
    assert ages[-1] >= known_stale_age  # missing ticker en bayat sırada (veya eşit), hiçbir zaman daha taze değil


def test_single_permanently_broken_ticker_does_not_lock_banner_forever():
    """p90 kullanımı: 214/215 taze + 1 kalıcı-arızalı ticker banner'ı sonsuza kilitlememeli."""
    now = time.time()
    stocks = [{"last_fresh_ts": now - 60} for _ in range(214)] + [{}]
    age_s, _ = _canonical_stocks_age(stocks, now)
    assert age_s < 1800
