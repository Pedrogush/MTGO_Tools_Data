"""CLI entrypoint for headless scrape publishing."""

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

from navigators.mtggoldfish import get_archetype_stats
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
from scraping import ScrapingMetagameRepository, fetch_archetypes
from scraping.mtgo import fetch_event
from services.mtgo_background_service import (
    convert_deck_to_classifier_format,
    deck_to_text,
    fetch_mtgo_events_for_period,
    save_mtgo_deck_metadata,
)
from services.radar_service import RadarService
from utils.archetype_classifier import ArchetypeClassifier
from utils.constants import MTGO_BACKGROUND_FETCH_DAYS, MTGO_LEAGUE_REFRESH_WINDOW_DAYS
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
DEFAULT_DECK_DOWNLOAD_DELAY_SECONDS = 0.0
DEFAULT_MTGO_EVENT_DELAY_SECONDS = 1.0


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


def _load_published_deck_snapshot(path: Path, *, format_name: str) -> dict[str, Any] | None:
    payload = _load_json_if_present(path)
    if not payload:
        return None
    try:
        validated = validate_archetype_deck_snapshot(payload)
    except ValueError:
        return None
    if validated.get("format") != format_name:
        return None
    return validated


class _ArchetypeHrefResolver:
    """Resolve MTGOFormatData archetype names onto the published archetype list.

    The MTGO classifier uses the MTGOFormatData taxonomy while the archetype
    list uses MTGGoldfish's; names for the same archetype frequently differ
    ("Countervine" vs "Counter Vine"). Matching is deliberately conservative:
    exact slug, then dash-insensitive slug, then a token-subset match that only
    applies when a single candidate qualifies. Unmatched names keep their
    display string and get a synthesized "{format}-{slug}" href, the same
    scheme MTGGoldfish hrefs follow.
    """

    def __init__(self, archetypes: list[dict[str, Any]], normalized_format: str) -> None:
        self.normalized_format = normalized_format
        self._by_slug: dict[str, dict[str, Any]] = {}
        self._by_compact: dict[str, list[dict[str, Any]]] = {}
        self._token_entries: list[tuple[frozenset[str], dict[str, Any]]] = []
        for entry in archetypes:
            name = str(entry.get("name", "")).strip()
            href = str(entry.get("href", "")).strip()
            if not name or not href:
                continue
            slug = normalize_name(name)
            self._by_slug.setdefault(slug, entry)
            self._by_compact.setdefault(slug.replace("-", ""), []).append(entry)
            self._token_entries.append((frozenset(slug.split("-")), entry))

    def resolve(self, archetype_name: str) -> dict[str, Any] | None:
        slug = normalize_name(archetype_name)
        if not slug:
            return None
        match = self._by_slug.get(slug)
        if match is not None:
            return match
        compact_matches = self._by_compact.get(slug.replace("-", ""), [])
        if len(compact_matches) == 1:
            return compact_matches[0]
        tokens = frozenset(slug.split("-"))
        token_matches = [
            entry
            for entry_tokens, entry in self._token_entries
            if tokens <= entry_tokens or entry_tokens <= tokens
        ]
        if len(token_matches) == 1:
            return token_matches[0]
        return None

    def canonicalize(self, archetype_name: str) -> tuple[str, str]:
        """Return (canonical display name, stable href) for an archetype name."""
        match = self.resolve(archetype_name)
        if match is not None:
            return str(match["name"]), str(match["href"])
        display = archetype_name.strip() or "Unknown"
        return display, f"{self.normalized_format}-{normalize_name(display)}"


def _load_archetype_href_resolver(
    output_root: Path, normalized_format: str
) -> _ArchetypeHrefResolver:
    payload = _load_json_if_present(
        output_root / "latest" / "archetypes" / f"{normalized_format}.json"
    )
    archetypes = list(payload.get("archetypes", [])) if payload else []
    return _ArchetypeHrefResolver(archetypes, normalized_format)


