#!/bin/bash
# tools/deploy-bundle.sh
# Pzt 30 Haz 09:30 TR cutover: 13-commit bundle deploy + smoke + auto-rollback
# Kullanım: ./tools/deploy-bundle.sh [--dry-run]
# Env: TARGET_SHA, ROLLBACK_SHA, SMOKE_SCRIPT, SERVICE, REPO_DIR

set -euo pipefail

# ─── Config ──────────────────────────────────────────────────────────────────
TARGET_SHA="${TARGET_SHA:-d2ac591}"
ROLLBACK_SHA="${ROLLBACK_SHA:-45f1a2a}"
SMOKE_SCRIPT="${SMOKE_SCRIPT:-/root/bist30/tools/post-deploy-smoke.sh}"
SERVICE="${SERVICE:-bist30}"
REPO_DIR="${REPO_DIR:-/root/bist30}"
LOG="${LOG:-/var/log/bist30-deploy.log}"
HEALTH_URL="${HEALTH_URL:-https://borsapusula.com/api/health}"
DRY_RUN=0

# ─── Flags ───────────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *) echo "Unknown arg: $arg"; exit 1 ;;
  esac
done

# ─── Helpers ─────────────────────────────────────────────────────────────────
log() {
  local msg="$(date '+%Y-%m-%d %H:%M:%S TR') $*"
  echo "$msg"
  echo "$msg" >> "$LOG" 2>/dev/null || true
}

dry() {
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY-RUN] SKIP: $*"
    return 0
  fi
  eval "$@"
}

fail_rollback() {
  local reason="$1"
  log "ROLLBACK REASON: $reason"
  log "Initiating rollback to $ROLLBACK_SHA..."
  dry "cd $REPO_DIR && git reset --hard $ROLLBACK_SHA"
  dry "systemctl restart $SERVICE"
  if [ "$DRY_RUN" = "0" ]; then
    sleep 5
    HTTP=$(curl -sw '%{http_code}' "$HEALTH_URL" -o /dev/null --max-time 8 2>/dev/null || echo "ERR")
    log "Post-rollback health: HTTP $HTTP"
  fi
  log "=== ROLLBACK COMPLETE ==="
}

# ─── 0. Dry-run banner ───────────────────────────────────────────────────────
log "=== DEPLOY START${DRY_RUN:+ [DRY-RUN]} ==="
log "Target: $TARGET_SHA | Rollback: $ROLLBACK_SHA | Service: $SERVICE"
[ "$DRY_RUN" = "1" ] && log "DRY-RUN mode: git pull / systemctl calls are SKIPPED"

# ─── 1. Pre-flight: service running ─────────────────────────────────────────
log "PRE-FLIGHT 1/4: Service status..."
if systemctl is-active --quiet "$SERVICE" 2>/dev/null; then
  log "  OK: $SERVICE is active"
else
  if [ "$DRY_RUN" = "1" ]; then
    log "  [DRY-RUN] WARN: $SERVICE not active (would abort in prod)"
  else
    log "  ERROR: $SERVICE is not active — aborting deploy"
    exit 1
  fi
fi

