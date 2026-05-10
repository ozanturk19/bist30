#!/bin/bash
# /root/bist30/predeploy_lint.sh
# Önlem #4: Template'lerde tehlikeli pattern'leri yakalar.
# Restart öncesi çalıştır: bash /root/bist30/predeploy_lint.sh
# Fail dönerse → restart yapma.

set -e
TEMPLATES=/root/bist30/templates
ERRORS=0

echo "🔍 Pre-deploy lint başladı..."

# 1) Türkçe apostrof JS string'inde (Backtest'te, sinyal'in vs)
APOST=$(grep -rnE "^[[:space:]]*[a-zA-Z0-9_]+[^/]*'[^']*[a-zçğıöşü]'[a-zçğıöşü]" "$TEMPLATES" 2>/dev/null \
  | grep -v ".bak." \
  | grep -vE "^[^:]+:[0-9]+:[[:space:]]*//" \
  | grep -vE "^[^:]+:[0-9]+:[[:space:]]*\*" \
  | grep -E "= '|return '|innerHTML = '|html \+= '" \
  | grep -v "// " \
  | grep -v "/\* " \
  | head -10)
if [ -n "$APOST" ]; then
  echo "❌ Türkçe apostrof JS string'inde:"
  echo "$APOST"
  ERRORS=$((ERRORS+1))
fi

# 2) getElementById(...) null safety olmadan property access
# Pattern: getElementById('id').something  veya .textContent =, .style. =
NULLPTR=$(grep -rnE "getElementById\\([^)]+\\)\\.(textContent|innerHTML|style|classList|value)" "$TEMPLATES" 2>/dev/null \
  | grep -v ".bak." \
  | grep -vE "if\\s*\\(.*getElementById" \
  | head -20)
if [ -n "$NULLPTR" ]; then
  echo "⚠️  getElementById direkt property access (null guard önerilir):"
  echo "$NULLPTR" | head -5
  echo "    (Bunlar kritik değil, sadece warning — null guard ekleyin)"
fi

# 3) Render-blocking script (defer/async olmadan body sonrası büyük lib)
BLOCKING=$(grep -rE "<script src=\"[^\"]*\\.min\\.js\"></script>" "$TEMPLATES" 2>/dev/null \
  | grep -v ".bak." \
  | grep -vE "defer|async|bp-search\\.js|gtag\\.js" \
  | head -5)
if [ -n "$BLOCKING" ]; then
  echo "ℹ️  Render-blocking lib script (ekleyin defer/async eğer mümkünse):"
  echo "$BLOCKING" | head -3
fi

# 4) Cache busting check — bp-search.js?v= yok mu?
NO_VERSION=$(grep -rE 'bp-search\.js"' "$TEMPLATES" 2>/dev/null \
  | grep -v ".bak." \
  | grep -v 'bp-search.js?v=' \
  | head -5)
if [ -n "$NO_VERSION" ]; then
  echo "❌ bp-search.js cache buster eksik:"
  echo "$NO_VERSION" | head -3
  ERRORS=$((ERRORS+1))
fi

# 5) Python syntax check on app.py
if ! /root/bist30/venv/bin/python -c "import ast; ast.parse(open('/root/bist30/app.py').read())" 2>/dev/null; then
  echo "❌ app.py SYNTAX ERROR!"
  /root/bist30/venv/bin/python -c "import ast; ast.parse(open('/root/bist30/app.py').read())"
  ERRORS=$((ERRORS+1))
fi

if [ "$ERRORS" -gt 0 ]; then
  echo ""
  echo "❌ Pre-deploy lint FAILED ($ERRORS critical issue) — restart YAPILMAMALI"
  exit 1
fi

echo ""
echo "✅ Pre-deploy lint passed"
exit 0
