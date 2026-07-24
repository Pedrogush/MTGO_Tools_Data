from navigators.videre import (
    fetch_event_payload,
    normalize_card_name,
    parse_card_entry,
)


def test_parse_card_entry_unquoted():
    assert parse_card_entry("(129825,Forest,2)") == ("Forest", 2)


def test_parse_card_entry_quoted_with_comma():
    assert parse_card_entry('(87695,"Ajani, Nacatl Pariah",4)') == ("Ajani, Nacatl Pariah", 4)


def test_parse_card_entry_normalizes_split_cards():
    assert parse_card_entry('(12345,"Wear/Tear",2)') == ("Wear // Tear", 2)


def test_normalize_card_name_leaves_regular_names_alone():
    assert normalize_card_name("Lightning Bolt") == "Lightning Bolt"
    assert normalize_card_name("Fire // Ice") == "Fire // Ice"


def test_fetch_event_payload_builds_clean_decks(monkeypatch):
    monkeypatch.setattr(
        "navigators.videre.fetch_event_decks",
        lambda event_id: [
            {
                "id": 37217704,
                "event_id": -521715179,
                "player": "Based",
                "mainboard": ['(18115,"Guide of Souls",4)', "(129825,Plains,20)"],
                "sideboard": ['(12345,"Wear/Tear",2)'],
            }
        ],
    )
    monkeypatch.setattr(
        "navigators.videre.fetch_event_standings",
        lambda event_id: {"based": {"player": "Based", "record": "5-0-0", "rank": None}},
    )

    payload = fetch_event_payload(
        {"id": -521715179, "name": "Modern League", "date": "2026-07-23T00:00:00.000Z", "kind": "League"}
    )

    assert payload["event_id"] == "-521715179"
    assert payload["title"] == "Modern League 2026-07-23"
    assert payload["publish_date"] == "2026-07-23"
    assert payload["event_type"] == "league"
    deck = payload["decks"][0]
    assert deck["deck_id"] == "37217704"
    assert deck["player"] == "Based"
    assert (deck["wins"], deck["losses"]) == ("5", "0")
    assert {"card_name": "Guide of Souls", "qty": 4, "sideboard": "false"} in deck["mainboard"]
    assert deck["sideboard"] == [{"card_name": "Wear // Tear", "qty": 2, "sideboard": "true"}]


def test_fetch_event_payload_unknown_player_record(monkeypatch):
    monkeypatch.setattr(
        "navigators.videre.fetch_event_decks",
        lambda event_id: [{"id": 1, "player": "Ghost", "mainboard": [], "sideboard": []}],
    )
    monkeypatch.setattr("navigators.videre.fetch_event_standings", lambda event_id: {})

    payload = fetch_event_payload({"id": 1, "name": "Modern Challenge 64", "date": "2026-07-23", "kind": "Challenge"})

    deck = payload["decks"][0]
    assert (deck["wins"], deck["losses"]) == ("?", "?")
