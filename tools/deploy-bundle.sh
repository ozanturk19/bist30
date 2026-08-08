#!/bin/bash
# tools/deploy-bundle.sh
# Pzt 30 Haz 09:30 TR cutover: 13-commit bundle deploy + smoke + auto-rollback
# Kullanım: ./tools/deploy-bundle.sh [--dry-run]
# Env: TARGET_SHA, ROLLBACK_SHA, SMOKE_SCRIPT, SERVICE, REPO_DIR

set -euo pipefail

# ─── Config ──────────────────────────────────────────────────────────────────
# CPO-1357 §4-1 / K1 — SABIT VARSAYILAN KALDIRILDI.
# Eskiden: TARGET_SHA=b1b7e3d, ROLLBACK_SHA=45f1a2a. 45f1a2a 2026-06-24 tarihli
# ve HEAD'e 261 commit / 46 gun uzakti. 'fail_rollback' 4 ayri kosuldan
# tetiklenip 'git reset --hard 45f1a2a' calistiriyordu — REPO_DIR canli servis
# dizini ve 'Restart=always' o eski kodu ayaga kaldirirdi. Yani sessiz bir
# varsayilan, FAZ1+FAZ2'nin tamamini silebilecek kurulu bir tuzakti.
# Yeni kural: verilmemisse SESSIZCE VARSAYMA, GURULTULU REDDET.
TARGET_SHA="${TARGET_SHA:-}"
ROLLBACK_SHA="${ROLLBACK_SHA:-}"
SMOKE_SCRIPT="${SMOKE_SCRIPT:-/root/bist30/tools/post-deploy-smoke.sh}"
SERVICE="${SERVICE:-bist30}"
REPO_DIR="${REPO_DIR:-/root/bist30}"
OPS_DIR="${OPS_DIR:-/root/ops}"
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
_DL=$( [ "$DRY_RUN" = "1" ] && echo " [DRY-RUN]" || true )

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
  # SON SAVUNMA HATTI: hedef bos ise >>git reset --hard<< calistirmak
  # "bilinmeyen bir yere don" demektir. Reset YERINE abort.
  if [ -z "$ROLLBACK_SHA" ]; then
    log "  FATAL: ROLLBACK_SHA bos — >>git reset --hard<< CALISTIRILMADI."
    log "  Servis mevcut haliyle birakildi; elle mudahale gerekiyor."
    log "=== ROLLBACK ABORTED (hedef yok) ==="
    exit 1
  fi
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

# ─── 0. Zorunlu parametreler + emniyet on-kontrolleri ───────────────────────
if [ -z "$TARGET_SHA" ] || [ -z "$ROLLBACK_SHA" ]; then
  echo "HATA: TARGET_SHA ve ROLLBACK_SHA acikca verilmeli — varsayilan YOK."
  echo "  Ornek: TARGET_SHA=\$(git rev-parse HEAD) ROLLBACK_SHA=\$(git rev-parse HEAD) ./tools/deploy-bundle.sh"
  echo "  ROLLBACK_SHA icin dogru deger DEPLOY ONCESI HEAD'dir."
  exit 1
fi

# Kisa SHA'lari TAM SHA'ya cozumle. Gerekce: idempotency kapisi 40 karakterlik
# 'git rev-parse HEAD' ciktisini 7 karakterlik TARGET_SHA ile '=' karsilastiriyordu
# -> hicbir zaman esit olamaz, kapi OLU koddu ve her kosu "WARN: HEAD != target"
# basip devam ediyordu.
# --verify --quiet SART. Ciplak `git rev-parse X^{commit}` cozemedigi argumani
# STDOUT'a AYNEN BASAR ve 128 ile cikar; `2>/dev/null || echo ""` bu yuzden bos
# string uretmez, capture "deadbeef^{commit}" olur ve -z kontrolu GECER.
# Olculdu: gecersiz SHA ile script sonuna kadar kosuyordu (EXIT=0).
# --verify --quiet ise basarisizlikta HICBIR SEY basmaz ve 1 doner.
TARGET_SHA=$(cd "$REPO_DIR" && git rev-parse --verify --quiet "${TARGET_SHA}^{commit}" || true)
ROLLBACK_SHA=$(cd "$REPO_DIR" && git rev-parse --verify --quiet "${ROLLBACK_SHA}^{commit}" || true)
if [ -z "$TARGET_SHA" ] || [ -z "$ROLLBACK_SHA" ]; then
  echo "HATA: verilen TARGET_SHA/ROLLBACK_SHA bu repoda bir commit'e cozulmuyor — abort."
  exit 1
fi

