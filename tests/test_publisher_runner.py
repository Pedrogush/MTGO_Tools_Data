import json

from publisher.contracts import (
    build_archetype_deck_snapshot,
    build_archetype_list_snapshot,
    build_deck_text_blob,
    build_mtgo_decklists_snapshot,
)
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
    run_path = tmp_path / "latest" / "runs" / "scrape-archetypes-modern.json"
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
        (tmp_path / "latest" / "runs" / "scrape-archetypes-modern.json").read_text(encoding="utf-8")
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


def test_scrape_metagame_accepts_titlecase_stats_key(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.get_archetype_stats",
        lambda _format: {
            "Modern": {
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
    snapshot = json.loads(latest_path.read_text(encoding="utf-8"))
    assert latest_path.exists()
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


def test_scrape_deck_texts_reuses_existing_published_blob(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.fetch_archetypes",
        lambda *args, **kwargs: [{"name": "Temur Rhinos", "href": "modern-temur-rhinos"}],
    )
    monkeypatch.setattr("publisher.runner.ScrapingMetagameRepository", _FakeRepo)

    archive_path = tmp_path / "archive" / "deck-texts" / "modern" / "123.json"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "kind": "deck_text_blob",
                "generated_at": "2026-03-22T12:00:00Z",
                "format": "modern",
                "source": "mtggoldfish",
                "deck_id": "123",
                "deck_name": "Temur Rhinos",
                "deck_text": "Deck 123",
            }
        ),
        encoding="utf-8",
    )

    sleeps: list[float] = []
    monkeypatch.setattr("publisher.runner.time.sleep", sleeps.append)

    def _boom(*args, **kwargs):
        raise AssertionError("download_deck_content should not be called for reused blobs")

    monkeypatch.setattr(_FakeRepo, "download_deck_content", _boom)

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
    assert sleeps == []
    run_manifest = json.loads(
        (tmp_path / "latest" / "runs" / "scrape-deck-texts-modern.json").read_text(encoding="utf-8")
    )
    assert run_manifest["results"][-1]["status"] == "skipped"
    assert run_manifest["results"][-1]["message"] == "Reused existing published deck-text blob."


def test_scrape_deck_texts_skips_empty_recent_window_without_failing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.fetch_archetypes",
        lambda *args, **kwargs: [{"name": "Temur Rhinos", "href": "modern-temur-rhinos"}],
    )

    class _OldDeckRepo(_FakeRepo):
        def get_decks_for_archetype(self, archetype, force_refresh=False, source_filter=None):
            return [
                {
                    "name": archetype["name"],
                    "number": "123",
                    "date": "2026-03-01",
                    "player": "Alice",
                    "event": "Modern Challenge",
                    "source": "mtggoldfish",
                }
            ]

    monkeypatch.setattr("publisher.runner.ScrapingMetagameRepository", _OldDeckRepo)

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
    latest_path = tmp_path / "latest" / "decks" / "modern" / "temur-rhinos.json"
    snapshot = json.loads(latest_path.read_text(encoding="utf-8"))
    run_manifest = json.loads(
        (tmp_path / "latest" / "runs" / "scrape-deck-texts-modern.json").read_text(encoding="utf-8")
    )

    assert snapshot["decks"] == []
    assert run_manifest["status"] == "success"
    assert run_manifest["results"][1]["status"] == "skipped"
    assert run_manifest["results"][1]["message"] == "No decks found within the last 7 days."