def _merge_mtgo_only_archetypes(
    archetypes: list[dict[str, Any]], *, output_root: Path, normalized_format: str
) -> list[dict[str, Any]]:
    """Union MTGO-only archetypes into the archetype list.

    Videre archetypes with no MTGGoldfish counterpart would otherwise have no
    list entry for their decks and radars to attach to. Union entries carry
    source="mtgo" so the MTGGoldfish deck scraper knows to skip them.
    """
    payload = _load_json_if_present(
        output_root / "latest" / "mtgo-decklists" / f"{normalized_format}.json"
    )
    if not payload:
        return archetypes
    resolver = _ArchetypeHrefResolver(archetypes, normalized_format)
    seen_hrefs = {str(entry.get("href", "")) for entry in archetypes}
    extras: dict[str, dict[str, Any]] = {}
    for event in payload.get("events", []):
        for deck in event.get("decks", []):
            name = str(deck.get("archetype") or deck.get("name") or "").strip()
            if not name or normalize_name(name) == "unknown":
                continue
            if resolver.resolve(name) is not None:
                continue
            display, href = resolver.canonicalize(name)
            if href in seen_hrefs:
                continue
            extras.setdefault(href, {"name": display, "href": href, "source": "mtgo"})
    if not extras:
        return archetypes
    merged = [*archetypes, *(extras[href] for href in sorted(extras))]
    return sorted(
        merged, key=lambda item: (item.get("name", "").lower(), item.get("href", "").lower())
    )


def _load_mtgo_radar_decks(
    output_root: Path, format_name: str
) -> tuple[dict[str, list[dict[str, str]]], dict[str, str]]:
    """Load published MTGO deck texts grouped by archetype slug.

    Returns (decks_by_archetype, display_names). Decks are deduplicated by
    deck id across events; rows without an id or deck text are ignored.
    """
    latest_path = output_root / "latest" / "mtgo-decklists" / f"{format_name}.json"
    payload = _load_json_if_present(latest_path)
    if not payload:
        return {}, {}
    try:
        snapshot = validate_mtgo_decklists_snapshot(payload)
    except ValueError:
        return {}, {}
    if snapshot.get("format") != format_name:
        return {}, {}

    resolver = _load_archetype_href_resolver(output_root, format_name)
    decks_by_archetype: dict[str, list[dict[str, str]]] = {}
    display_names: dict[str, str] = {}
    seen_deck_ids: set[str] = set()
    for event in snapshot.get("events", []):
        for deck in event.get("decks", []):
            deck_id = str(deck.get("number", "")).strip()
            deck_text = str(deck.get("deck_text") or "")
            if not deck_id or not deck_text.strip() or deck_id in seen_deck_ids:
                continue
            seen_deck_ids.add(deck_id)
            raw_name = str(deck.get("archetype") or deck.get("name") or "").strip() or "Unknown"
            archetype_name, _href = resolver.canonicalize(raw_name)
            archetype_slug = normalize_name(archetype_name)
            display_names.setdefault(archetype_slug, archetype_name)
            decks_by_archetype.setdefault(archetype_slug, []).append(
                {
                    "dedupe_key": deck_id,
                    "deck_id": deck_id,
                    "deck_name": archetype_name,
                    "deck_text": deck_text,
                }
            )
    return decks_by_archetype, display_names


def _is_path_fresh(path: Path, *, generated_at: str, max_stale_hours: int) -> bool:
    payload = _load_json_if_present(path)
    if not payload:
        return False
    existing_generated_at = _parse_generated_at(payload.get("generated_at"))
    current_generated_at = _parse_generated_at(generated_at)
    if existing_generated_at is None or current_generated_at is None:
        return False
    return current_generated_at - existing_generated_at <= timedelta(hours=max_stale_hours)


def _filter_recent_decks(
    decks: list[dict[str, Any]], days: int | None, *, reference_time: datetime | None = None
) -> list[dict[str, Any]]:
    if days is None:
        return decks
    cutoff = (reference_time or datetime.now(UTC)).replace(tzinfo=None) - timedelta(days=days)
    filtered: list[dict[str, Any]] = []
    for deck in decks:
        parsed = _parse_deck_date(deck.get("date", ""))
        if parsed is None or parsed >= cutoff:
            filtered.append(deck)
    return filtered


