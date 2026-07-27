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
    """27 Tem 11:05 TR canlı ölçümü: 14 taze(<10dk) + 18 bayat(~65.5sa) + 183 alan-yok."""
    now = time.time()
    stocks = (
        [{"last_fresh_ts": now - 300} for _ in range(14)]
        + [{"last_fresh_ts": now - 65.5 * 3600} for _ in range(18)]
        + [{} for _ in range(183)]
    )
    age_s, eff_ts = _canonical_stocks_age(stocks, now)
    assert age_s > 1800, "medyan/last-write hesabı gibi sessizce taze tarafa düşmemeli"
    # Sentinel epoch=0 gibi anlamsız (1970) bir tarih üretmemeli — 7 gün sınırında kalmalı.
    assert 6 * 86400 < age_s <= 7 * 86400 + 5


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
