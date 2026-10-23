#!/usr/bin/env bash
# D-62: Haftalik gercek trafik olcumu (Cuma raporuna).
# Salt-okur: yalniz nginx access log okur, hicbir sey yazmaz/degistirmez.
# Kullanim (VPS'te veya uzaktan):
#   ssh root@<vps> 'bash -s' < tools/live/trafik.sh [GUN_SAYISI]
# GUN_SAYISI varsayilan 7 (haftalik rapor); 14 periyodik D-11 izlemesi icin de kullanilabilir.
#
# Metodoloji (15.10 CPO olcumu + ayni gun DEV duzeltmesi):
#   - "JS calistiran tekil tarayici" = /api/* cagiran VE normal sayfa goren ayni IP (bot/script degil).
#   - Ham "tarayici UA" sayisi botlarla sisirilmis oldugu icin kullanilmaz.
#   - Kendi IP'lerimiz (QA/Playwright/donku) her zaman HARIC tutulur:
#       * VPS'in kendi genel IPv6'si (2a01:4f9:c013:41f2::1) -- outage-probe/smoke test kendine curl atiyor.
#       * Ekip agi bloğu (2a02:e0:b815:7c00::/64) -- manuel tarama/QA, gercek UA ile de gelebildigi icin
#         yalniz UA filtresi yetmez, IP bazli da elenir.
#       * Huawei Cloud / Cin bulut headless IP araliklari (116.204., 1.92., 121.37., 113.44., 2409:, 240e:)
#         -- gercek UA ile gelen ama bulut barindirmali headless/scraper trafigi (22.10 genis denetim).
#   - "Ziyaretci" (D-P1-2210-8): /api/* cagiran VE (>=2 sayfa goruntuleme YA DA dis siteden yonlendirme) ayni IP;
#     tek sayfa + referrersiz (dogrudan) tek istekler bot/prefetch kabul edilip sayilmaz.
#   - utm_source=chatgpt.com ayri bir kanal olarak sayilir (referrer'dan bagimsiz, ChatGPT tiklamasi).
set -euo pipefail
cd /var/log/nginx

GUN=${1:-7}

days=()
for i in $(seq $((GUN - 1)) -1 0); do
  days+=("$(date -u -d "-${i} day" +%d/%b/%Y)")
done
day_list="${days[*]}"
ilk_gun="${days[0]}"
son_gun="${days[$((GUN - 1))]}"

files=()
for f in borsapusula-access.log.14.gz borsapusula-access.log.13.gz borsapusula-access.log.12.gz \
         borsapusula-access.log.11.gz borsapusula-access.log.10.gz borsapusula-access.log.9.gz \
         borsapusula-access.log.8.gz borsapusula-access.log.7.gz borsapusula-access.log.6.gz \
         borsapusula-access.log.5.gz borsapusula-access.log.4.gz borsapusula-access.log.3.gz \
         borsapusula-access.log.2.gz borsapusula-access.log.1 borsapusula-access.log; do
  [ -f "$f" ] && files+=("$f")
done

echo "=== BorsaPusula Haftalik Trafik Olcumu (D-62) ==="
echo "Uretildi: $(date -u +'%Y-%m-%d %H:%M') UTC"
echo "Kapsam: son ${GUN} gun (${ilk_gun} - ${son_gun})"
echo "Kendi IP'ler haric: VPS'in kendi IPv6'si + ekip agi /64 blogu (QA/Playwright/dongu)"

