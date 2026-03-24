import json

from publisher.runner import main

TIMESTAMP = "2026-03-23T12:00:00Z"
LATER_TIMESTAMP = "2026-03-23T18:00:00Z"


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


def test_scrape_archetypes_writes_run_manifest_and_posix_path(monkeypatch, tmp_path):
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
    run_path = tmp_path / "latest" / "runs" / "scrape-archetypes.json"
    assert latest_path.exists()
    assert (tmp_path / "hourly" / "2026-03-23T12-00-00Z" / "archetypes" / "modern.json").exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_manifest = json.loads(run_path.read_text(encoding="utf-8"))
    assert manifest["latest"]["archetype_lists"][0]["path"] == "latest/archetypes/modern.json"
    assert run_manifest["summary"]["success"] == 1


def test_scrape_archetypes_uses_stale_fallback_when_latest_is_fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.fetch_archetypes",
        lambda *args, **kwargs: [{"name": "Temur Rhinos", "href": "modern-temur-rhinos"}],
    )
    first_exit = main(
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
    assert first_exit == 0

    def _boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("publisher.runner.fetch_archetypes", _boom)
    second_exit = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            LATER_TIMESTAMP,
            "--max-stale-hours",
            "24",
            "scrape-archetypes",
            "--format",
            "Modern",
        ]
    )

    assert second_exit == 0
    run_manifest = json.loads(
        (tmp_path / "latest" / "runs" / "scrape-archetypes.json").read_text(encoding="utf-8")
    )
    assert run_manifest["results"][0]["status"] == "stale-fallback"


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


def test_scrape_decks_references_shared_deck_text_blob(monkeypatch, tmp_path):
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
            "scrape-decks",
            "--format",
            "Modern",
            "--archetype",
            "Temur Rhinos",
            "--days",
            "7",
        ]
    )

    assert exit_code == 0
    latest_path = tmp_path / "latest" / "decks" / "modern" / "temur-rhinos.json"
    snapshot = json.loads(latest_path.read_text(encoding="utf-8"))
    assert snapshot["decks"][0]["deck_text_path"] == "archive/deck-texts/modern/123.json"


def test_scrape_deck_texts_deduplicates_by_deck_id(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.fetch_archetypes",
        lambda *args, **kwargs: [
            {"name": "Temur Rhinos", "href": "modern-temur-rhinos"},
            {"name": "Rhinos Copy", "href": "modern-rhinos-copy"},
        ],
    )

    class _DuplicatingRepo(_FakeRepo):
        def get_decks_for_archetype(self, archetype, force_refresh=False, source_filter=None):
            deck = super().get_decks_for_archetype(archetype, force_refresh, source_filter)[0]
            return [dict(deck, name=archetype["name"])]

    monkeypatch.setattr("publisher.runner.ScrapingMetagameRepository", _DuplicatingRepo)

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-deck-texts",
            "--format",
            "Modern",
            "--days",
            "7",
        ]
    )

    assert exit_code == 0
    deck_text_path = tmp_path / "archive" / "deck-texts" / "modern" / "123.json"
    manifest_path = tmp_path / "latest" / "latest.json"
    blob = json.loads(deck_text_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert blob["deck_text"] == "Deck 123"
    assert len(manifest["latest"]["deck_text_blobs"]) == 1
    assert manifest["latest"]["deck_text_blobs"][0]["path"] == "archive/deck-texts/modern/123.json"


def test_scrape_deck_texts_sleeps_between_unique_downloads(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.fetch_archetypes",
        lambda *args, **kwargs: [{"name": "Temur Rhinos", "href": "modern-temur-rhinos"}],
    )

    class _MultiDeckRepo(_FakeRepo):
        def get_decks_for_archetype(self, archetype, force_refresh=False, source_filter=None):
            return [
                {
                    "name": archetype["name"],
                    "number": "123",
                    "date": "2026-03-22",
                    "player": "Alice",
                    "event": "Modern Challenge",
                    "source": "mtggoldfish",
                },
                {
                    "name": archetype["name"],
                    "number": "456",
                    "date": "2026-03-22",
                    "player": "Bob",
                    "event": "Modern Challenge",
                    "source": "mtggoldfish",
                },
            ]

    sleeps: list[float] = []
    monkeypatch.setattr("publisher.runner.ScrapingMetagameRepository", _MultiDeckRepo)
    monkeypatch.setattr("publisher.runner.time.sleep", sleeps.append)

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-deck-texts",
            "--format",
            "Modern",
            "--days",
            "7",
            "--deck-download-delay-seconds",
            "3",
        ]
    )

    assert exit_code == 0
    assert sleeps == [3.0]
