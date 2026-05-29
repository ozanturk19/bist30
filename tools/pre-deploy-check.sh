#!/bin/bash
# scripts/pre-deploy-check.sh
# CPO-359 Pre-Deploy Tier 0 — Otomatik audit önceki deploy.
# Adımlar:
# 1. Jinja parse
# 2. KALICI_KURALLAR audit
# 3. Python compile
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
echo "1/3 Jinja parse..."
if python3 -c "
import jinja2,sys
e=jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
ok=True
for f in ['hisse.html','index.html','heatmap.html','tarama.html','gundem.html']:
  try: e.get_template(f); print(' ✓', f)
  except Exception as x: print(' ✗', f, x); ok=False
sys.exit(0 if ok else 1)
"; then
  echo "  ✓ Jinja parse OK"
else
  echo "  ✗ Jinja parse FAIL"
  FAIL=$((FAIL + 1))
fi

# 2. Python compile
echo ""
echo "2/3 Python compile (app.py)..."
if python3 -c "import ast;ast.parse(open('app.py').read())" 2>/dev/null; then
  echo "  ✓ app.py compile OK"
else
  echo "  ✗ app.py compile FAIL"
  FAIL=$((FAIL + 1))
fi

# 3. KALICI_KURALLAR audit
echo ""
echo "3/3 KALICI_KURALLAR audit..."
if ./tests/audit/kalici-kurallar-check.sh templates/hisse.html > /dev/null 2>&1; then
  echo "  ✓ KK 11/11 PASS"
else
  echo "  ✗ KK ihlali var. Detay için tests/audit/kalici-kurallar-check.sh çalıştır."
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
