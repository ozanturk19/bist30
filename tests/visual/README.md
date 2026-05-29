# Visual Regression Test (CPO-359 Tier 0)

## Klasörler
- `baseline/` — Onaylanmış referans PNG'ler (git'e commit edilir)
- `current/` — Son test çalıştırması PNG'leri (gitignore)
- `diff/` — Threshold üstü diff PNG'ler (gitignore, sadece FAIL durumunda)

## Kurulum
```bash
cd /Users/mac/Bist\ ve\ BTC/Bist30
npm install -D playwright @playwright/test
npx playwright install chromium
brew install imagemagick  # macOS
# veya
sudo apt install imagemagick  # Linux
```

## Workflow
```bash
# 1. İlk kez: baseline oluştur (LIVE sitesi sağlam iken)
node tools/visual-test.js --update-baseline

# 2. Her commit/deploy öncesi: visual test çalıştır
node tools/visual-test.js
./tools/visual-diff.sh --threshold 0.01

# 3. Kasıtlı değişiklik sonrası: baseline güncelle
node tools/visual-test.js --update-baseline
git add tests/visual/baseline
git commit -m "chore(visual): baseline update post Faz X"
```

## Pre-Deploy Pipeline (tam akış)
```bash
./tools/pre-deploy-check.sh   # Jinja + Python + KK audit
node tools/visual-test.js     # 60 PNG screenshot
./tools/visual-diff.sh        # ImageMagick compare
# Hepsi PASS → ssh deploy
```

## CPO-359 Standardı
- Tier 0 (DEV pre-deploy): Tüm scriptler PASS şart
- Tier 2 (CPO verify): visual-diff.sh ile bağımsız doğrulama
- Tier 4 (Ozan visual): Manuel screenshot (her major milestone)
