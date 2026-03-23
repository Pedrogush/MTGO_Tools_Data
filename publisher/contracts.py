"""Published artifact builders and validators for scrape snapshots."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

SCHEMA_VERSION = "1"
LATEST_MANIFEST_KIND = "latest_manifest"
ARCHETYPE_LIST_KIND = "archetype_list"
ARCHETYPE_DECKS_KIND = "archetype_decks"
METAGAME_KIND = "metagame_daily"
DECK_TEXTS_KIND = "deck_text_blob"


def _require_mapping(payload: Any, kind: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError(f"{kind} payload must be a mapping")
    return payload


def _require_string(payload: Mapping[str, Any], key: str, kind: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{kind}.{key} must be a non-empty string")
    return value


def _require_sequence(payload: Mapping[str, Any], key: str, kind: str) -> Sequence[Any]:
    value = payload.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValueError(f"{kind}.{key} must be a sequence")
    return value


def _validate_common_snapshot(payload: Any, *, kind: str) -> Mapping[str, Any]:
    snapshot = _require_mapping(payload, kind)
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{kind}.schema_version must be {SCHEMA_VERSION}")
    if snapshot.get("kind") != kind:
        raise ValueError(f"{kind}.kind must be {kind}")
    _require_string(snapshot, "generated_at", kind)
    _require_string(snapshot, "format", kind)
    return snapshot


def build_latest_manifest(*, generated_at: str, retention_days: int) -> dict[str, Any]:
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": LATEST_MANIFEST_KIND,
        "generated_at": generated_at,
        "retention_days": retention_days,
        "latest": {
            "archetype_lists": [],
            "archetype_decks": [],
            "metagame_daily": [],
            "deck_text_blobs": [],
        },
    }


def build_archetype_list_snapshot(
    *, generated_at: str, format_name: str, source: str, archetypes: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": ARCHETYPE_LIST_KIND,
        "generated_at": generated_at,
        "format": format_name,
        "source": source,
        "archetypes": [dict(item) for item in archetypes],
    }


def build_archetype_deck_snapshot(
    *,
    generated_at: str,
    format_name: str,
    archetype: Mapping[str, Any],
    source: str,
    decks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": ARCHETYPE_DECKS_KIND,
        "generated_at": generated_at,
        "format": format_name,
        "source": source,
        "archetype": dict(archetype),
        "decks": [dict(item) for item in decks],
    }


def build_metagame_snapshot(
    *,
    generated_at: str,
    format_name: str,
    source: str,
    generated_for_day: str,
    stats: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": METAGAME_KIND,
        "generated_at": generated_at,
        "format": format_name,
        "source": source,
        "generated_for_day": generated_for_day,
        "stats": [dict(item) for item in stats],
    }


def build_deck_text_blob(
    *,
    generated_at: str,
    format_name: str,
    archetype: Mapping[str, Any],
    source: str,
    deck_texts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": DECK_TEXTS_KIND,
        "generated_at": generated_at,
        "format": format_name,
        "source": source,
        "archetype": dict(archetype),
        "deck_texts": [dict(item) for item in deck_texts],
    }


def validate_latest_manifest(payload: Any) -> dict[str, Any]:
    manifest = deepcopy(_require_mapping(payload, LATEST_MANIFEST_KIND))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{LATEST_MANIFEST_KIND}.schema_version must be {SCHEMA_VERSION}")
    if manifest.get("kind") != LATEST_MANIFEST_KIND:
        raise ValueError(f"{LATEST_MANIFEST_KIND}.kind must be {LATEST_MANIFEST_KIND}")
    _require_string(manifest, "generated_at", LATEST_MANIFEST_KIND)
    retention_days = manifest.get("retention_days")
    if not isinstance(retention_days, int) or retention_days < 1:
        raise ValueError("latest_manifest.retention_days must be a positive integer")
    latest = _require_mapping(manifest.get("latest"), "latest_manifest.latest")
    required_groups = {
        "archetype_lists",
        "archetype_decks",
        "metagame_daily",
        "deck_text_blobs",
    }
    for group in required_groups:
        entries = _require_sequence(latest, group, "latest_manifest.latest")
        for entry in entries:
            entry_mapping = _require_mapping(entry, f"latest_manifest.latest.{group}[]")
            _require_string(entry_mapping, "format", f"latest_manifest.latest.{group}[]")
            _require_string(entry_mapping, "path", f"latest_manifest.latest.{group}[]")
            _require_string(entry_mapping, "updated_at", f"latest_manifest.latest.{group}[]")
    return manifest


def validate_archetype_list_snapshot(payload: Any) -> dict[str, Any]:
    snapshot = deepcopy(_validate_common_snapshot(payload, kind=ARCHETYPE_LIST_KIND))
    _require_string(snapshot, "source", ARCHETYPE_LIST_KIND)
    archetypes = _require_sequence(snapshot, "archetypes", ARCHETYPE_LIST_KIND)
    for entry in archetypes:
        archetype = _require_mapping(entry, f"{ARCHETYPE_LIST_KIND}.archetypes[]")
        _require_string(archetype, "name", f"{ARCHETYPE_LIST_KIND}.archetypes[]")
        _require_string(archetype, "href", f"{ARCHETYPE_LIST_KIND}.archetypes[]")
    return dict(snapshot)


def validate_archetype_deck_snapshot(payload: Any) -> dict[str, Any]:
    snapshot = deepcopy(_validate_common_snapshot(payload, kind=ARCHETYPE_DECKS_KIND))
    _require_string(snapshot, "source", ARCHETYPE_DECKS_KIND)
    archetype = _require_mapping(snapshot.get("archetype"), f"{ARCHETYPE_DECKS_KIND}.archetype")
    _require_string(archetype, "name", f"{ARCHETYPE_DECKS_KIND}.archetype")
    _require_string(archetype, "href", f"{ARCHETYPE_DECKS_KIND}.archetype")
    decks = _require_sequence(snapshot, "decks", ARCHETYPE_DECKS_KIND)
    for entry in decks:
        deck = _require_mapping(entry, f"{ARCHETYPE_DECKS_KIND}.decks[]")
        _require_string(deck, "number", f"{ARCHETYPE_DECKS_KIND}.decks[]")
        _require_string(deck, "source", f"{ARCHETYPE_DECKS_KIND}.decks[]")
    return dict(snapshot)


def validate_metagame_snapshot(payload: Any) -> dict[str, Any]:
    snapshot = deepcopy(_validate_common_snapshot(payload, kind=METAGAME_KIND))
    _require_string(snapshot, "source", METAGAME_KIND)
    _require_string(snapshot, "generated_for_day", METAGAME_KIND)
    stats = _require_sequence(snapshot, "stats", METAGAME_KIND)
    for entry in stats:
        item = _require_mapping(entry, f"{METAGAME_KIND}.stats[]")
        _require_string(item, "archetype", f"{METAGAME_KIND}.stats[]")
        deck_count = item.get("deck_count")
        if not isinstance(deck_count, int) or deck_count < 0:
            raise ValueError(f"{METAGAME_KIND}.stats[].deck_count must be a non-negative integer")
        daily_counts = _require_mapping(item.get("daily_counts"), f"{METAGAME_KIND}.stats[]")
        for key, value in daily_counts.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"{METAGAME_KIND}.stats[].daily_counts keys must be strings")
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"{METAGAME_KIND}.stats[].daily_counts values must be non-negative integers"
                )
    return dict(snapshot)


def validate_deck_text_blob(payload: Any) -> dict[str, Any]:
    snapshot = deepcopy(_validate_common_snapshot(payload, kind=DECK_TEXTS_KIND))
    _require_string(snapshot, "source", DECK_TEXTS_KIND)
    archetype = _require_mapping(snapshot.get("archetype"), f"{DECK_TEXTS_KIND}.archetype")
    _require_string(archetype, "name", f"{DECK_TEXTS_KIND}.archetype")
    _require_string(archetype, "href", f"{DECK_TEXTS_KIND}.archetype")
    deck_texts = _require_sequence(snapshot, "deck_texts", DECK_TEXTS_KIND)
    for entry in deck_texts:
        item = _require_mapping(entry, f"{DECK_TEXTS_KIND}.deck_texts[]")
        _require_string(item, "deck_id", f"{DECK_TEXTS_KIND}.deck_texts[]")
        _require_string(item, "deck_text", f"{DECK_TEXTS_KIND}.deck_texts[]")
    return dict(snapshot)
