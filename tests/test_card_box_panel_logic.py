"""Tests for wx-independent methods of CardBoxPanel.

These tests cover pure-Python logic that does not require a wx display or
event loop. wx is stubbed out via sys.modules so the tests run in headless
CI environments without wxPython installed.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub wx BEFORE importing any wx-dependent module.
# card_box_panel.py is loaded directly (bypassing widgets/panels/__init__.py)
# to avoid pulling in unrelated panel modules that have additional
# transitive dependencies (bs4, services, etc.).
# ---------------------------------------------------------------------------
if "wx" not in sys.modules:
    _wx_stub = MagicMock()
    # wx.Panel must be a real Python class so CardBoxPanel can inherit from it.
    _wx_stub.Panel = type("_WxPanel", (object,), {})
    sys.modules["wx"] = _wx_stub


def _load_card_box_panel_module():
    """Load widgets/panels/card_box_panel.py directly, bypassing the package __init__."""
    import pathlib

    src = pathlib.Path(__file__).parent.parent / "widgets" / "panels" / "card_box_panel.py"
    spec = importlib.util.spec_from_file_location("widgets.panels.card_box_panel", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["widgets.panels.card_box_panel"] = mod
    spec.loader.exec_module(mod)
    return mod


_cbp_mod = _load_card_box_panel_module()
CardBoxPanel = _cbp_mod.CardBoxPanel


# ---------------------------------------------------------------------------
# _build_image_name_candidates
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "card, meta, expected",
    [
        ({"name": "Island"}, {}, ["Island"]),
        ({"name": "A // B"}, {}, ["A // B"]),
        ({"name": "A"}, {"aliases": ["Alias1"]}, ["A", "Alias1"]),
        ({"name": "A"}, {"aliases": ["A // B", "Other"]}, ["A", "A // B", "Other"]),
        ({"name": "A"}, {"aliases": "bad"}, ["A"]),
        ({"name": ""}, {}, []),
    ],
    ids=[
        "simple-card",
        "dfc-combined-name",
        "non-dfc-alias",
        "dfc-alias-promoted",
        "non-list-aliases",
        "empty-name",
    ],
)
def test_build_image_name_candidates(
    card: dict[str, Any], meta: dict[str, Any], expected: list[str]
) -> None:
    """_build_image_name_candidates must return the correct candidate list for each input."""
    result = CardBoxPanel._build_image_name_candidates(None, card, meta)
    assert result == expected


# ---------------------------------------------------------------------------
# preload_image
# ---------------------------------------------------------------------------
def test_preload_image_is_no_op() -> None:
    """preload_image() is now a no-op; it must not crash or call _refresh_card_bitmap."""
    call_count = 0

    def fake_refresh() -> None:
        nonlocal call_count
        call_count += 1

    stub = types.SimpleNamespace(_image_attempted=False, _refresh_card_bitmap=fake_refresh)

    CardBoxPanel.preload_image(stub)
    CardBoxPanel.preload_image(stub)

    assert call_count == 0


def test_preload_image_does_not_raise_regardless_of_state() -> None:
    """preload_image() must be safe to call whether or not _image_attempted is set."""
    for attempted in (True, False):
        stub = types.SimpleNamespace(_image_attempted=attempted)
        CardBoxPanel.preload_image(stub)  # must not raise