# TEMIZ AGAC ZORUNLU. Gerekce: fail_rollback >>git reset --hard<< calistirir ve
# REPO_DIR canli servis dizinidir; kirli agacta tetiklenirse commit'lenmemis is
# geri donusu OLMADAN silinir. Mevcut 5 on-kontrolun hicbiri buna bakmiyordu.
# DRY-RUN'DA DA KOSAR: salt-okunur bir kontrol, ve dry-run'in isi zaten
# "gercek kosu ne yapardi" sorusunu yanitlamak. Dry-run'da atlanirsa dry-run
# YESIL derken gercek kosu ABORT eder — dry-run'i yalanci yapar.
if true; then
  KIRLI=$(cd "$REPO_DIR" && git status --porcelain --untracked-files=no | wc -l)
  if [ "$KIRLI" != "0" ]; then
    echo "HATA: $REPO_DIR kirli ($KIRLI izlenen dosya degisik) — deploy DURDURULDU."
    echo "  Sebep: rollback yolu 'git reset --hard' calistirir; kirli agacta bu"
    echo "  commit'lenmemis isi geri donusu olmadan siler."
    (cd "$REPO_DIR" && git status --short --untracked-files=no | head -20)
    exit 1
  fi
fi

# ─── 0b. Dry-run banner ─────────────────────────────────────────────────────
log "=== DEPLOY START${_DL} ==="
log "Target: $TARGET_SHA | Rollback: $ROLLBACK_SHA | Service: $SERVICE"
[ "$DRY_RUN" = "1" ] && log "DRY-RUN mode: git pull / systemctl calls are SKIPPED"

# ─── 0. Pre-flight: mailbox gate (CPO-1148 §2) ──────────────────────────────
# Mekanik gate — davranışsal taahhüt (mailbox'ı çekmeyi "unutmama" sözü) iki
# kez tutmadı (bkz. check_mailbox_before_forensic_action / reverify_prod_state
# geçmişi). git log diff kontrolü koda gömülü: DEV'in son mailbox yanıtından
# (mailbox/dev-to-cpo.md'ye son commit) SONRA cpo-to-dev.md'ye giden bir
# commit varsa, işlenmemiş yeni bir CPO mesajı var demektir — deploy durur.
log "PRE-FLIGHT 0/5: Mailbox gate..."
if [ -d "$OPS_DIR/.git" ]; then
  if ! (cd "$OPS_DIR" && git pull --ff-only origin main --quiet); then
    log "  ERROR: $OPS_DIR git pull --ff-only başarısız — aborting (ops repo'yu elle kontrol et)"
    exit 1
  fi
  LAST_DEV_REPLY_COMMIT=$(cd "$OPS_DIR" && git log -1 --format=%H -- mailbox/dev-to-cpo.md 2>/dev/null || echo "")
  if [ -n "$LAST_DEV_REPLY_COMMIT" ]; then
    NEW_CPO_COMMITS=$(cd "$OPS_DIR" && git log --oneline "${LAST_DEV_REPLY_COMMIT}..HEAD" -- mailbox/cpo-to-dev.md 2>/dev/null || echo "")
  else
    NEW_CPO_COMMITS=""
  fi
  if [ -n "$NEW_CPO_COMMITS" ]; then
    log "  ERROR: son DEV yanıtından SONRA yeni CPO mesajı var — deploy DURDURULDU:"
    log "$NEW_CPO_COMMITS"
    log "  Önce mailbox/cpo-to-dev.md'yi oku, gerekiyorsa deploy hedefini/planını güncelle."
    exit 1
  fi
  log "  OK: son DEV yanıtından sonra yeni CPO mesajı yok"
else
  log "  WARN: $OPS_DIR git repo değil — mailbox gate atlandı (kontrol edilemedi)"
fi

# ─── 1. Pre-flight: service running ─────────────────────────────────────────
log "PRE-FLIGHT 1/5: Service status..."
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
log "PRE-FLIGHT 2/5: Disk space..."
AVAIL_KB=$(df -k "$REPO_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo "0")
AVAIL_MB=$((AVAIL_KB / 1024))
if [ "$AVAIL_MB" -gt 500 ]; then
  log "  OK: ${AVAIL_MB}MB available"
else
  log "  ERROR: Only ${AVAIL_MB}MB available — need >500MB. Aborting."
  exit 1
fi

# ─── 3. Pre-flight: repo on main branch ─────────────────────────────────────
log "PRE-FLIGHT 3/5: Branch check..."
BRANCH=$(cd "$REPO_DIR" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [ "$BRANCH" = "main" ]; then
  log "  OK: on branch main"
else
  log "  ERROR: Repo is on branch '$BRANCH' (expected main) — aborting"
  exit 1
fi

# ─── 4. Pre-flight: idempotency check ───────────────────────────────────────
log "PRE-FLIGHT 4/5: Idempotency check..."
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
log "=== DEPLOY SUCCESS${_DL} — ${TARGET_SHA} stable ==="
exit 0
