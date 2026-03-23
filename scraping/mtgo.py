"""Headless MTGO decklist scraping helpers."""

from __future__ import annotations

from typing import Any

from navigators.mtgo_decklists import (
    fetch_deck_event as _fetch_deck_event,
)
from navigators.mtgo_decklists import (
    fetch_decklist_index as _fetch_decklist_index,
)
from services.mtgo_background_service import parse_mtgo_deck


def fetch_event_index(year: int, month: int) -> list[dict[str, Any]]:
    return _fetch_decklist_index(year, month)


def fetch_event(event_url: str) -> dict[str, Any]:
    return _fetch_deck_event(event_url)


def parse_event_decks(event_payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_decks = event_payload.get("decklists", [])
    return [parse_mtgo_deck(raw_deck) for raw_deck in raw_decks]
