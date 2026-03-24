#!/usr/bin/env bash
set -euo pipefail

# Populate missing deck-text archive blobs from the current latest deck snapshots
# without mutating publish manifests or hourly snapshot folders.

formats=(Modern Standard Pioneer Legacy Vintage Pauper)
output_root="${PUBLISH_OUTPUT_ROOT:-data}"
deck_download_delay_seconds="${PUBLISH_DECK_DOWNLOAD_DELAY_SECONDS:-0.5}"
source_filter="${PUBLISH_SOURCE_FILTER:-both}"

echo "Output root: $output_root"
echo "Deck download delay seconds: $deck_download_delay_seconds"
echo "Source filter: $source_filter"
echo "Formats: ${formats[*]}"

python3 - "$output_root" "$deck_download_delay_seconds" "$source_filter" "${formats[@]}" <<'PY'
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from publisher.contracts import build_deck_text_blob, validate_deck_text_blob
from publisher.layout import normalize_name, write_json
from publisher.runner import _utc_now
from scraping import ScrapingMetagameRepository


def load_reusable_blob(path: Path, *, format_name: str, deck_id: str) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        validated = validate_deck_text_blob(payload)
    except Exception:
        return False
    return validated.get("format") == format_name and validated.get("deck_id") == deck_id


def archive_path_for(output_root: Path, normalized_format: str, deck: dict[str, Any]) -> Path:
    deck_text_path = str(deck.get("deck_text_path", "")).strip()
    if deck_text_path:
        return output_root / deck_text_path
    deck_id = str(deck.get("number", "")).strip()
    return output_root / "archive" / "deck-texts" / normalized_format / f"{deck_id}.json"


def main() -> int:
    output_root = Path(sys.argv[1])
    deck_download_delay_seconds = float(sys.argv[2])
    raw_source_filter = sys.argv[3]
    formats = sys.argv[4:]
    source_filter = None if raw_source_filter == "both" else raw_source_filter
    generated_at = _utc_now()
    repo = ScrapingMetagameRepository()

    total_reused = 0
    total_downloaded = 0
    failures: list[str] = []

    for format_name in formats:
        normalized_format = normalize_name(format_name)
        decks_dir = output_root / "latest" / "decks" / normalized_format
        if not decks_dir.exists():
            message = (
                f"{format_name}: missing deck snapshot directory {decks_dir}; "
                "run the publisher warmup first."
            )
            print(f"ERROR: {message}", file=sys.stderr)
            failures.append(message)
            continue

        unique_decks: dict[str, dict[str, Any]] = {}
        snapshot_files = sorted(decks_dir.glob("*.json"))
        for snapshot_path in snapshot_files:
            try:
                payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            except Exception as exc:
                message = f"{format_name}: failed to read {snapshot_path}: {exc}"
                print(f"ERROR: {message}", file=sys.stderr)
                failures.append(message)
                continue

            for deck in payload.get("decks", []):
                deck_id = str(deck.get("number", "")).strip()
                if deck_id:
                    unique_decks.setdefault(deck_id, deck)

        missing_decks: list[tuple[str, dict[str, Any], Path]] = []
        for deck_id, deck in sorted(unique_decks.items()):
            archive_path = archive_path_for(output_root, normalized_format, deck)
            if load_reusable_blob(archive_path, format_name=normalized_format, deck_id=deck_id):
                total_reused += 1
                continue
            missing_decks.append((deck_id, deck, archive_path))

        print(
            f"{format_name}: found {len(unique_decks)} unique decks, "
            f"{len(missing_decks)} missing archive blobs."
        )

        downloaded_for_format = 0
        for index, (deck_id, deck, archive_path) in enumerate(missing_decks):
            if index > 0 and deck_download_delay_seconds > 0:
                time.sleep(deck_download_delay_seconds)

            try:
                deck_text = repo.download_deck_content(deck, source_filter=source_filter)
                snapshot = build_deck_text_blob(
                    generated_at=generated_at,
                    format_name=normalized_format,
                    deck_id=deck_id,
                    source=deck.get("source", source_filter or "mtggoldfish"),
                    deck_name=deck.get("name", deck_id),
                    deck_text=deck_text,
                )
                validate_deck_text_blob(snapshot)
                write_json(archive_path, snapshot)
                downloaded_for_format += 1
                total_downloaded += 1
            except Exception as exc:
                message = (
                    f"{format_name}: failed to download deck {deck_id} "
                    f"({deck.get('name', deck_id)}): {exc}"
                )
                print(f"ERROR: {message}", file=sys.stderr)
                failures.append(message)

        print(
            f"{format_name}: wrote {downloaded_for_format} missing archive blobs, "
            f"reused {len(unique_decks) - len(missing_decks)} existing blobs."
        )

    print(
        f"Completed fill-missing pass: downloaded={total_downloaded}, reused={total_reused}, "
        f"failures={len(failures)}."
    )
    return 1 if failures else 0


raise SystemExit(main())
PY
