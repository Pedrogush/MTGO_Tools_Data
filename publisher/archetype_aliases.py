"""Curated aliases from MTGOFormatData (Videre) archetype names to MTGGoldfish names.

The automatic resolver tiers in ``publisher.runner._ArchetypeHrefResolver``
(exact slug, dash-insensitive slug, unique token subset) cannot bridge renames,
acronyms, or word-order differences, and they deliberately refuse ambiguous
token matches. This map covers the remaining pairs that are clearly the same
archetype under two labels, keyed by ``normalize_name`` slug of the Videre name
per format. Aliases take precedence over the automatic tiers, so they can also
override a wrong tier match (e.g. Vintage "PO" would otherwise token-match
"Lurrus PO" instead of "Paradoxical Outcome").

Only add pairs that are unambiguous. Names that could plausibly fold into more
than one MTGGoldfish archetype (e.g. Modern "Prowess", Legacy "Energy",
Standard "Reanimator") are intentionally left out — they publish under their
Videre name as MTGO-only union archetypes instead of being misfiled.

Curated 2026-07-25 against the live data-publish archetype lists; see
docs/archetype_taxonomy.md for the full comparison tables.
"""

from __future__ import annotations

ARCHETYPE_ALIASES: dict[str, dict[str, str]] = {
    "legacy": {
        "death-taxes": "Death and Taxes (60 Card)",
        "dimir-delver": "Dimir Tempo",
        "esper-delver": "Esper Tempo",
        "jund-reanimator": "Reanimator",
        "mono-blue-delver": "Mono-Blue Tempo",
        "post": "Blue Cloudpost",
        "tes": "The EPIC Storm",
        "white-beanstalk": "Beanstalk Control (Non-Yorion)",
    },
    "modern": {
        "5-color-creativity": "Indomitable Creativity",
        "azorius-blink": "Azorius GenericBlink",
        "esper-blink": "Esper GenericBlink",
        "goryo-reanimator": "Goryo's Vengeance",
        "jund-creativity": "Indomitable Creativity",
        "ramp-eldrazi": "Eldrazi Ramp",
    },
    "pauper": {
        "caw-gates": "Azorius Gates",
        "golgari-garden": "Golgari Gardens",
        "mono-blue-terror": "Blue Terror",
        "tireless-tribe": "Inside Out Combo",
        "walls-cascade": "Walls Combo",
    },
    "pioneer": {
        "mono-green-devotion": "Nykthos Ramp",
        "sultai-neoform-combo": "Atraxa Neoform",
    },
    "standard": {
        "izzet-elementals": "Izzet Spellementals",
    },
    "vintage": {
        "breach": "Underworld Breach",
        "po": "Paradoxical Outcome",
        "ub-lurrus-control": "Dimir Lurrus Control",
    },
}

__all__ = ["ARCHETYPE_ALIASES"]
