#!/usr/bin/env python3
"""CPO-1158/1159/DEV-1506 — gevent+threading.Lock+flock deadlock finder.

Kullanım: bu script'i VPS'te (gerçek gevent ortamında) çalıştır, `EXTRACTED_BLOCK_PATH`
altında test edilecek "modül-seviyesi state + read/update fonksiyonları" bloğunu ver.

    python3 -c "import re; src=open('app.py').read(); \
        m=re.search(r'_GEMINI_QUOTA_CB_PATH = .*?(?=\\ndef _gemini_call\\()', src, re.DOTALL); \
        open('/tmp/block.py','w').write(m.group(0))"
    scp /tmp/block.py root@VPS:/tmp/block.py
    scp tools/stress_test_gevent_shared_lock.py root@VPS:/tmp/
    ssh root@VPS "/root/bist30/venv/bin/python3 /tmp/stress_test_gevent_shared_lock.py /tmp/block.py"

Neden var: 28 Tem 2026, CPO-1158'in istediği §3.2 (cross-worker paylaşımlı Gemini kota
circuit breaker state'i, rate-limiter'ın threading.Lock+flock deseniyle) VPS'in gerçek
gevent ortamında STRES TESTİNDE tekrarlanabilir bir DEADLOCK'a girdi — 10 gerçek OS
thread'i (gevent hub threadpool, maxsize=10) AYNI `threading.Lock()`'a aynı anda
çarpınca ilerleme tamamen duruyordu (`.get(timeout=X)` olmadan test edilince görünür
oldu; timeout'lu testler yalnız "hepsi zaman aşımına uğradı" gösteriyordu, gerçek
deadlock'u `progress` sayacıyla adım adım izlemek gerekti). Kod deploy edilmeden
geri alındı (DEV-1506). CPO-1159 iki şart koydu: (a) poison test dosyasını sil,
(b) bu stres testini regresyon olarak sakla — bu script o saklama işidir.

Herhangi bir GELECEKTEKİ "threading.Lock() + flock() ile paylaşımlı state" tasarımı
(§3.2'nin LOCK_NB revizyonu dahil) DEPLOY EDİLMEDEN ÖNCE bu script ile (veya
eşdeğeriyle) VPS'in gerçek gevent ortamında test edilmeli. Yalnızca `pytest tests/`
suite'ine YAZILMADI çünkü: gevent hub + gerçek threadpool + saniyeler süren
eşzamanlı yük gerektiriyor — hızlı/deterministik/yerel local suite'in kapsamı dışında.
"""
import sys
import time
import threading
import fcntl as _fcntl
import os
import json
import logging
import tempfile

import gevent
from gevent import monkey
monkey.patch_all()

logger = logging.getLogger()


def run(block_path, n_workers=10, n_per_worker=30, per_call_timeout=None):
    """block_path: modül-seviyesi state + fonksiyonları içeren çıkarılmış kod bloğu.
    Blok, en az şu adı sağlamalı: bir `update`-benzeri fonksiyon (mutate alan bir
    callable kabul edip state'i atomic günceller) VE bir `read` fonksiyonu.
    Bu script generik olarak `_gemini_quota_cb_update`/`_gemini_quota_cb_read` adlarını
    arar — farklı bir state için kullanılacaksa bu isimleri güncelle.
    """
    path = tempfile.mktemp()
    ns = {
        "_fcntl": _fcntl, "time": time, "os": os, "json": json,
        "threading": threading, "logger": logger,
        "_GEMINI_QUOTA_CB_PATH": path,  # blok kendi os.environ fallback'ini kullanırsa üzerine yazılabilir — bkz. NOT
        "_GEMINI_QUOTA_CB_THRESHOLD": 10,
        "_GEMINI_QUOTA_CB_COOLDOWN": 3600,
    }
    with open(block_path) as f:
        code = f.read()
    exec(code, ns)  # noqa: S102 — kasıtlı, izole VPS test scripti

    update_fn = ns.get("_gemini_quota_cb_update")
    read_fn = ns.get("_gemini_quota_cb_read")
    if not update_fn or not read_fn:
        print("FAIL: blok _gemini_quota_cb_update/_gemini_quota_cb_read sağlamıyor")
        sys.exit(2)

    def mutate(state):
        state["consecutive_429"] = state.get("consecutive_429", 0) + 1

    hub = gevent.get_hub()
    total = n_workers * n_per_worker
    progress = [0]
    progress_lock = threading.Lock()

    def worker(n):
        for _ in range(n):
            g = hub.threadpool.spawn(update_fn, mutate)
            g.get(timeout=per_call_timeout) if per_call_timeout else g.get()
            with progress_lock:
                progress[0] += 1

    start = time.time()
    greenlets = [gevent.spawn(worker, n_per_worker) for _ in range(n_workers)]
    gevent.joinall(greenlets, timeout=120)
    elapsed = time.time() - start

    stuck = [g for g in greenlets if not g.ready()]
    final = read_fn()
    print(f"attempted={total} completed={progress[0]} elapsed={elapsed:.1f}s stuck_greenlets={len(stuck)}")
    print(f"final_state={final}")

    if stuck or progress[0] < total:
        print("DEADLOCK/STALL DETECTED — bu tasarım güvenli değil, deploy ETME")
        sys.exit(1)
    if final.get("consecutive_429") != total:
        print(f"LOST UPDATES — beklenen {total}, gerçek {final.get('consecutive_429')}")
        sys.exit(1)
    print("PASS — deadlock/lost-update yok")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("kullanım: stress_test_gevent_shared_lock.py <block.py> [n_workers] [n_per_worker]")
        sys.exit(2)
    n_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    n_per_worker = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    run(sys.argv[1], n_workers=n_workers, n_per_worker=n_per_worker)
