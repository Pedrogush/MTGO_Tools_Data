import json
from datetime import datetime

from publisher.mtgo_archive import MtgoArchiveRepository

REFERENCE = datetime(2026, 3, 23)


def _write_event(tmp_path, event_id, decks):
    path = tmp_path / "archive" / "mtgo-decklists" / "modern" / f"{event_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"decks": decks}), encoding="utf-8")


def _deck(number, archetype="Burn", date="2026-03-22", text="4 Lightning Bolt\nsideboard\n"):
    return {
        "number": number,
        "date": date,
        "archetype": archetype,
        "name": archetype,
        "source": "mtgo",
        "format": "modern",
        "deck_text": text,
    }


def test_load_rows_dedupes_and_sorts_newest_first(tmp_path):
    _write_event(tmp_path, "1", [_deck("10", date="2026-03-20"), _deck("11", date="2026-03-22")])
    _write_event(tmp_path, "2", [_deck("10", date="2026-03-20"), _deck("12", date="2026-03-21")])

    rows = MtgoArchiveRepository(tmp_path, "Modern", reference_time=REFERENCE).load_rows()

    assert [row["number"] for row in rows] == ["11", "12", "10"]


def test_get_archetypes_returns_distinct_slugged_entries(tmp_path):
    _write_event(tmp_path, "1", [_deck("10", archetype="Boros Energy"), _deck("11", archetype="Burn")])

    archetypes = MtgoArchiveRepository(tmp_path, "Modern", reference_time=REFERENCE).get_archetypes()

    assert archetypes == [
        {"name": "Boros Energy", "href": "boros-energy"},
        {"name": "Burn", "href": "burn"},
    ]


def test_get_decks_for_archetype_strips_deck_text(tmp_path):
    _write_event(tmp_path, "1", [_deck("10", archetype="Burn"), _deck("11", archetype="Tron")])

    repo = MtgoArchiveRepository(tmp_path, "Modern", reference_time=REFERENCE)
    decks = repo.get_decks_for_archetype({"name": "Burn", "href": "burn"})

    assert [deck["number"] for deck in decks] == ["10"]
    assert all("deck_text" not in deck for deck in decks)


def test_download_deck_content_returns_embedded_text(tmp_path):
    _write_event(tmp_path, "1", [_deck("10", text="4 Bolt\nsideboard\n2 Smash\n")])

    repo = MtgoArchiveRepository(tmp_path, "Modern", reference_time=REFERENCE)
    assert repo.download_deck_content({"number": "10"}) == "4 Bolt\nsideboard\n2 Smash\n"


def test_get_archetype_stats_counts_by_day(tmp_path):
    _write_event(
        tmp_path,
        "1",
        [
            _deck("10", date="2026-03-22"),
            _deck("11", date="2026-03-22"),
            _deck("12", date="2026-03-21", archetype="Tron"),
        ],
    )

    stats = MtgoArchiveRepository(tmp_path, "Modern", reference_time=REFERENCE).get_archetype_stats(
        lookback_dates=["2026-03-21", "2026-03-22", "2026-03-23"]
    )

    assert stats == [
        {
            "archetype": "Burn",
            "deck_count": 2,
            "daily_counts": {"2026-03-21": 0, "2026-03-22": 2, "2026-03-23": 0},
        },
        {
            "archetype": "Tron",
            "deck_count": 1,
            "daily_counts": {"2026-03-21": 1, "2026-03-22": 0, "2026-03-23": 0},
        },
    ]


def test_missing_archive_dir_yields_empty(tmp_path):
    repo = MtgoArchiveRepository(tmp_path, "Modern", reference_time=REFERENCE)
    assert repo.load_rows() == []
    assert repo.get_archetypes() == []


def test_load_rows_windows_out_old_and_undated_decks(tmp_path):
    _write_event(
        tmp_path,
        "1",
        [
            _deck("10", date="2026-03-22"),
            _deck("11", date="2026-03-01"),
            _deck("12", date="not-a-date"),
        ],
    )

    rows = MtgoArchiveRepository(tmp_path, "Modern", reference_time=REFERENCE).load_rows()

    assert [row["number"] for row in rows] == ["10"]