# ─── 2. Pre-flight: disk space (need >500MB) ────────────────────────────────
log "PRE-FLIGHT 2/4: Disk space..."
AVAIL_KB=$(df -k "$REPO_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo "0")
AVAIL_MB=$((AVAIL_KB / 1024))
if [ "$AVAIL_MB" -gt 500 ]; then
  log "  OK: ${AVAIL_MB}MB available"
else
  log "  ERROR: Only ${AVAIL_MB}MB available — need >500MB. Aborting."
  exit 1
fi

# ─── 3. Pre-flight: repo on main branch ─────────────────────────────────────
log "PRE-FLIGHT 3/4: Branch check..."
BRANCH=$(cd "$REPO_DIR" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [ "$BRANCH" = "main" ]; then
  log "  OK: on branch main"
else
  log "  ERROR: Repo is on branch '$BRANCH' (expected main) — aborting"
  exit 1
fi

# ─── 4. Pre-flight: idempotency check ───────────────────────────────────────
log "PRE-FLIGHT 4/4: Idempotency check..."
CURRENT_SHA=$(cd "$REPO_DIR" && git rev-parse HEAD 2>/dev/null || echo "unknown")
log "  Current: $CURRENT_SHA | Target: $TARGET_SHA"
if [ "$CURRENT_SHA" = "$TARGET_SHA" ]; then
  log "  SKIP: Already at target $TARGET_SHA — deploy not needed."
  log "=== DEPLOY SKIPPED (idempotent) ==="
  exit 0
fi

# ─── 5. Fetch + verify target SHA reachable ─────────────────────────────────
log "DEPLOY 1/4: Fetching + verifying target SHA..."
dry "cd $REPO_DIR && git fetch origin main --quiet"
if [ "$DRY_RUN" = "0" ]; then
  if ! (cd "$REPO_DIR" && git cat-file -e "${TARGET_SHA}^{commit}" 2>/dev/null); then
    log "ERROR: Target SHA $TARGET_SHA not found in repo after fetch — aborting"
    exit 1
  fi
  log "  OK: $TARGET_SHA reachable"
else
  log "  [DRY-RUN] OK: SHA reachability check skipped"
fi

# ─── 6. Git pull ─────────────────────────────────────────────────────────────
log "DEPLOY 2/4: Pulling main..."
dry "cd $REPO_DIR && git pull --ff-only origin main --quiet"
if [ "$DRY_RUN" = "0" ]; then
  NEW_SHA=$(cd "$REPO_DIR" && git rev-parse HEAD)
  log "  HEAD after pull: $NEW_SHA"
  if [ "$NEW_SHA" != "$TARGET_SHA" ]; then
    log "  WARN: HEAD ($NEW_SHA) != target ($TARGET_SHA)"
  else
    log "  OK: HEAD matches target"
  fi
fi

# ─── 7. Reload service ───────────────────────────────────────────────────────
log "DEPLOY 3/4: Reloading service..."
dry "systemctl reload $SERVICE || systemctl restart $SERVICE"
if [ "$DRY_RUN" = "0" ]; then
  sleep 5
  if systemctl is-active --quiet "$SERVICE"; then
    log "  OK: $SERVICE active after reload"
  else
    log "  ERROR: $SERVICE not active after reload — initiating rollback"
    fail_rollback "service not active after reload"
    exit 2
  fi
fi

# ─── 8. Smoke test ───────────────────────────────────────────────────────────
log "DEPLOY 4/4: Smoke test..."
if [ "$DRY_RUN" = "1" ]; then
  log "  [DRY-RUN] SKIP: smoke test ($SMOKE_SCRIPT)"
else
  if [ ! -x "$SMOKE_SCRIPT" ]; then
    log "  ERROR: Smoke script not found or not executable: $SMOKE_SCRIPT"
    fail_rollback "smoke script missing"
    exit 2
  fi
  if ! "$SMOKE_SCRIPT"; then
    log "  SMOKE FAILED"
    fail_rollback "smoke test failed"
    exit 2
  fi
  log "  OK: Smoke PASS"
fi

# ─── 9. Health loop (5x 30s = 2.5min) ───────────────────────────────────────
log "HEALTH: Monitoring 5 checks x 30s..."
if [ "$DRY_RUN" = "1" ]; then
  log "  [DRY-RUN] SKIP: health loop"
else
  for i in 1 2 3 4 5; do
    HTTP=$(curl -sw '%{http_code}' "$HEALTH_URL" -o /dev/null --max-time 8 2>/dev/null || echo "ERR")
    if [ "$HTTP" != "200" ]; then
      log "  HEALTH FAILED (HTTP $HTTP at check $i/5)"
      fail_rollback "health check returned HTTP $HTTP"
      exit 3
    fi
    log "  Health $i/5: HTTP $HTTP OK"
    [ "$i" -lt 5 ] && sleep 30
  done
fi

# ─── Done ────────────────────────────────────────────────────────────────────
log "=== DEPLOY SUCCESS${DRY_RUN:+ [DRY-RUN]} — ${TARGET_SHA} stable ==="
exit 0
