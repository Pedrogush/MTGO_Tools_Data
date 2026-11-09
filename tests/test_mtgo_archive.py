import json
from datetime import datetime

import pytest

from publisher.mtgo_archive import (
    MtgoArchiveRepository,
    canonical_archetype,
    preferred_display_names,
)


def _write_snapshot(root, decks, fmt="pauper"):
    path = root / "latest" / "mtgo-decklists" / f"{fmt}.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"format": fmt, "events": [{"id": "1", "decks": decks}]}), encoding="utf-8"
    )


def _row(number, archetype, date="2026-11-08"):
    return {
        "number": number,
        "date": date,
        "archetype": archetype,
        "name": archetype,
        "source": "mtgo",
        "deck_text": f"4 Card {number}\nsideboard\n",
    }


REFERENCE = datetime(2026, 11, 9, 12)


def test_canonical_archetype_formats_href_and_falls_back_to_unknown():
    assert canonical_archetype("Boros Energy", "modern") == ("Boros Energy", "modern-boros-energy")
    assert canonical_archetype(" BR ", "modern") == ("BR", "modern-br")
    assert canonical_archetype(None, "modern") == ("Unknown", "modern-unknown")
    assert canonical_archetype("???", "modern") == ("Unknown", "modern-unknown")


def test_preferred_display_names_picks_most_common_spelling():
    names = ["Death & Taxes", "Death & taxes", "Death & Taxes", "Burn"]
    assert preferred_display_names(names) == {"death-taxes": "Death & Taxes", "burn": "Burn"}


def test_repository_dedupes_windows_and_groups(tmp_path):
    _write_snapshot(
        tmp_path,
        [
            _row("1", "Red Rally"),
            _row("1", "Red Rally"),  # duplicate deck id across events
            _row("2", "Red Rally", date="2026-11-02"),  # first day of the 7-day window
            _row("3", "Red Rally", date="2026-11-01"),  # outside the window
            _row("4", "UB", date="2026-11-07"),
            _row("5", None),
            {**_row("6", "Faeries"), "date": ""},  # undated rows are excluded
        ],
    )
    repo = MtgoArchiveRepository(tmp_path, "Pauper", reference_time=REFERENCE)

    assert [row["number"] for row in repo.load_rows()] == ["5", "1", "4", "2"]
    assert repo.get_archetypes() == [
        {"name": "Red Rally", "href": "pauper-red-rally", "source": "mtgo"},
        {"name": "UB", "href": "pauper-ub", "source": "mtgo"},
    ]
    decks = repo.get_decks_for_archetype({"name": "Red Rally"})
    assert [deck["number"] for deck in decks] == ["1", "2"]
    assert all("deck_text" not in deck for deck in decks)
    assert repo.download_deck_content({"number": "2"}).startswith("4 Card 2")
    with pytest.raises(ValueError):
        repo.download_deck_content({"number": "3"})


def test_repository_requires_the_snapshot(tmp_path):
    repo = MtgoArchiveRepository(tmp_path, "Pauper", reference_time=REFERENCE)
    with pytest.raises(FileNotFoundError, match="scrape-mtgo-decklists"):
        repo.load_rows()


def test_repository_rejects_snapshot_for_another_format(tmp_path):
    _write_snapshot(tmp_path, [_row("1", "Burn")], fmt="pauper")
    (tmp_path / "latest" / "mtgo-decklists" / "pauper.json").rename(
        tmp_path / "latest" / "mtgo-decklists" / "modern.json"
    )
    with pytest.raises(ValueError, match="expected 'modern'"):
        MtgoArchiveRepository(tmp_path, "Modern", reference_time=REFERENCE).load_rows()
