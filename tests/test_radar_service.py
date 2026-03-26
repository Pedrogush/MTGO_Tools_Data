"""Tests for the headless radar service."""

from unittest.mock import MagicMock

import pytest

from services.radar_service import CardFrequency, RadarData, RadarService


@pytest.fixture
def mock_metagame_repo():
    return MagicMock()


@pytest.fixture
def mock_deck_service():
    return MagicMock()


@pytest.fixture
def radar_service(mock_metagame_repo, mock_deck_service):
    return RadarService(metagame_repository=mock_metagame_repo, deck_service=mock_deck_service)


@pytest.fixture
def sample_archetype():
    return {"name": "Azorius Control", "href": "https://example.com/archetype"}


@pytest.fixture
def sample_decks():
    return [
        {"name": "Deck 1", "number": "1"},
        {"name": "Deck 2", "number": "2"},
        {"name": "Deck 3", "number": "3"},
    ]


def test_calculate_frequencies_basic():
    service = RadarService()
    card_stats = {
        "Lightning Bolt": [4, 4, 4],
        "Counterspell": [2, 2],
        "Consider": [4],
    }

    frequencies = service._calculate_frequencies(card_stats, total_decks=3)

    bolt = next(item for item in frequencies if item.card_name == "Lightning Bolt")
    counter = next(item for item in frequencies if item.card_name == "Counterspell")
    consider = next(item for item in frequencies if item.card_name == "Consider")

    assert bolt.appearances == 3
    assert bolt.total_copies == 12
    assert bolt.max_copies == 4
    assert bolt.avg_copies == 4.0
    assert bolt.inclusion_rate == 100.0
    assert bolt.expected_copies == 4.0
    assert bolt.copy_distribution == {4: 3}

    assert counter.appearances == 2
    assert counter.total_copies == 4
    assert counter.max_copies == 2
    assert counter.avg_copies == 2.0
    assert counter.inclusion_rate == pytest.approx(66.7, abs=0.1)
    assert counter.expected_copies == pytest.approx(1.33, abs=0.01)
    assert counter.copy_distribution == {2: 2, 0: 1}

    assert consider.appearances == 1
    assert consider.total_copies == 4
    assert consider.max_copies == 4
    assert consider.avg_copies == 4.0
    assert consider.inclusion_rate == pytest.approx(33.3, abs=0.1)
    assert consider.expected_copies == pytest.approx(1.33, abs=0.01)
    assert consider.copy_distribution == {4: 1, 0: 2}


def test_calculate_radar_success(
    radar_service, mock_metagame_repo, mock_deck_service, sample_archetype, sample_decks
):
    mock_metagame_repo.get_decks_for_archetype.return_value = sample_decks
    mock_metagame_repo.download_deck_content.side_effect = [
        "4 Lightning Bolt\n3 Island\n\nSideboard\n2 Counterspell",
        "4 Lightning Bolt\n4 Island\n\nSideboard\n1 Counterspell",
        "4 Lightning Bolt\n2 Island\n\nSideboard\n3 Counterspell",
    ]

    def mock_analyze(_content):
        return {
            "mainboard_cards": [("Lightning Bolt", 4), ("Island", 3)],
            "sideboard_cards": [("Counterspell", 2)],
        }

    mock_deck_service.analyze_deck.side_effect = mock_analyze

    radar = radar_service.calculate_radar(sample_archetype, "Modern")

    assert radar.archetype_name == "Azorius Control"
    assert radar.format_name == "Modern"
    assert radar.total_decks_analyzed == 3
    assert radar.decks_failed == 0
    assert radar.mainboard_cards[0].card_name == "Lightning Bolt"
    assert radar.sideboard_cards[0].card_name == "Counterspell"


def test_calculate_radar_from_deck_texts_parses_sideboard_and_duplicate_lines():
    service = RadarService()

    radar = service.calculate_radar_from_deck_texts(
        archetype_name="Painter",
        format_name="legacy",
        deck_texts=[
            "4 Goblin Welder\n1 Lotus Petal\n1 Lotus Petal\nsideboard\n2 Pyroblast\n",
            "4 Goblin Welder\n2 Grindstone\nsideboard\n1 Pyroblast\n1 Red Elemental Blast\n",
        ],
    )

    welder = next(item for item in radar.mainboard_cards if item.card_name == "Goblin Welder")
    petal = next(item for item in radar.mainboard_cards if item.card_name == "Lotus Petal")
    pyroblast = next(item for item in radar.sideboard_cards if item.card_name == "Pyroblast")

    assert radar.total_decks_analyzed == 2
    assert radar.decks_failed == 0
    assert welder.expected_copies == 4.0
    assert petal.total_copies == 2
    assert pyroblast.appearances == 2
    assert pyroblast.copy_distribution == {2: 1, 1: 1}


def test_export_radar_as_decklist():
    service = RadarService()
    radar = RadarData(
        archetype_name="Test Archetype",
        format_name="Modern",
        mainboard_cards=[
            CardFrequency("Lightning Bolt", 10, 40, 4, 4.0, 100.0, 4.0, {4: 10}),
            CardFrequency("Counterspell", 5, 10, 2, 2.0, 50.0, 1.0, {2: 5, 0: 5}),
            CardFrequency("Consider", 3, 3, 1, 1.0, 30.0, 0.3, {1: 3, 0: 7}),
        ],
        sideboard_cards=[
            CardFrequency("Abrade", 8, 16, 2, 2.0, 80.0, 1.6, {2: 8, 0: 2}),
            CardFrequency("Negate", 2, 2, 1, 1.0, 20.0, 0.2, {1: 2, 0: 8}),
        ],
        total_decks_analyzed=10,
        decks_failed=0,
    )

    decklist = service.export_radar_as_decklist(radar, min_expected_copies=0.5)

    assert "4 Lightning Bolt" in decklist
    assert "2 Counterspell" in decklist
    assert "1 Consider" not in decklist
    assert "Sideboard" in decklist
    assert "2 Abrade" in decklist
