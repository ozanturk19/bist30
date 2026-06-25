#!/bin/bash
# Pzt 30 Haz 09:30 TR cutover — 24h öncesi Ozan hatırlatma dispatch
# Crontab: 0 9 29 6 * /root/bist30/tools/pzt-cutover-countdown.sh
# Çalışma: Paz 29 Haz 09:00 UTC+3 (06:00 UTC)

set -euo pipefail

OPS_DIR="/root/ops"
REMINDER_DIR="${OPS_DIR}/cpo-to-ozan"
REMINDER_FILE="${REMINDER_DIR}/2026-06-29-0900-CPO-cutover-24h.md"
LOG_FILE="/var/log/bist30-cutover-countdown.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# Health check — cutover öncesi servis durumu
HEALTH_STATUS="UNKNOWN"
if curl -sf http://localhost:8003/api/health >/dev/null 2>&1; then
    HEALTH_STATUS="PASS"
else
    HEALTH_STATUS="FAIL"
fi

log "Pzt cutover 24h reminder tetiklendi. Health: ${HEALTH_STATUS}"

mkdir -p "$REMINDER_DIR"

cat > "$REMINDER_FILE" << 'REMINDEREOF'
# 24h Cutover Reminder — Pzt 30 Haz 09:30 TR

## Bundle Bilgisi
- **Commit sayısı:** 15 commit
- **TARGET_SHA:** d2ac591
- **ROLLBACK_SHA:** 45f1a2a

## Deploy Komutu
```bash
TARGET_SHA=d2ac591 ROLLBACK_SHA=45f1a2a ./tools/deploy-bundle.sh
```

## Dokümantasyon
- Playbook: `ops/docs/pzt-cutover-playbook.md` (8 bölüm)
- Failsafe: `ops/docs/pzt-cutover-failsafe-manual.md` (8 senaryo)

## Pre-flight Sırası
1. dry-run → log gözden geçir
2. live deploy (BIST öncesi 09:30 TR)
3. smoke retry (tools/post-deploy-smoke.sh)
4. CPO walk-through
5. BIST açılış monitor (10:00-10:30 TR)

## 24h İçinde Yapılacaklar
- [ ] Phase 3 #2 paket önceliği A/B/C tercih (Ozan karar)
- [ ] SENTRY_DSN — hesap oluşturma + env set (tools/sentry-dsn-aktivasyon-rehberi.md)
- [ ] UptimeRobot — monitor URL ekle (tools/setup-uptimerobot.sh)
- [ ] Son smoke baseline (Cu+Cmt+Paz 3-run median PASS olmalı)

## Notlar
- Port 8003 → prod; Port 8004 → paper-bot (DOKUNMA)
- BIST seans 10:00-18:00 TR arası restart YASAK
- Rollback: 45f1a2a — git reset + systemctl restart bist30

REMINDEREOF

# Health durumunu dosyaya ekle
echo "" >> "$REMINDER_FILE"
echo "## Health Check (Paz 09:00 TR)" >> "$REMINDER_FILE"
echo "- Servis durumu: **${HEALTH_STATUS}**" >> "$REMINDER_FILE"
echo "- Kontrol zamanı: $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$REMINDER_FILE"

if [[ "${HEALTH_STATUS}" == "FAIL" ]]; then
    echo "- ⚠️  UYARI: Health check FAIL — cutover öncesi araştır!" >> "$REMINDER_FILE"
fi

# Ops repo'ya commit + push
cd "$OPS_DIR"
git add cpo-to-ozan/
git commit -m "auto: 24h cutover reminder — Pzt 30 Haz 09:30 TR (health: ${HEALTH_STATUS})"
git push origin main

log "Reminder dispatched: ${REMINDER_FILE}"
log "Health: ${HEALTH_STATUS} — cutover 24h sonra."
