"""Headless scraping surface isolated from the desktop UI package graph."""

from scraping.mtgo import fetch_event, fetch_event_index, parse_event_decks

__all__ = [
    "fetch_event",
    "fetch_event_index",
    "parse_event_decks",
]