for f in "${files[@]}"; do zcat -f "$f"; done | awk -F'"' -v day_list="$day_list" -v ngun="$GUN" '
BEGIN {
  n = split(day_list, D, " ");
  for (i = 1; i <= n; i++) indays[D[i]] = 1;
  self_ip = "2a01:4f9:c013:41f2::1";
  team_prefix = "2a02:e0:b815:7c00:";
  n_cloud = split("116.204. 1.92. 121.37. 113.44. 2409: 240e:", CLOUD, " ");
  # bos veri setinde bile length()/for-in uc bulmasin diye tipi erkenden dizi sabitle
  split("", aib); split("", fin); split("", asset); split("", pgv);
  split("", g); split("", aiv); split("", mob); split("", ext);
  chatgpt_clicks = 0;
}
{
  split($1, a, " "); ip = a[1]; dt = substr(a[4], 2, 11);
  if (!(dt in indays)) next;
  if (ip == self_ip || index(ip, team_prefix) == 1) next;
  is_cloud = 0;
  for (ci = 1; ci <= n_cloud; ci++) if (index(ip, CLOUD[ci]) == 1) { is_cloud = 1; break; }
  if (is_cloud) next;

  split($2, r, " "); m = r[1]; path = r[2];
  split($3, s, " "); st = s[1];
  ref = tolower($4); ua = $6; lua = tolower(ua);

  if (path ~ /utm_source=chatgpt\.com/) chatgpt_clicks++;

  if (lua ~ /gptbot|oai-searchbot|chatgpt-user|claudebot|claude-user|claude-searchbot|perplexitybot|perplexity-user|google-extended|ccbot|bytespider|meta-externalagent|amazonbot|applebot/) {
    b = "Diger_AI";
    if (lua ~ /gptbot/) b = "GPTBot";
    else if (lua ~ /oai-searchbot/) b = "OAI-SearchBot";
    else if (lua ~ /chatgpt-user/) b = "ChatGPT-User";
    else if (lua ~ /claude/) b = "Claude";
    else if (lua ~ /perplexity/) b = "Perplexity";
    else if (lua ~ /meta-external/) b = "Meta";
    else if (lua ~ /bytespider/) b = "ByteDance";
    else if (lua ~ /amazonbot/) b = "Amazon";
    else if (lua ~ /applebot/) b = "Apple";
    else if (lua ~ /ccbot/) b = "CommonCrawl";
    aib[b]++;
    if (path ~ /\/(bilanco|gelir-tablosu|nakit-akis)(\?|$)/) fin[b]++;
    next;
  }
  if (lua ~ /bot|crawl|spider|slurp|curl|wget|python|go-http|java\/|headless|phantom|lighthouse|borsapusulaqa|uptime|monitor|scan|httpclient|axios|node-fetch|okhttp|libwww|feed|preview|facebookexternalhit|whatsapp|telegram/ || ua == "-" || ua == "") next;

  if (path ~ /^\/api\// && st ~ /^(200|304)$/) asset[ip] = 1;
  if (m == "GET" && st ~ /^(200|304)$/ && path !~ /^\/(api|static|harita|sw\.js|favicon|robots|sitemap|llms|manifest|apple-touch|offline|_)/ && path !~ /\.(js|css|png|jpg|svg|ico|webp|woff2?|json|xml|txt|map)(\?|$)/) {
    pgv[ip]++;
    if (ref != "" && ref != "-") ext[ip] = 1;
    if (ref ~ /google\./) g[ip] = 1;
    if (ref ~ /chatgpt|openai|perplexity|claude\.ai|gemini|copilot/) aiv[ip] = 1;
    if (lua ~ /mobile|android|iphone/) mob[ip] = 1;
  }
}
END {
  js = 0; pv = 0; mobn = 0; gn = 0; ain = 0;
  for (k in asset) {
    if ((k in pgv) && (pgv[k] >= 2 || (k in ext))) {
      js++; pv += pgv[k];
      if (k in mob) mobn++;
      if (k in g) gn++;
      if (k in aiv) ain++;
    }
  }
  printf "\n--- Haftalik ozet (ziyaretci: JS calistiran VE >=2 sayfa ya da dis yonlendirme, kendi/ekip/bulut IP haric) ---\n";
  printf "Tekil IP (ziyaretci)\t%d\n", js;
  printf "Sayfa goruntuleme\t%d\n", pv;
  printf "Mobil (tekil IP)\t%d\n", mobn;
  printf "Google dan (tekil IP)\t%d\n", gn;
  printf "AI sohbetten (tekil IP)\t%d\n", ain;
  printf "ChatGPT tiklama (utm_source=chatgpt.com istek)\t%d\n", chatgpt_clicks;

  printf "\n--- AI bot dokumu (istek sayisi, %d gun) ---\n", ngun;
  if (length(aib) == 0) printf "(istek yok)\n";
  for (b in aib) printf "%s\t%d\n", b, aib[b];

  printf "\n--- Finansal tablo sayfalarini (bilanco/gelir-tablosu/nakit-akis) tarayan botlar ---\n";
  if (length(fin) == 0) printf "(istek yok)\n";
  for (b in fin) printf "%s\t%d\n", b, fin[b];
}'
