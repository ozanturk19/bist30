#!/bin/bash
# Phase 3 #2 B Integration Test — Pzt cutover pre-flight
# 5 modül: api_stale + UptimeRobot + Sentry + health extras + daemon guard
# Çalıştır: bash tests/phase3-2b-integration-test.sh
# Çıktı: GO / NO-GO + modül bazlı özet

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0
declare -a RESULTS=()

pass_module() { echo "  PASS: $1"; PASS=$((PASS+1)); RESULTS+=("PASS | $1"); }
fail_module() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); RESULTS+=("FAIL | $1"); }
divider() { echo ""; echo "─────────────────────────────────────────"; }

echo "╔══════════════════════════════════════════╗"
echo "║  Phase 3 #2 B — Integration Test Suite  ║"
echo "║  Pzt 30.06 cutover pre-flight            ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Paket 1: api_stale Alert ─────────────────────────────────────────────────
divider
echo "[Paket 1] api_stale Alert (test_alerts.py)"
if python3 -m pytest "$REPO_ROOT/tests/test_alerts.py" -q --tb=short 2>&1; then
    pass_module "Paket 1 — api_stale Alert"
else
    fail_module "Paket 1 — api_stale Alert"
fi

# ── Paket 2: UptimeRobot Forwarder ───────────────────────────────────────────
divider
echo "[Paket 2] UptimeRobot Forwarder (test_setup_uptimerobot.sh)"
if bash "$REPO_ROOT/tests/test_setup_uptimerobot.sh" 2>&1; then
    pass_module "Paket 2 — UptimeRobot Forwarder"
else
    fail_module "Paket 2 — UptimeRobot Forwarder"
fi

# ── Paket 3: Sentry Forwarder ─────────────────────────────────────────────────
divider
echo "[Paket 3] Sentry Forwarder (test_sentry_forwarder.py)"
if python3 -m pytest "$REPO_ROOT/tests/test_sentry_forwarder.py" -q --tb=short 2>&1; then
    pass_module "Paket 3 — Sentry Forwarder"
else
    fail_module "Paket 3 — Sentry Forwarder"
fi

# ── Paket 4: Health Endpoint Extras ───────────────────────────────────────────
divider
echo "[Paket 4] Health Endpoint Extras (test_health_extras.py)"
if python3 -m pytest "$REPO_ROOT/tests/test_health_extras.py" -q --tb=short 2>&1; then
    pass_module "Paket 4 — Health Endpoint Extras"
else
    fail_module "Paket 4 — Health Endpoint Extras"
fi

# ── Paket 5: Daemon Corruption Guard ─────────────────────────────────────────
divider
echo "[Paket 5] Daemon Corruption Guard (test_guards.py)"
if python3 -m pytest "$REPO_ROOT/tests/test_guards.py" -q --tb=short 2>&1; then
    pass_module "Paket 5 — Daemon Corruption Guard"
else
    fail_module "Paket 5 — Daemon Corruption Guard"
fi

# ── Final Özet ────────────────────────────────────────────────────────────────
divider
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  SONUÇ ÖZETİ                             ║"
echo "╠══════════════════════════════════════════╣"
for r in "${RESULTS[@]}"; do
    printf "║  %-40s║\n" "$r"
done
echo "╠══════════════════════════════════════════╣"
printf "║  Toplam: %d PASS / %d FAIL%-15s║\n" "$PASS" "$FAIL" ""
echo "╠══════════════════════════════════════════╣"
if [[ $FAIL -eq 0 ]]; then
    echo "║  🟢 GO — Pzt cutover için hazır          ║"
else
    echo "║  🔴 NO-GO — $FAIL modül fail, düzelt!     ║"
fi
echo "╚══════════════════════════════════════════╝"
echo ""

[[ $FAIL -eq 0 ]]