def _deck_text_archive_path(output_root: Path, format_name: str, deck_id: str) -> Path:
    return output_root / "archive" / "deck-texts" / format_name / f"{deck_id}.json"


def _mtgo_event_archive_path(output_root: Path, format_name: str, event_id: str) -> Path:
    return output_root / "archive" / "mtgo-decklists" / format_name / f"{event_id}.json"


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


def _filter_requested_snapshot_paths(
    paths: list[Path], archetype_filters: list[str] | None
) -> list[Path]:
    if not archetype_filters:
        return paths
    wanted = {normalize_name(value) for value in archetype_filters}
    return [path for path in paths if normalize_name(path.stem) in wanted]


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
        archetypes = _merge_mtgo_only_archetypes(
            archetypes, output_root=output_root, normalized_format=normalized_format
        )
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
        format_stats = raw_stats.get(format_name) or raw_stats.get(normalized_format, {})
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
        if archetype.get("source") == "mtgo":
            # Union entries from _merge_mtgo_only_archetypes have no
            # MTGGoldfish page to scrape; their decks ship via mtgo-decklists.
            continue
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
            filtered_decks = _filter_recent_decks(
                decks, days, reference_time=_parse_generated_at(generated_at)
            )
            # An archetype whose MTGGoldfish rows were all MTGO events has no
            # paper decks to publish here (they land in mtgo-decklists); only a
            # scrape that returned nothing at all is a failure.
            had_source_rows = bool(decks) or getattr(repo, "last_goldfish_rows_before_partition", 0) > 0
            if had_source_rows and not filtered_decks:
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
                    message=(
                        f"No decks found within the last {days} days."
                        if decks
                        else "All MTGGoldfish rows were MTGO events; published via mtgo-decklists."
                    ),
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


