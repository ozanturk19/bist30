#!/bin/bash
# tools/mobile-overflow-daily.sh — T9.1 gunluk mobil yatay-tasma otomasyonu
#
# mobile-overflow-check.mjs'i (CPO-1201/1204 M1-d harness) prod'a karsi gunde
# bir kez calistirir. Bu script'in kendisi hicbir deploy'u BLOKLAMAZ (bkz.
# DEV2 mailbox raporu: 204 kontrol ~4-5dk suruyor, pre-deploy-check.sh statik/
# hizli kontrol beklentisiyle celisir; post-deploy-smoke.sh reload sonrasi
# ANINDA calisan bir smoke, 4-5dk'lik playwright kosumu deploy'u fiilen kilitler).
# Bunun yerine bagimsiz gunluk gozlem: her kosum LOG'a tam cikti yazar (staleness
# LOG mtime'indan tespit edilebilir), FAIL/WARN durumunda mailbox'a ozet dusurur
# ("Gorunurluk Ertelenmez" — sessiz PASS-varsayimi degil, ama gunluk PASS
# gurultusu de mailbox'i doldurmasin diye yalniz durum degisiminde/olumsuzda yazar).
#
# Crontab: 20 4 * * * /root/bist30/tools/mobile-overflow-daily.sh >/dev/null 2>&1

set -uo pipefail
cd "$(dirname "$0")/.."

LOG="/var/log/bist30-mobile-overflow.log"
STATE="/var/log/bist30-mobile-overflow.laststatus"
MAILBOX="/root/ops/mailbox/dev2-to-cpo.md"
LOCK="/var/lock/bist30-mobile-overflow.lock"
TS="$(TZ='Europe/Istanbul' date '+%Y-%m-%d %H:%M:%S TR')"

exec 200>"$LOCK"
flock -n 200 || { echo "$TS SKIP — onceki kosum hala calisiyor" >> "$LOG"; exit 0; }

OUT="$(node tools/mobile-overflow-check.mjs --base=https://borsapusula.com 2>&1)"
EXIT=$?

{
  echo "=== $TS — exit=$EXIT ==="
  echo "$OUT"
  echo ""
} >> "$LOG"

STATUS="PASS"
[ "$EXIT" = "1" ] && STATUS="WARN"
[ "$EXIT" = "2" ] && STATUS="FAIL"

PREV_STATUS="$(cat "$STATE" 2>/dev/null || echo "UNKNOWN")"
echo "$STATUS" > "$STATE"

# Mailbox'a yalniz PASS-disi durumda VEYA durum degistiyse yaz — her gun ayni
# "PASS" satirini mailbox'a basmak gurultu, ama ilk kez FAIL'e donmek ya da
# FAIL'de kalmaya devam etmek sessizce yutulamaz.
if [ "$STATUS" != "PASS" ]; then
  SUMMARY="$(echo "$OUT" | grep -E '^Integrity failures:' || echo "(ozet satiri parse edilemedi, LOG'a bak)")"
  {
    echo ""
    echo "## [CRON-AUTO] mobile-overflow-check.mjs gunluk kosum — $STATUS [$TS]"
    echo ""
    echo '```'
    echo "$SUMMARY"
    echo '```'
    echo ""
    echo "Detay: $LOG (host), tests/mobile-overflow/latest.json (JSON). Onceki durum: $PREV_STATUS."
    echo ""
  } >> "$MAILBOX" 2>/dev/null
fi

exit 0
