#!/bin/bash
# tools/format-lint.sh
# CPO-1180 K6 — Format-lint: TR sayı/₺ formatı ve XU100/XU030 çıplak ticker
# regresyonlarını yakalar. Şablon listesi app.py route tablosundan TÜRETİLİR
# (elle seçilmez — K6 dersi: "kapsam elle seçilmez, kapsam derive edilir").
#
# Exit 0: bloklayıcı kategori ihlali yok / Exit 1: en az 1 bloklayıcı ihlal.
# Hex-token drift (kategori 4) SADECE UYARI — dozlarca mevcut occurrence var,
# toplu otomatik dönüşüm görsel regresyon riski taşır (tam_cozum_kural gereği
# tek tek VR ile doğrulanmalı) — backlog, bloklamaz.
#
# Kullanım: ./tools/format-lint.sh

set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

FAIL=0
ECHO_PASS='\033[0;32m'
ECHO_FAIL='\033[0;31m'
ECHO_WARN='\033[0;33m'
ECHO_HEADER='\033[1;34m'
ECHO_RESET='\033[0m'

printf "${ECHO_HEADER}=== format-lint (CPO-1180 K6) ===${ECHO_RESET}\n\n"

# ── Şablon listesini app.py route tablosundan türet ──────────────────────
# render_template("x.html", ...) çağrılarındaki TÜM template adlarını topla.
TEMPLATES=$(grep -oE "render_template\(\s*['\"][a-zA-Z0-9_/]+\.html" app.py \
  | sed -E "s/render_template\(\s*['\"]//" | sort -u)

TEMPLATE_FILES=""
for t in $TEMPLATES; do
  if [ -f "templates/$t" ]; then
    TEMPLATE_FILES="$TEMPLATE_FILES templates/$t"
  fi
done

TCOUNT=$(echo "$TEMPLATE_FILES" | wc -w | tr -d ' ')
echo "Taranan şablon sayısı (app.py route tablosundan türetildi): $TCOUNT"
echo ""

count_matches() {
  # $1 = pattern (extended regex), rest = files
  local pattern="$1"; shift
  grep -EnH "$pattern" "$@" 2>/dev/null | grep -vE '\{#|<!--' || true
}

# ── Kategori 1: Nokta-ondalıklı ₺ değeri (Python f-string + JS toFixed) ──
# NOT: ".0f" hariç — 0 ondalık basamak hiç nokta üretmez (yanlış-pozitif).
echo "1/4 Nokta-ondalıklı ₺ değeri..."
PY_HITS=$(count_matches '\.[1-9][0-9]*f\}[ ]?₺' app.py)
JS_HITS=$(count_matches "toFixed\([1-9][0-9]*\)[ ]*\+[ ]*['\"]₺" $TEMPLATE_FILES)
DEC_HITS="${PY_HITS}${JS_HITS}"
DEC_N=$(printf '%s\n' "$PY_HITS" "$JS_HITS" | grep -c '.' || true)
if [ -z "$DEC_HITS" ]; then
  printf "  ${ECHO_PASS}✓${ECHO_RESET} nokta-ondalıklı ₺: 0 ihlal\n"
else
  printf "  ${ECHO_FAIL}✗${ECHO_RESET} nokta-ondalıklı ₺: $DEC_N ihlal\n"
  printf '%s\n%s\n' "$PY_HITS" "$JS_HITS" | grep '.' | sed 's/^/      /'
  FAIL=$((FAIL + 1))
fi

# ── Kategori 2: Çıplak XU100/XU030 (BIST100/BIST30 çevrilmemiş) ─────────
# Bilinen regresyon deseni: kendine-eşleyen dict ("XU100:'XU100'") veya
# kullanıcıya doğrudan gösterilen metin ("vs XU030", ">XU030<", "XU030 ve").
echo ""
echo "2/4 Çıplak XU100/XU030 (BIST100/BIST30 çevrilmemiş)..."
XU_HITS=$(count_matches "XU100:[ ]?'XU100'|XU030:[ ]?'XU030'|vs XU0?[13]0|>XU0?[13]0<|XU030 (ve|/) XU100|XU030 / XU100" $TEMPLATE_FILES app.py)
if [ -z "$XU_HITS" ]; then
  printf "  ${ECHO_PASS}✓${ECHO_RESET} çıplak XU100/XU030: 0 ihlal\n"
else
  N=$(echo "$XU_HITS" | grep -c '.')
  printf "  ${ECHO_FAIL}✗${ECHO_RESET} çıplak XU100/XU030: $N ihlal\n"
  echo "$XU_HITS" | sed 's/^/      /'
  FAIL=$((FAIL + 1))
fi

# ── Kategori 3: "TL" para birimi yazımı (₺ sembolü yerine) ──────────────
# Sadece kullanıcıya görünür metin risklidir — kod yorumları/AI prompt
# talimatları ("1.234,56 TL yaz" gibi) hariç.
echo ""
echo "3/4 \"TL\" para birimi yazımı (₺ yerine)..."
TL_HITS=$(count_matches '[0-9][ ]?TL\b' $TEMPLATE_FILES | grep -vE '^\s*#|//' || true)
if [ -z "$TL_HITS" ]; then
  printf "  ${ECHO_PASS}✓${ECHO_RESET} \"TL\" yazımı: 0 ihlal\n"
else
  N=$(echo "$TL_HITS" | grep -c '.')
  printf "  ${ECHO_FAIL}✗${ECHO_RESET} \"TL\" yazımı: $N ihlal\n"
  echo "$TL_HITS" | sed 's/^/      /'
  FAIL=$((FAIL + 1))
fi

# ── Kategori 4 (UYARI — bloklamaz): tokens.css kanonik hex literal drift ─
# --bp-volume/--bp-premium gibi tokenlar var olduğu halde ham hex kullanımı.
# Toplu dönüşüm görsel regresyon riski taşır → backlog, sadece raporlanır.
echo ""
echo "4/4 [UYARI] Kanonik token hex-literal drift (--bp-volume #ffc850, --bp-premium #a855f7)..."
HEX_HITS=$(count_matches '#ffc850|#a855f7' $TEMPLATE_FILES app.py | grep -v 'tokens.css' || true)
if [ -z "$HEX_HITS" ]; then
  printf "  ${ECHO_PASS}✓${ECHO_RESET} token hex-literal: 0 occurrence\n"
else
  N=$(echo "$HEX_HITS" | grep -c '.')
  printf "  ${ECHO_WARN}⚠${ECHO_RESET} token hex-literal: $N occurrence (backlog — bloklamıyor)\n"
fi

echo ""
if [ "$FAIL" = "0" ]; then
  printf "${ECHO_PASS}✅ format-lint: bloklayıcı ihlal yok.${ECHO_RESET}\n"
  exit 0
else
  printf "${ECHO_FAIL}❌ format-lint: $FAIL kategori ihlal içeriyor — düzelt.${ECHO_RESET}\n"
  exit 1
fi
