import json

from publisher.runner import main

TIMESTAMP = "2026-03-23T12:00:00Z"


class _FakeRepo:
    def get_decks_for_archetype(self, archetype, force_refresh=False, source_filter=None):
        assert force_refresh is True
        return [
            {
                "name": archetype["name"],
                "number": "123",
                "date": "2026-03-22",
                "player": "Alice",
                "event": "Modern Challenge",
                "source": "mtggoldfish",
            }
        ]

    def download_deck_content(self, deck, source_filter=None):
        return f"Deck {deck['number']}"


def test_scrape_archetypes_writes_latest_and_hourly(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.fetch_archetypes",
        lambda *args, **kwargs: [{"name": "Temur Rhinos", "href": "modern-temur-rhinos"}],
    )

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-archetypes",
            "--format",
            "Modern",
        ]
    )

    assert exit_code == 0
    latest_path = tmp_path / "latest" / "archetypes" / "modern.json"
    manifest_path = tmp_path / "latest" / "latest.json"
    assert latest_path.exists()
    assert (tmp_path / "hourly" / "2026-03-23T12-00-00Z" / "archetypes" / "modern.json").exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["latest"]["archetype_lists"][0]["path"] == "latest/archetypes/modern.json"


def test_scrape_metagame_writes_daily_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.get_archetype_stats",
        lambda _format: {
            "modern": {
                "timestamp": 1.0,
                "Temur Rhinos": {
                    "decks": [{"number": "123"}],
                    "results": {"2026-03-22": 1, "2026-03-23": 0},
                },
            }
        },
    )

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-metagame",
            "--format",
            "Modern",
            "--day",
            "2026-03-23",
        ]
    )

    assert exit_code == 0
    latest_path = tmp_path / "latest" / "metagame" / "modern.json"
    daily_path = tmp_path / "daily" / "2026-03-23" / "metagame" / "modern.json"
    snapshot = json.loads(latest_path.read_text(encoding="utf-8"))
    assert latest_path.exists()
    assert daily_path.exists()
    assert snapshot["stats"][0]["archetype"] == "Temur Rhinos"


def test_scrape_deck_texts_writes_latest_and_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.fetch_archetypes",
        lambda *args, **kwargs: [{"name": "Temur Rhinos", "href": "modern-temur-rhinos"}],
    )
    monkeypatch.setattr("publisher.runner.ScrapingMetagameRepository", _FakeRepo)

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-deck-texts",
            "--format",
            "Modern",
            "--archetype",
            "Temur Rhinos",
            "--days",
            "7",
        ]
    )

    assert exit_code == 0
    latest_path = tmp_path / "latest" / "deck-texts" / "modern" / "temur-rhinos.json"
    manifest_path = tmp_path / "latest" / "latest.json"
    blob = json.loads(latest_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert blob["deck_texts"][0]["deck_text"] == "Deck 123"
    assert manifest["latest"]["deck_text_blobs"][0]["path"].endswith("temur-rhinos.json")
