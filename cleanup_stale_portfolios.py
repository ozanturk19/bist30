#!/usr/bin/env python3
"""KVKK saklama süresi (CPO-1691): portfolios/<uuid>.json bulut-senkron portföy
kayıtları e-posta/kimlik alanı taşımıyor, bu yüzden /unsubscribe ile
ilişkilendirilip silinemiyorlar. Ayrı bir saklama süresi politikası olarak:
12 aydır (updated_at/created_at) güncellenmemiş dosyalar silinir.

Aylık crontab'tan çalıştırılır — cd /root/bist30 && venv/bin/python3
cleanup_stale_portfolios.py >> /var/log/bist30_portfolio_cleanup.log 2>&1
"""
import json
import os
from datetime import datetime, timedelta, timezone

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PF_DIR = os.path.join(_APP_DIR, "portfolios")
_RETENTION_DAYS = 365  # 12 ay


def main():
    if not os.path.isdir(_PF_DIR):
        return
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=_RETENTION_DAYS)
    deleted = 0
    for fname in os.listdir(_PF_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(_PF_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts_raw = data.get("updated_at") or data.get("created_at")
            if ts_raw:
                ts = datetime.fromisoformat(ts_raw)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                ts = ts.astimezone(timezone.utc)
            else:
                # alan yoksa dosya mtime'a düş (bozuk/çok eski kayıt)
                ts = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
            if ts < cutoff:
                os.remove(path)
                deleted += 1
                print(f"{now.isoformat()} SILINDI {fname} (son_kayit={ts_raw or 'yok, mtime kullanildi'})")
        except Exception as e:
            print(f"{now.isoformat()} HATA {fname}: {e}")
    print(f"{now.isoformat()} tamamlandi, taranan_dizin={_PF_DIR}, silinen={deleted}")


if __name__ == "__main__":
    main()
