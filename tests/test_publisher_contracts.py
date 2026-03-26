from publisher.contracts import (
    build_archetype_deck_snapshot,
    build_archetype_list_snapshot,
    build_archetype_radar_snapshot,
    build_deck_text_blob,
    build_latest_manifest,
    build_metagame_snapshot,
    build_run_manifest,
    validate_archetype_deck_snapshot,
    validate_archetype_list_snapshot,
    validate_archetype_radar_snapshot,
    validate_deck_text_blob,
    validate_latest_manifest,
    validate_metagame_snapshot,
    validate_run_manifest,
)

TIMESTAMP = "2026-03-23T12:00:00Z"


def test_contract_builders_validate_examples() -> None:
    archetypes = [{"name": "Temur Rhinos", "href": "modern-temur-rhinos"}]
    archetype_snapshot = build_archetype_list_snapshot(
        generated_at=TIMESTAMP,
        format_name="modern",
        source="mtggoldfish",
        archetypes=archetypes,
    )
    assert validate_archetype_list_snapshot(archetype_snapshot)["archetypes"] == archetypes

    deck_snapshot = build_archetype_deck_snapshot(
        generated_at=TIMESTAMP,
        format_name="modern",
        source="both",
        archetype=archetypes[0],
        decks=[{"number": "123", "source": "mtggoldfish", "date": "2026-03-22"}],
    )
    assert validate_archetype_deck_snapshot(deck_snapshot)["archetype"]["name"] == "Temur Rhinos"

    radar_snapshot = build_archetype_radar_snapshot(
        generated_at=TIMESTAMP,
        format_name="modern",
        archetype=archetypes[0],
        source="published-deck-texts",
        total_decks_analyzed=3,
        decks_failed=1,
        mainboard_cards=[
            {
                "card_name": "Lightning Bolt",
                "appearances": 3,
                "total_copies": 12,
                "max_copies": 4,
                "avg_copies": 4.0,
                "inclusion_rate": 100.0,
                "expected_copies": 4.0,
                "copy_distribution": {4: 3},
            }
        ],
        sideboard_cards=[],
    )
    assert validate_archetype_radar_snapshot(radar_snapshot)["total_decks_analyzed"] == 3

    metagame_snapshot = build_metagame_snapshot(
        generated_at=TIMESTAMP,
        format_name="modern",
        source="mtggoldfish",
        generated_for_day="2026-03-23",
        stats=[{"archetype": "Temur Rhinos", "deck_count": 4, "daily_counts": {"2026-03-22": 4}}],
    )
    assert validate_metagame_snapshot(metagame_snapshot)["stats"][0]["deck_count"] == 4

    deck_text_blob = build_deck_text_blob(
        generated_at=TIMESTAMP,
        format_name="modern",
        source="both",
        deck_id="123",
        deck_name="Temur Rhinos",
        deck_text="4 Ragavan, Nimble Pilferer",
    )
    assert validate_deck_text_blob(deck_text_blob)["deck_id"] == "123"

    run_manifest = build_run_manifest(
        generated_at=TIMESTAMP,
        command="scrape-decks",
        status="success",
        max_stale_hours=24,
        results=[{"scope": "archetype-decks", "status": "success", "format": "modern"}],
        summary={"success": 1},
    )
    assert validate_run_manifest(run_manifest)["command"] == "scrape-decks"


def test_latest_manifest_validates_with_all_categories() -> None:
    manifest = build_latest_manifest(generated_at=TIMESTAMP, retention_days=7)
    manifest["latest"]["archetype_lists"].append(
        {"format": "modern", "path": "latest/archetypes/modern.json", "updated_at": TIMESTAMP}
    )
    manifest["latest"]["archetype_decks"].append(
        {
            "format": "modern",
            "archetype": "temur-rhinos",
            "path": "latest/decks/modern/temur-rhinos.json",
            "updated_at": TIMESTAMP,
        }
    )
    manifest["latest"]["archetype_radars"].append(
        {
            "format": "modern",
            "archetype": "temur-rhinos",
            "path": "latest/radars/modern/temur-rhinos.json",
            "updated_at": TIMESTAMP,
        }
    )
    manifest["latest"]["metagame_daily"].append(
        {"format": "modern", "path": "latest/metagame/modern.json", "updated_at": TIMESTAMP}
    )
    manifest["latest"]["deck_text_blobs"].append(
        {
            "format": "modern",
            "deck_id": "123",
            "path": "archive/deck-texts/modern/123.json",
            "updated_at": TIMESTAMP,
        }
    )
    manifest["latest"]["runs"].append(
        {
            "format": "scrape-decks",
            "path": "latest/runs/scrape-decks.json",
            "updated_at": TIMESTAMP,
        }
    )

    assert validate_latest_manifest(manifest)["retention_days"] == 7
