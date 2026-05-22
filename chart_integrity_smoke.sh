#!/bin/bash
# chart_integrity_smoke.sh — SPEC-008 L3
#
# Deploy sonrası TÜM hisse chart endpoint'lerini integrity açısından tarar.
# Her hisse için kontrol:
#   - HTTP 200
#   - integrity_error YOK (SPEC-008 L1 guard tetiklenmemiş)
#   - chart null/loading değil (kalıcı boş chart yok)
#
# Kabul kriteri: issues=0. Bir tane bile sorun → exit 1 (deploy verify FAIL).
#
# Kullanım: ./chart_integrity_smoke.sh [BASE_URL]
#   BASE_URL varsayılan http://localhost:8003

set -u
BASE="${1:-http://localhost:8003}"

TICKERS=$(curl -sf -m 25 "$BASE/api/data" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(' '.join(s['ticker'] for s in d.get('stocks', [])
                if s.get('ticker') not in ('XU030', 'XU100')))")

if [ -z "$TICKERS" ]; then
    echo "HATA: /api/data ticker listesi alınamadı"
    exit 2
fi

CHECKED=0; ISSUES=0; INTEG=0; LOADING=0; HTTP_FAIL=0

for T in $TICKERS; do
    CHECKED=$((CHECKED + 1))
    RESP=$(curl -sf -m 20 -w '\n%{http_code}' "$BASE/api/hisse/$T/chart" 2>/dev/null)
    CODE=$(printf '%s\n' "$RESP" | tail -n1)
    BODY=$(printf '%s\n' "$RESP" | sed '$d')

    if [ "$CODE" != "200" ]; then
        ISSUES=$((ISSUES + 1)); HTTP_FAIL=$((HTTP_FAIL + 1))
        echo "  $T — HTTP=$CODE"
        continue
    fi

    VERDICT=$(printf '%s' "$BODY" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print('PARSE'); sys.exit(0)
if d.get('integrity_error'):
    print('INTEG:' + str(d['integrity_error'])[:60])
elif d.get('loading') or not d.get('chart'):
    print('LOADING')
else:
    print('OK')")

    case "$VERDICT" in
        OK)      ;;
        INTEG*)  ISSUES=$((ISSUES + 1)); INTEG=$((INTEG + 1));   echo "  $T — $VERDICT" ;;
        LOADING) ISSUES=$((ISSUES + 1)); LOADING=$((LOADING + 1)); echo "  $T — loading/empty chart" ;;
        *)       ISSUES=$((ISSUES + 1)); echo "  $T — JSON parse hatası" ;;
    esac
done

echo "chart-integrity-smoke checked=$CHECKED issues=$ISSUES (integrity=$INTEG loading=$LOADING http_fail=$HTTP_FAIL)"
if [ "$ISSUES" -eq 0 ]; then
    echo "PASS"
    exit 0
else
    echo "FAIL"
    exit 1
fi
