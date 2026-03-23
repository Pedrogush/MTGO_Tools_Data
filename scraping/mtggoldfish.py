"""Headless MTGGoldfish scraping helpers."""

from __future__ import annotations

from typing import Any

from navigators.mtggoldfish import (
    fetch_deck_text as _fetch_deck_text,
)
from navigators.mtggoldfish import (
    get_archetype_decks as _get_archetype_decks,
)
from navigators.mtggoldfish import (
    get_archetypes as _get_archetypes,
)


def fetch_archetypes(
    format_name: str,
    *,
    cache_ttl: int | None = None,
    allow_stale: bool = True,
) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = {"allow_stale": allow_stale}
    if cache_ttl is not None:
        kwargs["cache_ttl"] = cache_ttl
    return _get_archetypes(format_name.lower(), **kwargs)


def fetch_archetype_decks(archetype_id: str) -> list[dict[str, Any]]:
    return _get_archetype_decks(archetype_id)


def fetch_deck_text(deck_id: str, *, source_filter: str | None = None) -> str:
    return _fetch_deck_text(deck_id, source_filter=source_filter)
