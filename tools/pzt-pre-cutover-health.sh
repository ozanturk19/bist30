#!/bin/bash
# Pzt 09:00 TR pre-cutover health check
# Crontab: 0 6 30 6 * /root/bist30/tools/pzt-pre-cutover-health.sh

set -euo pipefail

LOG="/var/log/pzt-pre-cutover.log"
TS="$(date '+%Y-%m-%d %H:%M:%S UTC')"

log() { echo "$TS $*" | tee -a "$LOG"; }

log "=== PRE-CUTOVER HEALTH CHECK ==="

# 1. Service active
if systemctl is-active bist30 > /dev/null 2>&1; then
    log "OK Service active"
else
    log "ALERT SERVICE INACTIVE"
fi

# 2. Health 200
HTTP=$(curl -sw '%{http_code}' http://localhost:8003/api/health -o /dev/null --max-time 8)
if [ "$HTTP" = "200" ]; then
    log "OK Health 200"
else
    log "ALERT Health $HTTP"
fi

# 3. Disk space >500MB
DISK_MB=$(df -m /root | awk 'NR==2 {print $4}')
if [ "$DISK_MB" -gt 500 ]; then
    log "OK Disk ${DISK_MB}MB"
else
    log "ALERT Disk DUSUK ${DISK_MB}MB"
fi

# 4. Branch main
BRANCH=$(cd /root/bist30 && git branch --show-current)
if [ "$BRANCH" = "main" ]; then
    log "OK Branch main"
else
    log "ALERT Branch $BRANCH (main olmali)"
fi

# 5. HEAD verify
HEAD=$(cd /root/bist30 && git rev-parse --short HEAD)
log "HEAD: $HEAD (beklenen pre-cutover: 45f1a2a)"

# 6. nginx 5xx 24h
NGINX_5XX=$(awk -v d="$(date -u '+%d/%b/%Y')" '$0 ~ d && $9 ~ /^(502|504)$/' /var/log/nginx/access.log 2>/dev/null | wc -l)
log "Nginx 5xx 24h: $NGINX_5XX (beklenen 0)"

# 7. Subprocess pool worker count
WORKERS=$(ps aux | grep -E 'yf_(fetch|chart|live|macro|fundamentals)' | grep -v grep | wc -l)
log "Subprocess workers: $WORKERS"

SERVICE_STATUS=$(systemctl is-active bist30 2>/dev/null || echo "inactive")

# Ozan dispatch
REPORT_DIR="/root/ops/cpo-to-ozan"
mkdir -p "$REPORT_DIR"

cat > "$REPORT_DIR/2026-06-30-0900-CPO-cutover-pre-flight.md" << READYEOF
# Pzt Cutover Pre-Flight Report — 09:00 TR

$TS

- Service: $SERVICE_STATUS
- Health: HTTP $HTTP
- Disk: ${DISK_MB}MB
- Branch: $BRANCH
- HEAD: $HEAD
- Nginx 5xx 24h: $NGINX_5XX
- Subprocess workers: $WORKERS

**Cutover komutu (09:30 TR):**
\`\`\`
TARGET_SHA=d2ac591 ROLLBACK_SHA=45f1a2a ./tools/deploy-bundle.sh
\`\`\`

CPO 30dk icinde dry-run + canli deploy baslayacak.
READYEOF

cd /root/ops && git add cpo-to-ozan/ && \
    git -c user.email=ops@borsapusula.com -c user.name=OpsBot commit -q \
        -m "auto: Pzt cutover pre-flight report" && \
    git push -q

log "Pre-flight report dispatched to ops/cpo-to-ozan/"
log "=== PRE-CUTOVER HEALTH CHECK COMPLETE ==="
