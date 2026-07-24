"""Videre Project API client for MTGO tournament data.

Replaces the direct mtgo.com decklist scraper. The Videre Project
(https://github.com/videre-project) runs a community REST API at
https://api.videreproject.com serving MTGO event, deck, and standings data
collected by their MTGOBot. Decklist coverage matches what mtgo.com
publishes (Top 32 of scheduled events plus the curated league 5-0s).
"""

from __future__ import annotations

import re
import time
from typing import Any

from curl_cffi import requests
from loguru import logger

from utils.constants import (
    MTGO_DECKLISTS_FETCH_RETRY_DELAYS_SECONDS,
    VIDERE_API_BASE_URL,
    VIDERE_REQUEST_TIMEOUT_SECONDS,
)

# Page size for paginated endpoints; the API caps rows per response.
_PAGE_LIMIT = 100
# Hard stop for pagination loops so a server bug cannot spin forever.
_MAX_PAGES = 50

# The API's Cloudflare Worker sheds load with 408s when a query trips its
# runtime guardrail; the same request typically succeeds moments later.
_RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}

# Card entries arrive as Postgres composite row literals:
#   (18115,"Birchlore Rangers",4)  or  (129825,Forest,2)
# Names containing commas/spaces are double-quoted; embedded quotes double.
_CARD_ENTRY_PATTERN = re.compile(r'^\((\d+),(?:"((?:[^"]|"")*)"|([^,]*)),(\d+)\)$')

_EMPTY_PAYLOAD: dict[str, Any] = {"data": [], "meta": {"has_more": False}}


def _is_empty_result(response: Any) -> bool:
    # The API answers 400 with message "No results found." for events whose
    # decklists have not been imported yet; that is an empty list, not an error.
    try:
        return response.json().get("message") == "No results found."
    except Exception:
        return False


def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{VIDERE_API_BASE_URL}{path}"
    delays = (0, *MTGO_DECKLISTS_FETCH_RETRY_DELAYS_SECONDS)
    last_error: Exception = RuntimeError(f"No request attempted for {url}")
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            logger.warning(
                "Retrying {} in {}s (attempt {}/{}): {}", path, delay, attempt, len(delays), last_error
            )
            time.sleep(delay)
        try:
            response = requests.get(url, params=params, timeout=VIDERE_REQUEST_TIMEOUT_SECONDS)
        except Exception as exc:  # noqa: BLE001 - transport errors are retryable
            last_error = exc
            continue
        if response.status_code == 400 and _is_empty_result(response):
            return _EMPTY_PAYLOAD
        if response.status_code in _RETRYABLE_STATUSES:
            last_error = RuntimeError(f"HTTP {response.status_code} from {url}")
            continue
        response.raise_for_status()
        return response.json()
    raise last_error


def _paginate(path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    for _ in range(_MAX_PAGES):
        payload = _get(path, {**params, "limit": _PAGE_LIMIT, "offset": offset})
        rows.extend(payload.get("data", []))
        meta = payload.get("meta", {})
        if not meta.get("has_more"):
            return rows
        offset = meta.get("next_offset", offset + _PAGE_LIMIT)
    logger.warning("Pagination cap reached for {} with params {}", path, params)
    return rows


def normalize_card_name(name: str) -> str:
    """Match the published deck-text convention for split cards.

    The Videre catalog stores split cards as "Wear/Tear" while MTGGoldfish
    deck texts and the vendored archetype data use "Wear // Tear".
    """
    if "/" in name and "//" not in name:
        return name.replace("/", " // ")
    return name


def parse_card_entry(entry: str) -> tuple[str, int]:
    match = _CARD_ENTRY_PATTERN.match(entry)
    if not match:
        raise ValueError(f"Unparseable Videre card entry: {entry!r}")
    quoted, bare, qty = match.group(2), match.group(3), match.group(4)
    name = quoted.replace('""', '"') if quoted is not None else bare
    return normalize_card_name(name), int(qty)


def fetch_events(format_name: str, *, min_date: str, max_date: str) -> list[dict[str, Any]]:
    """Return event rows (id, name, date, format, kind, rounds, players)."""
    return _paginate(
        "/events",
        {"format": format_name, "min_date": min_date, "max_date": max_date},
    )


def fetch_event_decks(event_id: int | str) -> list[dict[str, Any]]:
    return _paginate("/decks", {"event_id": event_id})


def fetch_event_standings(event_id: int | str) -> dict[str, dict[str, Any]]:
    """Return standings keyed by casefolded player name."""
    standings: dict[str, dict[str, Any]] = {}
    for row in _paginate("/standings", {"event_id": event_id}):
        player = str(row.get("player") or "").strip()
        if player:
            standings[player.casefold()] = row
    return standings


def _record_to_wins_losses(record: str | None) -> tuple[str, str]:
    parts = str(record or "").split("-")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return parts[0], parts[1]
    return "?", "?"


def _clean_deck(deck_row: dict[str, Any], standings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Convert a Videre deck row to the pipeline's clean deck shape."""
    player = str(deck_row.get("player") or "Unknown")
    standing = standings.get(player.casefold(), {})
    wins, losses = _record_to_wins_losses(standing.get("record"))

    def _board(entries: list[str] | None, sideboard: str) -> list[dict[str, Any]]:
        cards: dict[str, int] = {}
        for entry in entries or []:
            name, qty = parse_card_entry(entry)
            cards[name] = cards.get(name, 0) + qty
        return [
            {"card_name": name, "qty": qty, "sideboard": sideboard}
            for name, qty in cards.items()
        ]

    return {
        "deck_id": str(deck_row.get("id") or ""),
        "login_id": None,
        "player": player,
        "wins": wins,
        "losses": losses,
        "mainboard": _board(deck_row.get("mainboard"), "false"),
        "sideboard": _board(deck_row.get("sideboard"), "true"),
    }


def fetch_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    """Fetch decks and standings for an event row from :func:`fetch_events`.

    Returns the shape the publisher consumes: title, publish date, event
    type, and the event's decklists already converted to clean decks.
    """
    event_id = event["id"]
    date = str(event.get("date") or "")[:10]
    standings = fetch_event_standings(event_id)
    decks = [_clean_deck(row, standings) for row in fetch_event_decks(event_id)]
    name = str(event.get("name") or "MTGO Event")
    # mtgo.com-style display title: event name plus the ISO event day.
    title = name if date and date in name else f"{name} {date}".strip()
    return {
        "event_id": str(event_id),
        "title": title,
        "publish_date": date,
        "event_type": str(event.get("kind") or "unknown").lower(),
        "decks": decks,
    }
