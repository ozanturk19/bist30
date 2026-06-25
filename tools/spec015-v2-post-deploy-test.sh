#!/bin/bash
# tools/spec015-v2-post-deploy-test.sh
# SPEC-015 v2 post-deploy acceptance test
# Çalıştırma: ./tools/spec015-v2-post-deploy-test.sh [BASE_URL]
# JSON çıktı: ./tools/spec015-v2-post-deploy-test.sh --json
# Beklenen: Pzt 30 Haz 09:30 cutover SONRASI tüm checks PASS

set -euo pipefail

JSON_MODE=0
BASE="${BASE:-https://borsapusula.com}"

for arg in "$@"; do
  case "$arg" in
    --json) JSON_MODE=1 ;;
    http*) BASE="$arg" ;;
  esac
done

PASS=0
FAIL=0
WARN=0
RESULTS=()
LOG_FILE="/tmp/spec015-test-output.txt"
START_TS=$(date '+%Y-%m-%d %H:%M:%S TR')

log()  { [[ $JSON_MODE -eq 0 ]] && echo "$*" | tee -a "$LOG_FILE" || true; }
ok()   { PASS=$((PASS+1)); RESULTS+=("PASS|$1"); [[ $JSON_MODE -eq 0 ]] && echo "  ✓ $1" | tee -a "$LOG_FILE"; }
fail() { FAIL=$((FAIL+1)); RESULTS+=("FAIL|$1"); [[ $JSON_MODE -eq 0 ]] && echo "  ✗ FAIL: $1" | tee -a "$LOG_FILE"; }
warn() { WARN=$((WARN+1)); RESULTS+=("WARN|$1"); [[ $JSON_MODE -eq 0 ]] && echo "  ⚠ WARN: $1" | tee -a "$LOG_FILE"; }

> "$LOG_FILE"
log "=== SPEC-015 v2 Post-Deploy Acceptance Test ==="
log "BASE: $BASE"
log "Başlangıç: $START_TS"
log ""

# ── Test 1: jargon-term count (5 sayfa) ──────────────────────────────────────
log "1/5 jargon-term sayım (5 sayfa)..."

declare -A JARGON_EXPECTED
JARGON_EXPECTED["/"]="7"
JARGON_EXPECTED["/tarama"]="1"
JARGON_EXPECTED["/gucu_yuksek"]="5"
JARGON_EXPECTED["/hisse/AKBNK"]="8"
JARGON_EXPECTED["/sinyal_performans"]="3"

for url in "/" "/tarama" "/gucu_yuksek" "/hisse/AKBNK" "/sinyal_performans"; do
  exp="${JARGON_EXPECTED[$url]}"
  body=$(curl -s --max-time 15 "${BASE}${url}" 2>/dev/null || echo "")
  cnt=$(echo "$body" | grep -c 'class="jargon-term"' 2>/dev/null || echo "0")
  if [[ "$cnt" -eq "$exp" ]]; then
    ok "${url} jargon-term=${cnt} (beklenen=${exp})"
  elif [[ "$cnt" -gt "$exp" ]]; then
    warn "${url} jargon-term=${cnt} > beklenen=${exp} (fazla — incele)"
  else
    fail "${url} jargon-term=${cnt} (beklenen=${exp})"
  fi
done

log ""

# ── Test 2: learning-mode.js script tag (5 sayfa) ────────────────────────────
log "2/5 learning-mode.js script tag varlığı (5 sayfa)..."

for url in "/" "/tarama" "/gucu_yuksek" "/hisse/AKBNK" "/sinyal_performans"; do
  body=$(curl -s --max-time 15 "${BASE}${url}" 2>/dev/null || echo "")
  if echo "$body" | grep -q 'learning-mode\.js'; then
    ok "${url} learning-mode.js script tag MEVCUT"
  else
    fail "${url} learning-mode.js script tag YOK"
  fi
done

log ""

# ── Test 3: /metodoloji#rsi anchor href (4 yer) ──────────────────────────────
log "3/5 /metodoloji#rsi href varlığı (4 sayfa)..."

declare -A RSI_PAGES
RSI_PAGES["/"]="/"
RSI_PAGES["/hisse/AKBNK"]="/hisse/AKBNK"
RSI_PAGES["/sinyal_performans"]="/sinyal_performans"
RSI_PAGES["/gucu_yuksek"]="/gucu_yuksek"

