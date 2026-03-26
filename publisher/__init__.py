"""Publisher contracts and headless scrape runner entrypoints."""

from publisher.contracts import (
    SCHEMA_VERSION,
    validate_archetype_deck_snapshot,
    validate_archetype_list_snapshot,
    validate_archetype_radar_snapshot,
    validate_deck_text_blob,
    validate_format_card_pool_snapshot,
    validate_latest_manifest,
    validate_metagame_snapshot,
    validate_run_manifest,
)
from publisher.retention import prune_output_tree
from publisher.runner import main

__all__ = [
    "SCHEMA_VERSION",
    "main",
    "prune_output_tree",
    "validate_archetype_deck_snapshot",
    "validate_archetype_list_snapshot",
    "validate_archetype_radar_snapshot",
    "validate_deck_text_blob",
    "validate_format_card_pool_snapshot",
    "validate_latest_manifest",
    "validate_metagame_snapshot",
    "validate_run_manifest",
]
