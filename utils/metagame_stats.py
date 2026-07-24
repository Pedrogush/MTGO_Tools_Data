"""Aggregate metagame statistics over deck metadata rows."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc  # noqa: UP017

_FILTER_TOLERANCE = timedelta(seconds=5)


def _parse_iso(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.debug(f"Unable to parse date string: {date_str}")
            return None


def _filter_decks(
    decks: Iterable[dict[str, Any]],
    event_type: str | None = None,
    fmt: str | None = None,
    days: int | None = None,
) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    window = timedelta(days=days) if days is not None else None
    window_with_tolerance = (window + _FILTER_TOLERANCE) if window is not None else None

    filtered: list[dict[str, Any]] = []
    for deck in decks:
        if event_type and deck.get("event_type") != event_type:
            continue
        if fmt and (deck.get("format") or "").lower() != fmt.lower():
            continue
        if window_with_tolerance is not None:
            publish = _parse_iso(deck.get("publish_date"))
            if not publish:
                continue
            if publish.tzinfo is None:
                publish = publish.replace(tzinfo=UTC)
            if now - publish > window_with_tolerance:
                continue
        filtered.append(deck)
    return filtered


def count_decks_by_archetype(
    decks: Iterable[dict[str, Any]],
    event_type: str | None = None,
    fmt: str | None = None,
    days: int | None = None,
) -> list[tuple[str, int]]:
    filtered = _filter_decks(decks, event_type=event_type, fmt=fmt, days=days)
    counter = Counter()
    for deck in filtered:
        archetype = deck.get("archetype") or deck.get("deck_name") or "Unknown"
        counter[archetype] += 1
    return counter.most_common()


def count_decks_by_player(
    decks: Iterable[dict[str, Any]],
    event_type: str | None = None,
    fmt: str | None = None,
    days: int | None = None,
) -> list[tuple[str, int]]:
    filtered = _filter_decks(decks, event_type=event_type, fmt=fmt, days=days)
    counter = Counter()
    for deck in filtered:
        player = deck.get("player") or "Unknown"
        counter[player] += 1
    return counter.most_common()


def count_decks_by_event(
    decks: Iterable[dict[str, Any]],
    fmt: str | None = None,
    days: int | None = None,
) -> list[tuple[str, int]]:
    filtered = _filter_decks(decks, fmt=fmt, days=days)
    counter = Counter()
    for deck in filtered:
        label = deck.get("event_name") or deck.get("event_type") or "Unknown"
        counter[label] += 1
    return counter.most_common()


def summarize_meta_share(
    decks: Iterable[dict[str, Any]],
    event_type: str | None = None,
    days: int | None = None,
) -> dict[str, Counter]:
    filtered = _filter_decks(decks, event_type=event_type, days=days)
    result: dict[str, Counter] = defaultdict(Counter)
    for deck in filtered:
        fmt = deck.get("format") or "Unknown"
        archetype = deck.get("archetype") or deck.get("deck_name") or "Unknown"
        result[fmt][archetype] += 1
    return result


def aggregate_archetypes_for_window(
    decks: Iterable[dict[str, Any]],
    fmt: str | None = None,
    days: int = 1,
) -> dict[str, int]:
    """Aggregate archetype counts for a time window."""
    filtered = _filter_decks(decks, fmt=fmt, days=days)
    counter = Counter()
    for deck in filtered:
        archetype = deck.get("archetype") or deck.get("deck_name") or "Unknown"
        counter[archetype] += 1
    return dict(counter)


def calculate_metagame_percentages(
    archetype_counts: dict[str, int],
) -> dict[str, float]:
    """Calculate percentage share for each archetype."""
    total = sum(archetype_counts.values())
    if total == 0:
        return {}
    return {archetype: (count / total) * 100 for archetype, count in archetype_counts.items()}


def calculate_metagame_changes(
    current_period: dict[str, int],
    previous_period: dict[str, int],
) -> dict[str, float]:
    """Calculate percentage point changes between two time periods."""
    current_pct = calculate_metagame_percentages(current_period)
    previous_pct = calculate_metagame_percentages(previous_period)
    all_archetypes = set(current_pct.keys()) | set(previous_pct.keys())
    changes = {}
    for archetype in all_archetypes:
        current = current_pct.get(archetype, 0.0)
        previous = previous_pct.get(archetype, 0.0)
        changes[archetype] = current - previous
    return changes


__all__ = [
    "count_decks_by_archetype",
    "count_decks_by_player",
    "count_decks_by_event",
    "summarize_meta_share",
    "aggregate_archetypes_for_window",
    "calculate_metagame_percentages",
    "calculate_metagame_changes",
]
