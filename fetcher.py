#!/usr/bin/env python3
"""
fetcher.py — BorsaPusula yfinance fetcher daemon (SPEC-DECOUPLING-v2, CPO-420/421).

Mimari: gunicorn worker'larından TAMAMEN ayrı bir process. TÜM yfinance + ağır
fetch işini bu process yapar, sonuçları disk cache'lere atomik yazar. gunicorn
worker'lar sadece disk cache'leri mtime-guard ile okur (yfinance çağrısı YOK).

Phase-1 (commit 32068a4) revert nedeni: tek gunicorn worker'a tüm yfinance
yığma → gevent hub bloke → /hisse %50 timeout. Bu daemon ile gunicorn'daki
fetch yükü SIFIR.

Çağrı sırası:
  1. Hızlı yenilenenler: live_prices (30s), global_prices (60s)
  2. Ana sinyal döngüsü (900s): refresh_data (BIST + sinyal)
  3. Chart döngüsü (900s, sinyal sonrası): refresh_chart + 10 makro + warm
  4. Tüm disk cache'ler her cycle sonunda atomik yazılır

systemd: /etc/systemd/system/bist30-fetcher.service (Restart=always)
Log: /var/log/bist30-fetcher.log + stderr

Kullanım:
  $ BIST_ROLE=fetcher /root/bist30/venv/bin/python /root/bist30/fetcher.py
  $ systemctl start bist30-fetcher
"""

import os
import sys
import time
import signal
import logging
import traceback

# Fetcher rolü: app.py module-level _startup thread'ini başlatma → temiz import
os.environ["BIST_ROLE"] = "fetcher"

# Repo path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Logging — systemd journald + stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] fetcher: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fetcher")

# Sigterm graceful shutdown
_running = True
def _handle_term(signum, frame):
    global _running
    logger.info("SIGTERM/SIGINT — graceful shutdown başlıyor")
    _running = False
signal.signal(signal.SIGTERM, _handle_term)
signal.signal(signal.SIGINT, _handle_term)

logger.info("fetcher.py başlatılıyor — app module import...")

# app.py'yi import et — BIST_ROLE=fetcher olduğu için _startup thread atlanır
import app  # noqa: E402

logger.info("app module yüklendi. Cache'ler:")
logger.info("  CHART_XU100=%s",  app._CHART_XU100_DISK_PATH)
logger.info("  CHART_MACROS=%s", app._CHART_MACROS_DISK_PATH)
logger.info("  CHART_STOCKS=%s", app._CHART_STOCKS_DISK_PATH)
logger.info("  LIVE_PRICES=%s",  app._LIVE_PRICES_DISK_PATH)
logger.info("  FUNDAMENTALS=%s", app._FUNDAMENTALS_DISK_PATH)
logger.info("  LAST_CACHE=%s",   app._DISK_CACHE_PATH)

# Disk'ten önceki cache'leri yükle — yfinance fail olsa bile cache korunur
try:
    app._load_cache_from_disk()
    app._load_all_fetcher_caches()
    logger.info("Önceki cache'ler diskten yüklendi.")
except Exception as e:
    logger.warning("Cache pre-load: %s", e)


# Cycle interval (saniye)
LIVE_INTERVAL   = 30   # background_live_prices
GLOBAL_INTERVAL = 60   # background_global_prices
HEAVY_INTERVAL  = 900  # refresh_data + chart + warm (15dk)
MACRO_INTERVAL  = 300  # _fetch_macro (5dk)

_last_live   = 0
_last_global = 0
_last_heavy  = 0
_last_macro  = 0
_cycle = 0


def _safe(label, fn, *args, **kwargs):
    """Helper: try/except wrapper, fetcher cycle dursun."""
    try:
        fn(*args, **kwargs)
        return True
    except Exception as e:
        logger.error("FAIL [%s]: %s\n%s", label, e, traceback.format_exc())
        return False


def _heavy_cycle():
    """900s'de bir: BIST sinyal + tüm chart cache refresh + warm-up + disk save."""
    logger.info("=== HEAVY CYCLE başlıyor (refresh_data + chart + warm) ===")
    t0 = time.time()
    # 1. BIST sinyal (refresh_data zaten _save_cache_to_disk + _save_daily_snapshot çağırır)
    _safe("refresh_data", app.refresh_data)
    # 2. Chart cache'ler
    _safe("refresh_chart",       app.refresh_chart)
    _safe("refresh_xu100_chart", app.refresh_xu100_chart)
    macros = [
        ("BTC", app._btc_chart_cache),     ("ETH", app._eth_chart_cache),
        ("SOL", app._sol_chart_cache),     ("BNB", app._bnb_chart_cache),
        ("ALTIN", app._altin_chart_cache), ("GUMUS", app._gumus_chart_cache),
        ("PETROL", app._petrol_chart_cache),("DOGALGAZ", app._dogalgaz_chart_cache),
        ("SP500", app._sp500_chart_cache), ("NASDAQ", app._nasdaq_chart_cache),
    ]
    for key, cache in macros:
        _safe(f"refresh_varlik_{key}", app._refresh_varlik_chart, key, cache)
    # 3. Stock chart warm-up — en çok ziyaret edilen 5 ticker
    warm_tickers = ["THYAO", "AKBNK", "GARAN", "ASELS", "EREGL"]
    for t in warm_tickers:
        _safe(f"chart_warm_{t}", app._compute_chart_data, t, "2y")
    # 4. Fundamentals warm-up
    for t in warm_tickers[:3]:
        _safe(f"fundamentals_warm_{t}", app._get_fundamentals, t)
    # 5. TÜM cache'leri diske yaz (chart + live_prices + fundamentals)
    _safe("save_all_fetcher_caches", app._save_all_fetcher_caches)
    logger.info("=== HEAVY CYCLE tamamlandı (%.1fs) ===", time.time() - t0)


def _live_cycle():
    """30s'de bir: BIST live prices + disk save."""
    if _safe("fetch_live_prices", app.fetch_live_prices):
        # Sadece live_prices'i yaz (heavy cycle dışında chart cache değişmedi)
        _safe("save_live_prices", app._atomic_write_json,
              app._LIVE_PRICES_DISK_PATH, dict(app._live_prices))


def _global_cycle():
    """60s'de bir: kripto+emtia+US hisseleri live prices + disk save."""
    if _safe("fetch_global_prices", app.fetch_global_prices):
        _safe("save_global_prices", app._atomic_write_json,
              app._LIVE_PRICES_DISK_PATH, dict(app._live_prices))


def _macro_cycle():
    """5dk'da bir: makro ekonomik göstergeler."""
    _safe("fetch_macro", app._fetch_macro)
    # _fetch_macro zaten _save_macro_to_disk çağırır (mevcut)


# İlk açılışta hızlı bir heavy cycle (cache'leri pre-populate)
logger.info("İlk açılış: heavy cycle (cache pre-populate)...")
_heavy_cycle()
_last_heavy = time.time()
logger.info("İlk açılış tamamlandı. Sürekli döngüye geçiliyor (live=30s, global=60s, macro=5dk, heavy=15dk).")


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
            logger.info("Heartbeat: %d cycle, son heavy=%ds önce, son live=%ds önce",
                        _cycle, int(now - _last_heavy), int(now - _last_live))
    except Exception as e:
        logger.error("Main loop exception: %s\n%s", e, traceback.format_exc())
    # Kısa sleep — döngü hassasiyeti 5s
    time.sleep(5)

logger.info("fetcher.py exit (graceful)")
