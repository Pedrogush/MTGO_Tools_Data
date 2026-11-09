import json

from publisher.contracts import (
    build_archetype_list_snapshot,
    build_deck_text_blob,
    build_mtgo_decklists_snapshot,
)
from publisher.runner import main

TIMESTAMP = "2026-03-23T12:00:00Z"
LATER_TIMESTAMP = "2026-03-23T18:00:00Z"


def _deck_row(number, archetype, *, date="2026-03-22", archetype_id=1, fmt="modern", text=None):
    slug = (archetype or "unknown").lower().replace(" ", "-")
    return {
        "number": number,
        "date": date,
        "event": f"Modern Challenge 32 {date}",
        "result": "5-2",
        "player": f"player-{number}",
        "archetype": archetype or "Unknown",
        "archetype_href": f"{fmt}-{slug}",
        "archetype_id": archetype_id,
        "name": archetype or "Unknown",
        "source": "mtgo",
        "format": fmt,
        "deck_text": text or f"4 Lightning Bolt\n4 Card {number}\nsideboard\n2 Smash to Smithereens",
    }


def _seed_mtgo_snapshot(tmp_path, decks, *, fmt="modern", generated_at=TIMESTAMP):
    snapshot = build_mtgo_decklists_snapshot(
        generated_at=generated_at,
        format_name=fmt,
        source="videre-api",
        days=7,
        events=[
            {
                "id": "1",
                "url": "https://api.videreproject.com/decks?event_id=1",
                "title": "Modern Challenge 32",
                "publish_date": "2026-03-22",
                "event_type": "challenge",
                "decks_total": len(decks),
                "decks_cached": len(decks),
                "path": f"archive/mtgo-decklists/{fmt}/1.json",
                "decks": decks,
            }
        ],
    )
    path = tmp_path / "latest" / "mtgo-decklists" / f"{fmt}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    return path


def _run(tmp_path, *args, timestamp=TIMESTAMP):
    return main(["--output-root", str(tmp_path), "--timestamp", timestamp, *args])


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_scrape_archetypes_derives_list_from_mtgo_snapshot(tmp_path):
    _seed_mtgo_snapshot(
        tmp_path,
        [
            _deck_row("1", "Boros Energy"),
            _deck_row("2", "Boros Energy"),
            # Videre's fallback for decks it cannot place: a colour code with
            # a null archetype_id. Kept as its own archetype.
            _deck_row("3", "BR", archetype_id=None),
            # No archetype at all: never listed.
            _deck_row("4", None, archetype_id=None),
        ],
    )

    assert _run(tmp_path, "scrape-archetypes", "--format", "Modern") == 0

    snapshot = _load(tmp_path / "latest" / "archetypes" / "modern.json")
    assert snapshot["source"] == "videre-api"
    assert snapshot["archetypes"] == [
        {"name": "Boros Energy", "href": "modern-boros-energy", "source": "mtgo"},
        {"name": "BR", "href": "modern-br", "source": "mtgo"},
    ]
    run_manifest = _load(tmp_path / "latest" / "runs" / "scrape-archetypes-modern.json")
    assert run_manifest["status"] == "success"
    assert run_manifest["results"][0]["path"] == "latest/archetypes/modern.json"


def test_scrape_archetypes_uses_stale_fallback_without_mtgo_snapshot(tmp_path):
    latest_path = tmp_path / "latest" / "archetypes" / "modern.json"
    latest_path.parent.mkdir(parents=True)
    latest_path.write_text(
        json.dumps(
            build_archetype_list_snapshot(
                generated_at=TIMESTAMP,
                format_name="modern",
                source="videre-api",
                archetypes=[{"name": "Burn", "href": "modern-burn", "source": "mtgo"}],
            )
        ),
        encoding="utf-8",
    )

    exit_code = _run(tmp_path, "scrape-archetypes", "--format", "Modern", timestamp=LATER_TIMESTAMP)

    assert exit_code == 0
    run_manifest = _load(tmp_path / "latest" / "runs" / "scrape-archetypes-modern.json")
    assert run_manifest["results"][0]["status"] == "stale-fallback"
    assert "scrape-mtgo-decklists" in run_manifest["results"][0]["message"]


