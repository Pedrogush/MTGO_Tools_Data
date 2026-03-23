"""Publisher contracts and headless scrape runner entrypoints."""

from publisher.contracts import (
    SCHEMA_VERSION,
    validate_archetype_deck_snapshot,
    validate_archetype_list_snapshot,
    validate_deck_text_blob,
    validate_latest_manifest,
    validate_metagame_snapshot,
)
from publisher.runner import main

__all__ = [
    "SCHEMA_VERSION",
    "main",
    "validate_archetype_deck_snapshot",
    "validate_archetype_list_snapshot",
    "validate_deck_text_blob",
    "validate_latest_manifest",
    "validate_metagame_snapshot",
]
