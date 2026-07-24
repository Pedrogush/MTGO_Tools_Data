"""Filesystem paths and cache locations."""

from pathlib import Path

BASE_DATA_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = BASE_DATA_DIR / "cache"

MTGO_METADATA_CACHE_FILE = CACHE_DIR / "mtgo_deck_metadata.json"
DECK_CACHE_DB_FILE = CACHE_DIR / "deck_cache.db"
