#!/usr/bin/env bash
set -euo pipefail

# Run the same publisher command path as publish-hourly.yml, but target the
# repository's data tree by default so local warmups populate
# data/archive/deck-texts for later GitHub Actions runs.
#
# publisher.runner already skips the per-deck delay when it can reuse an
# existing published deck-text blob from the output root.

formats=(Modern Standard Pioneer Legacy Vintage Pauper)
days="${PUBLISH_WARMUP_DAYS:-7}"
output_root="${PUBLISH_OUTPUT_ROOT:-data}"
retention_days="${PUBLISH_RETENTION_DAYS:-7}"
deck_download_delay_seconds="${PUBLISH_DECK_DOWNLOAD_DELAY_SECONDS:-0.5}"

echo "Output root: $output_root"
echo "Retention days: $retention_days"
echo "Warmup window days: $days"
echo "Deck download delay seconds: $deck_download_delay_seconds"
echo "Formats: ${formats[*]}"

failed_formats=()
for format in "${formats[@]}"; do
  cmd=(
    python3 -m publisher.runner
    --output-root "$output_root"
    --retention-days "$retention_days"
    scrape-deck-texts
    --format "$format"
    --deck-download-delay-seconds "$deck_download_delay_seconds"
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
