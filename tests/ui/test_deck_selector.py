import pytest
import wx

from tests.ui.conftest import prepare_card_manager, pump_ui_events


@pytest.mark.usefixtures("wx_app")
def test_deck_selector_loads_archetypes_and_mainboard_stats(
    deck_selector_factory,
):
    frame = deck_selector_factory()
    try:
        frame.fetch_archetypes()
        pump_ui_events(wx.GetApp())
        assert frame.research_panel.archetype_list.GetCount() == 2

        frame.research_panel.archetype_list.SetSelection(0)
        frame.on_archetype_selected()
        pump_ui_events(wx.GetApp())

        assert frame.deck_list.GetCount() == 1
        frame.deck_list.SetSelection(0)
        frame.on_deck_selected(None)
        pump_ui_events(wx.GetApp())

        assert "8 card" in frame.main_table.count_label.GetLabel()
        assert "Mainboard: 8 cards" in frame.stats_summary.GetLabel()
        assert frame.deck_action_buttons.copy_button.IsEnabled()
    finally:
        frame.Destroy()


@pytest.mark.usefixtures("wx_app")
def test_builder_search_populates_results(
    deck_selector_factory,
):
    frame = deck_selector_factory()
    try:
        frame.card_data_dialogs_disabled = True
        prepare_card_manager(frame)
        frame._show_left_panel("builder", force=True)
        name_ctrl = frame.builder_panel.inputs["name"]
        name_ctrl.ChangeValue("Mountain")
        frame._on_builder_search()
        pump_ui_events(wx.GetApp())

        assert frame.builder_panel.results_ctrl is not None
        assert frame.builder_panel.results_ctrl.GetItemCount() >= 1
        assert "Mountain" in frame.builder_panel.results_ctrl.GetItemText(0)
    finally:
        frame.Destroy()


@pytest.mark.usefixtures("wx_app")
def test_notes_replaced_on_deck_switch(
    deck_selector_factory,
):
    """Notes for deck A must be cleared/replaced when switching to deck B."""
    frame = deck_selector_factory()
    try:
        # Load deck A with notes
        frame.deck_repo.set_current_deck({"href": "deck-a", "name": "Deck A"})
        frame.controller.deck_notes_store["deck-a"] = [
            {"id": "a1", "title": "Note A", "body": "Deck A note", "type": "General"}
        ]
        frame.deck_notes_panel.load_notes_for_current()
        assert frame.deck_notes_panel.get_notes()[0]["body"] == "Deck A note"

        # Switch to deck B (no saved notes)
        frame.deck_repo.set_current_deck({"href": "deck-b", "name": "Deck B"})
        frame.deck_notes_panel.load_notes_for_current()
        assert frame.deck_notes_panel.get_notes() == []
    finally:
        frame.Destroy()


@pytest.mark.usefixtures("wx_app")
def test_notes_loaded_on_session_restore(
    deck_selector_factory,
):
    """_render_current_deck() must load notes so they appear after app restart."""
    frame = deck_selector_factory()
    try:
        frame.deck_repo.set_current_deck({"href": "restore-deck", "name": "Restore Deck"})
        frame.controller.deck_notes_store["restore-deck"] = [
            {"id": "r1", "title": "Restored", "body": "Session note", "type": "General"}
        ]
        # Simulate session restore with saved zone cards
        frame.zone_cards = {
            "main": [{"name": "Mountain", "qty": 4}],
            "side": [],
            "out": [],
        }
        frame._render_current_deck()
        cards = frame.deck_notes_panel.get_notes()
        assert len(cards) == 1
        assert cards[0]["body"] == "Session note"
    finally:
        frame.Destroy()


@pytest.mark.usefixtures("wx_app")
def test_notes_persist_across_frames(
    deck_selector_factory,
):
    first_frame = deck_selector_factory()
    try:
        first_frame.deck_repo.set_current_deck({"href": "manual", "name": "Manual Deck"})
        first_frame.deck_notes_panel.set_notes(
            [{"id": "test-id", "title": "General", "body": "Important note", "type": "General"}]
        )
        first_frame.deck_notes_panel.save_current_notes()
    finally:
        first_frame.Destroy()

    second_frame = deck_selector_factory()
    try:
        second_frame.deck_repo.set_current_deck({"href": "manual", "name": "Manual Deck"})
        second_frame.deck_notes_panel.load_notes_for_current()
        cards = second_frame.deck_notes_panel.get_notes()
        assert len(cards) == 1
        assert cards[0]["body"] == "Important note"
    finally:
        second_frame.Destroy()
