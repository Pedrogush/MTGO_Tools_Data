"""Deck metadata source backed by the published mtgo-decklists archives.

Replaces the MTGGoldfish scraper as the input for archetype lists, deck
snapshots, deck-text blobs, and metagame counts. The archives are written by
the ``scrape-mtgo-decklists`` command (Videre API data) and are present in
the ``data-publish`` checkout that every publish job runs from, so deriving
the downstream products from them needs no network access at all.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from publisher.layout import normalize_name
from utils.constants import MTGO_BACKGROUND_FETCH_DAYS


class MtgoArchiveRepository:
    """Read deck metadata rows from ``archive/mtgo-decklists/<format>/``.

    Implements the access interface the publisher previously used with the
    MTGGoldfish-backed repository: ``get_decks_for_archetype`` and
    ``download_deck_content``.
    """

    # Deck texts are embedded in the archive rows; no politeness delay is
    # needed between "downloads".
    download_requires_network = False

    def __init__(
        self,
        output_root: Path,
        format_name: str,
        *,
        days: int = MTGO_BACKGROUND_FETCH_DAYS,
        reference_time: datetime | None = None,
    ):
        self.output_root = Path(output_root)
        self.format_name = normalize_name(format_name)
        # The archive directory accumulates beyond the retention window (and
        # still holds events from the retired mtgo.com scraper), so rows are
        # windowed by deck date; undated rows are excluded.
        self.days = days
        self.reference_time = reference_time or datetime.now()
        self._rows: list[dict[str, Any]] | None = None

    def _within_window(self, deck: dict[str, Any]) -> bool:
        raw = str(deck.get("date", ""))[:10]
        try:
            deck_date = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            return False
        cutoff = self.reference_time.replace(tzinfo=None) - timedelta(days=self.days)
        return deck_date >= cutoff

    def load_rows(self) -> list[dict[str, Any]]:
        """Return all archived deck metadata rows, newest first, deduped by id."""
        if self._rows is not None:
            return self._rows

        rows: list[dict[str, Any]] = []
        seen_deck_ids: set[str] = set()
        archive_dir = self.output_root / "archive" / "mtgo-decklists" / self.format_name
        for path in sorted(archive_dir.glob("*.json")):
            try:
                event = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping unreadable event archive {}: {}", path, exc)
                continue
            for deck in event.get("decks", []):
                deck_id = str(deck.get("number", "")).strip()
                if not deck_id or deck_id in seen_deck_ids or not self._within_window(deck):
                    continue
                seen_deck_ids.add(deck_id)
                rows.append(deck)
        rows.sort(key=lambda deck: (deck.get("date", ""), deck.get("number", "")), reverse=True)
        self._rows = rows
        return rows

    def get_archetypes(self) -> list[dict[str, Any]]:
        """Distinct archetypes present in the archives, as {name, href} rows."""
        names = {str(deck.get("archetype") or "").strip() for deck in self.load_rows()}
        return [
            {"name": name, "href": normalize_name(name)}
            for name in sorted(names, key=str.lower)
            if name
        ]

    def get_decks_for_archetype(
        self,
        archetype: dict[str, Any],
        force_refresh: bool = False,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        del force_refresh  # archives are immutable within a run
        wanted = normalize_name(str(archetype.get("name", "")))
        rows = [
            deck
            for deck in self.load_rows()
            if normalize_name(str(deck.get("archetype") or "")) == wanted
        ]
        if source_filter and source_filter != "both":
            rows = [deck for deck in rows if deck.get("source") == source_filter]
        # Snapshot rows exclude the embedded deck text; blobs are published
        # separately and referenced via deck_text_path.
        return [{key: value for key, value in deck.items() if key != "deck_text"} for deck in rows]

    def download_deck_content(self, deck: dict[str, Any], source_filter: str | None = None) -> str:
        del source_filter
        deck_id = str(deck.get("number", "")).strip()
        for row in self.load_rows():
            if str(row.get("number", "")).strip() == deck_id and row.get("deck_text"):
                return str(row["deck_text"])
        raise ValueError(f"Deck {deck_id} not present in mtgo-decklists archives")

    def get_archetype_stats(self, *, lookback_dates: list[str]) -> list[dict[str, Any]]:
        """Per-archetype deck counts by day, in metagame snapshot row shape."""
        by_archetype: dict[str, list[dict[str, Any]]] = {}
        for deck in self.load_rows():
            name = str(deck.get("archetype") or "").strip()
            if name:
                by_archetype.setdefault(name, []).append(deck)
        stats_rows = []
        for name in sorted(by_archetype, key=str.lower):
            decks = by_archetype[name]
            daily_counts = {
                day: sum(1 for deck in decks if str(deck.get("date", ""))[:10] == day)
                for day in sorted(lookback_dates)
            }
            stats_rows.append(
                {
                    "archetype": name,
                    "deck_count": len(decks),
                    "daily_counts": daily_counts,
                }
            )
        return stats_rows