def test_scrape_archetypes_hard_fails_without_any_input(tmp_path):
    assert _run(tmp_path, "scrape-archetypes", "--format", "Modern") == 1


def test_scrape_metagame_counts_decks_per_day(tmp_path):
    _seed_mtgo_snapshot(
        tmp_path,
        [
            _deck_row("1", "Burn", date="2026-03-22"),
            _deck_row("2", "Burn", date="2026-03-21"),
            _deck_row("3", "Burn", date="2026-03-21"),
            _deck_row("4", "Amulet Titan", date="2026-03-20"),
            _deck_row("5", None, archetype_id=None),
        ],
    )

    assert _run(tmp_path, "scrape-metagame", "--format", "Modern", "--day", "2026-03-23") == 0

    snapshot = _load(tmp_path / "latest" / "metagame" / "modern.json")
    daily = _load(tmp_path / "daily" / "2026-03-23" / "metagame" / "modern.json")
    assert snapshot == daily
    assert snapshot["source"] == "videre-api"
    assert [row["archetype"] for row in snapshot["stats"]] == ["Amulet Titan", "Burn"]
    burn = snapshot["stats"][1]
    assert burn["deck_count"] == 3
    assert burn["daily_counts"]["2026-03-21"] == 2
    assert burn["daily_counts"]["2026-03-22"] == 1
    assert burn["daily_counts"]["2026-03-23"] == 0
    assert len(burn["daily_counts"]) == 7


def test_scrape_deck_texts_publishes_snapshots_and_blobs_from_mtgo_rows(tmp_path):
    _seed_mtgo_snapshot(
        tmp_path,
        [
            _deck_row("10", "Burn", date="2026-03-22"),
            _deck_row("11", "Burn", date="2026-03-21"),
            _deck_row("12", "BR", archetype_id=None),
            _deck_row("13", None, archetype_id=None),
        ],
    )

    assert _run(tmp_path, "scrape-deck-texts", "--format", "Modern", "--days", "7") == 0

    burn = _load(tmp_path / "latest" / "decks" / "modern" / "burn.json")
    assert burn["source"] == "mtgo"
    assert burn["archetype"] == {"name": "Burn", "href": "modern-burn", "source": "mtgo"}
    assert [deck["number"] for deck in burn["decks"]] == ["10", "11"]
    first = burn["decks"][0]
    # The fields MTGO_Tools v1.3.0 reads from a deck row, with source "mtgo".
    for field in ("date", "number", "player", "event", "result", "name", "source"):
        assert field in first
    assert first["source"] == "mtgo"
    assert first["deck_text_path"] == "archive/deck-texts/modern/10.json"
    assert "deck_text" not in first

    assert (tmp_path / "latest" / "decks" / "modern" / "br.json").exists()
    assert not (tmp_path / "latest" / "decks" / "modern" / "unknown.json").exists()

    blob = _load(tmp_path / "archive" / "deck-texts" / "modern" / "10.json")
    assert blob["source"] == "mtgo"
    assert blob["deck_id"] == "10"
    assert blob["deck_name"] == "Burn"
    assert "Lightning Bolt" in blob["deck_text"]
    # Unclassified decks have no archetype snapshot, so no blob either.
    assert not (tmp_path / "archive" / "deck-texts" / "modern" / "13.json").exists()


def test_scrape_deck_texts_reuses_existing_published_blob(tmp_path):
    _seed_mtgo_snapshot(tmp_path, [_deck_row("10", "Burn")])
    blob_path = tmp_path / "archive" / "deck-texts" / "modern" / "10.json"
    blob_path.parent.mkdir(parents=True)
    blob_path.write_text(
        json.dumps(
            build_deck_text_blob(
                generated_at=TIMESTAMP,
                format_name="modern",
                deck_id="10",
                source="mtgo",
                deck_name="Burn",
                deck_text="4 Already Published",
            )
        ),
        encoding="utf-8",
    )

    assert _run(tmp_path, "scrape-deck-texts", "--format", "Modern", "--days", "7") == 0

    assert _load(blob_path)["deck_text"] == "4 Already Published"
    run_manifest = _load(tmp_path / "latest" / "runs" / "scrape-deck-texts-modern.json")
    blob_results = [r for r in run_manifest["results"] if r["scope"] == "deck-text"]
    assert blob_results[0]["message"] == "Reused existing published deck-text blob."


