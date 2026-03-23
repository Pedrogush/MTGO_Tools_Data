"""Headless scraping surface isolated from the desktop UI package graph."""

from scraping.metagame import ScrapingMetagameRepository
from scraping.mtggoldfish import fetch_archetype_decks, fetch_archetypes, fetch_deck_text
from scraping.mtgo import fetch_event, fetch_event_index, parse_event_decks

__all__ = [
    "ScrapingMetagameRepository",
    "fetch_archetype_decks",
    "fetch_archetypes",
    "fetch_deck_text",
    "fetch_event",
    "fetch_event_index",
    "parse_event_decks",
]
