#!/bin/bash
# /root/bist30/health_cron.sh — Crontab'tan her 5 dakikada bir çalışır.
# Üst üste 3 fail olursa mail atar (sadece 1 kez, sonra resolve olunca tekrar).

STATE=/root/bist30/health_state.txt
LOG=/var/log/bist30_health.log

if bash /root/bist30/smoke_test.sh > /tmp/smoke_$$.log 2>&1; then
  # PASS — eğer önceden alarm açıksa, "resolved" mail at
  prev_state=$(cat "$STATE" 2>/dev/null || echo "OK")
  if [ "$prev_state" = "ALARM" ]; then
    /root/bist30/venv/bin/python /root/bist30/notify_health.py RESOLVED 2>/dev/null
    echo "$(date) RESOLVED — site sağlıklı tekrar" >> "$LOG"
  fi
  echo "OK" > "$STATE"
  echo "0" > /root/bist30/health_fail_count.txt
  rm -f /tmp/smoke_$$.log
  exit 0
fi

# FAIL — sayacı artır
fails=$(cat /root/bist30/health_fail_count.txt 2>/dev/null || echo "0")
fails=$((fails + 1))
echo "$fails" > /root/bist30/health_fail_count.txt
echo "$(date) FAIL #$fails: $(cat /tmp/smoke_$$.log | head -3 | tr '\n' ' ')" >> "$LOG"
rm -f /tmp/smoke_$$.log

# 3 ardışık fail → alarm
if [ "$fails" -ge 3 ]; then
  prev_state=$(cat "$STATE" 2>/dev/null || echo "OK")
  if [ "$prev_state" = "OK" ]; then
    /root/bist30/venv/bin/python /root/bist30/notify_health.py ALARM 2>/dev/null
    echo "$(date) ALARM — $fails ardışık fail, mail gönderildi" >> "$LOG"
  fi
  echo "ALARM" > "$STATE"
fi

exit 1
