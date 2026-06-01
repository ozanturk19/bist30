#!/usr/bin/env python3
"""
fetcher-v3.py — BorsaPusula Phase-3 fetcher daemon (PER-TICKER cache).

SPEC-DECOUPLING-v2-PHASE3.md uyumlu:
- Per-ticker disk cache: data-staging/charts/chart_<TICKER>.json × 215
- 31MB monolit YASAK (Phase-2 v2'yi öldüren reparse contention budur)
- Kademeli fetch (ticker-ticker + sleep, bulk-burst yok)
- Nice=19 + IOSchedulingClass=idle (2-core'da prod'u açlıktan koru)
- Worker yfinance çağırmaz, sadece disk-read

Cycle:
  1. Heavy (900s): per-ticker chart × 215 + refresh_data + 10 makro chart + warm
  2. Live (30s): BIST live prices (kademeli)
  3. Global (60s): kripto/emtia/US prices
  4. Macro (5dk): _fetch_macro

Çıktı dizinleri (staging):
  /root/bist30-staging/data-staging/charts/chart_<T>.json
  /root/bist30-staging/data-staging/last_cache.json
  /root/bist30-staging/data-staging/live_prices_cache.json
  /root/bist30-staging/data-staging/chart_macros.json
"""

import os
import sys
import time
import signal
import logging
import traceback
import json
import tempfile

# Fetcher rolü: app.py module-level _startup thread'ini başlatma → temiz import
os.environ["BIST_ROLE"] = "fetcher"

# Repo path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Staging cache dizinleri
CACHE_DIR = os.path.join(BASE_DIR, "data-staging")
CHARTS_DIR = os.path.join(CACHE_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] fetcher-v3: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fetcher-v3")

_running = True
def _handle_term(signum, frame):
    global _running
    logger.info("SIGTERM/SIGINT — graceful shutdown")
    _running = False
signal.signal(signal.SIGTERM, _handle_term)
signal.signal(signal.SIGINT, _handle_term)

logger.info("fetcher-v3.py başlatılıyor — app module import...")
import app  # noqa: E402
logger.info("app module yüklendi. CACHE_DIR=%s CHARTS_DIR=%s", CACHE_DIR, CHARTS_DIR)


def _atomic_write_json(path, data):
    """POSIX-atomic write via tempfile + os.replace."""
    dir_ = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _save_per_ticker_chart(ticker, chart_data):
    """Per-ticker chart cache yaz — chart_<T>.json (KÜÇÜK dosya, mtime-guard friendly)."""
    if not chart_data:
        return False
    path = os.path.join(CHARTS_DIR, f"chart_{ticker}.json")
    try:
        _atomic_write_json(path, chart_data)
        return True
    except Exception as e:
        logger.warning("save chart_%s: %s", ticker, e)
        return False


