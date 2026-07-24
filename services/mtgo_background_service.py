"""MTGO event data helpers backed by the Videre Project API."""

from datetime import datetime

from loguru import logger

from navigators.videre import fetch_events
from utils.atomic_io import atomic_write_json, locked_path
from utils.constants import MTGO_DECKLISTS_ENABLED, MTGO_METADATA_CACHE_FILE
from utils.json_io import fast_load

MTGO_METADATA_CACHE = MTGO_METADATA_CACHE_FILE


def _mtgo_feature_disabled(message: str) -> bool:
    if not MTGO_DECKLISTS_ENABLED:
        logger.info(f"MTGO decklists disabled; {message}")
        return True
    return False


def fetch_mtgo_events_for_period(
    start_date: datetime,
    end_date: datetime,
    mtg_format: str = "modern",
):
    """
    Fetch MTGO events between start_date and end_date from the Videre API.

    Returns event rows with id, name, date, format, kind, rounds, players.
    """
    if _mtgo_feature_disabled("skipping fetch_mtgo_events_for_period"):
        return []

    logger.info(
        f"Fetching MTGO events for {mtg_format} from {start_date.date()} to {end_date.date()}"
    )
    events = fetch_events(
        mtg_format,
        min_date=start_date.date().isoformat(),
        max_date=end_date.date().isoformat(),
    )
    logger.info(f"Total events found: {len(events)}")
    return events


def convert_deck_to_classifier_format(clean_deck: dict, mtg_format: str = "modern") -> dict:
    """Convert clean deck format to ArchetypeClassifier format."""
    mainboard = [
        {"name": card["card_name"], "count": card["qty"]} for card in clean_deck["mainboard"]
    ]
    sideboard = [
        {"name": card["card_name"], "count": card["qty"]} for card in clean_deck["sideboard"]
    ]

    return {"mainboard": mainboard, "sideboard": sideboard, "format": mtg_format}


def deck_to_text(clean_deck: dict) -> str:
    """Convert clean deck format to text format."""
    lines = []

    for card in clean_deck["mainboard"]:
        lines.append(f"{card['qty']} {card['card_name']}")

    lines.append("sideboard")

    for card in clean_deck["sideboard"]:
        lines.append(f"{card['qty']} {card['card_name']}")

    return "\n".join(lines) + "\n"


def save_mtgo_deck_metadata(archetype: str, mtg_format: str, deck_metadata: dict) -> None:
    """
    Save MTGO deck metadata to JSON cache.

    Args:
        archetype: Archetype name
        mtg_format: Format (e.g., "modern")
        deck_metadata: Deck metadata dictionary
    """
    if _mtgo_feature_disabled("skip saving deck metadata"):
        return

    cache_key = f"{mtg_format}:{archetype}"

    try:
        with locked_path(MTGO_METADATA_CACHE):
            if MTGO_METADATA_CACHE.exists():
                try:
                    data = fast_load(MTGO_METADATA_CACHE)
                except Exception:
                    logger.warning("MTGO metadata cache invalid JSON; resetting file")
                    data = {}
            else:
                data = {}

            if cache_key not in data:
                data[cache_key] = []

            deck_id = deck_metadata.get("number")
            existing_ids = {d.get("number") for d in data[cache_key]}
            if deck_id not in existing_ids:
                data[cache_key].append(deck_metadata)

            atomic_write_json(MTGO_METADATA_CACHE, data, indent=2)

    except Exception as exc:
        logger.error(f"Failed to save MTGO deck metadata: {exc}")
        raise


def load_mtgo_deck_metadata(archetype: str, mtg_format: str) -> list[dict]:
    """
    Load MTGO deck metadata from JSON cache.

    Args:
        archetype: Archetype name
        mtg_format: Format (e.g., "modern")

    Returns:
        List of deck metadata dictionaries
    """
    if _mtgo_feature_disabled("returning no cached metadata"):
        return []

    cache_key = f"{mtg_format}:{archetype}"

    try:
        if not MTGO_METADATA_CACHE.exists():
            return []

        try:
            with locked_path(MTGO_METADATA_CACHE):
                data = fast_load(MTGO_METADATA_CACHE)
        except Exception:
            logger.warning("MTGO metadata cache invalid JSON; returning empty results")
            return []

        return data.get(cache_key, [])

    except Exception as exc:
        logger.warning(f"Failed to load MTGO deck metadata: {exc}")
        return []
