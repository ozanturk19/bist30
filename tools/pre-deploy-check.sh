#!/bin/bash
# scripts/pre-deploy-check.sh
# CPO-359 Pre-Deploy Tier 0 — Otomatik audit önceki deploy.
# Adımlar:
# 1. Jinja parse
# 2. KALICI_KURALLAR audit
# 3. Python compile
# 4. format-lint (CPO-1180 K6)
# 5. CSS token guard (CPO-1349 §1 madde-1)
# 6. style-guard (T1.7 — K-A/K-B/K-C/K-D)
# 7. lint_scope ratchet (T9.4 — bkz. asagidaki not)
# 8. node-syntax-check (DEV2-T-MOBOVF-1 / CPO-DEV2-011 onerisi — bkz. asagidaki not)
# Exit 0: tüm geçer / Exit 1: en az 1 fail
#
# Kullanım: ./scripts/pre-deploy-check.sh

set -e
FAIL=0
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Pre-Deploy Check (CPO-359 Tier 0) ==="
echo ""

# 1. Jinja parse
echo "1/8 Jinja parse..."
if python3 "$(dirname "$0")/_predeploy_jinja_check.py"; then
  echo "  ✓ Jinja parse OK"
else
  echo "  ✗ Jinja parse FAIL"
  FAIL=$((FAIL + 1))
fi

# 2. Python compile
echo ""
echo "2/8 Python compile (app.py)..."
if python3 -c "import ast;ast.parse(open('app.py').read())" 2>/dev/null; then
  echo "  ✓ app.py compile OK"
else
  echo "  ✗ app.py compile FAIL"
  FAIL=$((FAIL + 1))
fi

# 3. KALICI_KURALLAR audit
echo ""
echo "3/8 KALICI_KURALLAR audit..."
if ./tests/audit/kalici-kurallar-check.sh templates/hisse.html > /dev/null 2>&1; then
  echo "  ✓ KK 11/11 PASS"
else
  echo "  ✗ KK ihlali var. Detay için tests/audit/kalici-kurallar-check.sh çalıştır."
  FAIL=$((FAIL + 1))
fi

# 4. format-lint
echo ""
echo "4/8 format-lint (CPO-1180 K6)..."
if ./tools/format-lint.sh > /dev/null 2>&1; then
  echo "  ✓ format-lint PASS"
else
  echo "  ✗ format-lint ihlal var. Detay için ./tools/format-lint.sh çalıştır."
  FAIL=$((FAIL + 1))
fi

# 5. CSS token guard (CPO-1349 §1 madde-1)
# 08.08.2026: tokens.css yorumu icindeki kaza yorum-kapatma dizisi ikinci :root
# blogunun TAMAMINI dusurdu; 10/10 olcek token-i canlida TANIMSIZDI. Dosya HTTP 200
# donuyordu, boyutu dogruydu, grep iceride buluyordu. Elle calistirilan bir arac bir
# sonraki kazada yok hukmundedir -- kapiya baglandi.
echo ""
echo "5/8 CSS token guard (CPO-1349)..."
if python3 tools/css-token-guard.py static/css/*.css > /dev/null 2>&1; then
  echo "  ✓ CSS token guard PASS"
else
  echo "  ✗ CSS token guard FAIL. Detay: python3 tools/css-token-guard.py static/css/*.css"
  FAIL=$((FAIL + 1))
fi

echo ""
# 6. style-guard (T1.7) — css-token-guard YALNIZ static/css/*.css (2 dosya) bakiyor;
# sablonlarin icindeki ~2300 var(--bp-*) kullanimi HICBIR kapida denetlenmiyordu.
# K-A tanimsiz var() BLOKLAYICI (taban 0), K-B/K-C/K-D ratchet (yalniz dusebilir).
echo "6/8 style-guard (T1.7: sablon ici var()/ham hex/yerel :root/bos catch ratchet)..."
if python3 tools/style-guard.py > /dev/null 2>&1; then
  echo "  ✓ style-guard PASS"
else
  echo "  ✗ style-guard ihlal var. Detay için: python3 tools/style-guard.py --verbose"
  FAIL=1
fi

# 7. lint_scope ratchet (T9.4) — tools/lint_scope.py --check ZATEN YAZILMISTI
# (T1.7, 08.08.2026) ama HICBIR gate script'i cagirmiyordu; format-lint.sh yalniz
# bayraksiz modu (sablon listesi turetmek icin) kullaniyordu. Sonuc: sablon sayisi
# 27'den 26'ya dustugunde (abd_tarama.html kaldirildi, f9e4ac8) ratchet KIRIK
# duruma gecti ama hicbir deploy bunu raporlamadi — "YAZILMIS ama BAGLANMAMIS"
# sinifinin kendisi, 8f6006f'in kapattigi iki guard'la AYNI hastalik. Bagliyoruz.
echo ""
echo "7/8 lint_scope ratchet (T9.4: sablon sayisi daralma dedektoru)..."
if python3 tools/lint_scope.py --check > /dev/null 2>&1; then
  echo "  ✓ lint_scope PASS"
else
  echo "  ✗ lint_scope kapsam daraldi/dedektor kirik. Detay için: python3 tools/lint_scope.py --check"
  FAIL=$((FAIL + 1))
fi

# 8. node-syntax-check (DEV2-T-MOBOVF-1) -- T7.4'de (8a00386) hisse.html'deki
# tek-tirnak template-literal hatasi TUM inline <script> bloklarini kirdi
# (SyntaxError), ama Jinja parse / python compile / format-lint / CSS token
# guard / style-guard / lint_scope 7 katinin HICBIRI bunu yakalamadi -- hepsi
# Jinja/Python katmanina bakiyor, saf JS sozdizimine degil. Deploy-sonrasi
# canli konsolda yakalanip duzeltilmisti. Bu adim AYNI SINIF hatayi deploy-
# ONCESI yakalar (Jinja {{ }}/{% %} soyulup node --check ile dogrulanir,
# 31/31 mevcut sablonda 0 yanlis-pozitif dogrulanmistir).
echo ""
echo "8/8 node-syntax-check (DEV2-T-MOBOVF-1: sablon-ici JS sozdizimi)..."
if python3 tools/node-syntax-check.py > /dev/null 2>&1; then
  echo "  ✓ node-syntax-check PASS"
else
  echo "  ✗ node-syntax-check FAIL. Detay için: python3 tools/node-syntax-check.py"
  FAIL=$((FAIL + 1))
fi

echo ""
if [ "$FAIL" = "0" ]; then
  echo "✅ Pre-deploy TÜM CHECK GEÇTİ — deploy izinli."
  exit 0
else
  echo "❌ $FAIL fail tespit edildi — deploy reddedildi."
  exit 1
fi
