#!/bin/bash
# tools/restart-bist30-refresh-conditional.sh
# CPO-1193 §4: deploy zincirinde "systemctl restart bist30-refresh"
# yerine bu script çağrılır. Amaç: deploy'un, CPO-595 cron'un
# (07:00/15:00 UTC = 10:00/18:00 TR, Pzt-Cum) enforce ettiği "seans
# dışı durdurulmuş" durumu koşulsuz geri açmasını önlemek — DEV-1537'de
# bilinçli olarak durdurulan servis, 01.08 deploy'unda sessizce geri
# açılmıştı (bkz. CPO-1193 §4).
#
# Takvim mantığı artık lib/trading_calendar.py'de tek kanonik kaynak
# (CPO-1195 §2) — app.py da buradan okuyor, iki bağımsız kopya kalmadı.
# app.py'nin kendisini import ETMİYORUZ çünkü onun importu başlı başına
# tüm background thread'leri (digest-cron, macro-bg-loop, vs.) ayağa
# kaldırıyor; lib/trading_calendar.py yan etkisiz, saf bir modül.
set -euo pipefail

SERVICE="bist30-refresh"
PYTHON="${PYTHON:-/root/bist30/venv/bin/python3}"
[ -x "$PYTHON" ] || PYTHON="python3"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MARKET_OPEN=$(cd "$REPO_DIR" && "$PYTHON" lib/trading_calendar.py 2>/dev/null || echo "ERR")

TS="$(date '+%Y-%m-%d %H:%M:%S UTC')"

if [ "$MARKET_OPEN" = "1" ]; then
  echo "$TS restart-bist30-refresh-conditional: seans içi -> restart"
  systemctl restart "$SERVICE"
elif [ "$MARKET_OPEN" = "0" ]; then
  CURRENT=$(systemctl is-active "$SERVICE" 2>/dev/null) || true
  CURRENT="${CURRENT:-unknown}"
  echo "$TS restart-bist30-refresh-conditional: seans dışı -> SKIP (mevcut durum korunuyor: $CURRENT)"
else
  echo "$TS restart-bist30-refresh-conditional: seans-durumu sorgusu BAŞARISIZ -> güvenli taraf: SKIP, elle kontrol et" >&2
  exit 1
fi
