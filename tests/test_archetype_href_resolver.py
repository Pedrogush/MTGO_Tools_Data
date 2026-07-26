"""Tests for the publisher-side archetype href resolver."""

from publisher.runner import _ArchetypeHrefResolver

ARCHETYPES = [
    {"name": "Counter Vine", "href": "vintage-counter-vine"},
    {"name": "Dimir Psychic Frog", "href": "vintage-dimir-psychic-frog"},
    {"name": "Mono White Initiative", "href": "vintage-mono-white-initiative"},
    {"name": "Abzan Initiative", "href": "vintage-abzan-initiative"},
]


def _resolver():
    return _ArchetypeHrefResolver(ARCHETYPES, "vintage")


def test_exact_match():
    name, href = _resolver().canonicalize("Counter Vine")
    assert (name, href) == ("Counter Vine", "vintage-counter-vine")


def test_case_and_spacing_insensitive():
    name, href = _resolver().canonicalize("  counter   vine ")
    assert (name, href) == ("Counter Vine", "vintage-counter-vine")


def test_compact_match_bridges_word_splits():
    name, href = _resolver().canonicalize("Countervine")
    assert (name, href) == ("Counter Vine", "vintage-counter-vine")


def test_unique_token_subset_match():
    name, href = _resolver().canonicalize("Dimir Frog")
    assert (name, href) == ("Dimir Psychic Frog", "vintage-dimir-psychic-frog")


def test_ambiguous_token_subset_is_not_matched():
    resolver = _resolver()
    assert resolver.resolve("Initiative") is None
    name, href = resolver.canonicalize("Initiative")
    assert (name, href) == ("Initiative", "vintage-initiative")


def test_unmatched_name_gets_synthesized_href():
    name, href = _resolver().canonicalize("Broodscale")
    assert (name, href) == ("Broodscale", "vintage-broodscale")


def test_empty_name_falls_back_to_unknown():
    name, href = _resolver().canonicalize("")
    assert (name, href) == ("Unknown", "vintage-unknown")


def test_alias_overrides_wrong_token_match():
    # Without the alias, "PO" would token-match "Lurrus PO" instead of
    # "Paradoxical Outcome".
    resolver = _ArchetypeHrefResolver(
        [
            {"name": "Lurrus PO", "href": "vintage-lurrus-po"},
            {"name": "Paradoxical Outcome", "href": "vintage-paradoxical-outcome"},
        ],
        "vintage",
    )
    name, href = resolver.canonicalize("PO")
    assert (name, href) == ("Paradoxical Outcome", "vintage-paradoxical-outcome")


def test_alias_bridges_rename():
    resolver = _ArchetypeHrefResolver(
        [{"name": "Goryo's Vengeance", "href": "modern-goryo-s-vengeance"}],
        "modern",
    )
    name, href = resolver.canonicalize("Goryo Reanimator")
    assert (name, href) == ("Goryo's Vengeance", "modern-goryo-s-vengeance")


def test_alias_falls_through_when_target_missing():
    resolver = _ArchetypeHrefResolver(
        [{"name": "Counter Vine", "href": "vintage-counter-vine"}],
        "vintage",
    )
    name, href = resolver.canonicalize("Breach")
    assert (name, href) == ("Breach", "vintage-breach")
