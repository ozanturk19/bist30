#!/bin/bash
# SEO9 #6 (CPO-1194/1201/1206) — nginx 5xx-oranı görünürlüğü cron girişi.
# Mantık tools/nginx_5xx_monitor.py'de (test edilebilir); bu wrapper yalnız
# venv seçimi + concurrent-run kilidi sağlıyor (bist30-stale-watchdog.sh ile
# aynı flock deseni).
#
# Crontab: */5 * * * * /root/bist30/nginx_5xx_monitor.sh > /dev/null 2>&1
set -uo pipefail

LOCK="/var/lock/bist30-nginx-5xx-monitor.lock"
exec 200>"$LOCK"
flock -n 200 || exit 0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$SCRIPT_DIR/venv/bin/python3"
[ -x "$PY" ] || PY="python3"

mkdir -p "$SCRIPT_DIR/logs"
"$PY" "$SCRIPT_DIR/tools/nginx_5xx_monitor.py"
