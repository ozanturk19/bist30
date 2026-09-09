#!/usr/bin/env python3
"""bist30-macro-worker — CPO-1569

Makro verinin (SP500/NASDAQ/BTC/ALTIN/GUMUS/PETROL/USDTRY/EURTRY dahil 10
kalem) 7/24 tazeliğini sağlar. refresh_worker.py'nin aksine
background_refresh()'i (215 hisse EOD taraması + XU030/XU100 chart fetch +
stale-watchdog) HİÇ ÇAĞIRMAZ — sadece app.py import edildiğinde otomatik
başlayan _macro_bg_loop thread'ini (module-level, app.py satır ~4789)
canlı tutar.

_is_macro_leader() fcntl.flock'unu (_MACRO_LOCK_PATH) bist30-refresh.service
ile AYNEN PAYLAŞIR — kilit semantiği değişmedi, sadece ikinci bir tüketici.
BIST-yoğun saatlerde (10:00-19:00 TR, hafta içi — bist30-refresh.service'in
crontab penceresi) iki proses aynı kilide yarışır, kazanan bugünküyle aynı
180s cadence'te fetch eder. Pencere dışında (gece + hafta sonu)
bist30-refresh.service kapalı olduğu için bu proses tek başına kilidi alır
ve 600s cadence'te fetch etmeye devam eder (önceden: 15-63 saat donuk).
"""
import os
import sys
import logging
import time

os.environ.setdefault("REFRESH_WORKER", "1")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("macro-worker")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger.info("macro_worker.py: app.py import ediliyor (_macro_bg_loop otomatik başlar)...")
import app  # noqa: E402 — tüm init çalışır (cache, lock, _macro_bg_loop thread module-level start() edilir)

logger.info("macro_worker.py: background_refresh() ÇAĞRILMIYOR (kasıtlı) — sadece _macro_bg_loop canlı tutuluyor")
while True:
    time.sleep(3600)
