"""Headless radar service for archetype card-frequency analysis."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from loguru import logger

from repositories.metagame_repository import MetagameRepository, get_metagame_repository
from utils.constants import (
    RADAR_AVG_COPIES_ROUND_DIGITS,
    RADAR_EXPECTED_COPIES_ROUND_DIGITS,
    RADAR_INCLUSION_RATE_ROUND_DIGITS,
    RADAR_MIN_COPY_COUNT,
    RADAR_MIN_EXPECTED_COPIES_DEFAULT,
)

_DECK_LINE_RE = re.compile(r"^(?P<count>\d+)\s+(?P<name>.+?)\s*$")
_SIDEBOARD_MARKERS = {"sideboard", "sb:", "sb"}


@dataclass
class CardFrequency:
    """Statistics for a card's appearance in an archetype."""

    card_name: str
    appearances: int
    total_copies: int
    max_copies: int
    avg_copies: float
    inclusion_rate: float
    expected_copies: float
    copy_distribution: dict[int, int]


@dataclass
class RadarData:
    """Complete radar data for an archetype."""

    archetype_name: str
    format_name: str
    mainboard_cards: list[CardFrequency]
    sideboard_cards: list[CardFrequency]
    total_decks_analyzed: int
    decks_failed: int


@dataclass
class CardCopyTotal:
    """Total copies played for one card across a full-format card pool."""

    card_name: str
    copies_played: int


@dataclass
class FormatCardPoolData:
    """Aggregated card-pool view for all published decks in one format."""

    format_name: str
    cards: list[str]
    copy_totals: list[CardCopyTotal]
    total_decks_analyzed: int
    decks_failed: int


