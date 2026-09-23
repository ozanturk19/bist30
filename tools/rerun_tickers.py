#!/usr/bin/env python3
"""Tek seferlik: verilen tickerlar için analyze() → cache + disk (D-P0-2309c EOD yeniden çalıştırma).

Kullanım (VPS, refresh servisi kapalıyken): venv/bin/python3 tools/rerun_tickers.py [--notify] T1 T2 ...
Sinyal maili varsayılan KAPALI (geçmiş günün değişimi yeniden mail atmasın).
REFRESH_WORKER=web: import lider/refresh döngüsü başlatmaz, yalnız disk-reload.
"""
import os
import sys

os.environ["REFRESH_WORKER"] = "web"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app  # noqa: E402


def main(argv):
    notify = "--notify" in argv
    tickers = [a.upper() for a in argv if not a.startswith("--")]
    app._load_cache_from_disk()
    with app._lock:
        before = {s["ticker"]: s for s in (app._cache.get("data") or [])}
    print(f"cache: {len(before)} hisse")
    rescued = []
    for t in tickers:
        r = app.analyze(t)
        if not r:
            print(f"{t}: analyze None — {app._ANALYZE_FAIL_REASON.get(t)}")
            continue
        app._enrich_stock(r)
        r["last_fresh_ts"] = app.time.time()
        b = before.get(t, {})
        print(f"{t}: {b.get('price')} ({b.get('change_pct')}%, {b.get('signal')}) -> "
              f"{r.get('price')} ({r.get('change_pct')}%, {r.get('signal')})")
        rescued.append(r)
    app._merge_rescued_into_cache(rescued, notify=notify)
    print(f"yazıldı: {len(rescued)}/{len(tickers)}")


if __name__ == "__main__":
    main(sys.argv[1:])
