"""CLI entrypoint for headless scrape publishing."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
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
    build_run_manifest,
    validate_archetype_deck_snapshot,
    validate_archetype_list_snapshot,
    validate_deck_text_blob,
    validate_metagame_snapshot,
    validate_run_manifest,
)
from publisher.layout import (
    DEFAULT_MAX_STALE_HOURS,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_RETENTION_DAYS,
    daily_snapshot_dir,
    hourly_snapshot_dir,
    normalize_name,
    relative_posix_path,
    update_latest_manifest,
    write_json,
)
from scraping import ScrapingMetagameRepository, fetch_archetypes

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python 3.10 fallback
    UTC = timezone.utc  # noqa: UP017

STATUS_SUCCESS = "success"
STATUS_SKIPPED = "skipped"
STATUS_STALE_FALLBACK = "stale-fallback"
STATUS_HARD_FAILURE = "hard-failure"
HARD_FAILURE_STATES = {STATUS_HARD_FAILURE}
DEFAULT_DECK_DOWNLOAD_DELAY_SECONDS = 0.0


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str | None) -> str:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return _utc_now()


def _parse_day(timestamp: str, override: str | None = None) -> str:
    if override:
        return override
    return timestamp.split("T", 1)[0]


def _command_label(command: str, formats: list[str] | None) -> str:
    if not formats or len(formats) != 1:
        return command
    return f"{command}-{normalize_name(formats[0])}"


def _parse_deck_date(date_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _parse_generated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _load_json_if_present(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_reusable_deck_text_blob(
    path: Path, *, format_name: str, deck_id: str
) -> dict[str, Any] | None:
    payload = _load_json_if_present(path)
    if not payload:
        return None
    try:
        validated = validate_deck_text_blob(payload)
    except ValueError:
        return None
    if validated.get("format") != format_name or validated.get("deck_id") != deck_id:
        return None
    return validated


def _is_path_fresh(path: Path, *, generated_at: str, max_stale_hours: int) -> bool:
    payload = _load_json_if_present(path)
    if not payload:
        return False
    existing_generated_at = _parse_generated_at(payload.get("generated_at"))
    current_generated_at = _parse_generated_at(generated_at)
    if existing_generated_at is None or current_generated_at is None:
        return False
    return current_generated_at - existing_generated_at <= timedelta(hours=max_stale_hours)


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


def _deck_text_archive_path(output_root: Path, format_name: str, deck_id: str) -> Path:
    return output_root / "archive" / "deck-texts" / format_name / f"{deck_id}.json"


def _with_deck_text_refs(
    decks: list[dict[str, Any]], *, output_root: Path, format_name: str
) -> list[dict[str, Any]]:
    enriched = []
    for deck in decks:
        deck_id = str(deck.get("number", "")).strip()
        entry = dict(deck)
        if deck_id:
            entry["deck_text_path"] = relative_posix_path(
                _deck_text_archive_path(output_root, format_name, deck_id),
                output_root,
            )
        enriched.append(entry)
    return enriched


class RunRecorder:
    def __init__(
        self,
        *,
        output_root: Path,
        command: str,
        generated_at: str,
        retention_days: int,
        max_stale_hours: int,
    ) -> None:
        self.output_root = output_root
        self.command = command
        self.generated_at = generated_at
        self.retention_days = retention_days
        self.max_stale_hours = max_stale_hours
        self.results: list[dict[str, Any]] = []

    def add(
        self,
        *,
        scope: str,
        status: str,
        format_name: str | None = None,
        archetype: str | None = None,
        deck_id: str | None = None,
        path: str | None = None,
        message: str | None = None,
    ) -> None:
        result: dict[str, Any] = {"scope": scope, "status": status}
        if format_name:
            result["format"] = format_name
        if archetype:
            result["archetype"] = archetype
        if deck_id:
            result["deck_id"] = deck_id
        if path:
            result["path"] = path
        if message:
            result["message"] = message
        self.results.append(result)

    def write(self) -> tuple[Path, dict[str, Any]]:
        summary = Counter(result["status"] for result in self.results)
        overall_status = STATUS_HARD_FAILURE if summary[STATUS_HARD_FAILURE] else STATUS_SUCCESS
        manifest = build_run_manifest(
            generated_at=self.generated_at,
            command=self.command,
            status=overall_status,
            max_stale_hours=self.max_stale_hours,
            results=self.results,
            summary=dict(summary),
        )
        validate_run_manifest(manifest)
        latest_path = self.output_root / "latest" / "runs" / f"{self.command}.json"
        run_path = (
            hourly_snapshot_dir(self.output_root, self.generated_at)
            / "runs"
            / f"{self.command}.json"
        )
        write_json(latest_path, manifest)
        write_json(run_path, manifest)
        update_latest_manifest(
            self.output_root,
            generated_at=self.generated_at,
            retention_days=self.retention_days,
            category="runs",
            discriminator={"format": self.command},
            relative_path=relative_posix_path(latest_path, self.output_root),
        )
        logger.info(
            "Run {} summary: success={}, skipped={}, stale-fallback={}, hard-failure={}",
            self.command,
            summary[STATUS_SUCCESS],
            summary[STATUS_SKIPPED],
            summary[STATUS_STALE_FALLBACK],
            summary[STATUS_HARD_FAILURE],
        )
        return latest_path, manifest


def _selected_archetypes(
    *,
    output_root: Path,
    generated_at: str,
    max_stale_hours: int,
    recorder: RunRecorder,
    format_name: str,
) -> list[dict[str, Any]]:
    normalized_format = normalize_name(format_name)
    latest_path = output_root / "latest" / "archetypes" / f"{normalized_format}.json"
    try:
        archetypes = sorted(
            fetch_archetypes(format_name, allow_stale=True),
            key=lambda item: (item.get("name", "").lower(), item.get("href", "").lower()),
        )
        if not archetypes:
            raise RuntimeError(f"Archetype scrape returned no rows for {format_name}")
        snapshot = build_archetype_list_snapshot(
            generated_at=generated_at,
            format_name=normalized_format,
            source="mtggoldfish",
            archetypes=archetypes,
        )
        validate_archetype_list_snapshot(snapshot)
        hourly_path = (
            hourly_snapshot_dir(output_root, generated_at)
            / "archetypes"
            / f"{normalized_format}.json"
        )
        write_json(latest_path, snapshot)
        write_json(hourly_path, snapshot)
        update_latest_manifest(
            output_root,
            generated_at=generated_at,
            retention_days=recorder.retention_days,
            category="archetype_lists",
            discriminator={"format": normalized_format},
            relative_path=relative_posix_path(latest_path, output_root),
        )
        recorder.add(
            scope="archetype-list",
            status=STATUS_SUCCESS,
            format_name=normalized_format,
            path=relative_posix_path(latest_path, output_root),
        )
        return archetypes
    except Exception as exc:  # noqa: BLE001
        existing = _load_json_if_present(latest_path)
        if existing and _is_path_fresh(
            latest_path,
            generated_at=generated_at,
            max_stale_hours=max_stale_hours,
        ):
            recorder.add(
                scope="archetype-list",
                status=STATUS_STALE_FALLBACK,
                format_name=normalized_format,
                path=relative_posix_path(latest_path, output_root),
                message=str(exc),
            )
            return list(existing.get("archetypes", []))
        recorder.add(
            scope="archetype-list",
            status=STATUS_HARD_FAILURE,
            format_name=normalized_format,
            path=relative_posix_path(latest_path, output_root),
            message=str(exc),
        )
        return []


def _filter_requested_archetypes(
    archetypes: list[dict[str, Any]], archetype_filters: list[str] | None
) -> list[dict[str, Any]]:
    if not archetype_filters:
        return archetypes
    wanted = {normalize_name(value) for value in archetype_filters}
    return [item for item in archetypes if normalize_name(item.get("name", "")) in wanted]


def _write_metagame_snapshot(
    *,
    output_root: Path,
    generated_at: str,
    recorder: RunRecorder,
    max_stale_hours: int,
    format_name: str,
    generated_for_day: str,
) -> None:
    normalized_format = normalize_name(format_name)
    latest_path = output_root / "latest" / "metagame" / f"{normalized_format}.json"
    try:
        raw_stats = get_archetype_stats(format_name)
        format_stats = raw_stats.get(format_name.lower(), {})
        if not format_stats:
            raise RuntimeError(f"Metagame scrape returned no stats for {format_name}")
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
        snapshot = build_metagame_snapshot(
            generated_at=generated_at,
            format_name=normalized_format,
            source="mtggoldfish",
            generated_for_day=generated_for_day,
            stats=stats_rows,
        )
        validate_metagame_snapshot(snapshot)
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
            retention_days=recorder.retention_days,
            category="metagame_daily",
            discriminator={"format": normalized_format},
            relative_path=relative_posix_path(latest_path, output_root),
        )
        recorder.add(
            scope="metagame",
            status=STATUS_SUCCESS,
            format_name=normalized_format,
            path=relative_posix_path(latest_path, output_root),
        )
    except Exception as exc:  # noqa: BLE001
        if _is_path_fresh(latest_path, generated_at=generated_at, max_stale_hours=max_stale_hours):
            recorder.add(
                scope="metagame",
                status=STATUS_STALE_FALLBACK,
                format_name=normalized_format,
                path=relative_posix_path(latest_path, output_root),
                message=str(exc),
            )
            return
        recorder.add(
            scope="metagame",
            status=STATUS_HARD_FAILURE,
            format_name=normalized_format,
            path=relative_posix_path(latest_path, output_root),
            message=str(exc),
        )


def _write_archetype_deck_snapshots(
    *,
    output_root: Path,
    generated_at: str,
    recorder: RunRecorder,
    max_stale_hours: int,
    format_name: str,
    archetype_filters: list[str] | None,
    days: int | None,
    source_filter: str | None,
) -> list[dict[str, Any]]:
    repo = ScrapingMetagameRepository()
    normalized_format = normalize_name(format_name)
    archetypes = _filter_requested_archetypes(
        _selected_archetypes(
            output_root=output_root,
            generated_at=generated_at,
            max_stale_hours=max_stale_hours,
            recorder=recorder,
            format_name=format_name,
        ),
        archetype_filters,
    )
    if archetype_filters and not archetypes:
        recorder.add(
            scope="archetype-decks",
            status=STATUS_SKIPPED,
            format_name=normalized_format,
            message="No requested archetypes matched the current archetype list.",
        )
        return []

    selected_decks: list[dict[str, Any]] = []
    for archetype in archetypes:
        archetype_slug = normalize_name(archetype["name"])
        latest_path = (
            output_root / "latest" / "decks" / normalized_format / f"{archetype_slug}.json"
        )
        try:
            decks = repo.get_decks_for_archetype(
                archetype,
                force_refresh=True,
                source_filter=source_filter,
            )
            filtered_decks = _filter_recent_decks(decks, days)
            if decks and days is not None and not filtered_decks:
                snapshot = build_archetype_deck_snapshot(
                    generated_at=generated_at,
                    format_name=normalized_format,
                    archetype=archetype,
                    source=source_filter or "both",
                    decks=[],
                )
                validate_archetype_deck_snapshot(snapshot)
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
                    retention_days=recorder.retention_days,
                    category="archetype_decks",
                    discriminator={"format": normalized_format, "archetype": archetype_slug},
                    relative_path=relative_posix_path(latest_path, output_root),
                )
                recorder.add(
                    scope="archetype-decks",
                    status=STATUS_SKIPPED,
                    format_name=normalized_format,
                    archetype=archetype_slug,
                    path=relative_posix_path(latest_path, output_root),
                    message=f"No decks found within the last {days} days.",
                )
                continue
            recent_decks = sorted(
                _with_deck_text_refs(
                    filtered_decks,
                    output_root=output_root,
                    format_name=normalized_format,
                ),
                key=lambda item: (
                    item.get("date", ""),
                    item.get("number", ""),
                    item.get("player", ""),
                ),
                reverse=True,
            )
            if not recent_decks:
                raise RuntimeError(f"Deck scrape returned no rows for {archetype['name']}")
            snapshot = build_archetype_deck_snapshot(
                generated_at=generated_at,
                format_name=normalized_format,
                archetype=archetype,
                source=source_filter or "both",
                decks=recent_decks,
            )
            validate_archetype_deck_snapshot(snapshot)
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
                retention_days=recorder.retention_days,
                category="archetype_decks",
                discriminator={"format": normalized_format, "archetype": archetype_slug},
                relative_path=relative_posix_path(latest_path, output_root),
            )
            recorder.add(
                scope="archetype-decks",
                status=STATUS_SUCCESS,
                format_name=normalized_format,
                archetype=archetype_slug,
                path=relative_posix_path(latest_path, output_root),
            )
            selected_decks.extend(recent_decks)
        except Exception as exc:  # noqa: BLE001
            if _is_path_fresh(
                latest_path, generated_at=generated_at, max_stale_hours=max_stale_hours
            ):
                recorder.add(
                    scope="archetype-decks",
                    status=STATUS_STALE_FALLBACK,
                    format_name=normalized_format,
                    archetype=archetype_slug,
                    path=relative_posix_path(latest_path, output_root),
                    message=str(exc),
                )
                existing = _load_json_if_present(latest_path) or {}
                selected_decks.extend(existing.get("decks", []))
                continue
            recorder.add(
                scope="archetype-decks",
                status=STATUS_HARD_FAILURE,
                format_name=normalized_format,
                archetype=archetype_slug,
                path=relative_posix_path(latest_path, output_root),
                message=str(exc),
            )
    return selected_decks


def _write_deck_text_blobs(
    *,
    output_root: Path,
    generated_at: str,
    recorder: RunRecorder,
    max_stale_hours: int,
    format_name: str,
    archetype_filters: list[str] | None,
    days: int | None,
    source_filter: str | None,
    deck_download_delay_seconds: float,
) -> None:
    repo = ScrapingMetagameRepository()
    normalized_format = normalize_name(format_name)
    decks = _write_archetype_deck_snapshots(
        output_root=output_root,
        generated_at=generated_at,
        recorder=recorder,
        max_stale_hours=max_stale_hours,
        format_name=format_name,
        archetype_filters=archetype_filters,
        days=days,
        source_filter=source_filter,
    )
    unique_decks: dict[str, dict[str, Any]] = {}
    for deck in decks:
        deck_id = str(deck.get("number", "")).strip()
        if deck_id:
            unique_decks.setdefault(deck_id, deck)

    if not unique_decks:
        recorder.add(
            scope="deck-text",
            status=STATUS_SKIPPED,
            format_name=normalized_format,
            message="No deck IDs were available for deck-text publishing.",
        )
        return

    for index, (deck_id, deck) in enumerate(sorted(unique_decks.items())):
        archive_path = _deck_text_archive_path(output_root, normalized_format, deck_id)
        try:
            reused_blob = _load_reusable_deck_text_blob(
                archive_path,
                format_name=normalized_format,
                deck_id=deck_id,
            )
            if reused_blob is not None:
                update_latest_manifest(
                    output_root,
                    generated_at=generated_at,
                    retention_days=recorder.retention_days,
                    category="deck_text_blobs",
                    discriminator={"format": normalized_format, "deck_id": deck_id},
                    relative_path=relative_posix_path(archive_path, output_root),
                )
                recorder.add(
                    scope="deck-text",
                    status=STATUS_SKIPPED,
                    format_name=normalized_format,
                    deck_id=deck_id,
                    path=relative_posix_path(archive_path, output_root),
                    message="Reused existing published deck-text blob.",
                )
                continue
            if index > 0 and deck_download_delay_seconds > 0:
                logger.info(
                    "Sleeping {} seconds before downloading deck {}",
                    deck_download_delay_seconds,
                    deck_id,
                )
                time.sleep(deck_download_delay_seconds)
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
            update_latest_manifest(
                output_root,
                generated_at=generated_at,
                retention_days=recorder.retention_days,
                category="deck_text_blobs",
                discriminator={"format": normalized_format, "deck_id": deck_id},
                relative_path=relative_posix_path(archive_path, output_root),
            )
            recorder.add(
                scope="deck-text",
                status=STATUS_SUCCESS,
                format_name=normalized_format,
                deck_id=deck_id,
                path=relative_posix_path(archive_path, output_root),
            )
        except Exception as exc:  # noqa: BLE001
            if _is_path_fresh(
                archive_path, generated_at=generated_at, max_stale_hours=max_stale_hours
            ):
                recorder.add(
                    scope="deck-text",
                    status=STATUS_STALE_FALLBACK,
                    format_name=normalized_format,
                    deck_id=deck_id,
                    path=relative_posix_path(archive_path, output_root),
                    message=str(exc),
                )
                continue
            recorder.add(
                scope="deck-text",
                status=STATUS_HARD_FAILURE,
                format_name=normalized_format,
                deck_id=deck_id,
                path=relative_posix_path(archive_path, output_root),
                message=str(exc),
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Headless scrape publisher")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--timestamp", help="UTC timestamp for deterministic output naming")
    parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    parser.add_argument("--max-stale-hours", type=int, default=DEFAULT_MAX_STALE_HOURS)
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
        "--deck-download-delay-seconds",
        type=float,
        default=DEFAULT_DECK_DOWNLOAD_DELAY_SECONDS,
    )
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
    command_label = _command_label(args.command, getattr(args, "formats", None))
    recorder = RunRecorder(
        output_root=output_root,
        command=command_label,
        generated_at=generated_at,
        retention_days=args.retention_days,
        max_stale_hours=args.max_stale_hours,
    )

    if args.command == "scrape-archetypes":
        for format_name in args.formats:
            _selected_archetypes(
                output_root=output_root,
                generated_at=generated_at,
                max_stale_hours=args.max_stale_hours,
                recorder=recorder,
                format_name=format_name,
            )
    elif args.command == "scrape-metagame":
        generated_for_day = _parse_day(generated_at, args.generated_for_day)
        for format_name in args.formats:
            _write_metagame_snapshot(
                output_root=output_root,
                generated_at=generated_at,
                recorder=recorder,
                max_stale_hours=args.max_stale_hours,
                format_name=format_name,
                generated_for_day=generated_for_day,
            )
    elif args.command == "scrape-deck-texts":
        for format_name in args.formats:
            _write_deck_text_blobs(
                output_root=output_root,
                generated_at=generated_at,
                recorder=recorder,
                max_stale_hours=args.max_stale_hours,
                format_name=format_name,
                archetype_filters=args.archetypes,
                days=args.days,
                source_filter=None if args.source_filter == "both" else args.source_filter,
                deck_download_delay_seconds=args.deck_download_delay_seconds,
            )
    elif args.command == "scrape-decks":
        for format_name in args.formats:
            _write_archetype_deck_snapshots(
                output_root=output_root,
                generated_at=generated_at,
                recorder=recorder,
                max_stale_hours=args.max_stale_hours,
                format_name=format_name,
                archetype_filters=args.archetypes,
                days=args.days,
                source_filter=None if args.source_filter == "both" else args.source_filter,
            )
    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")

    run_manifest_path, run_manifest = recorder.write()
    logger.info("Wrote scrape artifacts to {}", output_root)
    return 1 if run_manifest["status"] in HARD_FAILURE_STATES else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
