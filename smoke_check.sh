#!/bin/bash
# Faz 12 P2.5 — Pre-deploy gate (local syntax + import + test suite)
# Usage: ./smoke_check.sh
# Called by .githooks/pre-push on every git push.
# Bypass (acil durum, CPO onayı şart): git push --no-verify

set -euo pipefail
REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_DIR"

PASS=0; FAIL=0

run_check() {
    local name="$1"; local cmd="$2"
    printf "  %-36s" "$name"
    if eval "$cmd" >/dev/null 2>&1; then
        echo "✅"
        PASS=$((PASS + 1))
    else
        echo "❌ FAIL"
        eval "$cmd" 2>&1 | head -5 | sed 's/^/    /'
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "── P2.5 Pre-deploy Gate ──────────────────────────"
run_check "syntax: app.py"        "python3 -m py_compile app.py"
run_check "syntax: alerting.py"   "python3 -m py_compile alerting.py"
run_check "import: DQV+alerting"  "python3 -c '
from business_rules   import validate_stocks_list
from cross_consistency import validate_stocks_cross_consistency
from anomaly           import validate_anomalies_list
from schema_validator  import validate_api_data, validate_api_macro, validate_api_hisse_chart
from email_qa          import validate_email_pre_send
from alerting          import emit_alert
'"
run_check "tests: DQV suite"      "python3 -m pytest tests/ -x -q 2>&1 | grep -E 'passed|failed|error'"

echo "──────────────────────────────────────────────────"
echo "  ${PASS} passed, ${FAIL} failed"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo "Gate: PASS ✅"
    exit 0
else
    echo "Gate: FAIL ❌"
    exit 1
fi
