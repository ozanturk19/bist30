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
ALERT=/root/ops/ALERT.md
FAILS_FILE=/root/bist30/health_fail_count.txt
STALE_FAILS_FILE=/root/bist30/health_stale_count.txt
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
# CPO-1106 (16 Tem 21:20 TR çift-restart) — smoke-watch.sh ayrı bir cooldown
# dosyası kullanıyor (/root/ops/smoke_watch_last_restart.txt), health_cron bunu
# bilmiyordu. Aynı outage'ı iki watchdog ayrı ayrı restart'lıyordu: health_cron'un
# curl'ü (30s timeout) smoke-watch'un restart'ından ÖNCE başladığı için GRACE
# penceresi (ActiveEnterTimestamp) henüz güncellenmemiş görüp atlamıyordu, sonra
# health_cron kendi 2-fail sayacıyla ikinci (gereksiz) restart'ı tetikliyordu.
SMOKE_RESTART_FILE=/root/ops/smoke_watch_last_restart.txt
can_restart() {
  local now_sec=$(date +%s)
  local last_restart=$(cat "$LAST_RESTART_FILE" 2>/dev/null || echo "0")
  local elapsed=$((now_sec - last_restart))
  if [ "$elapsed" -lt "$RESTART_COOLDOWN" ]; then
    echo "$(date) RESTART-SKIPPED — restart cooldown (${elapsed}s < ${RESTART_COOLDOWN}s)" >> "$LOG"
    return 1
  fi
  local smoke_last=$(cat "$SMOKE_RESTART_FILE" 2>/dev/null || echo "0")
  local smoke_elapsed=$((now_sec - smoke_last))
  if [ "$smoke_elapsed" -lt "$RESTART_COOLDOWN" ]; then
    echo "$(date) RESTART-SKIPPED — smoke-watch ${smoke_elapsed}s önce restart etti (<${RESTART_COOLDOWN}s), paylaşımlı cooldown" >> "$LOG"
    return 1
  fi
  return 0
}

