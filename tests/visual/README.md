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

## Computed-Style Baseline (interaktif state, pixel-diff kapsamı dışı)

`tools/visual-test.js` PAGES listesi statik sayfa yükleri çeker — chip/preset gibi
`.active` state'ler tıklama gerektirdiği için 60 PNG setine dahil değil. Bu tür
kurallar burada file:line + beklenen değerle kayıt altına alınır (CPO-1171 #3).

| Selector | Kaynak | Beklenen (computed) | Not |
|---|---|---|---|
| `.preset-chip[data-preset="PREMIUM"].active` | `templates/index.html:579-582` | `border-color`/`color` → `var(--bp-volume)` = `#ffc850` (`static/css/tokens.css:49`) | S-UI-3 (CPO-1169), `#ffd700` literalinden değiştirildi, commit `d7153f3`. Kardeş kural `WATCH` preset chip (`index.html:584-588`, literal `#b8c3ff`) aynı desenle canlı doğrulandı. |

Bir sonraki VR turunda: PREMIUM preset chip'e tıkla, `getComputedStyle` ile
`border-color`/`color` değerini `#ffc850`'ye eşitliğini doğrula, pixel kanıtını
bu tabloya ekle.
