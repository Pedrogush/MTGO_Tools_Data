"""CLI entrypoint for headless scrape publishing."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from navigators.mtggoldfish import get_archetype_stats
from publisher.contracts import (
    build_archetype_deck_snapshot,
    build_archetype_list_snapshot,
    build_deck_text_blob,
    build_metagame_snapshot,
    validate_archetype_deck_snapshot,
    validate_archetype_list_snapshot,
    validate_deck_text_blob,
    validate_metagame_snapshot,
)
from publisher.layout import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_RETENTION_DAYS,
    daily_snapshot_dir,
    hourly_snapshot_dir,
    normalize_name,
    update_latest_manifest,
    write_json,
)
from scraping import ScrapingMetagameRepository, fetch_archetypes

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python 3.10 fallback
    UTC = timezone.utc  # noqa: UP017


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_format_name(format_name: str) -> str:
    return normalize_name(format_name)


def _parse_timestamp(value: str | None) -> str:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return _utc_now()


def _parse_day(timestamp: str, override: str | None = None) -> str:
    if override:
        return override
    return timestamp.split("T", 1)[0]


def _parse_deck_date(date_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _filter_recent_decks(decks: list[dict[str, Any]], days: int | None) -> list[dict[str, Any]]:
    if days is None:
        return decks
    cutoff = datetime.now() - timedelta(days=days)
    filtered: list[dict[str, Any]] = []
    for deck in decks:
        parsed = _parse_deck_date(deck.get("date", ""))
        if parsed is None or parsed >= cutoff:
            filtered.append(deck)
    return filtered


def _selected_archetypes(
    format_name: str, archetype_filters: list[str] | None
) -> list[dict[str, Any]]:
    archetypes = sorted(
        fetch_archetypes(format_name, allow_stale=True),
        key=lambda item: (item.get("name", "").lower(), item.get("href", "").lower()),
    )
    if not archetype_filters:
        return archetypes
    wanted = {normalize_name(value) for value in archetype_filters}
    return [item for item in archetypes if normalize_name(item.get("name", "")) in wanted]


def _write_archetype_list_snapshot(
    *,
    output_root: Path,
    generated_at: str,
    retention_days: int,
    format_name: str,
    archetypes: list[dict[str, Any]],
) -> None:
    normalized_format = _normalize_format_name(format_name)
    snapshot = build_archetype_list_snapshot(
        generated_at=generated_at,
        format_name=normalized_format,
        source="mtggoldfish",
        archetypes=archetypes,
    )
    validate_archetype_list_snapshot(snapshot)
    latest_path = output_root / "latest" / "archetypes" / f"{normalized_format}.json"
    hourly_path = (
        hourly_snapshot_dir(output_root, generated_at) / "archetypes" / f"{normalized_format}.json"
    )
    write_json(latest_path, snapshot)
    write_json(hourly_path, snapshot)
    update_latest_manifest(
        output_root,
        generated_at=generated_at,
        retention_days=retention_days,
        category="archetype_lists",
        discriminator={"format": normalized_format},
        relative_path=str(latest_path.relative_to(output_root)),
    )


def _write_metagame_snapshot(
    *,
    output_root: Path,
    generated_at: str,
    retention_days: int,
    format_name: str,
    generated_for_day: str,
) -> None:
    raw_stats = get_archetype_stats(format_name)
    format_stats = raw_stats.get(format_name.lower(), {})
    stats_rows = []
    for archetype, payload in sorted(format_stats.items()):
        if archetype == "timestamp":
            continue
        daily_counts = payload.get("results", {})
        stats_rows.append(
            {
                "archetype": archetype,
                "deck_count": len(payload.get("decks", [])),
                "daily_counts": {key: daily_counts[key] for key in sorted(daily_counts)},
            }
        )
    normalized_format = _normalize_format_name(format_name)
    snapshot = build_metagame_snapshot(
        generated_at=generated_at,
        format_name=normalized_format,
        source="mtggoldfish",
        generated_for_day=generated_for_day,
        stats=stats_rows,
    )
    validate_metagame_snapshot(snapshot)
    latest_path = output_root / "latest" / "metagame" / f"{normalized_format}.json"
    daily_path = (
        daily_snapshot_dir(output_root, generated_for_day)
        / "metagame"
        / f"{normalized_format}.json"
    )
    write_json(latest_path, snapshot)
    write_json(daily_path, snapshot)
    update_latest_manifest(
        output_root,
        generated_at=generated_at,
        retention_days=retention_days,
        category="metagame_daily",
        discriminator={"format": normalized_format},
        relative_path=str(latest_path.relative_to(output_root)),
    )


def _write_deck_text_blobs(
    *,
    output_root: Path,
    generated_at: str,
    retention_days: int,
    format_name: str,
    archetype_filters: list[str] | None,
    days: int | None,
    source_filter: str | None,
) -> None:
    repo = ScrapingMetagameRepository()
    normalized_format = _normalize_format_name(format_name)
    for archetype in _selected_archetypes(format_name, archetype_filters):
        decks = repo.get_decks_for_archetype(
            archetype, force_refresh=True, source_filter=source_filter
        )
        recent_decks = _filter_recent_decks(decks, days)
        deck_texts = []
        seen_deck_ids: set[str] = set()
        for deck in recent_decks:
            deck_id = str(deck.get("number", "")).strip()
            if not deck_id or deck_id in seen_deck_ids:
                continue
            seen_deck_ids.add(deck_id)
            deck_texts.append(
                {
                    "deck_id": deck_id,
                    "deck_name": deck.get("name", archetype["name"]),
                    "deck_date": deck.get("date", ""),
                    "source": deck.get("source", source_filter or "mtggoldfish"),
                    "deck_text": repo.download_deck_content(deck, source_filter=source_filter),
                }
            )
        deck_texts.sort(key=lambda item: item["deck_id"])
        snapshot = build_deck_text_blob(
            generated_at=generated_at,
            format_name=normalized_format,
            archetype=archetype,
            source=source_filter or "both",
            deck_texts=deck_texts,
        )
        validate_deck_text_blob(snapshot)
        archetype_slug = normalize_name(archetype["name"])
        latest_path = (
            output_root / "latest" / "deck-texts" / normalized_format / f"{archetype_slug}.json"
        )
        hourly_path = (
            hourly_snapshot_dir(output_root, generated_at)
            / "deck-texts"
            / normalized_format
            / f"{archetype_slug}.json"
        )
        write_json(latest_path, snapshot)
        write_json(hourly_path, snapshot)
        update_latest_manifest(
            output_root,
            generated_at=generated_at,
            retention_days=retention_days,
            category="deck_text_blobs",
            discriminator={"format": normalized_format, "archetype": archetype_slug},
            relative_path=str(latest_path.relative_to(output_root)),
        )


def _write_archetype_deck_snapshots(
    *,
    output_root: Path,
    generated_at: str,
    retention_days: int,
    format_name: str,
    archetype_filters: list[str] | None,
    days: int | None,
    source_filter: str | None,
) -> None:
    repo = ScrapingMetagameRepository()
    normalized_format = _normalize_format_name(format_name)
    for archetype in _selected_archetypes(format_name, archetype_filters):
        decks = repo.get_decks_for_archetype(
            archetype, force_refresh=True, source_filter=source_filter
        )
        recent_decks = sorted(
            _filter_recent_decks(decks, days),
            key=lambda item: (
                item.get("date", ""),
                item.get("number", ""),
                item.get("player", ""),
            ),
            reverse=True,
        )
        snapshot = build_archetype_deck_snapshot(
            generated_at=generated_at,
            format_name=normalized_format,
            archetype=archetype,
            source=source_filter or "both",
            decks=recent_decks,
        )
        validate_archetype_deck_snapshot(snapshot)
        archetype_slug = normalize_name(archetype["name"])
        latest_path = (
            output_root / "latest" / "decks" / normalized_format / f"{archetype_slug}.json"
        )
        hourly_path = (
            hourly_snapshot_dir(output_root, generated_at)
            / "decks"
            / normalized_format
            / f"{archetype_slug}.json"
        )
        write_json(latest_path, snapshot)
        write_json(hourly_path, snapshot)
        update_latest_manifest(
            output_root,
            generated_at=generated_at,
            retention_days=retention_days,
            category="archetype_decks",
            discriminator={"format": normalized_format, "archetype": archetype_slug},
            relative_path=str(latest_path.relative_to(output_root)),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Headless scrape publisher")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--timestamp", help="UTC timestamp for deterministic output naming")
    parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    archetypes = subparsers.add_parser("scrape-archetypes")
    archetypes.add_argument("--format", dest="formats", action="append", required=True)

    metagame = subparsers.add_parser("scrape-metagame")
    metagame.add_argument("--format", dest="formats", action="append", required=True)
    metagame.add_argument("--day", dest="generated_for_day")

    deck_texts = subparsers.add_parser("scrape-deck-texts")
    deck_texts.add_argument("--format", dest="formats", action="append", required=True)
    deck_texts.add_argument("--archetype", dest="archetypes", action="append")
    deck_texts.add_argument("--days", type=int)
    deck_texts.add_argument(
        "--source-filter", choices=["mtggoldfish", "mtgo", "both"], default="both"
    )

    decks = subparsers.add_parser("scrape-decks")
    decks.add_argument("--format", dest="formats", action="append", required=True)
    decks.add_argument("--archetype", dest="archetypes", action="append")
    decks.add_argument("--days", type=int)
    decks.add_argument("--source-filter", choices=["mtggoldfish", "mtgo", "both"], default="both")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    generated_at = _parse_timestamp(args.timestamp)
    output_root = Path(args.output_root)

    if args.command == "scrape-archetypes":
        for format_name in args.formats:
            archetypes = _selected_archetypes(format_name, None)
            _write_archetype_list_snapshot(
                output_root=output_root,
                generated_at=generated_at,
                retention_days=args.retention_days,
                format_name=format_name,
                archetypes=archetypes,
            )
    elif args.command == "scrape-metagame":
        generated_for_day = _parse_day(generated_at, args.generated_for_day)
        for format_name in args.formats:
            _write_metagame_snapshot(
                output_root=output_root,
                generated_at=generated_at,
                retention_days=args.retention_days,
                format_name=format_name,
                generated_for_day=generated_for_day,
            )
    elif args.command == "scrape-deck-texts":
        for format_name in args.formats:
            _write_deck_text_blobs(
                output_root=output_root,
                generated_at=generated_at,
                retention_days=args.retention_days,
                format_name=format_name,
                archetype_filters=args.archetypes,
                days=args.days,
                source_filter=None if args.source_filter == "both" else args.source_filter,
            )
    elif args.command == "scrape-decks":
        for format_name in args.formats:
            _write_archetype_deck_snapshots(
                output_root=output_root,
                generated_at=generated_at,
                retention_days=args.retention_days,
                format_name=format_name,
                archetype_filters=args.archetypes,
                days=args.days,
                source_filter=None if args.source_filter == "both" else args.source_filter,
            )
    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")

    logger.info("Wrote scrape artifacts to {}", output_root)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
