from datetime import UTC, datetime

from services.mtgo_background_service import fetch_mtgo_events_for_period


def test_fetch_mtgo_events_for_period_passes_window_to_videre(monkeypatch):
    monkeypatch.setattr("services.mtgo_background_service.MTGO_DECKLISTS_ENABLED", True)
    captured = {}

    def fake_fetch_events(format_name, *, min_date, max_date):
        captured.update(format_name=format_name, min_date=min_date, max_date=max_date)
        return [{"id": -123, "name": "Modern League", "date": "2026-03-26T00:00:00.000Z"}]

    monkeypatch.setattr("services.mtgo_background_service.fetch_events", fake_fetch_events)

    start = datetime(2026, 3, 25, tzinfo=UTC)
    end = datetime(2026, 3, 27, tzinfo=UTC)

    events = fetch_mtgo_events_for_period(start, end, mtg_format="modern")

    assert captured == {"format_name": "modern", "min_date": "2026-03-25", "max_date": "2026-03-27"}
    assert [event["id"] for event in events] == [-123]


def test_fetch_mtgo_events_for_period_respects_feature_flag(monkeypatch):
    monkeypatch.setattr("services.mtgo_background_service.MTGO_DECKLISTS_ENABLED", False)
    monkeypatch.setattr(
        "services.mtgo_background_service.fetch_events",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not fetch")),
    )

    start = datetime(2026, 3, 25, tzinfo=UTC)
    end = datetime(2026, 3, 27, tzinfo=UTC)

    assert fetch_mtgo_events_for_period(start, end, mtg_format="modern") == []
