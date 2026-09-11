import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "dedupe_mtgo_archive.py"
MODULE_SPEC = importlib.util.spec_from_file_location("dedupe_mtgo_archive", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
dedupe = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = dedupe
MODULE_SPEC.loader.exec_module(dedupe)


def write_event(directory: Path, filename: str, event_id: str, deck_ids: list[str]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "kind": "mtgo_event_decklists",
                "event_id": event_id,
                "decks": [{"number": deck_id, "deck_text": "1 Island\n"} for deck_id in deck_ids],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_removes_legacy_copy_whose_id_suffixes_the_canonical_one(tmp_path):
    vintage = tmp_path / "vintage"
    legacy = write_event(
        vintage, "vintage-challenge-32-2026-07-2312848175.json",
        "vintage-challenge-32-2026-07-2312848175", ["1", "2"],
    )
    canonical = write_event(vintage, "12848175.json", "12848175", ["1", "2"])

    removable, warnings = dedupe.find_duplicates(tmp_path)

    assert removable == [(legacy, canonical)]
    assert warnings == []


def test_keeps_legacy_copy_holding_decks_the_canonical_one_lacks(tmp_path):
    vintage = tmp_path / "vintage"
    write_event(
        vintage, "vintage-challenge-32-2026-07-2312848175.json",
        "vintage-challenge-32-2026-07-2312848175", ["1", "2", "3"],
    )
    write_event(vintage, "12848175.json", "12848175", ["1", "2"])

    removable, warnings = dedupe.find_duplicates(tmp_path)

    assert removable == []
    assert any("absent from" in warning for warning in warnings)


def test_keeps_legacy_files_that_have_no_canonical_counterpart(tmp_path):
    vintage = tmp_path / "vintage"
    write_event(
        vintage, "vintage-league-2026-04-2210668.json",
        "vintage-league-2026-04-2210668", ["1"],
    )

    removable, warnings = dedupe.find_duplicates(tmp_path)

    assert removable == []
    assert warnings == []


def test_does_not_merge_distinct_league_events_sharing_a_digit_suffix(tmp_path):
    """A trailing-digit rule would collapse these; the canonical-id rule must not."""
    vintage = tmp_path / "vintage"
    write_event(
        vintage, "vintage-league-2026-04-2210668.json",
        "vintage-league-2026-04-2210668", ["1"],
    )
    write_event(
        vintage, "vintage-league-2026-05-2210668.json",
        "vintage-league-2026-05-2210668", ["2"],
    )

    removable, _ = dedupe.find_duplicates(tmp_path)

    assert removable == []


def test_prefers_the_longest_canonical_id_suffix(tmp_path):
    vintage = tmp_path / "vintage"
    write_event(vintage, "8175.json", "8175", ["9"])
    canonical = write_event(vintage, "12848175.json", "12848175", ["1"])
    legacy = write_event(
        vintage, "vintage-challenge-2312848175.json", "vintage-challenge-2312848175", ["1"]
    )

    removable, _ = dedupe.find_duplicates(tmp_path)

    assert removable == [(legacy, canonical)]


def test_negative_league_ids_are_canonical(tmp_path):
    legacy_dir = tmp_path / "legacy"
    canonical = write_event(legacy_dir, "n10668.json", "n10668", ["1"])
    legacy = write_event(
        legacy_dir, "legacy-league-2026-04-22n10668.json", "legacy-league-2026-04-22n10668", ["1"]
    )

    removable, _ = dedupe.find_duplicates(tmp_path)

    assert removable == [(legacy, canonical)]
