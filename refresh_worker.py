#!/usr/bin/env python3
"""bist30-refresh-worker — CPO-551 Aşama 4

Yfinance ağır iş + chart refresh'leri web process'ten ayırır.
bist30-refresh.service bu scripti çalıştırır (REFRESH_WORKER=1 env ile).
bist30.service (web) REFRESH_WORKER=web → sadece disk-reload.
"""
import os
import sys
import logging

os.environ.setdefault("REFRESH_WORKER", "1")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("refresh-worker")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger.info("refresh_worker.py: app.py import ediliyor...")
import app  # noqa: E402 — tüm init çalışır (cache, lock, thread'ler)

logger.info("refresh_worker.py: background_refresh() başlatılıyor (REFRESH_WORKER=1)")
app.background_refresh()
