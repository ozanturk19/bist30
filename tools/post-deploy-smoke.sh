#!/bin/bash
# tools/post-deploy-smoke.sh
# Pzt 30 Haz G24 bundle post-deploy smoke verify
# G24 subprocess isolation: live prices, chart, fundamentals, global prices
# Kullanım: ./tools/post-deploy-smoke.sh [HOST]
# Default host: http://localhost:8003 (prod VPS: http://135.181.206.109:8003)

set -euo pipefail

HOST="${1:-http://localhost:8003}"
FAIL=0
WARN=0
START=$(date +%s)

ok()   { echo "  ✓ $*"; }
fail() { echo "  ✗ FAIL: $*"; FAIL=$((FAIL+1)); }
warn() { echo "  ⚠ WARN: $*"; WARN=$((WARN+1)); }

echo "=== Post-Deploy Smoke — G24 Subprocess Bundle ==="
echo "Host: $HOST"
echo "$(date '+%Y-%m-%d %H:%M:%S TR')"
echo ""

# ── 1. Health ────────────────────────────────────────────────────────────────
echo "1/6 Health check..."
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$HOST/health" 2>/dev/null || echo "ERR")
if [ "$HTTP" = "200" ]; then
  ok "GET /health → 200"
else
  fail "GET /health → $HTTP (expected 200)"
fi

# ── 2. Ana sayfa yüklenme ─────────────────────────────────────────────────────
echo ""
echo "2/6 Ana sayfa (/) ..."
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$HOST/" 2>/dev/null || echo "ERR")
if [ "$HTTP" = "200" ]; then
  ok "GET / → 200"
else
  fail "GET / → $HTTP"
fi

# ── 3. Hisse sayfası (subprocess chart + fundamentals) ───────────────────────
echo ""
echo "3/6 Hisse sayfası THYAO (chart + fundamentals subprocess)..."
HISSE_OUT=$(curl -s --max-time 30 "$HOST/hisse/THYAO" 2>/dev/null || echo "CURL_ERR")
HTTP_HISSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$HOST/hisse/THYAO" 2>/dev/null || echo "ERR")
if [ "$HTTP_HISSE" = "200" ]; then
  ok "GET /hisse/THYAO → 200"
else
  fail "GET /hisse/THYAO → $HTTP_HISSE"
fi
# İçerik kontrolleri
if echo "$HISSE_OUT" | grep -q "chart-container\|chartData\|ohlcData" 2>/dev/null; then
  ok "Chart container/data mevcut"
else
  warn "Chart data bulunamadı (soğuk cache olabilir)"
fi
if echo "$HISSE_OUT" | grep -q "F/K\|piyasa-degeri\|fundamentals\|temel-gostergeler" 2>/dev/null; then
  ok "Fundamentals bölümü mevcut"
else
  warn "Fundamentals bölümü bulunamadı (subprocess timeout veya soğuk cache)"
fi

# ── 4. API live prices (subprocess fetch) ────────────────────────────────────
echo ""
echo "4/6 API /api/live-prices (subprocess live fetch)..."
LIVE_OUT=$(curl -s --max-time 30 "$HOST/api/live-prices" 2>/dev/null || echo "CURL_ERR")
LIVE_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$HOST/api/live-prices" 2>/dev/null || echo "ERR")
if [ "$LIVE_HTTP" = "200" ]; then
  ok "GET /api/live-prices → 200"
else
  fail "GET /api/live-prices → $LIVE_HTTP"
fi
if echo "$LIVE_OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)>0" 2>/dev/null; then
  COUNT=$(echo "$LIVE_OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo "?")
  ok "Live prices JSON: $COUNT sembol"
else
  warn "Live prices boş veya parse hatası (soğuk cache window normal)"
fi

# ── 5. XU030 chart API (subprocess fetch) ────────────────────────────────────
echo ""
echo "5/6 XU030 chart API (subprocess chart fetch)..."
XU030_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$HOST/api/chart/XU030" 2>/dev/null || echo "ERR")
if [ "$XU030_HTTP" = "200" ]; then
  ok "GET /api/chart/XU030 → 200"
elif [ "$XU030_HTTP" = "202" ] || [ "$XU030_HTTP" = "204" ]; then
  warn "GET /api/chart/XU030 → $XU030_HTTP (loading/cache miss, normal)"
else
  fail "GET /api/chart/XU030 → $XU030_HTTP"
fi

# ── 6. Global prices (subprocess fetch) ──────────────────────────────────────
echo ""
echo "6/6 Global prices API (subprocess global fetch)..."
GLOBAL_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$HOST/api/global-prices" 2>/dev/null || echo "ERR")
if [ "$GLOBAL_HTTP" = "200" ]; then
  ok "GET /api/global-prices → 200"
else
  warn "GET /api/global-prices → $GLOBAL_HTTP (soğuk cache olabilir)"
fi

# ── Özet ─────────────────────────────────────────────────────────────────────
END=$(date +%s)
ELAPSED=$((END - START))
echo ""
echo "──────────────────────────────────"
echo "Süre: ${ELAPSED}s"
if [ "$FAIL" = "0" ]; then
  echo "✅ Smoke PASS ($WARN uyarı) — G24 subprocess bundle deploy başarılı."
  echo "⚠️  Uyarılar soğuk cache (5-10dk cold window) nedeniyle olabilir. 10dk sonra tekrar çalıştır."
  exit 0
else
  echo "❌ $FAIL FAIL, $WARN WARN — deploy sonrası sorun var. Logları kontrol et:"
  echo "   ssh root@135.181.206.109 'journalctl -u bist30 -n 100'"
  exit 1
fi
