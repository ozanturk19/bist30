#!/bin/bash
# tests/audit/kalici-kurallar-check.sh
# KALICI_KURALLAR v1.1 otomatik grep audit
# Exit 0: tüm KK uyum / Exit 1: en az 1 ihlal
# CPO-359 yeni Tier 0 standardı — pre-commit hook'a bağlanır
#
# Kullanım: ./tests/audit/kalici-kurallar-check.sh [templates/hisse.html]

set -e
FILE="${1:-templates/hisse.html}"
FAIL=0
ECHO_HEADER='\033[1;34m'
ECHO_RESET='\033[0m'
ECHO_FAIL='\033[0;31m'
ECHO_PASS='\033[0;32m'

if [ ! -f "$FILE" ]; then
  echo "ERR: dosya yok: $FILE"
  exit 1
fi

check() {
  local name="$1"
  local pattern="$2"
  local expected="$3"  # 0=must be 0 / +N=must be ≥N
  # Jinja {# ... #} ve HTML <!-- ... --> comment satırlarını hariç tut (false positive engelle)
  local actual=$(grep -vE '^\s*\{#|^\s*<!--|^\s*//' "$FILE" | grep -cE "$pattern" 2>/dev/null; true)
  if [ "$expected" = "0" ]; then
    if [ "$actual" = "0" ]; then
      printf "${ECHO_PASS}✓${ECHO_RESET} %s: %s = 0\n" "$name" "$pattern"
    else
      printf "${ECHO_FAIL}✗${ECHO_RESET} %s: %s = %s (beklenen 0)\n" "$name" "$pattern" "$actual"
      FAIL=$((FAIL + 1))
    fi
  else
    if [ "$actual" -ge "$expected" ]; then
      printf "${ECHO_PASS}✓${ECHO_RESET} %s: %s = %s (≥%s)\n" "$name" "$pattern" "$actual" "$expected"
    else
      printf "${ECHO_FAIL}✗${ECHO_RESET} %s: %s = %s (beklenen ≥%s)\n" "$name" "$pattern" "$actual" "$expected"
      FAIL=$((FAIL + 1))
    fi
  fi
}

printf "${ECHO_HEADER}=== KALICI_KURALLAR v1.1 Audit — %s ===${ECHO_RESET}\n\n" "$FILE"

# K1 — Navigasyon (bp-main-nav var mı?)
check "K1 nav bar (bp-main-nav)" "bp-main-nav" 1

# K2 — Geri tuş yasak (bp-sh-back HTML class veya history.back)
check "K2 geri tuş HTML" 'class="bp-sh-back"' 0
check "K2 history.back" "history\.back\(\)" 0

# K3 — AL/SAT görünür wording
check "K3 'AL Sinyalleri' text" ">AL Sinyalleri<" 0
check "K3 'ORTA SAT' / 'GÜÇLÜ SAT' / 'ZAYIF SAT'" "ORTA SAT|GÜÇLÜ SAT|ZAYIF SAT" 0
check "K3 'al mı sat' SSS" "al mı sat" 0

# K6 — Bronz/Gümüş/Altın tier (canlı render — comment hariç)
check "K6 medals 🥇🥈🥉" "🥇|🥈|🥉" 0

# K9-1 — 'Orta Trend' string
check "K9-1 'Orta Trend' / 'ORTA TREND'" "Orta Trend|ORTA TREND" 0

# K10 — Drawer / openSignalDrawer
check "K10 bpDrawer canlı" "bpDrawer" 0
check "K10 openSignalDrawer" "openSignalDrawer" 0

printf "\n"
if [ "$FAIL" = "0" ]; then
  printf "${ECHO_PASS}✓ TÜM AUDIT GEÇTİ${ECHO_RESET} — KALICI_KURALLAR v1.1 uyum tam.\n"
  exit 0
else
  printf "${ECHO_FAIL}✗ %s ihlal tespit edildi${ECHO_RESET} — commit blokla.\n" "$FAIL"
  exit 1
fi
