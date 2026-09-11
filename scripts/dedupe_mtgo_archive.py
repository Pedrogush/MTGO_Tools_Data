#!/usr/bin/env python3
"""Remove legacy slug-named duplicates from the MTGO event archive.

Event archives used to be written as ``<slug><event_id>.json`` (for example
``vintage-challenge-32-2026-07-2312848175.json``). ``_mtgo_event_archive_path``
now names them ``<event_id>.json``, but the migration never deleted the old
files, so hundreds of events are stored twice. That is only ~1 MB on disk, but
every consumer that walks the archive - ``client_bundle.collect_bundle_sources``
included - reads both copies, which double-counts a fifth of the deck rows.

The legacy writer also stored the slug form as the payload's own ``event_id``
(``"vintage-challenge-32-2026-07-2312848175"``), so the two copies of an event do
not share an id. A duplicate is therefore identified as a file whose ``event_id``
*ends with* the id of an existing canonical ``<event_id>.json`` in the same
format. Matching against known canonical ids rather than a trailing-digit regex
matters: league archives embed a date immediately before the id
(``vintage-league-2026-04-2210668.json``), so a greedy regex merges distinct
events.

Files with no canonical counterpart are the only copy of their event and are
left alone, whatever they are named.

Dry run by default; pass --apply to delete.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_ARCHIVE_ROOT = Path("data") / "archive" / "mtgo-decklists"
# publisher.runner._mtgo_event_id: the bare Videre id, negative league ids
# carrying a leading "n".
CANONICAL_ID_RE = re.compile(r"^n?\d+$")


def load_payload(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def deck_ids(payload: dict) -> set[str] | None:
    decks = payload.get("decks")
    if not isinstance(decks, list):
        return None
    return {str(deck.get("number", "")) for deck in decks}


def find_duplicates(archive_root: Path) -> tuple[list[tuple[Path, Path]], list[str]]:
    """Return (removable, warnings) where removable is [(legacy, canonical), ...]."""
    removable: list[tuple[Path, Path]] = []
    warnings: list[str] = []

    for format_dir in sorted(p for p in archive_root.iterdir() if p.is_dir()):
        loaded: list[tuple[Path, str, dict]] = []
        for path in sorted(format_dir.glob("*.json")):
            payload = load_payload(path)
            if payload is None:
                warnings.append(f"{path} is unreadable; leaving it alone")
                continue
            event_id = str(payload.get("event_id", "")).strip()
            if not event_id:
                warnings.append(f"{path} has no event_id; leaving it alone")
                continue
            loaded.append((path, event_id, payload))

        canonical = {
            event_id: (path, payload)
            for path, event_id, payload in loaded
            if path.name == f"{event_id}.json" and CANONICAL_ID_RE.match(event_id)
        }

        for path, event_id, payload in loaded:
            if event_id in canonical and canonical[event_id][0] == path:
                continue
            # Longest suffix wins, so "…2312848175" prefers 12848175 over 8175.
            matches = sorted(
                (cid for cid in canonical if event_id.endswith(cid)),
                key=len,
                reverse=True,
            )
            if not matches:
                continue
            survivor_path, survivor_payload = canonical[matches[0]]

            survivor_ids = deck_ids(survivor_payload)
            legacy_ids = deck_ids(payload)
            if survivor_ids is None or legacy_ids is None:
                warnings.append(f"{path.name}: unreadable deck list; keeping both")
                continue
            # Never drop a copy holding deck rows the survivor lacks.
            missing = legacy_ids - survivor_ids
            if missing:
                warnings.append(
                    f"{path.name} holds {len(missing)} deck(s) absent from "
                    f"{survivor_path.name}; keeping both"
                )
                continue
            removable.append((path, survivor_path))

    return removable, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", default=str(DEFAULT_ARCHIVE_ROOT))
    parser.add_argument("--apply", action="store_true", help="Delete the duplicates")
    parser.add_argument("--quiet", action="store_true", help="Only print the summary")
    args = parser.parse_args(argv)

    archive_root = Path(args.archive_root)
    if not archive_root.exists():
        print(f"No archive at {archive_root}", file=sys.stderr)
        return 1

    removable, warnings = find_duplicates(archive_root)
    freed = 0
    for legacy, survivor in removable:
        freed += legacy.stat().st_size
        if not args.quiet:
            print(f"{'removing' if args.apply else 'would remove'} {legacy} (kept {survivor.name})")
        if args.apply:
            legacy.unlink()

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    print(
        f"{len(removable)} duplicate event files, {freed / 1048576:.2f} MB"
        f"{'' if args.apply else ' (dry run; pass --apply)'}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
