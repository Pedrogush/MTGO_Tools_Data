import json

from publisher.contracts import build_latest_manifest
from publisher.layout import write_json
from publisher.retention import prune_output_tree

NOW = "2026-03-23T18:00:00Z"


def _write_snapshot(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, payload)


def test_prune_output_tree_removes_old_snapshots_and_unreferenced_deck_texts(tmp_path):
    retained_hourly = tmp_path / "hourly" / "2026-03-23T12-00-00Z" / "decks" / "modern"
    expired_hourly = tmp_path / "hourly" / "2026-03-15T12-00-00Z" / "decks" / "modern"
    retained_daily = tmp_path / "daily" / "2026-03-20" / "metagame"
    expired_daily = tmp_path / "daily" / "2026-03-10" / "metagame"

    _write_snapshot(
        tmp_path / "latest" / "decks" / "modern" / "temur-rhinos.json",
        {
            "decks": [
                {
                    "number": "123",
                    "deck_text_path": "archive/deck-texts/modern/123.json",
                }
            ]
        },
    )
    _write_snapshot(
        retained_hourly / "temur-rhinos.json",
        {
            "decks": [
                {
                    "number": "123",
                    "deck_text_path": "archive/deck-texts/modern/123.json",
                }
            ]
        },
    )
    _write_snapshot(
        expired_hourly / "old-snapshot.json",
        {
            "decks": [
                {
                    "number": "999",
                    "deck_text_path": "archive/deck-texts/modern/999.json",
                }
            ]
        },
    )
    _write_snapshot(retained_daily / "modern.json", {"stats": []})
    _write_snapshot(expired_daily / "modern.json", {"stats": []})
    _write_snapshot(
        tmp_path / "archive" / "deck-texts" / "modern" / "123.json", {"deck_text": "keep"}
    )
    _write_snapshot(
        tmp_path / "archive" / "deck-texts" / "modern" / "999.json", {"deck_text": "drop"}
    )

    manifest = build_latest_manifest(generated_at=NOW, retention_days=7)
    manifest["latest"]["archetype_decks"].append(
        {
            "format": "modern",
            "archetype": "temur-rhinos",
            "path": "latest/decks/modern/temur-rhinos.json",
            "updated_at": NOW,
        }
    )
    manifest["latest"]["deck_text_blobs"].extend(
        [
            {
                "format": "modern",
                "deck_id": "123",
                "path": "archive/deck-texts/modern/123.json",
                "updated_at": NOW,
            },
            {
                "format": "modern",
                "deck_id": "999",
                "path": "archive/deck-texts/modern/999.json",
                "updated_at": NOW,
            },
        ]
    )
    _write_snapshot(tmp_path / "latest" / "latest.json", manifest)

    summary = prune_output_tree(tmp_path, generated_at=NOW, retention_days=7)

    assert summary["hourly_dirs_removed"] == 1
    assert summary["daily_dirs_removed"] == 1
    assert summary["deck_text_blobs_removed"] == 1
    assert summary["deck_text_manifest_entries_removed"] == 1
    assert (tmp_path / "hourly" / "2026-03-23T12-00-00Z").exists()
    assert not (tmp_path / "hourly" / "2026-03-15T12-00-00Z").exists()
    assert (tmp_path / "daily" / "2026-03-20").exists()
    assert not (tmp_path / "daily" / "2026-03-10").exists()
    assert (tmp_path / "archive" / "deck-texts" / "modern" / "123.json").exists()
    assert not (tmp_path / "archive" / "deck-texts" / "modern" / "999.json").exists()

    latest_manifest = json.loads((tmp_path / "latest" / "latest.json").read_text(encoding="utf-8"))
    assert latest_manifest["retention_days"] == 7
    assert latest_manifest["latest"]["deck_text_blobs"] == [
        {
            "format": "modern",
            "deck_id": "123",
            "path": "archive/deck-texts/modern/123.json",
            "updated_at": NOW,
        }
    ]