# Liveness probe — 30s timeout. SPEC-009 #25: bg-refresh cycle (900s) anında
# leader worker gevent hub'ı yoğunlaşır → /api/health ~15-25s yavaşlayabilir.
# 30s timeout bu geçici yavaşlığı tolere eder (15s fazla agresifti → churn).
response=$(curl -m 30 -s -w '\n%{http_code}' http://127.0.0.1:8003/api/health 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

# DEV-1431 audit-trail fix — önceden başarılı (200 + ok:true) tikler HİÇ log
# yazmıyordu, bu yüzden 08:20 TR restart'ının gerçek tetikleyicisi geriye dönük
# doğrulanamadı (forensic boşluk). Her tick'te (başarılı dahil) kompakt bir
# satır yaz — restart/alarm mantığına dokunmuyor, sadece ek gözlemlenebilirlik.
_ok_val=$(echo "$body" | grep -oE '"ok": *[a-z]+' | head -1 | sed -E 's/"ok": *//')
_status_val=$(echo "$body" | grep -oE '"status": *"[^"]*"' | head -1 | sed -E 's/.*"status": *"([^"]*)".*/\1/')
_bad_ticker_val=$(echo "$body" | grep -oE '"bad_ticker_count": *[0-9]+' | head -1 | sed -E 's/.*: *//')
echo "$(date) TICK http=$http_code ok=${_ok_val:-?} status=${_status_val:-?} bad_ticker=${_bad_ticker_val:-?}" >> "$LOG"

# CPO-1261 madde 2 — /api/health lock-free (bg thread'den önceden hesaplanmış
# snapshot'ı servis eder, app.py:8783) bu yüzden hub gerçekten bloke olsa bile
# ANINDA döner (3 Ağustos 23:05 TR outage kanıtı: /api/health 3/3 200 t=0.0016s,
# AYNI ANDA /api/data 5/5 20s timeout — health_cron o gece TEK FAIL göremedi,
# tespit 10dk'lik smoke-watch'a kaldı). Bu probe /api/health'in yukarıdaki hiçbir
# dallanmasına (BODY-STALE exit 0, http_code=200 exit 0) bağlı DEĞİL — her tick'te
# çalışır. /api/data'nın kendisi lock alıp gerçek veriyi döndürür, bu yüzden
# hub-bloke sınıfını /api/health'in kaçırdığı yerde yakalar.
DATA_FAILS_FILE=/root/bist30/health_data_fail_count.txt
data_response=$(curl -m 15 -s -w '\n%{http_code}' http://127.0.0.1:8003/api/data 2>/dev/null)
data_http_code=$(echo "$data_response" | tail -n1)
data_body=$(echo "$data_response" | sed '$d')
data_probe=$(echo "$data_body" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    stocks = d.get('stocks', [])
    dq = d.get('data_quality', '?')
    print(f'len={len(stocks)}|dq={dq}')
except Exception as e:
    print('PARSE_FAIL:' + str(e)[:40])
" 2>/dev/null)
data_stocks_len=$(echo "$data_probe" | sed -n 's/^len=\([0-9]*\)|.*/\1/p')
echo "$(date) DATA-TICK http=$data_http_code $data_probe" >> "$LOG"

if [ "$data_http_code" = "200" ] && [ -n "$data_stocks_len" ] && [ "$data_stocks_len" -gt 0 ] 2>/dev/null; then
  echo "0" > "$DATA_FAILS_FILE"
else
  data_fails=$(cat "$DATA_FAILS_FILE" 2>/dev/null || echo "0")
  data_fails=$((data_fails + 1))
  echo "$data_fails" > "$DATA_FAILS_FILE"
  echo "$(date) DATA-FAIL #$data_fails — http=$data_http_code $data_probe" >> "$LOG"
  # 2 ardışık fail'de bir kez ALERT (smoke-watch'un SERVICE_DOWN STREAK==2
  # deseniyle aynı disiplin — her tick'te tekrar yazıp spam etmez).
  if [ "$data_fails" -eq 2 ]; then
    _data_alert_tr_now=$(TZ='Europe/Istanbul' date '+%Y-%m-%d %H:%M:%S TR')
    {
      echo ""
      echo "### P0-ALERT [$_data_alert_tr_now] /api/data 2 ardışık fail (health hızlı dönerken data hang sınıfı)"
      echo "Detay: http=$data_http_code $data_probe"
      echo "Yorum: CPO-1261 madde 2 — /api/health lock-free snapshot olduğu için hub-bloke durumunda bile hızlı döner, bu probe /api/data'nın GERÇEK isteğini test eder."
      echo "Eylem: Claude session aç -> DEV gör -> forensic-snapshot.sh (SIGUSR2 greenlet dump dahil) incele"
    } >> "$ALERT"
  fi
fi

# CPO-1055 body-check fix — blind spot: HTTP 200 dönebilir ama veri seans
# içinde taze olmayabilir (13-14 Tem 2026 canlı vaka: Yahoo blok → refresh
# başarısız → stocks 16sa+ stale, health hâlâ HTTP 200/hızlı döndü, HTTP-kod-only
# kontrol bunu YAKALAMADI). "ok" alanı is_stale/market_day zaten hesaba katıyor
# (bkz. weekend-aware stale, commit 990a426) — burada tekrar iş mantığı yazmaya
# gerek yok, sadece tüketiyoruz. Restart bunu ÇÖZMEZ (Yahoo taraf blok,
# process-içi değil) — bu yüzden AUTO-RESTART tetiklemez, sadece 3 ardışık
# dakika sonra mail alarmı atar (aynı STATE/cooldown makinesini paylaşır).
if [ "$http_code" = "200" ] && echo "$body" | grep -q '"ok": *false'; then
  stale_fails=$(cat "$STALE_FAILS_FILE" 2>/dev/null || echo "0")
  stale_fails=$((stale_fails + 1))
  echo "$stale_fails" > "$STALE_FAILS_FILE"
  echo "$(date) BODY-STALE #$stale_fails — HTTP 200 ama body ok=false (veri seans içi taze değil)" >> "$LOG"
  if [ "$stale_fails" -ge 3 ]; then
    if send_mail_if_allowed ALARM; then
      echo "$(date) STALE ALARM — $stale_fails ardışık body-stale, restart tetiklenmedi (external cause)" >> "$LOG"
      echo "ALARM" > "$STATE"
    fi
  fi
  exit 0
fi
echo "0" > "$STALE_FAILS_FILE"

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

    # CPO-1128 (4) revize — health_cron restart'ları ALERT.md'de görünmüyordu
    # (tek üretici smoke-watch.sh idi). smoke-watch.sh formatıyla aynı, kaynağı
    # ayırt etmek için RESTART-AUTO-HEALTHCRON etiketiyle yazılıyor.
    _alert_tr_now=$(TZ='Europe/Istanbul' date '+%Y-%m-%d %H:%M:%S TR')
    {
      echo ""
      echo "### RESTART-AUTO-HEALTHCRON [$_alert_tr_now]"
      echo "fails=$fails (2 ardışık /api/health fail) -> systemctl restart bist30 | 15s sonrası: $recovery_code"
    } >> "$ALERT"

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
