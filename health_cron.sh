#!/bin/bash
# /root/bist30/health_cron.sh — Crontab'tan her 1 dakikada bir çalışır.
# 2 ardışık fail → AUTO-RESTART bist30 + mail
# 5 ardışık fail (5 dk) → CRITICAL alarm

STATE=/root/bist30/health_state.txt
LOG=/var/log/bist30_health.log
FAILS_FILE=/root/bist30/health_fail_count.txt

# Quick liveness probe (5s timeout) — /api/data should respond fast (cached)
http_code=$(curl -m 5 -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8003/api/data 2>/dev/null)

if [ "$http_code" = "200" ]; then
  prev_state=$(cat "$STATE" 2>/dev/null || echo "OK")
  prev_fails=$(cat "$FAILS_FILE" 2>/dev/null || echo "0")
  if [ "$prev_state" = "ALARM" ] || [ "$prev_state" = "RECOVERED" ]; then
    /root/bist30/venv/bin/python /root/bist30/notify_health.py RESOLVED 2>/dev/null
    echo "$(date) RESOLVED — site sağlıklı tekrar (prev_fails=$prev_fails)" >> "$LOG"
  fi
  echo "OK" > "$STATE"
  echo "0" > "$FAILS_FILE"
  exit 0
fi

# FAIL
fails=$(cat "$FAILS_FILE" 2>/dev/null || echo "0")
fails=$((fails + 1))
echo "$fails" > "$FAILS_FILE"
echo "$(date) FAIL #$fails — HTTP=$http_code" >> "$LOG"

# 2 ardışık fail → AUTO-RESTART
if [ "$fails" -ge 2 ] && [ "$fails" -lt 5 ]; then
  prev_state=$(cat "$STATE" 2>/dev/null || echo "OK")
  if [ "$prev_state" != "RECOVERED" ]; then
    echo "$(date) AUTO-RESTART triggered after $fails fails" >> "$LOG"
    systemctl restart bist30
    echo "RECOVERED" > "$STATE"
    sleep 15
    # Verify recovery
    recovery_code=$(curl -m 5 -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8003/api/data 2>/dev/null)
    if [ "$recovery_code" = "200" ]; then
      echo "$(date) AUTO-RESTART success" >> "$LOG"
    else
      echo "$(date) AUTO-RESTART FAILED — HTTP=$recovery_code, sending alarm" >> "$LOG"
      /root/bist30/venv/bin/python /root/bist30/notify_health.py ALARM 2>/dev/null
      echo "ALARM" > "$STATE"
    fi
  fi
fi

# 5+ ardışık fail (restart işe yaramadı) → CRITICAL alarm
if [ "$fails" -ge 5 ]; then
  prev_state=$(cat "$STATE" 2>/dev/null || echo "OK")
  if [ "$prev_state" != "ALARM" ]; then
    /root/bist30/venv/bin/python /root/bist30/notify_health.py ALARM 2>/dev/null
    echo "$(date) CRITICAL ALARM — $fails ardışık fail, restart çözmedi" >> "$LOG"
  fi
  echo "ALARM" > "$STATE"
fi

exit 1