def test_scrape_decks_windows_out_rows_older_than_retention(tmp_path):
    _seed_mtgo_snapshot(
        tmp_path,
        [
            _deck_row("1", "Burn", date="2026-03-22"),
            # Stale-fallback snapshots can hold events past the window.
            _deck_row("2", "Burn", date="2026-03-01"),
            _deck_row("3", "Living End", date="2026-03-01"),
        ],
    )

    assert _run(tmp_path, "scrape-decks", "--format", "Modern", "--days", "7") == 0

    archetypes = _load(tmp_path / "latest" / "archetypes" / "modern.json")["archetypes"]
    assert [entry["name"] for entry in archetypes] == ["Burn"]
    burn = _load(tmp_path / "latest" / "decks" / "modern" / "burn.json")
    assert [deck["number"] for deck in burn["decks"]] == ["1"]


def test_archetype_list_and_deck_snapshots_share_the_window(tmp_path):
    # TIMESTAMP is 2026-03-23T12:00Z; 2026-03-16 is the window's first day.
    _seed_mtgo_snapshot(
        tmp_path,
        [_deck_row("1", "Dredge", date="2026-03-16"), _deck_row("2", "Burn", date="2026-03-15")],
    )

    assert _run(tmp_path, "scrape-deck-texts", "--format", "Modern", "--days", "7") == 0

    archetypes = _load(tmp_path / "latest" / "archetypes" / "modern.json")["archetypes"]
    assert [entry["name"] for entry in archetypes] == ["Dredge"]
    dredge = _load(tmp_path / "latest" / "decks" / "modern" / "dredge.json")
    assert [deck["number"] for deck in dredge["decks"]] == ["1"]


def test_scrape_radars_builds_radars_and_card_pool_from_mtgo_rows(tmp_path):
    _seed_mtgo_snapshot(
        tmp_path,
        [
            _deck_row("1", "Burn", text="4 Lightning Bolt\n4 Goblin Guide\nsideboard\n2 Path to Exile"),
            _deck_row("2", "Burn", text="4 Lightning Bolt\n3 Goblin Guide\nsideboard\n1 Path to Exile"),
            _deck_row("3", "BR", archetype_id=None, text="4 Thoughtseize\nsideboard\n1 Duress"),
            _deck_row("4", None, archetype_id=None, text="4 Ornithopter\nsideboard\n"),
        ],
    )

    assert _run(tmp_path, "scrape-radars", "--format", "Modern") == 0

    radar = _load(tmp_path / "latest" / "radars" / "modern" / "burn.json")
    assert radar["archetype"] == {"name": "Burn", "href": "modern-burn", "source": "mtgo"}
    assert radar["source"] == "published-deck-texts"
    assert radar["total_decks_analyzed"] == 2
    bolt = next(c for c in radar["mainboard_cards"] if c["card_name"] == "Lightning Bolt")
    assert bolt["appearances"] == 2
    assert {c["card_name"] for c in radar["sideboard_cards"]} == {"Path to Exile"}
    assert (tmp_path / "latest" / "radars" / "modern" / "br.json").exists()
    assert not (tmp_path / "latest" / "radars" / "modern" / "unknown.json").exists()

    card_pool = _load(tmp_path / "latest" / "card-pools" / "modern.json")
    assert card_pool["total_decks_analyzed"] == 4
    assert "Ornithopter" in card_pool["cards"]


