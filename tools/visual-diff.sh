#!/bin/bash
# tools/visual-diff.sh
# ImageMagick compare ile baseline vs current PNG diff
# CPO-359 Tier 0 — visual regression check
#
# Kurulum: brew install imagemagick (macOS) veya apt install imagemagick (Linux)
# Kullanım: ./tools/visual-diff.sh [--threshold 0.01]
#   Threshold: pixel diff oranı (default 1% = 0.01)
#
# Exit 0: tüm dosyalar threshold altında
# Exit 1: en az 1 dosya threshold üstünde

set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASELINE="$PROJECT_ROOT/tests/visual/baseline"
CURRENT="$PROJECT_ROOT/tests/visual/current"
DIFF_DIR="$PROJECT_ROOT/tests/visual/diff"
THRESHOLD="${1:-0.01}"
[ "${1:0:11}" = "--threshold" ] && THRESHOLD="${2:-0.01}"

if ! command -v compare >/dev/null 2>&1; then
  echo "✗ ImageMagick 'compare' bulunamadı. Kurulum: brew install imagemagick"
  exit 2
fi

if [ ! -d "$BASELINE" ]; then
  echo "✗ Baseline dizini yok: $BASELINE"
  echo "  İlk önce baseline oluştur: node tools/visual-test.js --update-baseline"
  exit 2
fi

mkdir -p "$DIFF_DIR"

FAIL=0
TOTAL=0

for baseline_file in "$BASELINE"/*.png; do
  [ -f "$baseline_file" ] || continue
  TOTAL=$((TOTAL + 1))
  fname=$(basename "$baseline_file")
  current_file="$CURRENT/$fname"
  diff_file="$DIFF_DIR/$fname"

  if [ ! -f "$current_file" ]; then
    echo "✗ Eksik: $fname (current PNG yok)"
    FAIL=$((FAIL + 1))
    continue
  fi

  # AE: absolute error pixel count. Total pixels for ratio:
  pixels=$(identify -format "%[fx:w*h]" "$baseline_file" 2>/dev/null || echo 1)
  ae=$(compare -metric AE -fuzz 5% "$baseline_file" "$current_file" "$diff_file" 2>&1 || true)
  # ae may include garbage on full match
  ae_num=$(echo "$ae" | grep -oE '^[0-9]+' | head -1)
  ae_num=${ae_num:-0}
  ratio=$(awk "BEGIN{printf \"%.4f\", $ae_num / $pixels}")

  if awk "BEGIN{exit !($ratio > $THRESHOLD)}"; then
    echo "✗ $fname: diff $ratio > threshold $THRESHOLD (ae=$ae_num / $pixels)"
    FAIL=$((FAIL + 1))
  else
    echo "✓ $fname: diff $ratio (ae=$ae_num)"
    rm -f "$diff_file"  # eşleşen diff PNG'leri sil
  fi
done

echo ""
if [ "$FAIL" = "0" ]; then
  echo "✅ Visual regression GEÇTİ — $TOTAL dosya threshold altında ($THRESHOLD)."
  exit 0
else
  echo "❌ $FAIL/$TOTAL dosya threshold üstü diff. Bakın: $DIFF_DIR"
  exit 1
fi
