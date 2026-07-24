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


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _no_sleep(monkeypatch):
    monkeypatch.setattr("navigators.videre.time.sleep", lambda _s: None)
    monkeypatch.setattr(
        "navigators.videre.MTGO_DECKLISTS_FETCH_RETRY_DELAYS_SECONDS", (0.01, 0.01)
    )


def test_get_treats_400_no_results_as_empty(monkeypatch):
    from navigators.videre import fetch_event_decks

    _no_sleep(monkeypatch)
    monkeypatch.setattr(
        "navigators.videre.requests.get",
        lambda *a, **k: _FakeResponse(400, {"object": "error", "message": "No results found."}),
    )

    assert fetch_event_decks(12848183) == []


def test_get_retries_on_408_then_succeeds(monkeypatch):
    from navigators.videre import fetch_event_decks

    _no_sleep(monkeypatch)
    responses = [
        _FakeResponse(408, {}),
        _FakeResponse(200, {"data": [{"id": 1}], "meta": {"has_more": False}}),
    ]
    monkeypatch.setattr("navigators.videre.requests.get", lambda *a, **k: responses.pop(0))

    assert fetch_event_decks(-521715179) == [{"id": 1}]


def test_get_raises_after_exhausted_retries(monkeypatch):
    import pytest

    from navigators.videre import fetch_event_decks

    _no_sleep(monkeypatch)
    monkeypatch.setattr("navigators.videre.requests.get", lambda *a, **k: _FakeResponse(503, {}))

    with pytest.raises(RuntimeError, match="HTTP 503"):
        fetch_event_decks(1)


def test_get_does_not_retry_client_errors(monkeypatch):
    import pytest

    from navigators.videre import fetch_event_decks

    _no_sleep(monkeypatch)
    calls = []

    def _fake_get(*a, **k):
        calls.append(1)
        return _FakeResponse(404, {"message": "nope"})

    monkeypatch.setattr("navigators.videre.requests.get", _fake_get)

    with pytest.raises(RuntimeError, match="HTTP 404"):
        fetch_event_decks(1)
    assert len(calls) == 1


def test_get_sends_identifying_user_agent(monkeypatch):
    from navigators.videre import fetch_event_decks

    seen = {}

    def _fake_get(url, params=None, timeout=None, headers=None):
        seen["headers"] = headers
        return _FakeResponse(200, {"data": [], "meta": {"has_more": False}})

    monkeypatch.setattr("navigators.videre.requests.get", _fake_get)

    fetch_event_decks(1)
    assert "MTGO_Tools_Data" in seen["headers"]["User-Agent"]
    assert "github.com/Pedrogush/MTGO_Tools_Data" in seen["headers"]["User-Agent"]


def test_league_payload_skips_standings_and_synthesizes_five_zero(monkeypatch):
    from navigators.videre import fetch_event_payload

    monkeypatch.setattr(
        "navigators.videre.fetch_event_decks",
        lambda event_id: [{"id": 1, "player": "Based", "mainboard": [], "sideboard": []}],
    )

    def _no_standings(event_id):
        raise AssertionError("standings must not be fetched for leagues")

    monkeypatch.setattr("navigators.videre.fetch_event_standings", _no_standings)

    payload = fetch_event_payload(
        {"id": -1, "name": "Modern League", "date": "2026-07-23", "kind": "League"}
    )

    deck = payload["decks"][0]
    assert (deck["wins"], deck["losses"]) == ("5", "0")