class RadarService:
    """Service for calculating archetype radar card-frequency snapshots."""

    def __init__(
        self,
        metagame_repository: MetagameRepository | None = None,
        deck_service: Any | None = None,
    ) -> None:
        self.metagame_repo = metagame_repository or get_metagame_repository()
        self.deck_service = deck_service

    def calculate_radar(
        self,
        archetype: dict[str, Any],
        format_name: str,
        max_decks: int | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
        source_filter: str | None = None,
    ) -> RadarData:
        """Calculate radar data by fetching and analyzing decks for one archetype."""

        archetype_name = archetype.get("name", "Unknown")
        logger.info("Calculating radar for {} in {}", archetype_name, format_name)

        decks = self.metagame_repo.get_decks_for_archetype(archetype, source_filter=source_filter)
        if not decks:
            logger.warning("No decks found for {}", archetype_name)
            return RadarData(
                archetype_name=archetype_name,
                format_name=format_name,
                mainboard_cards=[],
                sideboard_cards=[],
                total_decks_analyzed=0,
                decks_failed=0,
            )

        if max_decks is not None:
            decks = decks[:max_decks]

        deck_texts: list[str] = []
        deck_names: list[str] = []
        failed_decks = 0

        for index, deck in enumerate(decks, 1):
            deck_name = deck.get("name", f"Deck {index}")
            if progress_callback:
                progress_callback(index, len(decks), deck_name)
            try:
                deck_texts.append(
                    self.metagame_repo.download_deck_content(deck, source_filter=source_filter)
                )
                deck_names.append(deck_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to download deck {}: {}", deck_name, exc)
                failed_decks += 1

        return self.calculate_radar_from_deck_texts(
            archetype_name=archetype_name,
            format_name=format_name,
            deck_texts=deck_texts,
            deck_names=deck_names,
            decks_failed=failed_decks,
        )

    def calculate_radar_from_deck_texts(
        self,
        *,
        archetype_name: str,
        format_name: str,
        deck_texts: Iterable[str],
        deck_names: Iterable[str] | None = None,
        decks_failed: int = 0,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> RadarData:
        """Calculate radar data from preloaded deck-text blobs."""

        texts = list(deck_texts)
        names = list(deck_names) if deck_names is not None else []
        if names and len(names) != len(texts):
            raise ValueError("deck_names must match deck_texts length")

        if not texts:
            return RadarData(
                archetype_name=archetype_name,
                format_name=format_name,
                mainboard_cards=[],
                sideboard_cards=[],
                total_decks_analyzed=0,
                decks_failed=decks_failed,
            )

        mainboard_stats: dict[str, list[int]] = defaultdict(list)
        sideboard_stats: dict[str, list[int]] = defaultdict(list)
        successful_decks = 0
        total_texts = len(texts)

        for index, deck_text in enumerate(texts, 1):
            deck_name = names[index - 1] if index - 1 < len(names) else f"Deck {index}"
            if progress_callback:
                progress_callback(index, total_texts, deck_name)
            try:
                analysis = self._analyze_deck(deck_text)
                for card_name, count in analysis["mainboard_cards"]:
                    mainboard_stats[card_name].append(int(count))
                for card_name, count in analysis["sideboard_cards"]:
                    sideboard_stats[card_name].append(int(count))
                successful_decks += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to analyze deck {}: {}", deck_name, exc)
                decks_failed += 1

        if successful_decks == 0:
            logger.error("Failed to analyze any decks for {}", archetype_name)
            return RadarData(
                archetype_name=archetype_name,
                format_name=format_name,
                mainboard_cards=[],
                sideboard_cards=[],
                total_decks_analyzed=0,
                decks_failed=decks_failed,
            )

        mainboard_frequencies = self._calculate_frequencies(mainboard_stats, successful_decks)
        sideboard_frequencies = self._calculate_frequencies(sideboard_stats, successful_decks)
        mainboard_frequencies.sort(
            key=lambda item: (item.expected_copies, item.inclusion_rate), reverse=True
        )
        sideboard_frequencies.sort(
            key=lambda item: (item.expected_copies, item.inclusion_rate), reverse=True
        )

        return RadarData(
            archetype_name=archetype_name,
            format_name=format_name,
            mainboard_cards=mainboard_frequencies,
            sideboard_cards=sideboard_frequencies,
            total_decks_analyzed=successful_decks,
            decks_failed=decks_failed,
        )

    def _analyze_deck(self, deck_text: str) -> dict[str, Any]:
        if self.deck_service is not None and hasattr(self.deck_service, "analyze_deck"):
            return self.deck_service.analyze_deck(deck_text)
        return self._parse_deck_text(deck_text)

    def _parse_deck_text(self, deck_text: str) -> dict[str, Any]:
        mainboard: dict[str, int] = {}
        sideboard: dict[str, int] = {}
        current_zone = mainboard

        for raw_line in deck_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.lower() in _SIDEBOARD_MARKERS:
                current_zone = sideboard
                continue

            match = _DECK_LINE_RE.match(line)
            if match is None:
                continue

            count = int(match.group("count"))
            if count <= 0:
                continue

            card_name = match.group("name").strip()
            if not card_name:
                continue

            current_zone[card_name] = current_zone.get(card_name, 0) + count

        return {
            "mainboard_cards": list(mainboard.items()),
            "sideboard_cards": list(sideboard.items()),
            "mainboard_count": sum(mainboard.values()),
            "sideboard_count": sum(sideboard.values()),
        }

    def _calculate_frequencies(
        self, card_stats: dict[str, list[int]], total_decks: int
    ) -> list[CardFrequency]:
        """Calculate frequency statistics for one zone."""

        frequencies: list[CardFrequency] = []
        for card_name, counts in card_stats.items():
            appearances = len(counts)
            total_copies = sum(counts)
            max_copies = max(counts)
            avg_copies = total_copies / appearances if appearances > 0 else 0
            inclusion_rate = (appearances / total_decks) * 100 if total_decks > 0 else 0
            expected_copies = total_copies / total_decks if total_decks > 0 else 0

            copy_distribution: dict[int, int] = defaultdict(int)
            for count in counts:
                copy_distribution[count] += 1
            zero_count = max(total_decks - appearances, 0)
            if zero_count:
                copy_distribution[0] += zero_count

            frequencies.append(
                CardFrequency(
                    card_name=card_name,
                    appearances=appearances,
                    total_copies=total_copies,
                    max_copies=max_copies,
                    avg_copies=round(avg_copies, RADAR_AVG_COPIES_ROUND_DIGITS),
                    inclusion_rate=round(inclusion_rate, RADAR_INCLUSION_RATE_ROUND_DIGITS),
                    expected_copies=round(expected_copies, RADAR_EXPECTED_COPIES_ROUND_DIGITS),
                    copy_distribution=dict(sorted(copy_distribution.items(), reverse=True)),
                )
            )

        return frequencies

    def calculate_format_card_pool_from_deck_texts(
        self,
        *,
        format_name: str,
        deck_texts: Iterable[str],
        deck_names: Iterable[str] | None = None,
        decks_failed: int = 0,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> FormatCardPoolData:
        """Aggregate a format-wide card pool from preloaded deck-text blobs."""

        texts = list(deck_texts)
        names = list(deck_names) if deck_names is not None else []
        if names and len(names) != len(texts):
            raise ValueError("deck_names must match deck_texts length")

        card_totals: dict[str, int] = defaultdict(int)
        card_names: set[str] = set()
        successful_decks = 0
        total_texts = len(texts)

        for index, deck_text in enumerate(texts, 1):
            deck_name = names[index - 1] if index - 1 < len(names) else f"Deck {index}"
            if progress_callback:
                progress_callback(index, total_texts, deck_name)
            try:
                analysis = self._analyze_deck(deck_text)
                combined_counts: dict[str, int] = defaultdict(int)
                for zone in ("mainboard_cards", "sideboard_cards"):
                    for card_name, count in analysis[zone]:
                        count_int = int(count)
                        combined_counts[card_name] += count_int
                        card_names.add(card_name)

                for card_name, count in combined_counts.items():
                    card_totals[card_name] += count

                successful_decks += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to analyze deck {} for card pool: {}", deck_name, exc)
                decks_failed += 1

        copy_totals = [
            CardCopyTotal(card_name=card_name, copies_played=copies_played)
            for card_name, copies_played in sorted(
                card_totals.items(),
                key=lambda item: (-item[1], item[0].lower()),
            )
        ]

        return FormatCardPoolData(
            format_name=format_name,
            cards=sorted(card_names, key=str.lower),
            copy_totals=copy_totals,
            total_decks_analyzed=successful_decks,
            decks_failed=decks_failed,
        )

    def export_radar_as_decklist(
        self,
        radar: RadarData,
        min_expected_copies: float = RADAR_MIN_EXPECTED_COPIES_DEFAULT,
        max_cards: int | None = None,
    ) -> str:
        """Export radar output as a representative decklist."""

        lines: list[str] = []

        mainboard = [
            card for card in radar.mainboard_cards if card.expected_copies >= min_expected_copies
        ]
        if max_cards is not None:
            mainboard = mainboard[:max_cards]

        for card in mainboard:
            count = max(RADAR_MIN_COPY_COUNT, round(card.avg_copies))
            lines.append(f"{count} {card.card_name}")

        sideboard = [
            card for card in radar.sideboard_cards if card.expected_copies >= min_expected_copies
        ]
        if max_cards is not None:
            sideboard = sideboard[:max_cards]

        if sideboard:
            lines.append("")
            lines.append("Sideboard")
            for card in sideboard:
                count = max(RADAR_MIN_COPY_COUNT, round(card.avg_copies))
                lines.append(f"{count} {card.card_name}")

        return "\n".join(lines)

    def get_radar_card_names(self, radar: RadarData, zone: str = "both") -> set[str]:
        """Return the set of card names present in a radar snapshot."""

        cards: set[str] = set()
        if zone in ("mainboard", "both"):
            cards.update(card.card_name for card in radar.mainboard_cards)
        if zone in ("sideboard", "both"):
            cards.update(card.card_name for card in radar.sideboard_cards)
        return cards


_default_service: RadarService | None = None


def get_radar_service() -> RadarService:
    """Return the shared radar service instance."""

    global _default_service
    if _default_service is None:
        _default_service = RadarService()
    return _default_service


def reset_radar_service() -> None:
    """Reset the shared radar service instance for tests."""

    global _default_service
    _default_service = None


__all__ = [
    "CardFrequency",
    "CardCopyTotal",
    "FormatCardPoolData",
    "RadarData",
    "RadarService",
    "get_radar_service",
    "reset_radar_service",
]
