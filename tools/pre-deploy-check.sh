#!/bin/bash
# scripts/pre-deploy-check.sh
# CPO-359 Pre-Deploy Tier 0 — Otomatik audit önceki deploy.
# Adımlar (C-39a/b, 27.09: 82 -> 8): G1 Sözdizimi, G2 Renk/token, G3 Kabuk/asset,
# G4 Yayımlanan metin, G5 Sayı/biçim, G6 Etkileşim, G7 İstemci durumu,
# G8 Kullanıcı verisi.
# Exit 0: tüm geçer / Exit 1: en az 1 fail
#
# Kullanım: ./scripts/pre-deploy-check.sh

set -e
FAIL=0
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Pre-Deploy Check (CPO-359 Tier 0) ==="
echo ""

# -- C-39a (27.09): kapi 1-41 + kapi 84 (K-DR) 7 GRUP ADIMINA birlesti ---------
# Karar tablosu: ~/ops/plans/2026-09-23-denetim/kanit/gate_table.md. Kurallar
# (betikler) AYNEN kalir, koşucu yeniden yazilmadi; yalniz adim sayisi azaldi.
# Grup icinde her kural ayri kosar; biri kirmiziysa grup FAIL olur ve kuralin
# adi + ciktisinin sonu basilir (sessiz gecis yok -- enjeksiyon kaniti:
# ~/ops/plans/shots/C-39a/enjeksiyon.txt). Kaldirilan: 7 lint_scope (KALDIR).
# Tek grup kosmak: PREDEPLOY_GROUP=renk bash tools/pre-deploy-check.sh
# Grup girdisi: "etiket|komut" (komut alt kabukta calisir).
# C-39b (27.09): kapi 42-82 de gruplara tasindi (46 -> 8 adim; yeni G7 Istemci
# durumu). Gruplar PARALEL kosar (31,7 -> ~10 sn); cikti grup sirasiyla basilir.
# Her kuralin pozitif kontrolu etiketinde: python3 tools/<betik> --ref <sha>.
PD_OUT=$(mktemp -d); trap 'rm -rf "$PD_OUT"' EXIT
PD_N=0
gate_group() {
  local key="$1" name="$2"; shift 2
  if [ -n "${PREDEPLOY_GROUP:-}" ] && [ "$PREDEPLOY_GROUP" != "$key" ]; then return 0; fi
  PD_N=$((PD_N + 1))
  local f; f="$PD_OUT/$(printf '%02d' $PD_N)-$key"
  (
    bad=0
    echo ""
    echo "$name..."
    for item in "$@"; do
      label="${item%%|*}"; cmd="${item#*|}"
      if ! out=$(eval "$cmd" 2>&1); then
        echo "  ✗ $label KIRIK. Detay: $cmd"
        echo "$out" | tail -15 | sed 's/^/      /'
        bad=$((bad + 1))
      fi
    done
    if [ "$bad" = "0" ]; then echo "  ✓ $name: $# kural PASS"; else echo FAIL > "$f.fail"; fi
  ) > "$f.out" 2>&1 &
}

# KALICI_KURALLAR: pre-commit ile ayni liste (CPO-1584), senkron tutulmali.
KK_AUDIT_FILES="templates/hisse.html templates/karsilastir.html templates/ozet.html templates/sektor_harita.html templates/tarama.html templates/hisseler.html templates/index.html templates/portfolio.html templates/gundem.html templates/metodoloji.html templates/blog.html templates/blog_article.html templates/takvim.html templates/harita_gun.html"

gate_group sozdizimi "G1 Sozdizimi" \
  "Jinja parse|python3 tools/_predeploy_jinja_check.py" \
  "Python compile (tum *.py)|git ls-files '*.py' | python3 -c 'import ast,sys;[ast.parse(open(f,encoding=\"utf-8\").read(),f) for f in sys.stdin.read().split()]'" \
  "node-syntax-check|python3 tools/node-syntax-check.py" \
  "K-BE global-collision-check|python3 tools/global-collision-check.py"

