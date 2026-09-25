#!/bin/bash
# D-40a1: KAP finansal uretimini bitene kadar surdurur (40 gecis siniri yok).
# Arac 429'da kendisi 15/30/60 dk bekler; bu dongu yalniz cikis 2 (6 bekleme sonuc vermedi) ve
# beklenmedik cokmelerde yeniden baslatir. Cikis 0 = bitti (taze hisseler atlanir, kaldigi yerden devam).
# Kullanim: nohup bash tools/kap_fin_loop.sh >/dev/null 2>&1 &   (log: /tmp/kap_fin_build.log)
cd "$(dirname "$0")/.." || exit 1
PY="${PY:-/root/bist30/venv/bin/python}"
LOG=/tmp/kap_fin_build.log
for i in $(seq 1 60); do
  "$PY" tools/build_kap_financials.py >> "$LOG" 2>&1
  rc=$?
  echo "== gecis $i rc=$rc $(date -u +%FT%TZ) json=$(ls data/kap_fin/*.json 2>/dev/null | grep -vc yil_sonu)" >> "$LOG"
  if [ $rc -eq 0 ] && ! tail -40 "$LOG" | grep -q "HATA "; then echo DONE >> "$LOG"; break; fi
  [ $rc -eq 2 ] && sleep 600 || sleep 60
done
