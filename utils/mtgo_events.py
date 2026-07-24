"""Classify tournament names as MTGO events vs paper events.

MTGGoldfish lists both MTGO results and paper tournaments. MTGO event data
now comes from the Videre API, so MTGGoldfish deck rows for MTGO events must
be dropped to avoid double-counting the same deck from both sources.

mtgo.com event names are formulaic: they start with the format and embed the
event day as an ISO date ("Modern League 2026-07-24", "Standard Challenge 32
2026-07-20 (1)", "Modern Last Chance 2026-07-19"). Paper event names are
freeform and, in five months of published history, never match that shape —
including store events whose names contain words like "League", "Challenge",
or "RCQ" without a format prefix and ISO date.
"""

from __future__ import annotations

import re

MTGO_EVENT_NAME_PATTERN = re.compile(
    r"^(?:Standard|Modern|Pioneer|Legacy|Vintage|Pauper)\b.*\d{4}-\d{2}-\d{2}",
    re.IGNORECASE,
)


def is_mtgo_event_name(event_name: str | None) -> bool:
    return bool(MTGO_EVENT_NAME_PATTERN.search(event_name or ""))