gate_group renk "G2 Renk/token" \
  "CSS token guard|python3 tools/css-token-guard.py static/css/*.css" \
  "style-guard|python3 tools/style-guard.py" \
  "K-G state-order-check|python3 tools/state-order-check.py" \
  "K-I contrast-check|python3 tools/contrast-check.py" \
  "K-K da-override-check|python3 tools/da-override-check.py" \
  "K-AP canon-conflict-check|python3 tools/canon-conflict-check.py" \
  "K-BG js-palette-check|python3 tools/js-palette-check.py" \
  "K-BO volume-axis-color-check|python3 tools/volume-axis-color-check.py" \
  "K-BW inline-style-hex-check (poz. kontrol --ref 4dc34f6)|python3 tools/inline-style-hex-check.py" \
  "K-BY template-color-channel-check (poz. kontrol --ref 5053319)|python3 tools/template-color-channel-check.py" \
  "K-CW score-band-canon-check|python3 tools/score-band-canon-check.py" \
  "K-CY canon-css-dup-check (poz. kontrol --ref b4b8bcf)|python3 tools/canon-css-dup-check.py" \
  "K-CZ brand-wordmark-canon-check (poz. kontrol --ref 8b3d756)|python3 tools/brand-wordmark-canon-check.py" \
  "K-DB py-palette-check (poz. kontrol --ref 5e864a7)|python3 tools/py-palette-check.py"

gate_group kabuk "G3 Kabuk/asset" \
  "sw_manifest (elle ?v= 0)|python3 tools/sw_manifest.py" \
  "K-AS nav-label-canon-check|python3 tools/nav-label-canon-check.py" \
  "K-AY sticky-anchor-check|python3 tools/sticky-anchor-check.py" \
  "K-AZ safearea-layer-check|python3 tools/safearea-layer-check.py" \
  "K-DR overflow-guard-canon-check (kapi 84)|python3 tools/overflow-guard-canon-check.py"

gate_group metin "G4 Yayimlanan metin" \
  "KALICI_KURALLAR audit|for f in \$KK_AUDIT_FILES; do ./tests/audit/kalici-kurallar-check.sh \"\$f\" >/dev/null 2>&1 || { echo \"KK ihlali: \$f\"; exit 1; }; done" \
  "K-H legal-text-sync-check|python3 tools/legal-text-sync-check.py" \
  "K-AQ glyph-canon-check|python3 tools/glyph-canon-check.py" \
  "K-BN eod-freshness-claim-check|python3 tools/eod-freshness-claim-check.py" \
  "K-BZ provenance-badge-check (poz. kontrol --ref 9c63d9f)|python3 tools/provenance-badge-check.py" \
  "K-CB window-claim-check (poz. kontrol --ref 4bd1ea0)|python3 tools/window-claim-check.py" \
  "K-CD relative-time-anchor-check (poz. kontrol --ref 7c7788f)|python3 tools/relative-time-anchor-check.py" \
  "K-CE intraday-claim-check|python3 tools/intraday-claim-check.py" \
  "K-CF blog-claim-check|python3 tools/blog-claim-check.py" \
  "K-CG app-published-text-check|python3 tools/app-published-text-check.py" \
  "K-CH static-js-text-check|python3 tools/static-js-text-check.py" \
  "K-CI manifest-text-check|python3 tools/manifest-text-check.py" \
  "K-CJ crawler-channel-check (poz. kontrol --ref bdc6013)|python3 tools/crawler-channel-check.py" \
  "K-CK sitemap-claim-check (poz. kontrol --ref e7a9221)|python3 tools/sitemap-claim-check.py" \
  "K-CL head-meta-check (poz. kontrol --ref ee2a473)|python3 tools/head-meta-check.py" \
  "K-CM glossary-where-check|python3 tools/glossary-where-check.py" \
  "K-CN score-claim-check (poz. kontrol --ref 29147f3)|python3 tools/score-claim-check.py" \
  "K-CO delivery-timing-claim-check|python3 tools/delivery-timing-claim-check.py" \
  "K-CV privacy-claim-flow-check|python3 tools/privacy-claim-flow-check.py" \
  "K-DE long-only-surface-check (poz. kontrol --ref 8b3f67b)|python3 tools/long-only-surface-check.py" \
  "K-DK signal-rule-canon-check (poz. kontrol --ref a2fc59e)|python3 tools/signal-rule-canon-check.py" \
  "K-DM sector-peer-promise-check (poz. kontrol --ref 334d01c)|python3 tools/sector-peer-promise-check.py" \
  "K-DN scope-claim-canon-check (poz. kontrol --ref 509c33a)|python3 tools/scope-claim-canon-check.py"

