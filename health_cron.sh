#!/bin/bash
# /root/bist30/health_cron.sh — Crontab'tan her 1 dakikada bir çalışır.
#
# 3 BUG FIX (MSG-007 Task C, 13 May 2026):
#   1. flock — concurrent cron tick race condition önler
#   2. AUTO-RESTART success sonrası STATE = "OK" yazılıyor (RESOLVED spam fix)
#   3. Mail cooldown 30dk, restart cooldown AYRI 10dk (T1.7 fix — 36dk downtime)
#
# 2 ardışık fail → AUTO-RESTART bist30 (restart cooldown 10dk)
# AUTO-RESTART fail → mail alarm (mail cooldown 30dk)
# 5 ardışık fail (5 dk) → CRITICAL alarm

# BUG 1 FIX — Concurrent cron tick'leri engelle
exec 200>/var/lock/bist30_health.lock
flock -n 200 || exit 0   # başka instance çalışıyorsa sessiz exit

STATE=/root/bist30/health_state.txt
LOG=/var/log/bist30_health.log
FAILS_FILE=/root/bist30/health_fail_count.txt
LAST_MAIL_FILE=/root/bist30/health_last_mail.txt
LAST_RESTART_FILE=/root/bist30/health_last_restart.txt
MAIL_COOLDOWN=1800     # 30 dakika — mail spam koruması
RESTART_COOLDOWN=600   # 10 dakika — restart loop koruması (T1.7 fix)

# SPEC-016 K5 (#45 Bulgu 2) — Deploy-lock: servis "activating/deactivating"
# durumundaysa restart SÜRÜYOR demektir. Bu pencerede /api/health 000 döner;
# watchdog bunu fail sayıp deploy'un ÜSTÜNE 2. restart basıyordu (deploy-double).
# ActiveEnterTimestamp restart anında eski kaldığı için #25 grace bu pencereyi
# korumuyor — durum kontrolü iki yönlü guard sağlar.
_active_state=$(systemctl is-active bist30 2>/dev/null)
if [ "$_active_state" != "active" ]; then
  echo "$(date) DEPLOY-SKIP — servis durumu '$_active_state' (restart sürüyor, kontrol atlandı)" >> "$LOG"
  exit 0
fi

# SPEC-009 #25 — Post-restart grace (4dk). Restart sonrası ağır startup burst
# (warm_*, refresh_data, chart) gevent hub'ı doyurur → /api/health geçici yavaş.
# Bu pencerede watchdog tetiklenmesi deploy → ekstra restart → 502 churn zinciri
# yaratıyordu. Servis 240s'den yeni ise kontrol atlanır.
_started_iso=$(systemctl show bist30 -p ActiveEnterTimestamp --value 2>/dev/null)
_started_sec=$(date -d "$_started_iso" +%s 2>/dev/null || echo 0)
_now_sec=$(date +%s)
if [ "$_started_sec" -gt 0 ] && [ $((_now_sec - _started_sec)) -lt 240 ]; then
  echo "$(date) GRACE — restart sonrası $((_now_sec - _started_sec))s (<240s), kontrol atlandı" >> "$LOG"
  exit 0
fi

# BUG 3 FIX — Mail cooldown helper (30dk)
send_mail_if_allowed() {
  local mail_type="$1"
  local now_sec=$(date +%s)
  local last_mail=$(cat "$LAST_MAIL_FILE" 2>/dev/null || echo "0")
  local elapsed=$((now_sec - last_mail))

  if [ "$elapsed" -lt "$MAIL_COOLDOWN" ]; then
    echo "$(date) MAIL-SKIPPED ($mail_type) — cooldown active (${elapsed}s < ${MAIL_COOLDOWN}s)" >> "$LOG"
    return 1
  fi

  /root/bist30/venv/bin/python /root/bist30/notify_health.py "$mail_type" 2>/dev/null
  echo "$now_sec" > "$LAST_MAIL_FILE"
  return 0
}

# T1.7 fix — Restart cooldown helper (10dk, mail'den bağımsız)
can_restart() {
  local now_sec=$(date +%s)
  local last_restart=$(cat "$LAST_RESTART_FILE" 2>/dev/null || echo "0")
  local elapsed=$((now_sec - last_restart))
  if [ "$elapsed" -lt "$RESTART_COOLDOWN" ]; then
    echo "$(date) RESTART-SKIPPED — restart cooldown (${elapsed}s < ${RESTART_COOLDOWN}s)" >> "$LOG"
    return 1
  fi
  return 0
}

# Liveness probe — 30s timeout. SPEC-009 #25: bg-refresh cycle (900s) anında
# leader worker gevent hub'ı yoğunlaşır → /api/health ~15-25s yavaşlayabilir.
# 30s timeout bu geçici yavaşlığı tolere eder (15s fazla agresifti → churn).
http_code=$(curl -m 30 -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8003/api/health 2>/dev/null)

if [ "$http_code" = "200" ]; then
  prev_state=$(cat "$STATE" 2>/dev/null || echo "OK")
  prev_fails=$(cat "$FAILS_FILE" 2>/dev/null || echo "0")

  # BUG 2 FIX — Sadece gerçekten ALARM state'inden geçişte RESOLVED mail gönder
  # Önceden: RECOVERED state'inden de RESOLVED gönderiyordu, prev_fails=0 olsa bile
  if [ "$prev_state" = "ALARM" ]; then
    if send_mail_if_allowed RESOLVED; then
      echo "$(date) RESOLVED — site sağlıklı tekrar (prev_fails=$prev_fails)" >> "$LOG"
    fi
  fi

  # Her zaman normal state'e dön
  echo "OK" > "$STATE"
  echo "0" > "$FAILS_FILE"
  exit 0
fi

# FAIL
fails=$(cat "$FAILS_FILE" 2>/dev/null || echo "0")
fails=$((fails + 1))
echo "$fails" > "$FAILS_FILE"
echo "$(date) FAIL #$fails — HTTP=$http_code" >> "$LOG"

# 2 ardışık fail → AUTO-RESTART (T1.7: restart cooldown 10dk, mail'den bağımsız)
if [ "$fails" -ge 2 ]; then
  if can_restart; then
    echo "$(date) AUTO-RESTART triggered after $fails fails" >> "$LOG"
    date +%s > "$LAST_RESTART_FILE"
    systemctl restart bist30
    echo "RECOVERED" > "$STATE"
    sleep 15
    # Verify recovery
    recovery_code=$(curl -m 30 -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8003/api/health 2>/dev/null)
    if [ "$recovery_code" = "200" ]; then
      echo "$(date) AUTO-RESTART success" >> "$LOG"
      # BUG 2 FIX — Başarılı restart sonrası STATE'i derhal "OK" yap
      echo "OK" > "$STATE"
      echo "0" > "$FAILS_FILE"
    else
      echo "$(date) AUTO-RESTART FAILED — HTTP=$recovery_code, sending alarm" >> "$LOG"
      if send_mail_if_allowed ALARM; then
        echo "ALARM" > "$STATE"
      fi
    fi
  fi
fi

# 5+ ardışık fail (restart işe yaramadı) → CRITICAL alarm
if [ "$fails" -ge 5 ]; then
  prev_state=$(cat "$STATE" 2>/dev/null || echo "OK")
  if [ "$prev_state" != "ALARM" ]; then
    if send_mail_if_allowed ALARM; then
      echo "$(date) CRITICAL ALARM — $fails ardışık fail, restart çözmedi" >> "$LOG"
      echo "ALARM" > "$STATE"
    fi
  fi
fi

exit 1
