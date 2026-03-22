"""
Toolbar Buttons - Shared utility buttons for the deck selector toolbar.

Provides quick-access buttons for opponent tracking, timers, history, and data tasks.
Navigation actions and maintenance/utility actions are visually separated by a divider,
with utility buttons rendered at lower visual weight.
"""

from collections.abc import Callable

import wx

from utils.constants import SUBDUED_TEXT


class ToolbarButtons(wx.Panel):
    """Panel containing the deck selector toolbar buttons."""

    def __init__(
        self,
        parent: wx.Window,
        on_open_opponent_tracker: Callable[[], None] | None = None,
        on_open_timer_alert: Callable[[], None] | None = None,
        on_open_match_history: Callable[[], None] | None = None,
        on_open_metagame_analysis: Callable[[], None] | None = None,
        on_load_collection: Callable[[], None] | None = None,
        on_download_card_images: Callable[[], None] | None = None,
        on_update_card_database: Callable[[], None] | None = None,
        on_export_diagnostics: Callable[[], None] | None = None,
        labels: dict[str, str] | None = None,
    ):
        """
        Initialize the toolbar button panel.

        Args:
            parent: Parent window
            on_open_opponent_tracker: Callback for "Opponent Tracker"
            on_open_timer_alert: Callback for "Timer Alert"
            on_open_match_history: Callback for "Match History"
            on_open_metagame_analysis: Callback for "Metagame Analysis"
            on_load_collection: Callback for "Load Collection"
            on_download_card_images: Callback for "Download Card Images"
            on_update_card_database: Callback for "Update Card Database"
            on_export_diagnostics: Callback for "Export Diagnostics"
        """
        super().__init__(parent)
        labels = labels or {}

        self._button_row = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self._button_row)

        # Navigation group — primary actions
        self.opponent_tracker_button = self._add_button(
            labels.get("opponent_tracker", "Opponent Tracker"), on_open_opponent_tracker
        )
        self.timer_alert_button = self._add_button(
            labels.get("timer_alert", "Timer Alert"), on_open_timer_alert
        )
        self.match_history_button = self._add_button(
            labels.get("match_history", "Match History"), on_open_match_history
        )
        self.metagame_analysis_button = self._add_button(
            labels.get("metagame_analysis", "Metagame Analysis"), on_open_metagame_analysis
        )

        # Divider between navigation and utility groups
        self._add_divider()

        # Utility group — maintenance/data actions, rendered at lower visual weight
        self.load_collection_button = self._add_button(
            labels.get("load_collection", "Load Collection"),
            on_load_collection,
            subdued=True,
        )
        self.download_images_button = self._add_button(
            labels.get("download_card_images", "Download Card Images"),
            on_download_card_images,
            subdued=True,
        )
        self.update_database_button = self._add_button(
            labels.get("update_card_database", "Update Card Database"),
            on_update_card_database,
            subdued=True,
        )
        self.export_diagnostics_button = self._add_button(
            labels.get("export_diagnostics", "Export Diagnostics"),
            on_export_diagnostics,
            subdued=True,
        )

        self._button_row.AddStretchSpacer(1)

    # ============= Helpers =============

    def _add_button(
        self,
        label: str,
        handler: Callable[[], None] | None,
        *,
        margin: int = 6,
        subdued: bool = False,
    ) -> wx.Button:
        """Create a toolbar button and bind its handler if provided."""
        button = wx.Button(self, label=label)
        if subdued:
            button.SetForegroundColour(wx.Colour(*SUBDUED_TEXT))
        if handler:
            button.Bind(wx.EVT_BUTTON, lambda _evt, cb=handler: cb())
        else:  # pragma: no cover - defensive fallback
            button.Disable()
        self._button_row.Add(button, 0, wx.RIGHT, margin)
        return button

    def _add_divider(self, gap: int = 8) -> None:
        """Add a vertical line divider between button groups."""
        self._button_row.AddSpacer(gap)
        line = wx.StaticLine(self, style=wx.LI_VERTICAL)
        self._button_row.Add(line, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 4)
        self._button_row.AddSpacer(gap)


__all__ = ["ToolbarButtons"]
