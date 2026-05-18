#!/bin/bash
# /root/bist30/smoke_test.sh — Restart sonrası pre-flight check
# Kullanım: bash /root/bist30/smoke_test.sh
# Critical sayfalarda JS error / data load / temel render kontrolü

set -e
cd /root/bist30

# 1) Service alive — /api/health curl (Bulgu 2: systemctl is-active ExecStartPost
#    bağlamında 'activating' state'inde false negative veriyordu → restart loop besliyor)
if ! curl -sf -m 5 http://localhost:8003/api/health -o /dev/null; then
  echo "❌ FAIL: /api/health unreachable"
  exit 1
fi

# 2) API endpoints respond
for ep in /api/data /api/macro /api/chart /api/chart/XU100; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8003${ep}")
  if [ "$status" != "200" ]; then
    echo "❌ FAIL: ${ep} returned ${status}"
    exit 1
  fi
done

# 3) /api/data has stocks (not empty, not loading)
loading=$(curl -s 'http://localhost:8003/api/data' | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("loading"))' 2>/dev/null || echo error)
count=$(curl -s 'http://localhost:8003/api/data' | python3 -c 'import json,sys;d=json.load(sys.stdin);print(len(d.get("stocks",[])))' 2>/dev/null || echo 0)
if [ "$loading" = "True" ]; then
  echo "⚠️  WARN: /api/data still loading (warmup may not be done yet)"
fi
if [ "$count" -lt 100 ]; then
  echo "❌ FAIL: /api/data only ${count} stocks (expected 100+)"
  exit 1
fi

# 4) Chart endpoints scale-sane (XU100 must be > 5000)
xu100_price=$(curl -s 'http://localhost:8003/api/chart/XU100' | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("chart",{}).get("summary",{}).get("price",0))' 2>/dev/null || echo 0)
if python3 -c "import sys;sys.exit(0 if float('${xu100_price}') >= 5000 else 1)" 2>/dev/null; then
  : # OK
else
  echo "❌ FAIL: XU100 price ${xu100_price} (scale glitch suspected)"
  exit 1
fi

# 5) HTML pages render without 500
for page in "/" "/hisse/THYAO" "/eth" "/sektor-harita" "/portfolio" "/sinyal-performans" "/blog" "/profil"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8003${page}")
  if [ "$status" != "200" ] && [ "$status" != "400" ]; then  # /profil without token returns 400, OK
    echo "❌ FAIL: ${page} returned ${status}"
    exit 1
  fi
done

# 6) JS syntax check — apostrophe + null reference patterns in templates
SYNTAX_BUGS=$(grep -rE "'\w+'\w+" /root/bist30/templates/*.html 2>/dev/null | grep -E "(Backtest'te|sinyal'in|hisse'nin)" | grep -v ".bak." | wc -l)
if [ "$SYNTAX_BUGS" -gt 0 ]; then
  echo "❌ FAIL: Turkish apostrophe in JS strings detected (${SYNTAX_BUGS} occurrences)"
  grep -rnE "'\w+'\w+" /root/bist30/templates/*.html | grep -E "(Backtest'te|sinyal'in|hisse'nin)" | grep -v ".bak." | head -5
  exit 1
fi

echo "✅ All smoke checks passed (${count} stocks, XU100=${xu100_price})"
exit 0
