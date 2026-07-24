"""Filesystem paths and cache locations."""

from pathlib import Path

BASE_DATA_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = BASE_DATA_DIR / "cache"
DECKS_DIR = Path.home() / "Documents" / "mtgo_decks"

ARCHETYPE_CACHE_FILE = CACHE_DIR / "archetype_cache.json"
ARCHETYPE_LIST_CACHE_FILE = CACHE_DIR / "archetype_list.json"
MTGO_DECK_CACHE_FILE = CACHE_DIR / "mtgo_decks.json"
MTGO_METADATA_CACHE_FILE = CACHE_DIR / "mtgo_deck_metadata.json"
DECK_CACHE_DB_FILE = CACHE_DIR / "deck_cache.db"
DECK_TEXT_CACHE_FILE = CACHE_DIR / "deck_text_cache.json"  # Individual deck content
ARCHETYPE_DECKS_CACHE_FILE = CACHE_DIR / "archetype_decks_cache.json"  # Deck lists per archetype
CURR_DECK_FILE = DECKS_DIR / "curr_deck.txt"
