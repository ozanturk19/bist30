#!/bin/bash
# tools/deploy-bundle.sh
# Pzt 30 Haz 09:30 TR cutover: 13-commit bundle deploy + smoke + auto-rollback
# Kullanım: ./tools/deploy-bundle.sh [--dry-run]
# Env: TARGET_SHA, ROLLBACK_SHA, SMOKE_SCRIPT, SERVICE, REPO_DIR
# Env (opsiyonel): ALLOW_UNPUSHED=1 — origin gorunurluk kapisini bypass eder,
#   varsayilan YOK, kullanildiginda deploy.log'a kayit dusurur (bkz. PRE-FLIGHT 5/6).

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

# CPO-1360 sonrasi olcum: mailbox kapisi HER ZAMAN DEV1'in kanalini okuyordu
# (cpo-to-dev.md / dev-to-cpo.md). DEV2 deploy ederken bu iki yonlu ariza uretir:
#   yanlis pozitif  -> DEV2, DEV1'in okunmamis mesaji yuzunden bloklanir
#   yanlis negatif  -> DEV2'ye giden okunmamis mesaj kapiyi HIC tetiklemez
# CPO-1361 §4 KOSUL — SESSIZ VARSAYILAN KALDIRILDI.
# Eskiden: DEPLOY_AGENT="${DEPLOY_AGENT:-dev}". Olculdu: DEPLOY_AGENT hicbir
# wrapper/env dosyasi/systemd drop-in'de set EDILMIYOR — yalnizca komut satirinda
# elle yaziliyordu. Bir kez yazmayi unutan DEV2 icin varsayilan `dev` devreye
# girer, kapi DEV1'in kanalini okur ve cb452de'de kapatilan YANLIS NEGATIF aynen
# geri gelir: DEV2'ye dusmus okunmamis CPO mesaji kapiyi HIC tetiklemez, deploy
# sessizce gecer. Ustelik hata vermeden — fark edilmesi zor.
# ROLLBACK_SHA ile AYNI SINIF hata: guvenlik karari olan bir degiskenin sessiz
# varsayilani olmamali. Yeni kural: verilmemisse GURULTULU REDDET (EXIT=1).
DEPLOY_AGENT="${DEPLOY_AGENT:-}"
if [ -z "$DEPLOY_AGENT" ]; then
  echo "HATA: DEPLOY_AGENT acikca verilmeli — varsayilan YOK. (gecerli: dev | dev2)"
  echo "  Bu degisken mailbox kapisinin HANGI kanali okuyacagini belirler;"
  echo "  yanlis/eksik deger okunmamis CPO mesajini sessizce atlatir."
  echo "  Ornek: DEPLOY_AGENT=dev2 TARGET_SHA=\$(git rev-parse HEAD) ROLLBACK_SHA=\$(git rev-parse HEAD) ./tools/deploy-bundle.sh"
  exit 1
fi
IN_BOX_DIR="mailbox"
case "$DEPLOY_AGENT" in
  dev)  IN_BOX="cpo-to-dev.md";  OUT_BOX="dev-to-cpo.md"
        OTHER_IN="cpo-to-dev2.md"; OTHER_OUT="dev2-to-cpo.md" ;;
  dev2) IN_BOX="cpo-to-dev2.md"; OUT_BOX="dev2-to-cpo.md"
        OTHER_IN="cpo-to-dev.md";  OTHER_OUT="dev-to-cpo.md" ;;
  *) echo "HATA: bilinmeyen DEPLOY_AGENT='$DEPLOY_AGENT' (gecerli: dev | dev2)"; exit 1 ;;
