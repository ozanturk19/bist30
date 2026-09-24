#!/usr/bin/env python3
"""D-04: resmi kapanış kesinleştirmesini elle çalıştırır (deploy gecesi tek seferlik).

Kullanım (VPS, refresh servisi kapalıyken): venv/bin/python3 tools/official_close_run.py [YYYY-MM-DD] [--notify]
Tarih verilmezse bugün (TR). Sinyal maili varsayılan KAPALI. Bülten yoksa/kapı geçilemezse çıkış kodu 1.
"""
import os
import sys
from datetime import date

os.environ["REFRESH_WORKER"] = "web"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app  # noqa: E402


def main(argv):
    notify = "--notify" in argv
    args = [a for a in argv if not a.startswith("--")]
    day = date.fromisoformat(args[0]) if args else app.datetime.now(app._TZ_TR).date()
    app._load_cache_from_disk()
    ok = app._run_official_close_pass(day, notify=notify)
    print("tamam" if ok else "bülten yok / kapı geçilemedi")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
