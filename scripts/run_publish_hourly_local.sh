#!/usr/bin/env bash
set -euo pipefail

# Run the same publisher command path as publish-hourly.yml, but without
# the remote workflow's download delay so local warmups complete faster.

format="${1:-Modern}"
archetype="${2:-}"
days="${3:-7}"
output_root="${4:-/tmp/publish-hourly-local-$(date +%s)}"
retention_days="${PUBLISH_RETENTION_DAYS:-7}"

cmd=(
  python3 -m publisher.runner
  --output-root "$output_root"
  --retention-days "$retention_days"
  scrape-deck-texts
  --format "$format"
  --deck-download-delay-seconds 0
  --days "$days"
)

if [[ -n "$archetype" ]]; then
  cmd+=(--archetype "$archetype")
fi

echo "Output root: $output_root"
echo "Running: ${cmd[*]}"
"${cmd[@]}"