for url in "/" "/hisse/AKBNK" "/sinyal_performans" "/gucu_yuksek"; do
  body=$(curl -s --max-time 15 "${BASE}${url}" 2>/dev/null || echo "")
  if echo "$body" | grep -q 'href="/metodoloji#rsi"'; then
    ok "${url} href='/metodoloji#rsi' MEVCUT"
  else
    fail "${url} href='/metodoloji#rsi' YOK"
  fi
done

log ""

# ── Test 4: glossary 6 terim (/metodoloji) ───────────────────────────────────
log "4/5 glossary 6 terim varlığı (/metodoloji)..."

GLOSSARY_PAGE=$(curl -s --max-time 15 "${BASE}/metodoloji" 2>/dev/null || echo "")

TERMS=("adx" "rsi" "ema" "supertrend" "kovalama" "r/r")
for term in "${TERMS[@]}"; do
  # Case-insensitive search, glossary terimler lower-case anchor id olarak geçer
  if echo "$GLOSSARY_PAGE" | grep -qi "id=\"${term}\""; then
    ok "/metodoloji glossary anchor #${term} MEVCUT"
  elif echo "$GLOSSARY_PAGE" | grep -qi "${term}"; then
    warn "/metodoloji '${term}' içerikte mevcut (anchor id yok — kontrol et)"
  else
    fail "/metodoloji '${term}' YOK"
  fi
done

log ""

# ── Test 5: MutationObserver / Sig-tip jargon (opsiyonel, curl-only check) ───
log "5/5 Sig-tip jargon MutationObserver (opsiyonel — JS exec gereksiz curl check)..."

SINYAL_BODY=$(curl -s --max-time 15 "${BASE}/sinyal_performans" 2>/dev/null || echo "")
if echo "$SINYAL_BODY" | grep -q 'MutationObserver'; then
  ok "/sinyal_performans MutationObserver kod varlığı ONAYLANDI"
else
  warn "/sinyal_performans MutationObserver bulunamadı (sayfa JS lazy-load ediyorsa normal)"
fi

if echo "$SINYAL_BODY" | grep -q 'sig-tip'; then
  ok "/sinyal_performans sig-tip class varlığı ONAYLANDI"
else
  warn "/sinyal_performans sig-tip class bulunamadı (dinamik render ise normal)"
fi

log ""

# ── Sonuç ─────────────────────────────────────────────────────────────────────
END_TS=$(date '+%Y-%m-%d %H:%M:%S TR')
TOTAL=$((PASS+FAIL+WARN))

if [[ $JSON_MODE -eq 1 ]]; then
  echo "{"
  echo "  \"timestamp\": \"$END_TS\","
  echo "  \"base\": \"$BASE\","
  echo "  \"pass\": $PASS,"
  echo "  \"fail\": $FAIL,"
  echo "  \"warn\": $WARN,"
  echo "  \"total\": $TOTAL,"
  echo "  \"status\": \"$([ $FAIL -eq 0 ] && echo 'PASS' || echo 'FAIL')\","
  echo "  \"results\": ["
  for i in "${!RESULTS[@]}"; do
    r="${RESULTS[$i]}"
    s="${r%%|*}"
    m="${r#*|}"
    comma=","
    [[ $i -eq $((${#RESULTS[@]}-1)) ]] && comma=""
    echo "    {\"status\": \"$s\", \"message\": \"$m\"}$comma"
  done
  echo "  ]"
  echo "}"
else
  log "═══════════════════════════════════════════════"
  log "SONUÇ: PASS=$PASS | FAIL=$FAIL | WARN=$WARN / TOTAL=$TOTAL"
  log "Bitiş: $END_TS"
  log "Log: $LOG_FILE"
  if [[ $FAIL -eq 0 ]]; then
    log ""
    log "✅ SPEC-015 v2 POST-DEPLOY ACCEPTANCE: PASS"
  else
    log ""
    log "❌ SPEC-015 v2 POST-DEPLOY ACCEPTANCE: FAIL ($FAIL adet hata)"
  fi
fi

exit $((FAIL > 0))
