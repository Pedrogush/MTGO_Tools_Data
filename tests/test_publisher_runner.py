import json

from publisher.contracts import build_archetype_deck_snapshot, build_deck_text_blob
from publisher.runner import main

TIMESTAMP = "2026-03-23T12:00:00Z"
LATER_TIMESTAMP = "2026-03-23T18:00:00Z"


def _mtgo_deck(
    number,
    archetype="Temur Rhinos",
    date="2026-03-22",
    player="Alice",
    deck_text="4 Lightning Bolt\nsideboard\n1 Boil\n",
):
    return {
        "number": number,
        "date": date,
        "event": "Modern Challenge 64 2026-03-22",
        "result": "5-2",
        "player": player,
        "archetype": archetype,
        "name": archetype,
        "source": "mtgo",
        "format": "modern",
        "deck_text": deck_text,
    }


def _seed_mtgo_archive(tmp_path, decks, *, format_name="modern", event_id="12000001"):
    path = tmp_path / "archive" / "mtgo-decklists" / format_name / f"{event_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "kind": "mtgo_event_decklists",
                "generated_at": TIMESTAMP,
                "format": format_name,
                "event_id": event_id,
                "event_url": f"https://api.videreproject.com/decks?event_id={event_id}",
                "event_title": "Modern Challenge 64 2026-03-22",
                "publish_date": "2026-03-22",
                "event_type": "challenge",
                "decks_total": len(decks),
                "decks_cached": len(decks),
                "decks": decks,
            }
        ),
        encoding="utf-8",
    )


def test_scrape_archetypes_writes_run_manifest_and_posix_path(tmp_path):
    _seed_mtgo_archive(tmp_path, [_mtgo_deck("123")])

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
    snapshot = json.loads(latest_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_manifest = json.loads(run_path.read_text(encoding="utf-8"))
    assert snapshot["source"] == "videre-api"
    assert snapshot["archetypes"] == [{"name": "Temur Rhinos", "href": "temur-rhinos"}]
    assert manifest["latest"]["archetype_lists"][0]["path"] == "latest/archetypes/modern.json"
    assert run_manifest["summary"]["success"] == 1


def test_scrape_archetypes_uses_stale_fallback_when_latest_is_fresh(monkeypatch, tmp_path):
    _seed_mtgo_archive(tmp_path, [_mtgo_deck("123")])
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
        raise RuntimeError("archives unreadable")

    monkeypatch.setattr("publisher.mtgo_archive.MtgoArchiveRepository.get_archetypes", _boom)
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


def test_scrape_metagame_writes_daily_snapshot(tmp_path):
    _seed_mtgo_archive(
        tmp_path,
        [
            _mtgo_deck("123", date="2026-03-22"),
            _mtgo_deck("124", date="2026-03-22", player="Bob"),
            _mtgo_deck("125", date="2026-03-21", player="Carol"),
        ],
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
    assert snapshot["source"] == "videre-api"
    stats = snapshot["stats"][0]
    assert stats["archetype"] == "Temur Rhinos"
    assert stats["deck_count"] == 3
    assert len(stats["daily_counts"]) == 7
    assert stats["daily_counts"]["2026-03-22"] == 2
    assert stats["daily_counts"]["2026-03-21"] == 1
    assert stats["daily_counts"]["2026-03-23"] == 0


def test_scrape_decks_references_shared_deck_text_blob(tmp_path):
    _seed_mtgo_archive(tmp_path, [_mtgo_deck("123")])

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
    assert "deck_text" not in snapshot["decks"][0]


def test_scrape_deck_texts_deduplicates_by_deck_id(tmp_path):
    # The same deck appears in two event archives; only one blob is written.
    _seed_mtgo_archive(tmp_path, [_mtgo_deck("123")], event_id="12000001")
    _seed_mtgo_archive(tmp_path, [_mtgo_deck("123")], event_id="12000002")

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
    assert blob["deck_text"].startswith("4 Lightning Bolt")
    assert len(manifest["latest"]["deck_text_blobs"]) == 1
    assert manifest["latest"]["deck_text_blobs"][0]["path"] == "archive/deck-texts/modern/123.json"


def test_scrape_deck_texts_skips_download_delay_for_archive_source(monkeypatch, tmp_path):
    # Deck texts come from local archives, so the politeness delay is skipped.
    _seed_mtgo_archive(tmp_path, [_mtgo_deck("123"), _mtgo_deck("456", player="Bob")])

    sleeps: list[float] = []
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
    assert sleeps == []
    assert (tmp_path / "archive" / "deck-texts" / "modern" / "123.json").exists()
    assert (tmp_path / "archive" / "deck-texts" / "modern" / "456.json").exists()


def test_scrape_deck_texts_reuses_existing_published_blob(monkeypatch, tmp_path):
    _seed_mtgo_archive(tmp_path, [_mtgo_deck("123")])

    archive_path = tmp_path / "archive" / "deck-texts" / "modern" / "123.json"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "kind": "deck_text_blob",
                "generated_at": "2026-03-22T12:00:00Z",
                "format": "modern",
                "source": "mtgo",
                "deck_id": "123",
                "deck_name": "Temur Rhinos",
                "deck_text": "Deck 123",
            }
        ),
        encoding="utf-8",
    )

    def _boom(*args, **kwargs):
        raise AssertionError("download_deck_content should not be called for reused blobs")

    monkeypatch.setattr("publisher.mtgo_archive.MtgoArchiveRepository.download_deck_content", _boom)

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
    run_manifest = json.loads(
        (tmp_path / "latest" / "runs" / "scrape-deck-texts-modern.json").read_text(encoding="utf-8")
    )
    assert run_manifest["results"][-1]["status"] == "skipped"
    assert run_manifest["results"][-1]["message"] == "Reused existing published deck-text blob."


def test_scrape_deck_texts_skips_empty_recent_window_without_failing(tmp_path):
    # Deck is inside the repository's 7-day archive window but outside the
    # narrower --days request window.
    _seed_mtgo_archive(tmp_path, [_mtgo_deck("123", date="2026-03-18")])

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
            "3",
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
    assert run_manifest["results"][1]["message"] == "No decks found within the last 3 days."


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
    assert latest_manifest["latest"]["mtgo_decklists"][0]["path"] == "latest/mtgo-decklists/modern.json"


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
