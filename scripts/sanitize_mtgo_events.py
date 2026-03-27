#!/usr/bin/env python3
"""Scan the data/archive/mtgo-decklists folder for events with no decks."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    data_root = Path(argv[0]) if argv else Path("data")
    mtgo_archive = data_root / "archive" / "mtgo-decklists"

    if not mtgo_archive.exists():
        print(f"Archive directory not found: {mtgo_archive}", file=sys.stderr)
        return 1

    empty_events: list[dict] = []
    total = 0
    errors = 0

    for event_file in sorted(mtgo_archive.rglob("*.json")):
        total += 1
        try:
            payload = json.loads(event_file.read_text(encoding="utf-8"))
            decks = payload.get("decks", [])
            if not decks:
                empty_events.append(
                    {
                        "path": str(event_file.relative_to(data_root)),
                        "event_id": payload.get("event_id"),
                        "event_title": payload.get("event_title"),
                        "format": payload.get("format"),
                        "publish_date": payload.get("publish_date"),
                        "decks_total": payload.get("decks_total", 0),
                    }
                )
        except Exception as exc:
            print(f"ERROR reading {event_file}: {exc}", file=sys.stderr)
            errors += 1

    print(f"Scanned {total} MTGO event files ({errors} read errors).")

    if not empty_events:
        print("No empty events found.")
        return 0

    print(f"\nFound {len(empty_events)} event(s) with no decks:")
    for event in empty_events:
        print(f"  {event['path']}")
        print(
            f"    format={event['format']}  date={event['publish_date']}"
            f"  decks_total={event['decks_total']}"
        )
        if event["event_title"]:
            print(f"    title: {event['event_title']}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