def test_scrape_radars_skips_format_card_pool_for_filtered_runs(tmp_path):
    _seed_mtgo_snapshot(tmp_path, [_deck_row("1", "Burn"), _deck_row("2", "Living End")])

    assert _run(tmp_path, "scrape-radars", "--format", "Modern", "--archetype", "Burn") == 0

    assert (tmp_path / "latest" / "radars" / "modern" / "burn.json").exists()
    assert not (tmp_path / "latest" / "radars" / "modern" / "living-end.json").exists()
    assert not (tmp_path / "latest" / "card-pools" / "modern.json").exists()


def test_scrape_radars_hard_fails_without_mtgo_snapshot(tmp_path):
    assert _run(tmp_path, "scrape-radars", "--format", "Modern") == 1


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
                    "archetype": "Mono Red Prowess",
                    "archetype_id": 4242,
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

    monkeypatch.setattr("publisher.runner.get_deck_cache", lambda: _FakeDeckCache())
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
    assert latest_snapshot["events"][0]["decks"][0]["source"] == "mtgo"
    assert event_snapshot["archetype_taxonomy"] == "videre"
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
                    "archetype": "Burn",
                    "archetype_id": 1,
                    "mainboard": [{"card_name": "Lightning Bolt", "qty": 4, "sideboard": "false"}],
                    "sideboard": [],
                }
            ],
        }

    monkeypatch.setattr("publisher.runner.fetch_event", _fetch_event)

    class _FakeDeckCache:
        def set(self, deck_id, deck_text, source):
            return True

    monkeypatch.setattr("publisher.runner.get_deck_cache", lambda: _FakeDeckCache())
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
                    "archetype_taxonomy": "videre",
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
                    "archetype": "Burn",
                    "archetype_id": 1,
                    "mainboard": [{"card_name": "Lightning Bolt", "qty": 4, "sideboard": "false"}],
                    "sideboard": [],
                }
            ],
        }

    monkeypatch.setattr("publisher.runner.fetch_event", _fetch_event)

    class _FakeDeckCache:
        def set(self, deck_id, deck_text, source):
            return True

    monkeypatch.setattr("publisher.runner.get_deck_cache", lambda: _FakeDeckCache())
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


def test_remove_legacy_event_archives_drops_slug_named_copies(tmp_path):
    """Re-archiving an event retires the pre-rename ``<slug><id>.json`` copy."""
    from publisher.runner import _remove_legacy_event_archives

    directory = tmp_path / "archive" / "mtgo-decklists" / "vintage"
    directory.mkdir(parents=True)
    canonical = directory / "12848175.json"
    legacy = directory / "vintage-challenge-32-2026-07-2312848175.json"
    unrelated = directory / "12847688.json"
    for path in (canonical, legacy, unrelated):
        path.write_text("{}", encoding="utf-8")

    _remove_legacy_event_archives(tmp_path, "vintage", "12848175")

    assert canonical.exists()
    assert unrelated.exists()
    assert not legacy.exists()


def test_remove_legacy_event_archives_is_a_noop_without_legacy_copies(tmp_path):
    from publisher.runner import _remove_legacy_event_archives

    directory = tmp_path / "archive" / "mtgo-decklists" / "vintage"
    directory.mkdir(parents=True)
    canonical = directory / "12848175.json"
    canonical.write_text("{}", encoding="utf-8")

    _remove_legacy_event_archives(tmp_path, "vintage", "12848175")

    assert canonical.exists()


def _clean_deck(deck_id, archetype, archetype_id=1):
    return {
        "deck_id": deck_id,
        "login_id": None,
        "player": f"player-{deck_id}",
        "wins": "5",
        "losses": "0",
        "archetype": archetype,
        "archetype_id": archetype_id,
        "mainboard": [{"card_name": "Lightning Bolt", "qty": 4, "sideboard": "false"}],
        "sideboard": [],
    }


class _NullDeckCache:
    def set(self, deck_id, deck_text, source):
        return True


