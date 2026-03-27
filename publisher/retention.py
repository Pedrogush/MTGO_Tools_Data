"""Working-tree retention helpers for published scrape artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from publisher.contracts import build_latest_manifest, validate_latest_manifest
from publisher.layout import DEFAULT_OUTPUT_ROOT, DEFAULT_RETENTION_DAYS, write_json

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python 3.10 fallback
    UTC = timezone.utc  # noqa: UP017


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _parse_prune_timestamp(value: str | None) -> str:
    if value:
        return _parse_timestamp(value).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return _utc_now()


def _parse_hourly_dir(name: str) -> datetime | None:
    try:
        day_token, time_token = name.split("T", 1)
        hour, minute, second = time_token.removesuffix("Z").split("-", 2)
        return _parse_timestamp(f"{day_token}T{hour}:{minute}:{second}Z")
    except ValueError:
        return None


def _parse_daily_dir(name: str) -> date | None:
    try:
        return date.fromisoformat(name)
    except ValueError:
        return None


def _deck_text_generated_at(path: Path) -> datetime | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    generated_at = payload.get("generated_at")
    if not isinstance(generated_at, str):
        return None
    try:
        return _parse_timestamp(generated_at)
    except ValueError:
        return None


def _prune_empty_parents(path: Path, *, stop_at: Path) -> None:
    current = path
    while current != stop_at and current.exists():
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _existing_entries(output_root: Path, entries: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        entry
        for entry in entries
        if isinstance(entry.get("path"), str) and (output_root / entry["path"]).exists()
    ]


def prune_output_tree(
    output_root: Path,
    *,
    generated_at: str | None = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> dict[str, int]:
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")

    normalized_generated_at = _parse_prune_timestamp(generated_at)
    cutoff_ts = _parse_timestamp(normalized_generated_at) - timedelta(days=retention_days)
    cutoff_day = cutoff_ts.date()

    summary = {
        "hourly_dirs_removed": 0,
        "daily_dirs_removed": 0,
        "deck_text_blobs_removed": 0,
        "deck_text_manifest_entries_removed": 0,
    }

    hourly_root = output_root / "hourly"
    if hourly_root.exists():
        for path in sorted(hourly_root.iterdir()):
            if not path.is_dir():
                continue
            parsed = _parse_hourly_dir(path.name)
            if parsed is not None and parsed < cutoff_ts:
                shutil.rmtree(path)
                summary["hourly_dirs_removed"] += 1
                continue

    daily_root = output_root / "daily"
    if daily_root.exists():
        for path in sorted(daily_root.iterdir()):
            if not path.is_dir():
                continue
            parsed = _parse_daily_dir(path.name)
            if parsed is not None and parsed < cutoff_day:
                shutil.rmtree(path)
                summary["daily_dirs_removed"] += 1

    archive_root = output_root / "archive" / "deck-texts"
    if archive_root.exists():
        for path in sorted(archive_root.rglob("*.json")):
            generated_at = _deck_text_generated_at(path)
            if generated_at is None or generated_at >= cutoff_ts:
                continue
            path.unlink()
            summary["deck_text_blobs_removed"] += 1
            _prune_empty_parents(path.parent, stop_at=archive_root)

    manifest_path = output_root / "latest" / "latest.json"
    if manifest_path.exists():
        manifest = validate_latest_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    else:
        manifest = build_latest_manifest(
            generated_at=normalized_generated_at,
            retention_days=retention_days,
        )

    manifest["generated_at"] = normalized_generated_at
    manifest["retention_days"] = retention_days
    manifest["latest"]["archetype_lists"] = _existing_entries(
        output_root, manifest["latest"].get("archetype_lists", [])
    )
    manifest["latest"]["archetype_decks"] = _existing_entries(
        output_root, manifest["latest"].get("archetype_decks", [])
    )
    manifest["latest"]["archetype_radars"] = _existing_entries(
        output_root, manifest["latest"].get("archetype_radars", [])
    )
    manifest["latest"]["format_card_pools"] = _existing_entries(
        output_root, manifest["latest"].get("format_card_pools", [])
    )
    manifest["latest"]["metagame_daily"] = _existing_entries(
        output_root, manifest["latest"].get("metagame_daily", [])
    )
    manifest["latest"]["runs"] = _existing_entries(output_root, manifest["latest"].get("runs", []))

    existing_deck_entries = manifest["latest"].get("deck_text_blobs", [])
    manifest["latest"]["deck_text_blobs"] = _existing_entries(output_root, existing_deck_entries)
    summary["deck_text_manifest_entries_removed"] = len(existing_deck_entries) - len(
        manifest["latest"]["deck_text_blobs"]
    )
    manifest["latest"]["mtgo_decklists"] = _existing_entries(
        output_root, manifest["latest"].get("mtgo_decklists", [])
    )

    write_json(manifest_path, manifest)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prune publisher working-tree artifacts")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--timestamp", help="UTC timestamp used for retention cutoff")
    parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary = prune_output_tree(
        Path(args.output_root),
        generated_at=args.timestamp,
        retention_days=args.retention_days,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
