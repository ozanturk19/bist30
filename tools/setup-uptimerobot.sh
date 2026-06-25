#!/bin/bash
# Usage: ./tools/setup-uptimerobot.sh <API_KEY>
# Pushes 5 monitor configs to UptimeRobot

set -euo pipefail

API_KEY="${1:?API_KEY required}"
API_URL="https://api.uptimerobot.com/v2/newMonitor"

declare -a MONITORS=(
  "borsapusula-root|https://borsapusula.com/|300|BorsaPusula"
  "borsapusula-health|https://borsapusula.com/api/health|300|ok"
  "borsapusula-data|https://borsapusula.com/api/data|300|"
  "borsapusula-akbnk|https://borsapusula.com/hisse/AKBNK|300|AKBNK"
  "borsapusula-sinyal|https://borsapusula.com/sinyal_performans|600|Sinyal"
)

for entry in "${MONITORS[@]}"; do
  IFS='|' read -r name url interval keyword <<< "$entry"
  echo "Setting up: $name -> $url"
  curl -s -X POST "$API_URL" \
    -d "api_key=$API_KEY" \
    -d "friendly_name=$name" \
    -d "url=$url" \
    -d "type=1" \
    -d "interval=$interval" \
    ${keyword:+-d "keyword_value=$keyword"}
  echo ""
done

echo "5 monitor configured. Verify: https://uptimerobot.com/dashboard"