def test_scrape_radars_writes_snapshots_from_published_deck_texts(tmp_path):
    deck_snapshot_path = tmp_path / "latest" / "decks" / "modern" / "temur-rhinos.json"
    deck_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    deck_snapshot_path.write_text(
        json.dumps(
            build_archetype_deck_snapshot(
                generated_at=TIMESTAMP,
                format_name="modern",
                source="both",
                archetype={"name": "Temur Rhinos", "href": "modern-temur-rhinos"},
                decks=[
                    {
                        "name": "Temur Rhinos",
                        "number": "123",
                        "date": "2026-03-22",
                        "player": "Alice",
                        "event": "Modern Challenge",
                        "source": "mtggoldfish",
                        "deck_text_path": "archive/deck-texts/modern/123.json",
                    },
                    {
                        "name": "Temur Rhinos",
                        "number": "456",
                        "date": "2026-03-22",
                        "player": "Bob",
                        "event": "Modern Challenge",
                        "source": "mtggoldfish",
                        "deck_text_path": "archive/deck-texts/modern/456.json",
                    },
                ],
            ),
            indent=2,
        ),
        encoding="utf-8",
    )

    for deck_id, deck_text in {
        "123": "4 Crashing Footfalls\n4 Fire // Ice\nsideboard\n2 Force of Vigor\n",
        "456": "4 Crashing Footfalls\n2 Fire // Ice\nsideboard\n1 Force of Vigor\n",
    }.items():
        blob_path = tmp_path / "archive" / "deck-texts" / "modern" / f"{deck_id}.json"
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        blob_path.write_text(
            json.dumps(
                build_deck_text_blob(
                    generated_at=TIMESTAMP,
                    format_name="modern",
                    source="mtggoldfish",
                    deck_id=deck_id,
                    deck_name="Temur Rhinos",
                    deck_text=deck_text,
                ),
                indent=2,
            ),
            encoding="utf-8",
        )

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-radars",
            "--format",
            "Modern",
        ]
    )

    assert exit_code == 0
    latest_path = tmp_path / "latest" / "radars" / "modern" / "temur-rhinos.json"
    card_pool_path = tmp_path / "latest" / "card-pools" / "modern.json"
    manifest_path = tmp_path / "latest" / "latest.json"
    run_path = tmp_path / "latest" / "runs" / "scrape-radars-modern.json"
    snapshot = json.loads(latest_path.read_text(encoding="utf-8"))
    card_pool = json.loads(card_pool_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_manifest = json.loads(run_path.read_text(encoding="utf-8"))

    assert latest_path.exists()
    assert card_pool_path.exists()
    assert snapshot["kind"] == "archetype_radar"
    assert snapshot["total_decks_analyzed"] == 2
    assert snapshot["mainboard_cards"][0]["card_name"] == "Crashing Footfalls"
    assert card_pool["kind"] == "format_card_pool"
    assert card_pool["cards"] == ["Crashing Footfalls", "Fire // Ice", "Force of Vigor"]
    assert card_pool["copy_totals"] == [
        {"card_name": "Crashing Footfalls", "copies_played": 8},
        {"card_name": "Fire // Ice", "copies_played": 6},
        {"card_name": "Force of Vigor", "copies_played": 3},
    ]
    assert (
        manifest["latest"]["archetype_radars"][0]["path"]
        == "latest/radars/modern/temur-rhinos.json"
    )
    assert manifest["latest"]["format_card_pools"][0]["path"] == "latest/card-pools/modern.json"
    assert run_manifest["summary"]["success"] == 2


def _write_mtgo_decklists_fixture(tmp_path, decks):
    snapshot = build_mtgo_decklists_snapshot(
        generated_at=TIMESTAMP,
        format_name="modern",
        source="videre-api",
        days=7,
        events=[
            {
                "id": "12345",
                "url": "https://api.videreproject.com/decks?event_id=12345",
                "title": "Modern League",
                "publish_date": "2026-03-22",
                "event_type": "league",
                "decks_total": len(decks),
                "decks_cached": len(decks),
                "path": "archive/mtgo-decklists/modern/12345.json",
                "decks": decks,
            }
        ],
    )
    path = tmp_path / "latest" / "mtgo-decklists" / "modern.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def test_scrape_radars_merges_mtgo_decklists_into_radars_and_card_pool(tmp_path):
    deck_snapshot_path = tmp_path / "latest" / "decks" / "modern" / "temur-rhinos.json"
    deck_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    deck_snapshot_path.write_text(
        json.dumps(
            build_archetype_deck_snapshot(
                generated_at=TIMESTAMP,
                format_name="modern",
                source="both",
                archetype={"name": "Temur Rhinos", "href": "modern-temur-rhinos"},
                decks=[
                    {
                        "name": "Temur Rhinos",
                        "number": "123",
                        "date": "2026-03-22",
                        "player": "Alice",
                        "event": "Modern Challenge",
                        "source": "mtggoldfish",
                        "deck_text_path": "archive/deck-texts/modern/123.json",
                    }
                ],
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    blob_path = tmp_path / "archive" / "deck-texts" / "modern" / "123.json"
    blob_path.parent.mkdir(parents=True, exist_ok=True)
    blob_path.write_text(
        json.dumps(
            build_deck_text_blob(
                generated_at=TIMESTAMP,
                format_name="modern",
                source="mtggoldfish",
                deck_id="123",
                deck_name="Temur Rhinos",
                deck_text="4 Crashing Footfalls\n",
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_mtgo_decklists_fixture(
        tmp_path,
        [
            {
                "number": "999",
                "archetype": "Temur Rhinos",
                "name": "Temur Rhinos",
                "source": "mtgo",
                "deck_text": "4 Crashing Footfalls\n4 Bonecrusher Giant\n",
            },
            {
                "number": "888",
                "archetype": "Izzet Murktide",
                "name": "Izzet Murktide",
                "source": "mtgo",
                "deck_text": "4 Murktide Regent\n",
            },
            {
                "number": "777",
                "archetype": "Unknown",
                "name": "Unknown",
                "source": "mtgo",
                "deck_text": "4 Island\n",
            },
        ],
    )

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-radars",
            "--format",
            "Modern",
        ]
    )

    assert exit_code == 0
    rhinos_radar = json.loads(
        (tmp_path / "latest" / "radars" / "modern" / "temur-rhinos.json").read_text(
            encoding="utf-8"
        )
    )
    assert rhinos_radar["total_decks_analyzed"] == 2

    murktide_radar = json.loads(
        (tmp_path / "latest" / "radars" / "modern" / "izzet-murktide.json").read_text(
            encoding="utf-8"
        )
    )
    assert murktide_radar["archetype"] == {
        "name": "Izzet Murktide",
        "href": "modern-izzet-murktide",
    }
    assert murktide_radar["total_decks_analyzed"] == 1

    assert not (tmp_path / "latest" / "radars" / "modern" / "unknown.json").exists()

    card_pool = json.loads(
        (tmp_path / "latest" / "card-pools" / "modern.json").read_text(encoding="utf-8")
    )
    assert card_pool["total_decks_analyzed"] == 4
    assert {"Crashing Footfalls", "Bonecrusher Giant", "Murktide Regent", "Island"} <= set(
        card_pool["cards"]
    )


def test_scrape_radars_succeeds_when_goldfish_has_no_decks(tmp_path):
    deck_snapshot_path = tmp_path / "latest" / "decks" / "modern" / "temur-rhinos.json"
    deck_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    deck_snapshot_path.write_text(
        json.dumps(
            build_archetype_deck_snapshot(
                generated_at=TIMESTAMP,
                format_name="modern",
                source="both",
                archetype={"name": "Temur Rhinos", "href": "modern-temur-rhinos"},
                decks=[],
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_mtgo_decklists_fixture(
        tmp_path,
        [
            {
                "number": "999",
                "archetype": "Temur Rhinos",
                "name": "Temur Rhinos",
                "source": "mtgo",
                "deck_text": "4 Crashing Footfalls\n",
            }
        ],
    )

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-radars",
            "--format",
            "Modern",
        ]
    )

    assert exit_code == 0
    radar = json.loads(
        (tmp_path / "latest" / "radars" / "modern" / "temur-rhinos.json").read_text(
            encoding="utf-8"
        )
    )
    assert radar["total_decks_analyzed"] == 1
    card_pool = json.loads(
        (tmp_path / "latest" / "card-pools" / "modern.json").read_text(encoding="utf-8")
    )
    assert card_pool["total_decks_analyzed"] == 1
    assert card_pool["cards"] == ["Crashing Footfalls"]
    run_manifest = json.loads(
        (tmp_path / "latest" / "runs" / "scrape-radars-modern.json").read_text(encoding="utf-8")
    )
    assert run_manifest["status"] == "success"
    assert not any(result["status"] == "hard-failure" for result in run_manifest["results"])


def test_scrape_radars_merges_mtgo_decks_under_canonical_archetype_name(tmp_path):
    archetypes_path = tmp_path / "latest" / "archetypes" / "modern.json"
    archetypes_path.parent.mkdir(parents=True, exist_ok=True)
    archetypes_path.write_text(
        json.dumps(
            build_archetype_list_snapshot(
                generated_at=TIMESTAMP,
                format_name="modern",
                source="mtggoldfish",
                archetypes=[{"name": "Counter Vine", "href": "modern-counter-vine"}],
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    deck_snapshot_path = tmp_path / "latest" / "decks" / "modern" / "counter-vine.json"
    deck_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    deck_snapshot_path.write_text(
        json.dumps(
            build_archetype_deck_snapshot(
                generated_at=TIMESTAMP,
                format_name="modern",
                source="both",
                archetype={"name": "Counter Vine", "href": "modern-counter-vine"},
                decks=[],
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_mtgo_decklists_fixture(
        tmp_path,
        [
            {
                "number": "999",
                "archetype": "Countervine",
                "name": "Countervine",
                "source": "mtgo",
                "deck_text": "4 Vengevine\n",
            }
        ],
    )

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-radars",
            "--format",
            "Modern",
        ]
    )

    assert exit_code == 0
    radar = json.loads(
        (tmp_path / "latest" / "radars" / "modern" / "counter-vine.json").read_text(
            encoding="utf-8"
        )
    )
    assert radar["total_decks_analyzed"] == 1
    assert radar["archetype"] == {"name": "Counter Vine", "href": "modern-counter-vine"}
    assert not (tmp_path / "latest" / "radars" / "modern" / "countervine.json").exists()


def test_scrape_archetypes_unions_mtgo_only_archetypes(monkeypatch, tmp_path):
    _write_mtgo_decklists_fixture(
        tmp_path,
        [
            {
                "number": "1",
                "archetype": "Temur Rhinos",
                "name": "Temur Rhinos",
                "source": "mtgo",
                "deck_text": "4 Crashing Footfalls\n",
            },
            {
                "number": "2",
                "archetype": "Broodscale",
                "name": "Broodscale",
                "source": "mtgo",
                "deck_text": "4 Basking Broodscale\n",
            },
            {
                "number": "3",
                "archetype": "Unknown",
                "name": "Unknown",
                "source": "mtgo",
                "deck_text": "4 Island\n",
            },
        ],
    )
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
    snapshot = json.loads(
        (tmp_path / "latest" / "archetypes" / "modern.json").read_text(encoding="utf-8")
    )
    by_name = {entry["name"]: entry for entry in snapshot["archetypes"]}
    assert by_name["Broodscale"] == {
        "name": "Broodscale",
        "href": "modern-broodscale",
        "source": "mtgo",
    }
    assert "source" not in by_name["Temur Rhinos"]
    assert "Unknown" not in by_name


def test_scrape_decks_skips_mtgo_union_archetypes(monkeypatch, tmp_path):
    _write_mtgo_decklists_fixture(
        tmp_path,
        [
            {
                "number": "2",
                "archetype": "Broodscale",
                "name": "Broodscale",
                "source": "mtgo",
                "deck_text": "4 Basking Broodscale\n",
            }
        ],
    )
    monkeypatch.setattr(
        "publisher.runner.fetch_archetypes",
        lambda *args, **kwargs: [{"name": "Temur Rhinos", "href": "modern-temur-rhinos"}],
    )

    class _GoldfishOnlyRepo(_FakeRepo):
        def get_decks_for_archetype(self, archetype, force_refresh=False, source_filter=None):
            assert archetype.get("source") != "mtgo"
            return super().get_decks_for_archetype(
                archetype, force_refresh=force_refresh, source_filter=source_filter
            )

    monkeypatch.setattr("publisher.runner.ScrapingMetagameRepository", _GoldfishOnlyRepo)

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-decks",
            "--format",
            "Modern",
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "latest" / "decks" / "modern" / "temur-rhinos.json").exists()
    assert not (tmp_path / "latest" / "decks" / "modern" / "broodscale.json").exists()


def test_scrape_radars_skips_format_card_pool_for_filtered_runs(tmp_path):
    deck_snapshot_path = tmp_path / "latest" / "decks" / "modern" / "temur-rhinos.json"
    deck_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    deck_snapshot_path.write_text(
        json.dumps(
            build_archetype_deck_snapshot(
                generated_at=TIMESTAMP,
                format_name="modern",
                source="both",
                archetype={"name": "Temur Rhinos", "href": "modern-temur-rhinos"},
                decks=[
                    {
                        "name": "Temur Rhinos",
                        "number": "123",
                        "date": "2026-03-22",
                        "player": "Alice",
                        "event": "Modern Challenge",
                        "source": "mtggoldfish",
                        "deck_text_path": "archive/deck-texts/modern/123.json",
                    }
                ],
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    blob_path = tmp_path / "archive" / "deck-texts" / "modern" / "123.json"
    blob_path.parent.mkdir(parents=True, exist_ok=True)
    blob_path.write_text(
        json.dumps(
            build_deck_text_blob(
                generated_at=TIMESTAMP,
                format_name="modern",
                source="mtggoldfish",
                deck_id="123",
                deck_name="Temur Rhinos",
                deck_text="4 Crashing Footfalls\n",
            ),
            indent=2,
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-radars",
            "--format",
            "Modern",
            "--archetype",
            "Temur Rhinos",
        ]
    )

    assert exit_code == 0
    assert not (tmp_path / "latest" / "card-pools" / "modern.json").exists()
    run_manifest = json.loads(
        (tmp_path / "latest" / "runs" / "scrape-radars-modern.json").read_text(encoding="utf-8")
    )
    assert run_manifest["results"][-1]["scope"] == "format-card-pool"
    assert run_manifest["results"][-1]["status"] == "skipped"


def test_scrape_mtgo_decklists_writes_archived_event_snapshots(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.fetch_mtgo_events_for_period",
        lambda **kwargs: [
            {
                "id": -12836735,
                "name": "Modern Challenge 64",
                "date": "2026-03-26T00:00:00.000Z",
                "format": "Modern",
                "kind": "Challenge",
            }
        ],
    )
    monkeypatch.setattr(
        "publisher.runner.fetch_event",
        lambda _event: {
            "event_id": "-12836735",
            "title": "Modern Challenge 64 2026-03-26",
            "publish_date": "2026-03-26",
            "event_type": "challenge",
            "decks": [
                {
                    "deck_id": "123",
                    "login_id": None,
                    "player": "Alice",
                    "wins": "5",
                    "losses": "2",
                    "mainboard": [
                        {"card_name": "Lightning Bolt", "qty": 4, "sideboard": "false"}
                    ],
                    "sideboard": [],
                }
            ],
        },
    )

    class _FakeDeckCache:
        def set(self, deck_id, deck_text, source):
            assert deck_id == "123"
            assert "Lightning Bolt" in deck_text
            assert source == "mtgo"
            return True

    class _FakeClassifier:
        def assign_archetypes(self, decks, fmt):
            for deck in decks:
                deck["archetype"] = "Mono Red Prowess"
                deck["archetype_score"] = 1.0
            assert fmt == "modern"

    monkeypatch.setattr("publisher.runner.get_deck_cache", lambda: _FakeDeckCache())
    monkeypatch.setattr("publisher.runner.ArchetypeClassifier", lambda: _FakeClassifier())
    monkeypatch.setattr("publisher.runner.save_mtgo_deck_metadata", lambda *args, **kwargs: None)

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-mtgo-decklists",
            "--format",
            "Modern",
            "--days",
            "7",
            "--event-delay-seconds",
            "0",
        ]
    )

    assert exit_code == 0
    latest_path = tmp_path / "latest" / "mtgo-decklists" / "modern.json"
    event_path = tmp_path / "archive" / "mtgo-decklists" / "modern" / "n12836735.json"
    run_path = tmp_path / "latest" / "runs" / "scrape-mtgo-decklists-modern.json"
    manifest_path = tmp_path / "latest" / "latest.json"

    assert latest_path.exists()
    assert event_path.exists()
    assert run_path.exists()

    latest_snapshot = json.loads(latest_path.read_text(encoding="utf-8"))
    event_snapshot = json.loads(event_path.read_text(encoding="utf-8"))
    latest_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert latest_snapshot["events"][0]["id"] == "n12836735"
    assert latest_snapshot["source"] == "videre-api"
    assert event_snapshot["decks"][0]["archetype"] == "Mono Red Prowess"
    assert event_snapshot["decks"][0]["archetype_href"] == "modern-mono-red-prowess"
    assert latest_snapshot["events"][0]["decks"][0]["archetype_href"] == "modern-mono-red-prowess"
    assert latest_manifest["latest"]["mtgo_decklists"][0]["path"] == "latest/mtgo-decklists/modern.json"


def test_scrape_decks_mtgo_only_archetype_writes_empty_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.fetch_archetypes",
        lambda *args, **kwargs: [{"name": "Raker Shops", "href": "vintage-raker-shops"}],
    )

    class _MtgoOnlyRepo(_FakeRepo):
        last_goldfish_rows_before_partition = 3

        def get_decks_for_archetype(self, archetype, force_refresh=False, source_filter=None):
            return []

    monkeypatch.setattr("publisher.runner.ScrapingMetagameRepository", _MtgoOnlyRepo)

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-decks",
            "--format",
            "Vintage",
            "--days",
            "7",
        ]
    )

    assert exit_code == 0
    snapshot = json.loads(
        (tmp_path / "latest" / "decks" / "vintage" / "raker-shops.json").read_text(encoding="utf-8")
    )
    run_manifest = json.loads(
        (tmp_path / "latest" / "runs" / "scrape-decks-vintage.json").read_text(encoding="utf-8")
    )

    assert snapshot["decks"] == []
    assert run_manifest["status"] == "success"
    skip = [r for r in run_manifest["results"] if r["scope"] == "archetype-decks"][0]
    assert skip["status"] == "skipped"
    assert "MTGO events" in skip["message"]


def test_scrape_mtgo_decklists_single_event_failure_is_skipped(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "publisher.runner.fetch_mtgo_events_for_period",
        lambda **kwargs: [
            {"id": 111, "name": "Modern Challenge 64", "date": "2026-03-26", "kind": "Challenge"},
            {"id": 222, "name": "Modern League", "date": "2026-03-26", "kind": "League"},
        ],
    )

    def _fetch_event(event):
        if event["id"] == 222:
            raise RuntimeError("HTTP 408 from https://api.videreproject.com/decks?event_id=222")
        return {
            "event_id": "111",
            "title": "Modern Challenge 64 2026-03-26",
            "publish_date": "2026-03-26",
            "event_type": "challenge",
            "decks": [
                {
                    "deck_id": "9",
                    "login_id": None,
                    "player": "Alice",
                    "wins": "5",
                    "losses": "2",
                    "mainboard": [{"card_name": "Lightning Bolt", "qty": 4, "sideboard": "false"}],
                    "sideboard": [],
                }
            ],
        }

    monkeypatch.setattr("publisher.runner.fetch_event", _fetch_event)

    class _FakeDeckCache:
        def set(self, deck_id, deck_text, source):
            return True

    class _FakeClassifier:
        def assign_archetypes(self, decks, fmt):
            for deck in decks:
                deck["archetype"] = "Burn"

    monkeypatch.setattr("publisher.runner.get_deck_cache", lambda: _FakeDeckCache())
    monkeypatch.setattr("publisher.runner.ArchetypeClassifier", lambda: _FakeClassifier())
    monkeypatch.setattr("publisher.runner.save_mtgo_deck_metadata", lambda *args, **kwargs: None)

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-mtgo-decklists",
            "--format",
            "Modern",
            "--days",
            "7",
            "--event-delay-seconds",
            "0",
        ]
    )

    assert exit_code == 0
    run_manifest = json.loads(
        (tmp_path / "latest" / "runs" / "scrape-mtgo-decklists-modern.json").read_text(
            encoding="utf-8"
        )
    )
    assert run_manifest["status"] == "success"
    event_results = [r for r in run_manifest["results"] if r["scope"] == "mtgo-event"]
    assert sorted(r["status"] for r in event_results) == ["skipped", "success"]

    snapshot = json.loads(
        (tmp_path / "latest" / "mtgo-decklists" / "modern.json").read_text(encoding="utf-8")
    )
    assert [e["id"] for e in snapshot["events"]] == ["111"]


def test_recent_league_refetches_despite_archive(monkeypatch, tmp_path):
    # TIMESTAMP is 2026-03-23T12:00:00Z; the league ran the day before.
    events = [
        {"id": -7, "name": "Modern League", "date": "2026-03-22", "kind": "League"},
        {"id": 8, "name": "Modern Challenge 64", "date": "2026-03-22", "kind": "Challenge"},
    ]
    monkeypatch.setattr("publisher.runner.fetch_mtgo_events_for_period", lambda **kwargs: events)

    for archive_id, title in (("n7", "Modern League 2026-03-22"), ("8", "Modern Challenge 64 2026-03-22")):
        path = tmp_path / "archive" / "mtgo-decklists" / "modern" / f"{archive_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "event_title": title,
                    "publish_date": "2026-03-22",
                    "event_type": "league",
                    "decks_total": 2,
                    "decks_cached": 2,
                    "decks": [],
                }
            ),
            encoding="utf-8",
        )

    fetched = []

    def _fetch_event(event):
        fetched.append(event["id"])
        return {
            "event_id": str(event["id"]),
            "title": "Modern League 2026-03-22",
            "publish_date": "2026-03-22",
            "event_type": "league",
            "decks": [
                {
                    "deck_id": "77",
                    "login_id": None,
                    "player": "Alice",
                    "wins": "5",
                    "losses": "0",
                    "mainboard": [{"card_name": "Lightning Bolt", "qty": 4, "sideboard": "false"}],
                    "sideboard": [],
                }
            ],
        }

    monkeypatch.setattr("publisher.runner.fetch_event", _fetch_event)

    class _FakeDeckCache:
        def set(self, deck_id, deck_text, source):
            return True

    class _FakeClassifier:
        def assign_archetypes(self, decks, fmt):
            for deck in decks:
                deck["archetype"] = "Burn"

    monkeypatch.setattr("publisher.runner.get_deck_cache", lambda: _FakeDeckCache())
    monkeypatch.setattr("publisher.runner.ArchetypeClassifier", lambda: _FakeClassifier())
    monkeypatch.setattr("publisher.runner.save_mtgo_deck_metadata", lambda *args, **kwargs: None)

    exit_code = main(
        [
            "--output-root",
            str(tmp_path),
            "--timestamp",
            TIMESTAMP,
            "scrape-mtgo-decklists",
            "--format",
            "Modern",
            "--days",
            "7",
            "--event-delay-seconds",
            "0",
        ]
    )

    assert exit_code == 0
    # Recent league re-fetched despite its archive; archived challenge untouched.
    assert fetched == [-7]
    archive = json.loads(
        (tmp_path / "archive" / "mtgo-decklists" / "modern" / "n7.json").read_text(encoding="utf-8")
    )
    assert archive["decks"][0]["number"] == "77"
