#!/bin/bash
# Faz 12 P2.4b — P1 hourly cron: ALERT.md saatlik özet log
ALERT_MD="/root/bist30/ALERT.md"
LOG_DIR="/root/bist30/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/dqv_hourly.log"

if [ ! -f "$ALERT_MD" ]; then
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') | DQV_HOURLY | ALERT.md yok" >> "$LOG"
    exit 0
fi

CUTOFF=$(date -u -d '1 hour ago' '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -u -v-1H '+%Y-%m-%d %H:%M:%S')
P0_CNT=$(awk -v cut="$CUTOFF" 'match($0, /\[([0-9 :-]+) UTC\]/, a) && a[1] >= cut && / P0/ {count++} END{print count+0}' "$ALERT_MD")
P1_CNT=$(awk -v cut="$CUTOFF" 'match($0, /\[([0-9 :-]+) UTC\]/, a) && a[1] >= cut && / P1/ {count++} END{print count+0}' "$ALERT_MD")
TOTAL_CNT=$(wc -l < "$ALERT_MD")

echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') | DQV_HOURLY | P0=${P0_CNT} P1=${P1_CNT} son_1h | toplam_satirlar=${TOTAL_CNT}" >> "$LOG"

# 30 günden eski log satırlarını temizle (log rotation)
if [ "$(wc -l < "$LOG")" -gt 1000 ]; then
    tail -720 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi

# --- CPO-1165 D-DQV-1 -------------------------------------------------------
# DQV yalnız ALERT.md şema doğrulamasını görüyordu; 31.07'de haber servisi 6+
# saat %36 başarı oranında çalışırken (101 FAIL, CB 8 kez açıldı) DQV "P0=0 P1=0"
# yazmaya devam etti — yanlış güven verdi. Servis-degradasyonu artık kapsamda:
# news_degraded, CB açık kalma süresi (retry_after_s), ve refresh doluluk oranı
# (bad_ticker_count/count, yalnız seans içiyken anlamlı — hafta sonu/gece stale
# olması tasarım gereği, bkz. [[project_weekend_refresh_stale_by_design]]).
HEALTH_JSON=$(curl -s --max-time 5 http://localhost:8003/api/health)
if [ -n "$HEALTH_JSON" ]; then
    python3 - "$HEALTH_JSON" <<'PYEOF' >> "$LOG" 2>&1
import json, sys, datetime

try:
    d = json.loads(sys.argv[1])
except Exception as e:
    now_err = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"{now_err} UTC | DQV_NEWS | health JSON parse hatasi: {e}")
    sys.exit(0)

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
news = d.get("news", {}) or {}
degraded = bool(news.get("degraded"))
retry_after_s = news.get("retry_after_s", 0)
ok_today = news.get("ok_today", 0)
fail_today = news.get("fail_today", 0)
cb_opens_today = news.get("cb_opens_today", 0)

# CPO-1184/1185 D-7 (P2): anlik 'degraded' bayragi orneklendigi saniyeye gore
# false olabilir (CB o an kapali/retry_after dolmus) — kotu bir saati (fail
# deltasi > ok deltasi) kacirabilir (04:05 vakasi: degraded=false ama o saatte
# 23 hata/3 basari). Onceki tick'i kendi log dosyasindan oku, delta'ya bak —
# bayrak false olsa da kotu saat gorulsun.
import re
prev_ok, prev_fail = None, None
try:
    with open("/root/bist30/logs/dqv_hourly.log") as lf:
        for line in lf:
            m = re.search(r'DQV_NEWS \| degraded=\S+ retry_after_s=\S+ ok_today=(\d+) fail_today=(\d+)', line)
            if m:
                prev_ok, prev_fail = int(m.group(1)), int(m.group(2))
except Exception:
    pass

ok_delta = (ok_today - prev_ok) if prev_ok is not None else None
fail_delta = (fail_today - prev_fail) if prev_fail is not None else None
silent_bad_hour = (not degraded and fail_delta is not None and ok_delta is not None
                    and fail_delta > ok_delta and fail_delta > 0)

print(f"{now} UTC | DQV_NEWS | degraded={str(degraded).lower()} retry_after_s={retry_after_s} "
      f"ok_today={ok_today} fail_today={fail_today} cb_opens_today={cb_opens_today} "
      f"ok_delta={ok_delta if ok_delta is not None else 'n/a'} "
      f"fail_delta={fail_delta if fail_delta is not None else 'n/a'}")

if degraded:
    with open("/root/bist30/ALERT.md", "a") as f:
        f.write(f"[{now} UTC] P1 DQV_NEWS: news_degraded=true retry_after_s={retry_after_s} "
                f"ok_today={ok_today} fail_today={fail_today} cb_opens_today={cb_opens_today}\n")
elif silent_bad_hour:
    with open("/root/bist30/ALERT.md", "a") as f:
        f.write(f"[{now} UTC] P2 DQV_NEWS: degraded=false ama saatlik fail_delta={fail_delta} > "
                f"ok_delta={ok_delta} (ornekleme-araligi kotu saat, CPO-1184/1185 D-7) "
                f"ok_today={ok_today} fail_today={fail_today}\n")

stocks_count = (d.get("stocks", {}) or {}).get("count", 0) or 0
bad_ticker_count = d.get("bad_ticker_count", 0) or 0
market_open = (d.get("data_freshness", {}) or {}).get("market_open", False)
fill_ratio = None
if stocks_count:
    fill_ratio = 1 - (bad_ticker_count / stocks_count)

print(f"{now} UTC | DQV_REFRESH | market_open={str(bool(market_open)).lower()} "
      f"bad_ticker_count={bad_ticker_count}/{stocks_count} "
      f"fill_ratio={round(fill_ratio, 3) if fill_ratio is not None else 'n/a'}")

if market_open and fill_ratio is not None and fill_ratio < 0.5:
    with open("/root/bist30/ALERT.md", "a") as f:
        f.write(f"[{now} UTC] P1 DQV_REFRESH: seans-ici doluluk dusuk "
                f"bad_ticker_count={bad_ticker_count}/{stocks_count} fill_ratio={round(fill_ratio, 3)}\n")
PYEOF
else
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') | DQV_NEWS | /api/health yanit vermedi (curl bos)" >> "$LOG"
fi
