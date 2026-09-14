#!/bin/bash
# Güvenli restart — restart sonrası smoke test çalıştırır, fail olursa rollback uyarısı
set -e
cd /root/bist30

echo "🔍 git pull kontrolü..."
git fetch origin main --quiet
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git rev-parse origin/main)
if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  echo "⬇️  Yerel HEAD ($LOCAL_SHA) origin/main'den ($REMOTE_SHA) geride — pull ediliyor..."
  git pull --ff-only origin main
else
  echo "✅ Yerel HEAD zaten origin/main ile eşit ($LOCAL_SHA)."
fi

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
