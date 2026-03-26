from datetime import datetime, timezone

from services.mtgo_background_service import fetch_mtgo_events_for_period


def test_fetch_mtgo_events_for_period_matches_format_exactly(monkeypatch):
    monkeypatch.setattr("services.mtgo_background_service.MTGO_DECKLISTS_ENABLED", True)
    monkeypatch.setattr(
        "services.mtgo_background_service.fetch_decklist_index",
        lambda year, month: [
            {
                "title": "Modern League",
                "format": "Modern",
                "publish_date": "2026-03-26T12:00:00Z",
                "url": "https://www.mtgo.com/decklist/modern-league-1",
                "event_type": "league",
            },
            {
                "title": "Premodern League",
                "format": "Premodern",
                "publish_date": "2026-03-26T12:00:00Z",
                "url": "https://www.mtgo.com/decklist/premodern-league-1",
                "event_type": "league",
            },
        ],
    )

    start = datetime(2026, 3, 25, tzinfo=timezone.utc)
    end = datetime(2026, 3, 27, tzinfo=timezone.utc)

    events = fetch_mtgo_events_for_period(start, end, mtg_format="modern")

    assert [event["url"] for event in events] == ["https://www.mtgo.com/decklist/modern-league-1"]
