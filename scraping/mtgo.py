"""Headless MTGO event data helpers backed by the Videre API."""

from __future__ import annotations

from typing import Any

from navigators.videre import (
    fetch_event_payload as _fetch_event_payload,
)
from navigators.videre import (
    fetch_events as _fetch_events,
)


def fetch_event_index(format_name: str, *, min_date: str, max_date: str) -> list[dict[str, Any]]:
    return _fetch_events(format_name, min_date=min_date, max_date=max_date)


def fetch_event(event: dict[str, Any]) -> dict[str, Any]:
    return _fetch_event_payload(event)


def parse_event_decks(event_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return event_payload.get("decks", [])
