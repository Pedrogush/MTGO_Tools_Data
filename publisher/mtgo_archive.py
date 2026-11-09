"""Deck metadata source backed by the published MTGO decklist snapshot.

Every downstream product - archetype lists, archetype deck snapshots,
deck-text blobs, radars, format card pools, and metagame counts - is derived
from ``latest/mtgo-decklists/<format>.json``, which ``scrape-mtgo-decklists``
builds from the Videre Project API. Deriving them needs no network access.

Archetype names are Videre's own labels (``archetype`` on each ``/decks``
row). Decks Videre cannot place come back either as a bare colour code
("BR", "WBG") with a null ``archetype_id``, or with no archetype at all.
Colour codes are kept as archetypes of their own: they are real, stable
buckets of decks that the client can list and build radars for, and folding
them into "Unknown" would hide 10-15% of a format. Decks with no archetype at
all canonicalize to "Unknown", which never appears in archetype lists, deck
snapshots, radars, or metagame stats, but still feeds the format card pool.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from publisher.layout import normalize_name
from utils.constants import MTGO_BACKGROUND_FETCH_DAYS

UNKNOWN_ARCHETYPE = "Unknown"
UNKNOWN_SLUG = normalize_name(UNKNOWN_ARCHETYPE)
# The publisher's deck rows always carry source "mtgo". MTGO_Tools keys on this
# value: it merges bundle MTGO decks over cached rows with the same source, and
# never tries to scrape MTGGoldfish for archetypes or decks marked "mtgo".
MTGO_SOURCE = "mtgo"


def archetype_slug(name: str | None) -> str:
    slug = normalize_name(str(name or ""))
    return slug or UNKNOWN_SLUG


def canonical_archetype(name: str | None, normalized_format: str) -> tuple[str, str]:
    """Return (display name, href) for a Videre archetype label.

    Hrefs are ``<format>-<slug>``, the same shape MTGGoldfish hrefs had, which
    MTGO_Tools relies on to attribute cached decks to a format.
    """
    display = str(name or "").strip()
    if not normalize_name(display):
        display = UNKNOWN_ARCHETYPE
    return display, f"{normalized_format}-{archetype_slug(display)}"


def preferred_display_names(names: Iterable[str]) -> dict[str, str]:
    """Pick one display name per slug: the most common spelling, ties alphabetical.

    Guards against two spellings ("Death & Taxes" / "Death and Taxes" style
    case or punctuation drift) of one archetype producing one snapshot file but
    two names the client would try to match exactly.
    """
    counts: dict[str, Counter[str]] = {}
    for name in names:
        display = str(name or "").strip() or UNKNOWN_ARCHETYPE
        counts.setdefault(archetype_slug(display), Counter())[display] += 1
    return {
        slug: sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]
        for slug, counter in counts.items()
    }


class MtgoArchiveRepository:
    """Read deck rows from the published ``latest/mtgo-decklists`` snapshot."""

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
        self.days = days
        self.reference_time = reference_time or datetime.now()
        self._rows: list[dict[str, Any]] | None = None

    @property
    def snapshot_path(self) -> Path:
        return self.output_root / "latest" / "mtgo-decklists" / f"{self.format_name}.json"

    def _within_window(self, deck: dict[str, Any]) -> bool:
        # The snapshot already holds only the fetch window's events, but a
        # stale-fallback snapshot can be older; window by deck date so a stale
        # input never republishes decks past retention. Undated rows are kept
        # out rather than guessed at.
        try:
            deck_date = datetime.strptime(str(deck.get("date", ""))[:10], "%Y-%m-%d")
        except ValueError:
            return False
        cutoff = self.reference_time.replace(tzinfo=None) - timedelta(days=self.days)
        return deck_date >= cutoff.replace(hour=0, minute=0, second=0, microsecond=0)

    def load_rows(self) -> list[dict[str, Any]]:
        """Return the snapshot's deck rows, newest first, deduped by deck id."""
        if self._rows is not None:
            return self._rows
        if not self.snapshot_path.exists():
            raise FileNotFoundError(
                f"No MTGO decklist snapshot at {self.snapshot_path}; "
                "run scrape-mtgo-decklists for this format first."
            )
        payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        if normalize_name(str(payload.get("format", ""))) != self.format_name:
            raise ValueError(
                f"{self.snapshot_path} holds format {payload.get('format')!r}, "
                f"expected {self.format_name!r}"
            )

        rows: list[dict[str, Any]] = []
        seen_deck_ids: set[str] = set()
        for event in payload.get("events", []):
            for deck in event.get("decks", []):
                deck_id = str(deck.get("number", "")).strip()
                if not deck_id or deck_id in seen_deck_ids or not self._within_window(deck):
                    continue
                seen_deck_ids.add(deck_id)
                rows.append(deck)
        rows.sort(
            key=lambda deck: (str(deck.get("date", "")), str(deck.get("number", ""))),
            reverse=True,
        )
        self._rows = rows
        return rows

    def archetype_groups(self) -> dict[str, tuple[str, list[dict[str, Any]]]]:
        """Group rows by archetype slug -> (display name, rows newest first)."""
        rows = self.load_rows()
        display_names = preferred_display_names(
            str(deck.get("archetype") or deck.get("name") or "") for deck in rows
        )
        groups: dict[str, tuple[str, list[dict[str, Any]]]] = {}
        for deck in rows:
            slug = archetype_slug(deck.get("archetype") or deck.get("name"))
            groups.setdefault(slug, (display_names[slug], []))[1].append(deck)
        return groups

    def archetype_entry(self, slug: str, display: str) -> dict[str, Any]:
        return {
            "name": display,
            "href": f"{self.format_name}-{slug}",
            "source": MTGO_SOURCE,
        }

    def get_archetypes(self) -> list[dict[str, Any]]:
        """Archetypes present in the window as archetype-list entries."""
        entries = [
            self.archetype_entry(slug, display)
            for slug, (display, _rows) in self.archetype_groups().items()
            if slug != UNKNOWN_SLUG
        ]
        return sorted(entries, key=lambda item: (item["name"].lower(), item["href"]))

    def get_decks_for_archetype(self, archetype: dict[str, Any]) -> list[dict[str, Any]]:
        """Deck metadata rows for one archetype, without the embedded deck text."""
        slug = archetype_slug(str(archetype.get("name", "")))
        _display, rows = self.archetype_groups().get(slug, ("", []))
        return [{key: value for key, value in deck.items() if key != "deck_text"} for deck in rows]

    def download_deck_content(self, deck: dict[str, Any]) -> str:
        deck_id = str(deck.get("number", "")).strip()
        for row in self.load_rows():
            if str(row.get("number", "")).strip() == deck_id and row.get("deck_text"):
                return str(row["deck_text"])
        raise ValueError(f"Deck {deck_id} is not present in the MTGO decklist snapshot")

    def get_archetype_stats(self, *, lookback_dates: list[str]) -> list[dict[str, Any]]:
        """Per-archetype deck counts by day, in metagame snapshot row shape."""
        stats_rows = []
        for slug, (display, rows) in self.archetype_groups().items():
            if slug == UNKNOWN_SLUG:
                continue
            daily_counts = {
                day: sum(1 for deck in rows if str(deck.get("date", ""))[:10] == day)
                for day in sorted(lookback_dates)
            }
            stats_rows.append(
                {"archetype": display, "deck_count": len(rows), "daily_counts": daily_counts}
            )
        return sorted(stats_rows, key=lambda row: row["archetype"].lower())
