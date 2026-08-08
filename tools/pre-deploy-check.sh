#!/bin/bash
# scripts/pre-deploy-check.sh
# CPO-359 Pre-Deploy Tier 0 — Otomatik audit önceki deploy.
# Adımlar:
# 1. Jinja parse
# 2. KALICI_KURALLAR audit
# 3. Python compile
# 4. format-lint (CPO-1180 K6)
# 5. CSS token guard (CPO-1349 §1 madde-1)
# Exit 0: tüm geçer / Exit 1: en az 1 fail
#
# Kullanım: ./scripts/pre-deploy-check.sh

set -e
FAIL=0
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Pre-Deploy Check (CPO-359 Tier 0) ==="
echo ""

# 1. Jinja parse
echo "1/5 Jinja parse..."
if python3 "$(dirname "$0")/_predeploy_jinja_check.py"; then
  echo "  ✓ Jinja parse OK"
else
  echo "  ✗ Jinja parse FAIL"
  FAIL=$((FAIL + 1))
fi

# 2. Python compile
echo ""
echo "2/5 Python compile (app.py)..."
if python3 -c "import ast;ast.parse(open('app.py').read())" 2>/dev/null; then
  echo "  ✓ app.py compile OK"
else
  echo "  ✗ app.py compile FAIL"
  FAIL=$((FAIL + 1))
fi

# 3. KALICI_KURALLAR audit
echo ""
echo "3/5 KALICI_KURALLAR audit..."
if ./tests/audit/kalici-kurallar-check.sh templates/hisse.html > /dev/null 2>&1; then
  echo "  ✓ KK 11/11 PASS"
else
  echo "  ✗ KK ihlali var. Detay için tests/audit/kalici-kurallar-check.sh çalıştır."
  FAIL=$((FAIL + 1))
fi

# 4. format-lint
echo ""
echo "4/5 format-lint (CPO-1180 K6)..."
if ./tools/format-lint.sh > /dev/null 2>&1; then
  echo "  ✓ format-lint PASS"
else
  echo "  ✗ format-lint ihlal var. Detay için ./tools/format-lint.sh çalıştır."
  FAIL=$((FAIL + 1))
fi

# 5. CSS token guard (CPO-1349 §1 madde-1)
# 08.08.2026: tokens.css yorumu icindeki kaza yorum-kapatma dizisi ikinci :root
# blogunun TAMAMINI dusurdu; 10/10 olcek token-i canlida TANIMSIZDI. Dosya HTTP 200
# donuyordu, boyutu dogruydu, grep iceride buluyordu. Elle calistirilan bir arac bir
# sonraki kazada yok hukmundedir -- kapiya baglandi.
echo ""
echo "5/5 CSS token guard (CPO-1349)..."
if python3 tools/css-token-guard.py static/css/*.css > /dev/null 2>&1; then
  echo "  ✓ CSS token guard PASS"
else
  echo "  ✗ CSS token guard FAIL. Detay: python3 tools/css-token-guard.py static/css/*.css"
  FAIL=$((FAIL + 1))
fi

echo ""
if [ "$FAIL" = "0" ]; then
  echo "✅ Pre-deploy TÜM CHECK GEÇTİ — deploy izinli."
  exit 0
else
  echo "❌ $FAIL fail tespit edildi — deploy reddedildi."
  exit 1
fi
