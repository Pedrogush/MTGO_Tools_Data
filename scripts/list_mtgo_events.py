"""List recent MTGO events from the Videre API."""

import sys
from datetime import UTC, datetime, timedelta

from navigators.videre import fetch_events

DEFAULT_DAYS = 7


def list_events(format_filter: str = None, days: int = DEFAULT_DAYS):
    """
    List recent MTGO events.

    Args:
        format_filter: Optional format filter (e.g., 'modern', 'legacy')
        days: How many days back to list (default: 7)
    """
    now = datetime.now(UTC)
    start = now - timedelta(days=days)
    format_name = format_filter or "Modern"

    print(f"\nFetching {format_name.title()} events from {start.date()} to {now.date()}...")
    events = fetch_events(
        format_name, min_date=start.date().isoformat(), max_date=now.date().isoformat()
    )

    if not events:
        print("No events found.")
        return

    print(f"\nFound {len(events)} events:\n")
    for event in events:
        name = event.get("name", "N/A")
        kind = event.get("kind", "other")
        date = str(event.get("date", "N/A"))[:10]
        players = event.get("players", "?")

        print(f"[{date}] {name:40s} ({kind:12s}) - {players} players (id {event.get('id')})")


if __name__ == "__main__":
    format_filter = sys.argv[1] if len(sys.argv) > 1 else None

    if format_filter and format_filter.lower() in ["-h", "--help", "help"]:
        print("\nUsage: python list_mtgo_events.py [format] [days]")
        print("\nExamples:")
        print("  python list_mtgo_events.py           # List Modern events, last 7 days")
        print("  python list_mtgo_events.py legacy    # List Legacy events")
        print("  python list_mtgo_events.py pauper 3  # List Pauper events, last 3 days")
        print()
    else:
        days = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DAYS
        list_events(format_filter=format_filter, days=days)
