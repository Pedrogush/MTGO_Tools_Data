#!/usr/bin/env bash
set -euo pipefail

# Run the same publisher command path as publish-hourly.yml, but without
# the remote workflow's download delay so local warmups complete faster.

formats=(Modern Standard Pioneer Legacy Vintage Pauper)
days="${PUBLISH_WARMUP_DAYS:-7}"
output_root="${PUBLISH_OUTPUT_ROOT:-/tmp/publish-hourly-local-$(date +%s)}"
retention_days="${PUBLISH_RETENTION_DAYS:-7}"

echo "Output root: $output_root"
echo "Retention days: $retention_days"
echo "Warmup window days: $days"
echo "Formats: ${formats[*]}"

failed_formats=()
for format in "${formats[@]}"; do
  cmd=(
    python3 -m publisher.runner
    --output-root "$output_root"
    --retention-days "$retention_days"
    scrape-deck-texts
    --format "$format"
    --deck-download-delay-seconds 0
    --days "$days"
  )

  echo
  echo "Running format: $format"
  echo "Command: ${cmd[*]}"
  if ! "${cmd[@]}"; then
    failed_formats+=("$format")
  fi
done

if ((${#failed_formats[@]} > 0)); then
  echo
  echo "Completed with failures in formats: ${failed_formats[*]}"
  exit 1
fi

echo
echo "Completed successfully for all formats."