gate_group sayi "G5 Sayi/bicim kanonu" \
  "format-lint (K6)|./tools/format-lint.sh" \
  "K-AR threshold-sync-check|python3 tools/threshold-sync-check.py" \
  "K-BA tr-decimal-input-check|python3 tools/tr-decimal-input-check.py" \
  "K-BD tr-calendar-day-check|python3 tools/tr-calendar-day-check.py" \
  "K-BP direction-zero-check|python3 tools/direction-zero-check.py" \
  "K-BQ stop-level-canon-check|python3 tools/stop-level-canon-check.py" \
  "K-BR indicator-precision-check|python3 tools/indicator-precision-check.py" \
  "K-BS indicator-panel-canon-check|python3 tools/indicator-panel-canon-check.py" \
  "K-BU label-derived-number-check|python3 tools/label-derived-number-check.py" \
  "K-BV money-scale-canon-check|python3 tools/money-scale-canon-check.py" \
  "K-BX fundamental-card-band-check (poz. kontrol --ref e7cb2cf)|python3 tools/fundamental-card-band-check.py" \
  "K-CC export-parity-check (poz. kontrol --ref 00d37b9)|python3 tools/export-parity-check.py" \
  "K-DC index-ticker-channel-check (poz. kontrol --ref 4905153)|python3 tools/index-ticker-channel-check.py" \
  "K-DG tr-fold-canon-check (poz. kontrol --ref 684f16c)|python3 tools/tr-fold-canon-check.py" \
  "K-DL fundamental-field-presentation-check (poz. kontrol --ref ccf2893)|python3 tools/fundamental-field-presentation-check.py"

gate_group etkilesim "G6 Etkilesim sozlesmesi" \
  "K-AT tooltip-canon-check|python3 tools/tooltip-canon-check.py" \
  "K-AV sort-canon-check|python3 tools/sort-canon-check.py" \
  "K-AW newtab-canon-check|python3 tools/newtab-canon-check.py" \
  "K-AX autorefresh-canon-check|python3 tools/autorefresh-canon-check.py" \
  "K-BT innerhtml-sibling-check|python3 tools/innerhtml-sibling-check.py" \
  "K-CX dynamic-tip-canon-check|python3 tools/dynamic-tip-canon-check.py" \
  "K-DH learning-mode-surface-check (poz. kontrol --ref 1dd9684)|python3 tools/learning-mode-surface-check.py" \
  "K-DO hidden-write-target-check (poz. kontrol --ref 77f66e9)|python3 tools/hidden-write-target-check.py" \
  "K-DP control-role-behavior-check (poz. kontrol --ref 61777f3)|python3 tools/control-role-behavior-check.py"

gate_group istemci "G7 Istemci durumu" \
  "K-CP tab-visibility-canon-check|python3 tools/tab-visibility-canon-check.py" \
  "K-CQ url-state-param-check|python3 tools/url-state-param-check.py" \
  "K-CS form-url-state-check|python3 tools/form-url-state-check.py" \
  "K-CT url-state-owner-check|python3 tools/url-state-owner-check.py" \
  "K-CU client-server-state-owner-check|python3 tools/client-server-state-owner-check.py"

# E2E->KALDIR adaylari: Playwright e2e yazilana kadar kural olarak KALIR.
gate_group veri "G8 Kullanici verisi (e2e oncesi)" \
  "K-BH copy-promise-check|python3 tools/copy-promise-check.py" \
  "K-BI merge-report-check|python3 tools/merge-report-check.py" \
  "K-BJ position-validation-check|python3 tools/position-validation-check.py" \
  "K-BK api-data-loading-guard|python3 tools/api-data-loading-guard.py" \
  "K-BM local-data-guard|python3 tools/local-data-guard.py"

wait
cat "$PD_OUT"/*.out 2>/dev/null
FAIL=$(ls "$PD_OUT"/*.fail 2>/dev/null | wc -l | tr -d ' ')

echo ""
if [ "$FAIL" = "0" ]; then
  echo "✅ Pre-deploy TÜM CHECK GEÇTİ — deploy izinli."
  exit 0
else
  echo "❌ $FAIL grup fail — deploy reddedildi."
  exit 1
fi