esac
LOG="${LOG:-/var/log/bist30-deploy.log}"
# CANLIDA NE KOSUYOR — kalici kayit. Deploy log'u logrotate ile donuyor
# (/etc/logrotate.d/bist30), bu yuzden "son basarili SHA" icin tek basina
# guvenilir degil. REPO_DIR ve OPS_DIR birer git agaci oldugu icin state
# dosyasi ikisinin de DISINDA tutulur.
STATE_SHA="${STATE_SHA:-/var/lib/bist30/deployed_sha}"
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
  local msg="$(TZ='Europe/Istanbul' date '+%Y-%m-%d %H:%M:%S TR') $*"
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
log "PRE-FLIGHT 0/6: Mailbox gate (agent=$DEPLOY_AGENT)..."
if [ -d "$OPS_DIR/.git" ]; then
  if ! (cd "$OPS_DIR" && git pull --ff-only origin main --quiet); then
    log "  ERROR: $OPS_DIR git pull --ff-only başarısız — aborting (ops repo'yu elle kontrol et)"
    exit 1
  fi
  log "  kanal: gelen=$IN_BOX  giden=$OUT_BOX"
  LAST_REPLY_COMMIT=$(cd "$OPS_DIR" && git log -1 --format=%H -- "$IN_BOX_DIR/$OUT_BOX" 2>/dev/null || echo "")
  if [ -z "$LAST_REPLY_COMMIT" ]; then
    # SESSIZ ATLAMA KAPATILDI: eskiden bu dal NEW_CPO_COMMITS="" atayip kapiyi
    # gecirirdi. Giden kutusunun hic gecmisi yoksa "okundu" DIYEMEYIZ.
    log "  ERROR: $OUT_BOX icin hic commit yok — kapi karar veremiyor, deploy DURDURULDU."
    log "  (Eskiden bu durum SESSIZCE gecerdi; belirsizlikte davranis artik RED.)"
    exit 1
  fi
  NEW_CPO_COMMITS=$(cd "$OPS_DIR" && git log --oneline "${LAST_REPLY_COMMIT}..HEAD" -- "$IN_BOX_DIR/$IN_BOX" 2>/dev/null || echo "")
  if [ -n "$NEW_CPO_COMMITS" ]; then
    log "  ERROR: son $DEPLOY_AGENT yanıtından SONRA yeni CPO mesajı var — deploy DURDURULDU:"
    log "$NEW_CPO_COMMITS"
    log "  Önce $IN_BOX'i oku, gerekiyorsa deploy hedefini/planını güncelle."
    exit 1
  fi
  log "  OK: son $DEPLOY_AGENT yanıtından sonra $IN_BOX'e yeni mesaj yok"
  # DIGER ajanin kanali: BLOKLAMAZ, ama capraz sinyal kaybolmasin diye raporlanir.
  OTHER_LAST=$(cd "$OPS_DIR" && git log -1 --format=%H -- "$IN_BOX_DIR/$OTHER_OUT" 2>/dev/null || echo "")
  if [ -n "$OTHER_LAST" ]; then
    OTHER_NEW=$(cd "$OPS_DIR" && git log --oneline "${OTHER_LAST}..HEAD" -- "$IN_BOX_DIR/$OTHER_IN" 2>/dev/null || echo "")
    if [ -n "$OTHER_NEW" ]; then
      log "  NOT (bloklamaz): $OTHER_IN kanalinda islenmemis $(echo "$OTHER_NEW" | wc -l) mesaj var."
    fi
  fi
else
  log "  WARN: $OPS_DIR git repo değil — mailbox gate atlandı (kontrol edilemedi)"
fi

