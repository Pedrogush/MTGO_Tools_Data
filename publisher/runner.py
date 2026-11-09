"""CLI entrypoint for headless scrape publishing.

Every product is sourced from the Videre Project API. ``scrape-mtgo-decklists``
is the only command that talks to the network; the others derive their output
from the ``latest/mtgo-decklists/<format>.json`` snapshot it publishes (see
``publisher.mtgo_archive``).
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from publisher.contracts import (
    build_archetype_deck_snapshot,
    build_archetype_list_snapshot,
    build_archetype_radar_snapshot,
    build_deck_text_blob,
    build_format_card_pool_snapshot,
    build_metagame_snapshot,
    build_mtgo_decklists_snapshot,
    build_run_manifest,
    validate_archetype_deck_snapshot,
    validate_archetype_list_snapshot,
    validate_archetype_radar_snapshot,
    validate_deck_text_blob,
    validate_format_card_pool_snapshot,
    validate_metagame_snapshot,
    validate_mtgo_decklists_snapshot,
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
from publisher.mtgo_archive import (
    MTGO_SOURCE,
    UNKNOWN_SLUG,
    MtgoArchiveRepository,
    canonical_archetype,
    preferred_display_names,
)
from scraping.mtgo import fetch_event
from services.mtgo_background_service import (
    deck_to_text,
    fetch_mtgo_events_for_period,
    save_mtgo_deck_metadata,
)
from services.radar_service import RadarService
from utils.constants import (
    METAGAME_STATS_LOOKBACK_DAYS,
    MTGO_BACKGROUND_FETCH_DAYS,
    MTGO_LEAGUE_REFRESH_WINDOW_DAYS,
)
from utils.deck_text_cache import get_deck_cache

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python 3.10 fallback
    UTC = timezone.utc  # noqa: UP017

STATUS_SUCCESS = "success"
STATUS_CACHED = "cached"
STATUS_SKIPPED = "skipped"
STATUS_STALE_FALLBACK = "stale-fallback"
STATUS_HARD_FAILURE = "hard-failure"
HARD_FAILURE_STATES = {STATUS_HARD_FAILURE}
DEFAULT_MTGO_EVENT_DELAY_SECONDS = 1.0
VIDERE_SOURCE = "videre-api"
# Event archives record which taxonomy their deck rows' archetype names use.
# Archives written before the MTGGoldfish source was removed carry names that
# were rewritten onto MTGGoldfish's taxonomy; those are re-fetched once rather
# than reused, so a format never mixes the two vocabularies.
ARCHETYPE_TAXONOMY = "videre"


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


def _deck_text_archive_path(output_root: Path, format_name: str, deck_id: str) -> Path:
    return output_root / "archive" / "deck-texts" / format_name / f"{deck_id}.json"


def _mtgo_event_archive_path(output_root: Path, format_name: str, event_id: str) -> Path:
    return output_root / "archive" / "mtgo-decklists" / format_name / f"{event_id}.json"


def _remove_legacy_event_archives(output_root: Path, format_name: str, event_id: str) -> None:
    """Drop pre-rename copies of an event archive.

    Archives were once named ``<slug><event_id>.json`` and recorded that same
    slug form as their payload ``event_id``. Both copies are still read by
    everything that walks the archive - ``client_bundle.collect_bundle_sources``
    included - so the event's decks get counted twice. Re-archiving an event is
    the natural moment to retire its old copy; see
    ``scripts/dedupe_mtgo_archive.py`` for the one-off backfill.
    """
    canonical = _mtgo_event_archive_path(output_root, format_name, event_id)
    for path in canonical.parent.glob(f"*{event_id}.json"):
        if path != canonical:
            path.unlink(missing_ok=True)


def _mtgo_event_id(event: dict[str, Any]) -> str:
    """Filesystem-safe archive id for a Videre event row (league ids are negative)."""
    raw = str(event.get("id", "")).strip()
    return raw.replace("-", "n", 1) if raw.startswith("-") else (raw or "unknown-event")


def _is_recent_league_event(event: dict[str, Any], generated_at: str) -> bool:
    """League dumps grow during the day, so a fresh archive can be partial."""
    if str(event.get("kind") or "").lower() != "league":
        return False
    event_date = _parse_deck_date(str(event.get("date", ""))[:10])
    reference = _parse_generated_at(generated_at)
    if event_date is None or reference is None:
        return True
    return reference.replace(tzinfo=None) - event_date <= timedelta(
        days=MTGO_LEAGUE_REFRESH_WINDOW_DAYS
    )


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
            "Run {} summary: success={}, cached={}, skipped={}, stale-fallback={}, hard-failure={}",
            self.command,
            summary[STATUS_SUCCESS],
            summary[STATUS_CACHED],
            summary[STATUS_SKIPPED],
            summary[STATUS_STALE_FALLBACK],
            summary[STATUS_HARD_FAILURE],
        )
        return latest_path, manifest


def _archive_repository(
    output_root: Path, format_name: str, generated_at: str, *, days: int | None = None
) -> MtgoArchiveRepository:
    # One window for every product derived in a run: the archetype list and
    # the deck snapshots must agree on which decks count, or an archetype
    # whose decks sit on the window's first day is listed with no decks.
    return MtgoArchiveRepository(
        output_root,
        format_name,
        days=days or MTGO_BACKGROUND_FETCH_DAYS,
        reference_time=_parse_generated_at(generated_at),
    )


def _selected_archetypes(
    *,
    output_root: Path,
    generated_at: str,
    max_stale_hours: int,
    recorder: RunRecorder,
    format_name: str,
    repo: MtgoArchiveRepository | None = None,
) -> list[dict[str, Any]]:
    normalized_format = normalize_name(format_name)
    latest_path = output_root / "latest" / "archetypes" / f"{normalized_format}.json"
    try:
        repo = repo or _archive_repository(output_root, format_name, generated_at)
        archetypes = repo.get_archetypes()
        if not archetypes:
            raise RuntimeError(f"No MTGO decks in the window yield archetypes for {format_name}")
        snapshot = build_archetype_list_snapshot(
            generated_at=generated_at,
            format_name=normalized_format,
            source=VIDERE_SOURCE,
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
        day_anchor = datetime.strptime(generated_for_day, "%Y-%m-%d")
        lookback_dates = [
            (day_anchor - timedelta(days=offset)).strftime("%Y-%m-%d")
            for offset in range(METAGAME_STATS_LOOKBACK_DAYS)
        ]
        stats_rows = _archive_repository(
            output_root, format_name, generated_at
        ).get_archetype_stats(lookback_dates=lookback_dates)
        if not stats_rows:
            raise RuntimeError(f"No MTGO decks in the window yield metagame stats for {format_name}")
        snapshot = build_metagame_snapshot(
            generated_at=generated_at,
            format_name=normalized_format,
            source=VIDERE_SOURCE,
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


def _write_deck_snapshot_file(
    *,
    output_root: Path,
    generated_at: str,
    recorder: RunRecorder,
    normalized_format: str,
    archetype: dict[str, Any],
    archetype_slug: str,
    decks: list[dict[str, Any]],
) -> Path:
    latest_path = output_root / "latest" / "decks" / normalized_format / f"{archetype_slug}.json"
    snapshot = build_archetype_deck_snapshot(
        generated_at=generated_at,
        format_name=normalized_format,
        archetype=archetype,
        source=MTGO_SOURCE,
        decks=decks,
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
    return latest_path


def _write_archetype_deck_snapshots(
    *,
    output_root: Path,
    generated_at: str,
    recorder: RunRecorder,
    max_stale_hours: int,
    format_name: str,
    archetype_filters: list[str] | None,
    days: int | None,
    repo: MtgoArchiveRepository | None = None,
) -> list[dict[str, Any]]:
    normalized_format = normalize_name(format_name)
    repo = repo or _archive_repository(output_root, format_name, generated_at, days=days)
    archetypes = _filter_requested_archetypes(
        _selected_archetypes(
            output_root=output_root,
            generated_at=generated_at,
            max_stale_hours=max_stale_hours,
            recorder=recorder,
            format_name=format_name,
            repo=repo,
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
            decks = repo.get_decks_for_archetype(archetype)
            if not decks:
                raise RuntimeError(f"No MTGO decks found for {archetype['name']}")
            recent_decks = sorted(
                _with_deck_text_refs(
                    decks,
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
            _write_deck_snapshot_file(
                output_root=output_root,
                generated_at=generated_at,
                recorder=recorder,
                normalized_format=normalized_format,
                archetype=archetype,
                archetype_slug=archetype_slug,
                decks=recent_decks,
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
) -> None:
    normalized_format = normalize_name(format_name)
    repo = _archive_repository(output_root, format_name, generated_at, days=days)
    decks = _write_archetype_deck_snapshots(
        output_root=output_root,
        generated_at=generated_at,
        recorder=recorder,
        max_stale_hours=max_stale_hours,
        format_name=format_name,
        archetype_filters=archetype_filters,
        days=days,
        repo=repo,
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

    for deck_id, deck in sorted(unique_decks.items()):
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
            snapshot = build_deck_text_blob(
                generated_at=generated_at,
                format_name=normalized_format,
                deck_id=deck_id,
                source=MTGO_SOURCE,
                deck_name=deck.get("name", deck_id),
                deck_text=repo.download_deck_content(deck),
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


def _write_format_card_pool_snapshot(
    *,
    output_root: Path,
    generated_at: str,
    recorder: RunRecorder,
    max_stale_hours: int,
    format_name: str,
    loaded_decks: list[dict[str, str]],
    failed_decks: int,
) -> None:
    normalized_format = normalize_name(format_name)
    latest_path = output_root / "latest" / "card-pools" / f"{normalized_format}.json"
    radar_service = RadarService()

    try:
        if not loaded_decks:
            raise RuntimeError("No deck texts were available for format card-pool generation.")

        card_pool = radar_service.calculate_format_card_pool_from_deck_texts(
            format_name=normalized_format,
            deck_texts=[deck["deck_text"] for deck in loaded_decks],
            deck_names=[deck["deck_name"] for deck in loaded_decks],
            decks_failed=failed_decks,
        )
        snapshot = build_format_card_pool_snapshot(
            generated_at=generated_at,
            format_name=normalized_format,
            source="published-deck-texts",
            total_decks_analyzed=card_pool.total_decks_analyzed,
            decks_failed=card_pool.decks_failed,
            cards=card_pool.cards,
            copy_totals=[asdict(item) for item in card_pool.copy_totals],
        )
        validate_format_card_pool_snapshot(snapshot)
        hourly_path = (
            hourly_snapshot_dir(output_root, generated_at)
            / "card-pools"
            / f"{normalized_format}.json"
        )
        write_json(latest_path, snapshot)
        write_json(hourly_path, snapshot)
        update_latest_manifest(
            output_root,
            generated_at=generated_at,
            retention_days=recorder.retention_days,
            category="format_card_pools",
            discriminator={"format": normalized_format},
            relative_path=relative_posix_path(latest_path, output_root),
        )
        recorder.add(
            scope="format-card-pool",
            status=STATUS_SUCCESS,
            format_name=normalized_format,
            path=relative_posix_path(latest_path, output_root),
        )
    except Exception as exc:  # noqa: BLE001
        if _is_path_fresh(latest_path, generated_at=generated_at, max_stale_hours=max_stale_hours):
            recorder.add(
                scope="format-card-pool",
                status=STATUS_STALE_FALLBACK,
                format_name=normalized_format,
                path=relative_posix_path(latest_path, output_root),
                message=str(exc),
            )
            return
        recorder.add(
            scope="format-card-pool",
            status=STATUS_HARD_FAILURE,
            format_name=normalized_format,
            path=relative_posix_path(latest_path, output_root),
            message=str(exc),
        )


def _publish_archetype_radar_snapshot(
    *,
    output_root: Path,
    generated_at: str,
    recorder: RunRecorder,
    radar_service: RadarService,
    normalized_format: str,
    archetype: dict[str, Any],
    archetype_slug: str,
    latest_path: Path,
    loaded_decks: list[dict[str, str]],
    failed_decks: int,
) -> None:
    radar = radar_service.calculate_radar_from_deck_texts(
        archetype_name=archetype["name"],
        format_name=normalized_format,
        deck_texts=[deck["deck_text"] for deck in loaded_decks],
        deck_names=[deck["deck_name"] for deck in loaded_decks],
        decks_failed=failed_decks,
    )
    snapshot = build_archetype_radar_snapshot(
        generated_at=generated_at,
        format_name=normalized_format,
        archetype=archetype,
        source="published-deck-texts",
        total_decks_analyzed=radar.total_decks_analyzed,
        decks_failed=radar.decks_failed,
        mainboard_cards=[asdict(card) for card in radar.mainboard_cards],
        sideboard_cards=[asdict(card) for card in radar.sideboard_cards],
    )
    validate_archetype_radar_snapshot(snapshot)
    hourly_path = (
        hourly_snapshot_dir(output_root, generated_at)
        / "radars"
        / normalized_format
        / latest_path.name
    )
    write_json(latest_path, snapshot)
    write_json(hourly_path, snapshot)
    update_latest_manifest(
        output_root,
        generated_at=generated_at,
        retention_days=recorder.retention_days,
        category="archetype_radars",
        discriminator={"format": normalized_format, "archetype": archetype_slug},
        relative_path=relative_posix_path(latest_path, output_root),
    )
    recorder.add(
        scope="archetype-radar",
        status=STATUS_SUCCESS,
        format_name=normalized_format,
        archetype=archetype_slug,
        path=relative_posix_path(latest_path, output_root),
    )


def _radar_source_decks(rows: list[dict[str, Any]], display: str) -> list[dict[str, str]]:
    decks: list[dict[str, str]] = []
    for deck in rows:
        deck_id = str(deck.get("number", "")).strip()
        deck_text = str(deck.get("deck_text") or "")
        if not deck_id or not deck_text.strip():
            continue
        decks.append(
            {
                "dedupe_key": deck_id,
                "deck_id": deck_id,
                "deck_name": display,
                "deck_text": deck_text,
            }
        )
    return decks


def _write_archetype_radar_snapshots(
    *,
    output_root: Path,
    generated_at: str,
    recorder: RunRecorder,
    max_stale_hours: int,
    format_name: str,
    archetype_filters: list[str] | None,
    max_decks: int | None,
) -> None:
    normalized_format = normalize_name(format_name)
    repo = _archive_repository(output_root, format_name, generated_at)
    try:
        groups = repo.archetype_groups()
        if not groups:
            raise RuntimeError("The MTGO decklist snapshot holds no decks in the window.")
    except Exception as exc:  # noqa: BLE001
        recorder.add(
            scope="archetype-radar",
            status=STATUS_HARD_FAILURE,
            format_name=normalized_format,
            message=f"No MTGO decks were available for radar publishing: {exc}",
        )
        return

    wanted = {normalize_name(value) for value in archetype_filters or []}
    radar_slugs = [
        slug for slug in sorted(groups) if slug != UNKNOWN_SLUG and (not wanted or slug in wanted)
    ]
    if archetype_filters and not radar_slugs:
        recorder.add(
            scope="archetype-radar",
            status=STATUS_SKIPPED,
            format_name=normalized_format,
            message="No requested archetypes matched the current MTGO decks.",
        )
        return

    radar_service = RadarService()
    for slug in radar_slugs:
        display, rows = groups[slug]
        latest_path = output_root / "latest" / "radars" / normalized_format / f"{slug}.json"
        loaded_decks = _radar_source_decks(rows, display)
        if max_decks is not None:
            loaded_decks = loaded_decks[:max_decks]
        try:
            if not loaded_decks:
                raise RuntimeError("No deck texts were available for radar generation.")
            _publish_archetype_radar_snapshot(
                output_root=output_root,
                generated_at=generated_at,
                recorder=recorder,
                radar_service=radar_service,
                normalized_format=normalized_format,
                archetype=repo.archetype_entry(slug, display),
                archetype_slug=slug,
                latest_path=latest_path,
                loaded_decks=loaded_decks,
                failed_decks=0,
            )
        except Exception as exc:  # noqa: BLE001
            if _is_path_fresh(
                latest_path,
                generated_at=generated_at,
                max_stale_hours=max_stale_hours,
            ):
                recorder.add(
                    scope="archetype-radar",
                    status=STATUS_STALE_FALLBACK,
                    format_name=normalized_format,
                    archetype=slug,
                    path=relative_posix_path(latest_path, output_root),
                    message=str(exc),
                )
                continue
            recorder.add(
                scope="archetype-radar",
                status=STATUS_HARD_FAILURE,
                format_name=normalized_format,
                archetype=slug,
                path=relative_posix_path(latest_path, output_root),
                message=str(exc),
            )

    if archetype_filters:
        recorder.add(
            scope="format-card-pool",
            status=STATUS_SKIPPED,
            format_name=normalized_format,
            message="Skipped format card-pool publication because archetype filters produce a partial format artifact.",
        )
        return

    # Unclassified decks have no meaningful radar but still belong in the pool.
    _write_format_card_pool_snapshot(
        output_root=output_root,
        generated_at=generated_at,
        recorder=recorder,
        max_stale_hours=max_stale_hours,
        format_name=format_name,
        loaded_decks=[
            deck
            for display, rows in groups.values()
            for deck in _radar_source_decks(rows, display)
        ],
        failed_decks=0,
    )


def _write_mtgo_decklist_snapshots(
    *,
    output_root: Path,
    generated_at: str,
    recorder: RunRecorder,
    max_stale_hours: int,
    format_name: str,
    days: int,
    event_delay_seconds: float,
) -> None:
    normalized_format = normalize_name(format_name)
    latest_path = output_root / "latest" / "mtgo-decklists" / f"{normalized_format}.json"
    deck_cache = get_deck_cache()
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    try:
        events = fetch_mtgo_events_for_period(
            start_date=start_date,
            end_date=end_date,
            mtg_format=normalized_format,
        )
        archived_events: list[dict[str, Any]] = []

        for index, event in enumerate(events):
            if not str(event.get("id", "")).strip():
                recorder.add(
                    scope="mtgo-event",
                    status=STATUS_HARD_FAILURE,
                    format_name=normalized_format,
                    message="Encountered MTGO event entry without an id.",
                )
                continue

            event_id = _mtgo_event_id(event)
            event_url = f"https://api.videreproject.com/decks?event_id={event['id']}"
            archive_path = _mtgo_event_archive_path(output_root, normalized_format, event_id)
            if archive_path.exists() and not _is_recent_league_event(event, generated_at):
                try:
                    existing = json.loads(archive_path.read_text(encoding="utf-8"))
                    if existing.get("archetype_taxonomy") != ARCHETYPE_TAXONOMY:
                        raise ValueError("archive predates Videre archetype names")
                    decks = existing.get("decks", [])
                    for deck in decks:
                        deck_id = str(deck.get("number", "")).strip()
                        deck_text = deck.get("deck_text", "")
                        archetype = deck.get("archetype", "Unknown")
                        if deck_id and deck_text:
                            deck_cache.set(deck_id, deck_text, source="mtgo")
                        save_mtgo_deck_metadata(archetype, normalized_format, deck)
                    relative_archive_path = relative_posix_path(archive_path, output_root)
                    archived_events.append(
                        {
                            "id": event_id,
                            "url": event_url,
                            "title": existing.get("event_title", "MTGO Event"),
                            "publish_date": existing.get("publish_date", generated_at),
                            "event_type": existing.get("event_type", "unknown"),
                            "decks_total": existing.get("decks_total", 0),
                            "decks_cached": existing.get("decks_cached", 0),
                            "path": relative_archive_path,
                            "decks": decks,
                        }
                    )
                    recorder.add(
                        scope="mtgo-event",
                        status=STATUS_CACHED,
                        format_name=normalized_format,
                        path=relative_archive_path,
                        message=f"Loaded {len(decks)} decks from archive.",
                    )
                except Exception as exc:
                    logger.warning("Failed to load archive for {}: {}; will fetch live.", event_url, exc)
                else:
                    continue

            try:
                payload = fetch_event(event)
                clean_decks = payload.get("decks", [])
                if not clean_decks:
                    logger.warning("Event {} returned no decklists, skipping.", event_url)
                    recorder.add(
                        scope="mtgo-event",
                        status=STATUS_SKIPPED,
                        format_name=normalized_format,
                        message=f"{event_url}: Event returned no decklists.",
                    )
                    continue
                event_date = payload.get("publish_date") or str(event.get("date", ""))[:10] or generated_at
                event_title = payload.get("title") or event.get("name") or "MTGO Event"
                decks_cached = 0
                deck_metadata_rows: list[dict[str, Any]] = []

                for clean_deck in clean_decks:
                    deck_id = str(clean_deck.get("deck_id") or "").strip()
                    if not deck_id:
                        continue

                    if deck_cache.set(deck_id, deck_to_text(clean_deck), source="mtgo"):
                        decks_cached += 1

                    wins = str(clean_deck.get("wins", "?")).strip() or "?"
                    losses = str(clean_deck.get("losses", "?")).strip() or "?"
                    archetype, archetype_href = canonical_archetype(
                        clean_deck.get("archetype"), normalized_format
                    )
                    deck_metadata = {
                        "number": deck_id,
                        "date": event_date,
                        "event": event_title,
                        "result": "?" if wins == "?" and losses == "?" else f"{wins}-{losses}",
                        "player": clean_deck.get("player", "Unknown"),
                        "archetype": archetype,
                        "archetype_href": archetype_href,
                        "archetype_id": clean_deck.get("archetype_id"),
                        "name": archetype,
                        "source": MTGO_SOURCE,
                        "format": normalized_format,
                        "deck_text": deck_to_text(clean_deck).rstrip("\n"),
                    }
                    save_mtgo_deck_metadata(archetype, normalized_format, deck_metadata)
                    deck_metadata_rows.append(deck_metadata)

                event_snapshot = {
                    "schema_version": "1",
                    "kind": "mtgo_event_decklists",
                    "generated_at": generated_at,
                    "format": normalized_format,
                    "event_id": event_id,
                    "archetype_taxonomy": ARCHETYPE_TAXONOMY,
                    "event_url": event_url,
                    "event_title": event_title,
                    "publish_date": event_date,
                    "event_type": payload.get("event_type", "unknown"),
                    "decks_total": len(clean_decks),
                    "decks_cached": decks_cached,
                    "decks": deck_metadata_rows,
                }
                write_json(archive_path, event_snapshot)
                _remove_legacy_event_archives(output_root, normalized_format, event_id)
                relative_archive_path = relative_posix_path(archive_path, output_root)
                recorder.add(
                    scope="mtgo-event",
                    status=STATUS_SUCCESS,
                    format_name=normalized_format,
                    path=relative_archive_path,
                    message=f"Cached {decks_cached}/{len(clean_decks)} decks.",
                )
                archived_events.append(
                    {
                        "id": event_id,
                        "url": event_url,
                        "title": event_title,
                        "publish_date": event_date,
                        "event_type": payload.get("event_type", "unknown"),
                        "decks_total": len(clean_decks),
                        "decks_cached": decks_cached,
                        "path": relative_archive_path,
                        "decks": deck_metadata_rows,
                    }
                )
                if index < len(events) - 1 and event_delay_seconds > 0:
                    time.sleep(event_delay_seconds)
            except Exception as exc:  # noqa: BLE001
                if archive_path.exists():
                    try:
                        existing = json.loads(archive_path.read_text(encoding="utf-8"))
                        archived_events.append(
                            {
                                "id": event_id,
                                "url": event_url,
                                "title": existing.get("event_title", "MTGO Event"),
                                "publish_date": existing.get("publish_date", generated_at),
                                "event_type": existing.get("event_type", "unknown"),
                                "decks_total": existing.get("decks_total", 0),
                                "decks_cached": existing.get("decks_cached", 0),
                                "path": relative_posix_path(archive_path, output_root),
                                "decks": existing.get("decks", []),
                            }
                        )
                        recorder.add(
                            scope="mtgo-event",
                            status=STATUS_STALE_FALLBACK,
                            format_name=normalized_format,
                            path=relative_posix_path(archive_path, output_root),
                            message=f"{event_url}: fetch failed, using existing archive. Error: {exc}",
                        )
                    except Exception:
                        recorder.add(
                            scope="mtgo-event",
                            status=STATUS_SKIPPED,
                            format_name=normalized_format,
                            message=f"{event_url}: fetch failed and archive unreadable; will retry next run. Error: {exc}",
                        )
                else:
                    # A single unreachable event is not a freshness violation:
                    # the snapshot still publishes and the 7-day window retries
                    # the event on the next scheduled run.
                    recorder.add(
                        scope="mtgo-event",
                        status=STATUS_SKIPPED,
                        format_name=normalized_format,
                        message=f"{event_url}: fetch failed; will retry next run. Error: {exc}",
                    )

        if events and not archived_events:
            raise RuntimeError(
                "Failed to persist any MTGO events for this format; see run results for failures."
            )

        # One display name and href per archetype slug across the window, so
        # the client's exact-name match between deck rows and the archetype
        # list holds even if Videre's spelling of a label drifts between
        # events. Idempotent for rows that are already canonical.
        window_decks = [deck for event in archived_events for deck in event.get("decks", [])]
        display_names = preferred_display_names(
            str(deck.get("archetype") or deck.get("name") or "") for deck in window_decks
        )
        for deck in window_decks:
            display, _href = canonical_archetype(
                deck.get("archetype") or deck.get("name"), normalized_format
            )
            archetype, archetype_href = canonical_archetype(
                display_names.get(normalize_name(display), display), normalized_format
            )
            deck["archetype"] = archetype
            deck["name"] = archetype
            deck["archetype_href"] = archetype_href

        snapshot = build_mtgo_decklists_snapshot(
            generated_at=generated_at,
            format_name=normalized_format,
            source=VIDERE_SOURCE,
            days=days,
            events=archived_events,
        )
        validate_mtgo_decklists_snapshot(snapshot)
        hourly_path = (
            hourly_snapshot_dir(output_root, generated_at)
            / "mtgo-decklists"
            / f"{normalized_format}.json"
        )
        write_json(latest_path, snapshot)
        write_json(hourly_path, snapshot)
        update_latest_manifest(
            output_root,
            generated_at=generated_at,
            retention_days=recorder.retention_days,
            category="mtgo_decklists",
            discriminator={"format": normalized_format},
            relative_path=relative_posix_path(latest_path, output_root),
        )
        recorder.add(
            scope="mtgo-decklists",
            status=STATUS_SUCCESS if archived_events else STATUS_SKIPPED,
            format_name=normalized_format,
            path=relative_posix_path(latest_path, output_root),
            message=(
                "No MTGO events matched the requested window."
                if not archived_events
                else None
            ),
        )
    except Exception as exc:  # noqa: BLE001
        if _is_path_fresh(latest_path, generated_at=generated_at, max_stale_hours=max_stale_hours):
            recorder.add(
                scope="mtgo-decklists",
                status=STATUS_STALE_FALLBACK,
                format_name=normalized_format,
                path=relative_posix_path(latest_path, output_root),
                message=str(exc),
            )
            return
        recorder.add(
            scope="mtgo-decklists",
            status=STATUS_HARD_FAILURE,
            format_name=normalized_format,
            path=relative_posix_path(latest_path, output_root),
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

    decks = subparsers.add_parser("scrape-decks")
    decks.add_argument("--format", dest="formats", action="append", required=True)
    decks.add_argument("--archetype", dest="archetypes", action="append")
    decks.add_argument("--days", type=int)

    radars = subparsers.add_parser("scrape-radars")
    radars.add_argument("--format", dest="formats", action="append", required=True)
    radars.add_argument("--archetype", dest="archetypes", action="append")
    radars.add_argument("--max-decks", type=int)

    mtgo_decklists = subparsers.add_parser("scrape-mtgo-decklists")
    mtgo_decklists.add_argument("--format", dest="formats", action="append", required=True)
    mtgo_decklists.add_argument("--days", type=int, default=MTGO_BACKGROUND_FETCH_DAYS)
    mtgo_decklists.add_argument(
        "--event-delay-seconds",
        type=float,
        default=DEFAULT_MTGO_EVENT_DELAY_SECONDS,
    )

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
            )
    elif args.command == "scrape-radars":
        for format_name in args.formats:
            _write_archetype_radar_snapshots(
                output_root=output_root,
                generated_at=generated_at,
                recorder=recorder,
                max_stale_hours=args.max_stale_hours,
                format_name=format_name,
                archetype_filters=args.archetypes,
                max_decks=args.max_decks,
            )
    elif args.command == "scrape-mtgo-decklists":
        for format_name in args.formats:
            _write_mtgo_decklist_snapshots(
                output_root=output_root,
                generated_at=generated_at,
                recorder=recorder,
                max_stale_hours=args.max_stale_hours,
                format_name=format_name,
                days=args.days,
                event_delay_seconds=args.event_delay_seconds,
            )
    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")

    run_manifest_path, run_manifest = recorder.write()
    logger.info("Wrote scrape artifacts to {}", output_root)
    return 1 if run_manifest["status"] in HARD_FAILURE_STATES else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
