#!/bin/bash
# Güvenli restart — restart sonrası smoke test çalıştırır, fail olursa rollback uyarısı
set -e
echo "🔄 bist30 restart başlıyor..."
systemctl restart bist30
echo "⏳ Warmup bekleniyor (45s)..."
sleep 45
echo "🔍 Smoke test çalıştırılıyor..."
if bash /root/bist30/smoke_test.sh; then
  echo "✅ Restart başarılı, site sağlıklı."
  exit 0
else
  echo "❌ Smoke test FAIL — site bozuk! Logları kontrol et:"
  echo "   journalctl -u bist30 -n 50 --no-pager"
  echo "   tail -50 /root/bist30/logs/*.log 2>/dev/null"
  exit 1
fi