# ─── 1. Pre-flight: service running ─────────────────────────────────────────
log "PRE-FLIGHT 1/6: Service status..."
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
log "PRE-FLIGHT 2/6: Disk space..."
AVAIL_KB=$(df -k "$REPO_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo "0")
AVAIL_MB=$((AVAIL_KB / 1024))
if [ "$AVAIL_MB" -gt 500 ]; then
  log "  OK: ${AVAIL_MB}MB available"
else
  log "  ERROR: Only ${AVAIL_MB}MB available — need >500MB. Aborting."
  exit 1
fi

# ─── 3. Pre-flight: repo on main branch ─────────────────────────────────────
log "PRE-FLIGHT 3/6: Branch check..."
BRANCH=$(cd "$REPO_DIR" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [ "$BRANCH" = "main" ]; then
  log "  OK: on branch main"
else
  log "  ERROR: Repo is on branch '$BRANCH' (expected main) — aborting"
  exit 1
fi

# ─── 4. Pre-flight: idempotency check ───────────────────────────────────────
log "PRE-FLIGHT 4/6: Idempotency check..."
CURRENT_SHA=$(cd "$REPO_DIR" && git rev-parse HEAD 2>/dev/null || echo "unknown")

# CALISAN kodun SHA'si. Sirayla: kalici state dosyasi -> deploy log'unun
# son GERCEK basari satiri (dry-run satirlari " [DRY-RUN]" etiketi tasir ve
# bu desene UYMAZ) -> bilinmiyor.
LIVE_SHA=""
if [ -r "$STATE_SHA" ]; then
  LIVE_SHA=$(cat "$STATE_SHA" 2>/dev/null | tr -d '[:space:]')
fi
if [ -z "$LIVE_SHA" ]; then
  LIVE_SHA=$( (cat "$LOG" "$LOG".1 2>/dev/null; zcat "$LOG".*.gz 2>/dev/null) \
              | grep -oE '=== DEPLOY SUCCESS — [0-9a-f]{40} stable ===' \
              | tail -1 | grep -oE '[0-9a-f]{40}' || true )
fi
log "  Repo HEAD: $CURRENT_SHA"
log "  Calisan  : ${LIVE_SHA:-BILINMIYOR}"
log "  Hedef    : $TARGET_SHA"

SKIP_PULL=0
if [ "$CURRENT_SHA" = "$TARGET_SHA" ] && [ "$LIVE_SHA" = "$TARGET_SHA" ]; then
  log "  SKIP: hem repo hem CALISAN kod zaten $TARGET_SHA — deploy gereksiz."
  log "=== DEPLOY SKIPPED (idempotent) ==="
  exit 0
elif [ "$CURRENT_SHA" = "$TARGET_SHA" ]; then
  # Eski davranis burada `exit 0` idi ve RELOAD'a HIC ULASMIYORDU.
  # Commit'ler dogrudan prod agacinda atildiginda repo HEAD ilerler ama
  # calisan kod eski kalir; arac hicbir sey yapmadan "basarili" gorunurdu.
  # Kapinin olcmesi gereken sey repo degil CALISAN KOD.
  log "  Repo zaten hedefte AMA calisan kod ${LIVE_SHA:-BILINMIYOR} — pull ATLANACAK, RELOAD GEREKLI."
  SKIP_PULL=1
fi

# ─── 5. Pre-flight: origin gorunurluk kapisi (CPO-1366) ─────────────────────
# DEV2-020: idempotency kapisi "repo HEAD" yerine "CALISAN KOD"a bakacak
# sekilde duzeltilince (yukaridaki 4/6) bir yan kapi actik — SKIP_PULL=1 dalina
# giren, origin/main'in HENUZ GORMEDIGI (push edilmemis) bir TARGET_SHA da
# sessizce kabul edilip dogrudan reload ile canliya inebiliyordu. Bu fiilen
# oldu: 09.08 sabahi origin efbf5af'teyken REPO_DIR'de 6 push'lanmamis commit
# reload'a kadar gitti (bkz. DEV2-020). Eski kapi bunu YANLIS SEBEPTEN
# (HEAD==TARGET kor kontrolu) engelliyordu; kor noktayi duzeltince o tesadufi
# koruma da gitti. Kural: TARGET_SHA origin/main'in atasi degilse GURULTULU
# REDDET. Uc ayri durum, uc ayri ayirt edici mesaj (log dizesine degil exit
# koduna gore karar verilecek):
#   fetch OK   + ancestor EVET  -> EXIT=0  devam
#   fetch OK   + ancestor HAYIR -> EXIT=1  "hedef SHA origin/main'de YOK"
#   fetch FAIL                  -> EXIT=1  "origin'e ulasilamadi" (bayat
#     origin/main'e bakip yanlis sebepten gecirmek/kilitlemekten farkli —
#     P0 rollback'te origin erisilemezse bu kapi acikca ALLOW_UNPUSHED=1 ister,
#     sessizce gecmez).
# Kacis: ALLOW_UNPUSHED=1 — varsayilan YOK (DEPLOY_AGENT deseniyle ayni sinif),
# kullanildiginda deploy.log'a hedef SHA + tarih + "ALLOW_UNPUSHED ile gecildi"
# satiri duser; sessizce atlayan bir guard, olmayan guard'dan daha kotudur.
log "PRE-FLIGHT 5/6: Origin gorunurluk kapisi (TARGET_SHA origin/main'de mi)..."
ALLOW_UNPUSHED="${ALLOW_UNPUSHED:-}"
if ! (cd "$REPO_DIR" && git fetch -q origin main); then
  log "  ERROR: origin'e ulasilamadi, kapi dogrulanamadi (ALLOW_UNPUSHED=1 ile gecilebilir)"
  if [ "$ALLOW_UNPUSHED" = "1" ]; then
    log "  ALLOW_UNPUSHED ile gecildi — hedef: $TARGET_SHA  tarih: $(TZ='Europe/Istanbul' date '+%Y-%m-%d %H:%M:%S TR')"
  else
    exit 1
  fi
elif (cd "$REPO_DIR" && git merge-base --is-ancestor "$TARGET_SHA" origin/main); then
  log "  OK: $TARGET_SHA origin/main'de gorunur (push edilmis)"
else
  log "  ERROR: hedef SHA origin/main'de YOK — once push et (ALLOW_UNPUSHED=1 ile gecilebilir)"
  if [ "$ALLOW_UNPUSHED" = "1" ]; then
    log "  ALLOW_UNPUSHED ile gecildi — hedef: $TARGET_SHA  tarih: $(TZ='Europe/Istanbul' date '+%Y-%m-%d %H:%M:%S TR')"
  else
    exit 1
  fi
fi

# ─── 6. Fetch + verify target SHA reachable ─────────────────────────────────
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

# ─── 7. Git pull ─────────────────────────────────────────────────────────────
log "DEPLOY 2/4: Pulling main..."
if [ "$SKIP_PULL" = "1" ]; then
  log "  SKIP: repo zaten $TARGET_SHA — pull yapilmadi (yalniz reload gerekli)."
elif true; then
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
fi

# ─── 7b. Pre-deploy code guard (T9.4) ───────────────────────────────────────
# pre-deploy-check.sh (Jinja parse + py_compile + KALICI_KURALLAR 11/11 +
# format-lint + CSS token guard + style-guard + lint_scope ratchet) zaten
# yaziliydi ve calisir durumdaydi ama hicbir deploy yolundan cagirilmiyordu —
# guard'lar dogruydu, sadece deploy pipeline'ina hic baglanmamisti (Master
# Program T9.4 acik wiring gap'i, bagimsiz denetimle bulundu 15.08.2026).
# Bu noktada REPO_DIR (pull sonrasi ya da SKIP_PULL durumunda zaten) TARGET_SHA
# icerigindedir; kontrol servise HENUZ dokunulmadan (reload'dan ONCE) calisir —
# basarisizsa reload/restart HIC TETIKLENMEZ, sadece repo ROLLBACK_SHA'ya
# resetlenir (servis o ana kadar dokunulmadigi icin zaten eski kodu calistirmaya
# devam ediyordur — bu bir "rollback" degil, kirli/bozuk pull'u geri almak).
log "DEPLOY 2b/4: Pre-deploy guard (pre-deploy-check.sh, T9.4)..."
PRE_DEPLOY_CHECK="${PRE_DEPLOY_CHECK:-$REPO_DIR/tools/pre-deploy-check.sh}"
if [ "$DRY_RUN" = "1" ]; then
  log "  [DRY-RUN] SKIP: pre-deploy guard ($PRE_DEPLOY_CHECK)"
elif [ ! -x "$PRE_DEPLOY_CHECK" ]; then
  log "  ERROR: pre-deploy guard bulunamadi veya calistirilabilir degil: $PRE_DEPLOY_CHECK"
  (cd "$REPO_DIR" && git reset --hard "$ROLLBACK_SHA") >/dev/null 2>&1 || true
  log "  Repo $ROLLBACK_SHA'ya resetlendi (servis dokunulmadi, hala eski kod calisiyor)."
  exit 2
elif ! (cd "$REPO_DIR" && "$PRE_DEPLOY_CHECK"); then
  log "  PRE-DEPLOY GUARD FAILED — reload/restart TETIKLENMEDI."
  (cd "$REPO_DIR" && git reset --hard "$ROLLBACK_SHA") >/dev/null 2>&1 || true
  log "  Repo $ROLLBACK_SHA'ya resetlendi (servis dokunulmadi, hala eski kod calisiyor)."
  exit 2
else
  log "  OK: pre-deploy guard PASS"
fi

# ─── 8. Reload service ───────────────────────────────────────────────────────
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

# ─── 9. Smoke test ───────────────────────────────────────────────────────────
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

# ─── 10. Health loop (5x 30s = 2.5min) ──────────────────────────────────────
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
if [ "$DRY_RUN" = "0" ]; then
  mkdir -p "$(dirname "$STATE_SHA")" 2>/dev/null || true
  printf '%s\n' "$TARGET_SHA" > "$STATE_SHA" 2>/dev/null \
    && log "  Calisan kod kaydi guncellendi: $STATE_SHA" \
    || log "  UYARI: $STATE_SHA yazilamadi — sonraki kosu log'a dusecek"
fi
log "=== DEPLOY SUCCESS${_DL} — ${TARGET_SHA} stable ==="
exit 0