def test_scrape_mtgo_decklists_refetches_archives_with_pre_videre_names(monkeypatch, tmp_path):
    """Archives whose names were rewritten onto MTGGoldfish's taxonomy are re-fetched once."""
    events = [{"id": 8, "name": "Modern Challenge 32", "date": "2026-03-20", "kind": "Challenge"}]
    monkeypatch.setattr("publisher.runner.fetch_mtgo_events_for_period", lambda **kwargs: events)
    archive = tmp_path / "archive" / "mtgo-decklists" / "modern" / "8.json"
    archive.parent.mkdir(parents=True)
    archive.write_text(
        json.dumps(
            {
                "event_title": "Modern Challenge 32 2026-03-20",
                "publish_date": "2026-03-20",
                "event_type": "challenge",
                "decks": [_deck_row("80", "Counter Vine", date="2026-03-20")],
            }
        ),
        encoding="utf-8",
    )
    fetched = []

    def _fetch_event(event):
        fetched.append(event["id"])
        return {
            "event_id": "8",
            "title": "Modern Challenge 32 2026-03-20",
            "publish_date": "2026-03-20",
            "event_type": "challenge",
            "decks": [_clean_deck("80", "Countervine")],
        }

    monkeypatch.setattr("publisher.runner.fetch_event", _fetch_event)
    monkeypatch.setattr("publisher.runner.get_deck_cache", lambda: _NullDeckCache())
    monkeypatch.setattr("publisher.runner.save_mtgo_deck_metadata", lambda *args, **kwargs: None)

    args = ["scrape-mtgo-decklists", "--format", "Modern", "--event-delay-seconds", "0"]
    assert _run(tmp_path, *args) == 0
    assert fetched == [8]
    rewritten = _load(archive)
    assert rewritten["archetype_taxonomy"] == "videre"
    assert rewritten["decks"][0]["archetype"] == "Countervine"

    # Second run reuses the now-tagged archive.
    assert _run(tmp_path, *args, timestamp=LATER_TIMESTAMP) == 0
    assert fetched == [8]


def test_scrape_mtgo_decklists_unifies_spellings_and_keeps_colour_codes(monkeypatch, tmp_path):
    events = [
        {"id": 1, "name": "Modern Challenge 32", "date": "2026-03-22", "kind": "Challenge"},
        {"id": 2, "name": "Modern Challenge 32", "date": "2026-03-21", "kind": "Challenge"},
    ]
    monkeypatch.setattr("publisher.runner.fetch_mtgo_events_for_period", lambda **kwargs: events)
    decks_by_event = {
        1: [_clean_deck("1", "Death & Taxes"), _clean_deck("2", "Death & Taxes")],
        2: [
            _clean_deck("3", "Death & taxes"),
            _clean_deck("4", "BR", archetype_id=None),
            _clean_deck("5", None, archetype_id=None),
        ],
    }
    monkeypatch.setattr(
        "publisher.runner.fetch_event",
        lambda event: {
            "event_id": str(event["id"]),
            "title": f"Modern Challenge 32 {event['date']}",
            "publish_date": event["date"],
            "event_type": "challenge",
            "decks": decks_by_event[event["id"]],
        },
    )
    monkeypatch.setattr("publisher.runner.get_deck_cache", lambda: _NullDeckCache())
    monkeypatch.setattr("publisher.runner.save_mtgo_deck_metadata", lambda *args, **kwargs: None)

    assert _run(tmp_path, "scrape-mtgo-decklists", "--format", "Modern", "--event-delay-seconds", "0") == 0

    snapshot = _load(tmp_path / "latest" / "mtgo-decklists" / "modern.json")
    rows = {deck["number"]: deck for event in snapshot["events"] for deck in event["decks"]}
    assert {rows[n]["archetype"] for n in ("1", "2", "3")} == {"Death & Taxes"}
    assert rows["3"]["archetype_href"] == "modern-death-taxes"
    assert rows["4"]["archetype"] == "BR"
    assert rows["4"]["archetype_href"] == "modern-br"
    assert rows["4"]["archetype_id"] is None
    assert rows["5"]["archetype"] == "Unknown"
    assert all(row["source"] == "mtgo" for row in rows.values())
