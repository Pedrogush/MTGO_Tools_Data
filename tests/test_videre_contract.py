"""Pin the Videre API response shapes the publisher parses.

Fixtures under tests/fixtures/videre are trimmed real responses (Modern,
2026-11-08). ``openapi_subset.json`` is the matching slice of
https://api.videreproject.com/openapi.json; ``scripts/check_videre_contract.py``
runs the same ``check_openapi`` against the live spec.
"""

import copy
import json
from pathlib import Path

import pytest

import navigators.videre as videre
from navigators.videre_contract import check_envelope, check_openapi, check_rows
from publisher.runner import _mtgo_event_id

FIXTURES = Path(__file__).parent / "fixtures" / "videre"


def _fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("path", "fixture"),
    [("/events", "events.json"), ("/decks", "decks.json"), ("/standings", "standings.json")],
)
def test_fixture_responses_match_pinned_fields(path, fixture):
    assert check_envelope(path, _fixture(fixture)) == []


def test_fixture_decks_cover_object_card_entries_and_colour_code_archetypes():
    rows = _fixture("decks.json")["data"]
    assert all(isinstance(entry, dict) for row in rows for entry in row["mainboard"])
    assert any(row["archetype_id"] is None and row["archetype"] == "BR" for row in rows)


def test_parser_reads_fixture_responses(monkeypatch):
    responses = {
        "/events": _fixture("events.json"),
        "/decks": _fixture("decks.json"),
        "/standings": _fixture("standings.json"),
    }
    monkeypatch.setattr(videre, "_get", lambda path, params: responses[path])

    events = videre.fetch_events("Modern", min_date="2026-11-08", max_date="2026-11-08")
    challenge = next(e for e in events if e["kind"] == "Challenge")
    league = next(e for e in events if e["kind"] == "League")
    assert _mtgo_event_id(league).startswith("n")

    payload = videre.fetch_event_payload(challenge)
    assert payload["event_id"] == "12857704"
    assert payload["title"] == "Modern Challenge 32 2026-11-08"
    assert payload["publish_date"] == "2026-11-08"
    assert payload["event_type"] == "challenge"

    decks = {deck["player"]: deck for deck in payload["decks"]}
    blink = decks["_Arise"]
    assert blink["deck_id"] == "58711435"
    assert (blink["wins"], blink["losses"]) == ("4", "2")
    assert blink["archetype"] == "Azorius Blink"
    assert blink["archetype_id"] == 28548
    assert blink["mainboard"][0] == {"card_name": "Solitude", "qty": 4, "sideboard": "false"}
    assert all(card["sideboard"] == "true" for card in blink["sideboard"])

    colour_code = decks["DragonFodder"]
    assert colour_code["archetype"] == "BR"
    assert colour_code["archetype_id"] is None


def test_live_spec_snapshot_satisfies_contract():
    assert check_openapi(_fixture("openapi_subset.json")) == []


def test_check_openapi_reports_missing_and_retyped_fields():
    spec = copy.deepcopy(_fixture("openapi_subset.json"))
    deck_parts = spec["components"]["schemas"]["EventDeck"]["allOf"]
    for part in deck_parts:
        part.get("properties", {}).pop("archetype", None)
        board = part.get("properties", {}).get("mainboard")
        if board:
            board["items"]["properties"]["quantity"] = {"type": "string"}
    spec["components"]["schemas"]["Event"]["properties"]["id"] = {"type": "string"}
    spec["paths"]["/events"]["get"]["parameters"] = [
        param for param in spec["paths"]["/events"]["get"]["parameters"] if param["name"] != "min_date"
    ]
    del spec["paths"]["/standings"]

    problems = check_openapi(spec)

    assert "GET /decks row: field 'archetype' is missing" in problems
    assert any("mainboard[]: field 'quantity' is 'string'" in p for p in problems)
    assert any("GET /events row: field 'id' is 'string'" in p for p in problems)
    assert "GET /events: query parameter 'min_date' is missing" in problems
    assert "GET /standings is missing" in problems


def test_check_rows_flags_pre_october_card_literals_and_null_ids():
    row = dict(_fixture("decks.json")["data"][0])
    row["mainboard"] = ['(18115,"Birchlore Rangers",4)']
    row["id"] = None
    problems = check_rows("/decks", [row])
    assert any("mainboard[0]: expected an object" in p for p in problems)
    assert "/decks data[0]: field 'id' is null" in problems