def _load_radar_source_texts(
    *,
    output_root: Path,
    format_name: str,
    decks: list[dict[str, Any]],
    repo: ScrapingMetagameRepository,
) -> tuple[list[dict[str, str]], int]:
    loaded_decks: list[dict[str, str]] = []
    failed_decks = 0

    for index, deck in enumerate(decks, 1):
        deck_id = str(deck.get("number", "")).strip()
        deck_name = str(deck.get("name", "")).strip() or deck_id or f"Deck {index}"
        dedupe_key = deck_id or f"anon-{index}-{deck_name}"

        blob_path: Path | None = None
        deck_text_path = deck.get("deck_text_path")
        if isinstance(deck_text_path, str) and deck_text_path:
            blob_path = output_root / Path(deck_text_path)
        elif deck_id:
            blob_path = _deck_text_archive_path(output_root, format_name, deck_id)

        if blob_path is not None and deck_id:
            reusable_blob = _load_reusable_deck_text_blob(
                blob_path,
                format_name=format_name,
                deck_id=deck_id,
            )
            if reusable_blob is not None:
                loaded_decks.append(
                    {
                        "dedupe_key": dedupe_key,
                        "deck_id": deck_id,
                        "deck_name": deck_name,
                        "deck_text": reusable_blob["deck_text"],
                    }
                )
                continue

        try:
            source_filter = deck.get("source")
            if source_filter not in {"mtggoldfish", "mtgo"}:
                source_filter = None
            loaded_decks.append(
                {
                    "dedupe_key": dedupe_key,
                    "deck_id": deck_id,
                    "deck_name": deck_name,
                    "deck_text": repo.download_deck_content(deck, source_filter=source_filter),
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load radar source deck {}: {}", deck_name, exc)
            failed_decks += 1

    return loaded_decks, failed_decks


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
    deck_root = output_root / "latest" / "decks" / normalized_format
    snapshot_paths = (
        sorted(deck_root.glob("*.json"), key=lambda path: path.name) if deck_root.exists() else []
    )
    snapshot_paths = _filter_requested_snapshot_paths(snapshot_paths, archetype_filters)

    mtgo_decks_by_archetype, mtgo_display_names = _load_mtgo_radar_decks(
        output_root, normalized_format
    )
    if archetype_filters:
        wanted = {normalize_name(value) for value in archetype_filters}
        mtgo_decks_by_archetype = {
            slug: decks for slug, decks in mtgo_decks_by_archetype.items() if slug in wanted
        }

    if archetype_filters and not snapshot_paths and not mtgo_decks_by_archetype:
        recorder.add(
            scope="archetype-radar",
            status=STATUS_SKIPPED,
            format_name=normalized_format,
            message="No requested archetypes matched the current published deck snapshots.",
        )
        return

    if not snapshot_paths and not mtgo_decks_by_archetype:
        recorder.add(
            scope="archetype-radar",
            status=STATUS_HARD_FAILURE,
            format_name=normalized_format,
            message="No latest deck snapshots or MTGO decklists were found for radar publishing.",
        )
        return

    repo = ScrapingMetagameRepository()
    radar_service = RadarService()
    format_card_pool_decks: dict[str, dict[str, str]] = {}
    format_card_pool_failed_decks = 0

    for snapshot_path in snapshot_paths:
        archetype_slug = normalize_name(snapshot_path.stem)
        latest_path = output_root / "latest" / "radars" / normalized_format / snapshot_path.name
        mtgo_decks = mtgo_decks_by_archetype.pop(archetype_slug, [])

        try:
            deck_snapshot = _load_published_deck_snapshot(
                snapshot_path,
                format_name=normalized_format,
            )
            if deck_snapshot is None:
                raise RuntimeError(f"Published deck snapshot is invalid: {snapshot_path}")

            archetype = deck_snapshot["archetype"]
            archetype_slug = normalize_name(archetype.get("name", snapshot_path.stem))
            mtgo_decks.extend(mtgo_decks_by_archetype.pop(archetype_slug, []))
            selected_decks = list(deck_snapshot.get("decks", []))
            if max_decks is not None:
                selected_decks = selected_decks[:max_decks]

            if not selected_decks and not mtgo_decks:
                snapshot = build_archetype_radar_snapshot(
                    generated_at=generated_at,
                    format_name=normalized_format,
                    archetype=archetype,
                    source="published-deck-texts",
                    total_decks_analyzed=0,
                    decks_failed=0,
                    mainboard_cards=[],
                    sideboard_cards=[],
                )
                validate_archetype_radar_snapshot(snapshot)
                hourly_path = (
                    hourly_snapshot_dir(output_root, generated_at)
                    / "radars"
                    / normalized_format
                    / snapshot_path.name
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
                    status=STATUS_SKIPPED,
                    format_name=normalized_format,
                    archetype=archetype_slug,
                    path=relative_posix_path(latest_path, output_root),
                    message="No published decks were available for radar generation.",
                )
                continue

            loaded_decks: list[dict[str, str]] = []
            failed_decks = 0
            if selected_decks:
                loaded_decks, failed_decks = _load_radar_source_texts(
                    output_root=output_root,
                    format_name=normalized_format,
                    decks=selected_decks,
                    repo=repo,
                )
            merged_decks: dict[str, dict[str, str]] = {}
            for deck in [*loaded_decks, *mtgo_decks]:
                merged_decks.setdefault(deck["dedupe_key"], deck)
            loaded_decks = list(merged_decks.values())
            if max_decks is not None:
                loaded_decks = loaded_decks[:max_decks]
            if not loaded_decks:
                raise RuntimeError("No deck texts were available for radar generation.")

            format_card_pool_failed_decks += failed_decks
            for deck in loaded_decks:
                format_card_pool_decks.setdefault(deck["dedupe_key"], deck)

            _publish_archetype_radar_snapshot(
                output_root=output_root,
                generated_at=generated_at,
                recorder=recorder,
                radar_service=radar_service,
                normalized_format=normalized_format,
                archetype=archetype,
                archetype_slug=archetype_slug,
                latest_path=latest_path,
                loaded_decks=loaded_decks,
                failed_decks=failed_decks,
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
                    archetype=archetype_slug,
                    path=relative_posix_path(latest_path, output_root),
                    message=str(exc),
                )
                continue
            recorder.add(
                scope="archetype-radar",
                status=STATUS_HARD_FAILURE,
                format_name=normalized_format,
                archetype=archetype_slug,
                path=relative_posix_path(latest_path, output_root),
                message=str(exc),
            )

    for archetype_slug in sorted(mtgo_decks_by_archetype):
        mtgo_decks = mtgo_decks_by_archetype[archetype_slug]
        for deck in mtgo_decks:
            format_card_pool_decks.setdefault(deck["dedupe_key"], deck)
        if archetype_slug == "unknown":
            # Unclassified decks feed the card pool but have no meaningful radar.
            continue
        latest_path = (
            output_root / "latest" / "radars" / normalized_format / f"{archetype_slug}.json"
        )
        archetype = {
            "name": mtgo_display_names.get(archetype_slug, archetype_slug),
            "href": f"{normalized_format}-{archetype_slug}",
        }
        loaded_decks = mtgo_decks[:max_decks] if max_decks is not None else mtgo_decks
        try:
            _publish_archetype_radar_snapshot(
                output_root=output_root,
                generated_at=generated_at,
                recorder=recorder,
                radar_service=radar_service,
                normalized_format=normalized_format,
                archetype=archetype,
                archetype_slug=archetype_slug,
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
                    archetype=archetype_slug,
                    path=relative_posix_path(latest_path, output_root),
                    message=str(exc),
                )
                continue
            recorder.add(
                scope="archetype-radar",
                status=STATUS_HARD_FAILURE,
                format_name=normalized_format,
                archetype=archetype_slug,
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

    _write_format_card_pool_snapshot(
        output_root=output_root,
        generated_at=generated_at,
        recorder=recorder,
        max_stale_hours=max_stale_hours,
        format_name=format_name,
        loaded_decks=list(format_card_pool_decks.values()),
        failed_decks=format_card_pool_failed_decks,
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
    classifier = ArchetypeClassifier()
    href_resolver = _load_archetype_href_resolver(output_root, normalized_format)
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
                classifier_decks = [
                    convert_deck_to_classifier_format(deck, mtg_format=normalized_format)
                    for deck in clean_decks
                ]
                classifier.assign_archetypes(classifier_decks, normalized_format)

                event_date = payload.get("publish_date") or str(event.get("date", ""))[:10] or generated_at
                event_title = payload.get("title") or event.get("name") or "MTGO Event"
                decks_cached = 0
                deck_metadata_rows: list[dict[str, Any]] = []

                for clean_deck, classifier_deck in zip(clean_decks, classifier_decks):
                    deck_id = str(clean_deck.get("deck_id") or "").strip()
                    if not deck_id:
                        continue

                    if deck_cache.set(deck_id, deck_to_text(clean_deck), source="mtgo"):
                        decks_cached += 1

                    wins = str(clean_deck.get("wins", "?")).strip() or "?"
                    losses = str(clean_deck.get("losses", "?")).strip() or "?"
                    archetype, archetype_href = href_resolver.canonicalize(
                        str(classifier_deck.get("archetype", "Unknown"))
                    )
                    deck_metadata = {
                        "number": deck_id,
                        "date": event_date,
                        "event": event_title,
                        "result": "?" if wins == "?" and losses == "?" else f"{wins}-{losses}",
                        "player": clean_deck.get("player", "Unknown"),
                        "archetype": archetype,
                        "archetype_href": archetype_href,
                        "name": archetype,
                        "source": "mtgo",
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
                    "event_url": event_url,
                    "event_title": event_title,
                    "publish_date": event_date,
                    "event_type": payload.get("event_type", "unknown"),
                    "decks_total": len(clean_decks),
                    "decks_cached": decks_cached,
                    "decks": deck_metadata_rows,
                }
                write_json(archive_path, event_snapshot)
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

        # Rows loaded from event archives may predate archetype-href
        # canonicalization; re-resolve every row so the published snapshot is
        # uniformly keyed. Idempotent for rows that are already canonical.
        for archived_event in archived_events:
            for deck in archived_event.get("decks", []):
                raw_name = str(deck.get("archetype") or deck.get("name") or "Unknown")
                archetype, archetype_href = href_resolver.canonicalize(raw_name)
                deck["archetype"] = archetype
                deck["name"] = archetype
                deck["archetype_href"] = archetype_href

        snapshot = build_mtgo_decklists_snapshot(
            generated_at=generated_at,
            format_name=normalized_format,
            source="videre-api",
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
