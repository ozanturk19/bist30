#!/bin/bash
# tools/restart-bist30-refresh-conditional.sh
# CPO-1193 §4: deploy zincirinde "systemctl restart bist30-refresh"
# yerine bu script çağrılır. Amaç: deploy'un, CPO-595 cron'un
# (07:00/15:00 UTC = 10:00/18:00 TR, Pzt-Cum) enforce ettiği "seans
# dışı durdurulmuş" durumu koşulsuz geri açmasını önlemek — DEV-1537'de
# bilinçli olarak durdurulan servis, 01.08 deploy'unda sessizce geri
# açılmıştı (bkz. CPO-1193 §4).
#
# Takvim mantığı app.py'nin is_trading_day()/_market_open() ile aynı
# (hafta içi + `holidays` paketi Turkey() takvimi + 10-18 TR saat
# penceresi) — app.py'yi import ETMİYORUZ çünkü import başlı başına
# tüm background thread'leri (digest-cron, macro-bg-loop, vs.) ayağa
# kaldırıyor; burada sadece aynı iki kural bağımsız değerlendiriliyor.
set -euo pipefail

SERVICE="bist30-refresh"
PYTHON="${PYTHON:-/root/bist30/venv/bin/python3}"
[ -x "$PYTHON" ] || PYTHON="python3"

MARKET_OPEN=$("$PYTHON" -c "
from datetime import datetime
from zoneinfo import ZoneInfo
now = datetime.now(ZoneInfo('Europe/Istanbul'))
trading_day = now.weekday() < 5
if trading_day:
    try:
        import holidays
        trading_day = now.date() not in holidays.Turkey()
    except Exception:
        pass
print('1' if (trading_day and 10 <= now.hour < 18) else '0')
" 2>/dev/null || echo "ERR")

TS="$(date '+%Y-%m-%d %H:%M:%S UTC')"

if [ "$MARKET_OPEN" = "1" ]; then
  echo "$TS restart-bist30-refresh-conditional: seans içi -> restart"
  systemctl restart "$SERVICE"
elif [ "$MARKET_OPEN" = "0" ]; then
  CURRENT=$(systemctl is-active "$SERVICE" 2>/dev/null || echo unknown)
  echo "$TS restart-bist30-refresh-conditional: seans dışı -> SKIP (mevcut durum korunuyor: $CURRENT)"
else
  echo "$TS restart-bist30-refresh-conditional: seans-durumu sorgusu BAŞARISIZ -> güvenli taraf: SKIP, elle kontrol et" >&2
  exit 1
fi
