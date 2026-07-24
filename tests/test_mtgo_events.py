import pytest

from utils.mtgo_events import is_mtgo_event_name

# Real event names from five months of published snapshots (2026-03 → 2026-07).
MTGO_NAMES = [
    "Modern League 2026-07-24",
    "Modern Challenge 64 2026-07-23 (1)",
    "Standard Challenge 32 2026-07-20",
    "Modern Last Chance 2026-07-20 (1)",
    "Standard Showcase Qualifier 2026-03-29",
    "Modern RC Super Qualifier 2026-06-07",
    "Modern Showcase Challenge 2026-07-12",
    "pauper challenge 32 2026-07-01",
]

PAPER_NAMES = [
    "Store Qualifier CAMS 13 | MODERN | The Raccoon House",
    "Modern Store Championship",
    "Vault 509 Trading Card Shop Modern RCQ",
    "First summer RCQ",
    "Mid-Month Madness #2 - White Elephant",
    "LDXP SEA26 3/28 Modern ReCQ 3:00 PM",
    "Mont Weekly Modern",
    "Modern RCQ Kristiansand 2026",
    "Srlandsmesterskap 2026 + RCQ",
    "$$Big Brain Games #8 $$",
    "",
]


@pytest.mark.parametrize("name", MTGO_NAMES)
def test_mtgo_event_names_are_detected(name):
    assert is_mtgo_event_name(name)


@pytest.mark.parametrize("name", PAPER_NAMES)
def test_paper_event_names_are_kept(name):
    assert not is_mtgo_event_name(name)


def test_none_is_not_mtgo():
    assert not is_mtgo_event_name(None)