def _safe(label, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.error("FAIL [%s]: %s", label, e)
        return None


LIVE_INTERVAL = 30
GLOBAL_INTERVAL = 60
MACRO_INTERVAL = 300
HEAVY_INTERVAL = 900

_last_live = 0
_last_global = 0
_last_macro = 0
_last_heavy = 0
_cycle = 0


def _heavy_cycle():
    """Per-ticker chart × 215 + refresh_data + makro + warm (KADEMELI, ticker-ticker)."""
    logger.info("=== HEAVY CYCLE başladı (per-ticker chart × %d) ===", len(app.BIST100))
    t0 = time.time()

    # 1. BIST sinyal (refresh_data zaten atomik disk yazar)
    _safe("refresh_data", app.refresh_data)

    # 2. Per-ticker chart × 215 (KADEMELI, ticker-ticker + 0.05s sleep)
    chart_ok = 0
    chart_fail = 0
    for ticker in app.BIST100:
        if not _running:
            break
        try:
            data = app._compute_chart_data(ticker, "2y")
            if data and _save_per_ticker_chart(ticker, data):
                chart_ok += 1
            else:
                chart_fail += 1
            time.sleep(0.05)
        except Exception as e:
            chart_fail += 1
            logger.debug("chart_%s: %s", ticker, e)
    logger.info("Per-ticker chart: ok=%d fail=%d", chart_ok, chart_fail)

    # 3. Makro chart × 10 (XU100 + 10 makro varlık)
    _safe("refresh_chart", app.refresh_chart)
    _safe("refresh_xu100_chart", app.refresh_xu100_chart)
    macros = [
        ("BTC", app._btc_chart_cache), ("ETH", app._eth_chart_cache),
        ("SOL", app._sol_chart_cache), ("BNB", app._bnb_chart_cache),
        ("ALTIN", app._altin_chart_cache), ("GUMUS", app._gumus_chart_cache),
        ("PETROL", app._petrol_chart_cache), ("DOGALGAZ", app._dogalgaz_chart_cache),
        ("SP500", app._sp500_chart_cache), ("NASDAQ", app._nasdaq_chart_cache),
    ]
    macro_dict = {}
    for key, cache in macros:
        _safe(f"refresh_varlik_{key}", app._refresh_varlik_chart, key, cache)
        if cache.get("data"):
            macro_dict[key] = cache
    if macro_dict:
        _atomic_write_json(os.path.join(CACHE_DIR, "chart_macros.json"), macro_dict)

    # 4. Fundamentals warm (5 ticker)
    fund_tickers = ["THYAO", "AKBNK", "GARAN", "ASELS", "EREGL"]
    for t in fund_tickers:
        if not _running:
            break
        _safe(f"fundamentals_{t}", app._get_fundamentals, t)
        time.sleep(0.2)
    if app._fundamentals_cache:
        _atomic_write_json(os.path.join(CACHE_DIR, "fundamentals_cache.json"),
                           app._fundamentals_cache)

    logger.info("=== HEAVY CYCLE tamamlandı (%.1fs) ===", time.time() - t0)


def _live_cycle():
    """BIST live prices — kademeli (P1 fallback ile bulk dene + per-ticker fallback)."""
    _safe("fetch_live_prices", app.fetch_live_prices)
    if app._live_prices:
        try:
            with app._lock:
                _atomic_write_json(os.path.join(CACHE_DIR, "live_prices_cache.json"),
                                   dict(app._live_prices))
        except Exception as e:
            logger.debug("live_prices disk: %s", e)


def _global_cycle():
    """Global kripto/emtia/US prices."""
    _safe("fetch_global_prices", app.fetch_global_prices)
    if app._live_prices:
        try:
            with app._lock:
                _atomic_write_json(os.path.join(CACHE_DIR, "live_prices_cache.json"),
                                   dict(app._live_prices))
        except Exception:
            pass


def _macro_cycle():
    """Makro göstergeler."""
    _safe("fetch_macro", app._fetch_macro)


# İlk açılış: heavy cycle (cache pre-populate)
logger.info("İlk açılış: heavy cycle başlıyor (215 ticker × per-ticker chart)...")
_heavy_cycle()
_last_heavy = time.time()
logger.info("İlk açılış tamam. Sürekli döngüye geçiliyor.")


while _running:
    now = time.time()
    try:
        if now - _last_live >= LIVE_INTERVAL:
            _live_cycle()
            _last_live = now
        if now - _last_global >= GLOBAL_INTERVAL:
            _global_cycle()
            _last_global = now
        if now - _last_macro >= MACRO_INTERVAL:
            _macro_cycle()
            _last_macro = now
        if now - _last_heavy >= HEAVY_INTERVAL:
            _heavy_cycle()
            _last_heavy = now
        _cycle += 1
        if _cycle % 60 == 0:
            logger.info("Heartbeat: %d cycle, son heavy=%ds önce", _cycle, int(now - _last_heavy))
    except Exception as e:
        logger.error("Main loop: %s\n%s", e, traceback.format_exc())
    time.sleep(5)

logger.info("fetcher-v3.py exit (graceful)")
