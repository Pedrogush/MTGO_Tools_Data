"""
Deck Stats Panel - Displays deck statistics, mana curve, and color distribution.

Shows summary statistics, mana curve breakdown, color concentration, type counts,
and opening-hand land probability analysis.
"""

import math
from collections import Counter
from typing import Any

import wx

from services.deck_service import DeckService, get_deck_service
from utils.card_data import CardDataManager
from utils.constants import DARK_ACCENT, DARK_ALT, DARK_PANEL, LIGHT_TEXT, SUBDUED_TEXT

_CARD_TYPES = [
    "Land",
    "Creature",
    "Instant",
    "Sorcery",
    "Enchantment",
    "Artifact",
    "Planeswalker",
    "Battle",
]

# MTG color identity → (short label, bar colour)
_COLOR_MAP: dict[str, tuple[str, tuple[int, int, int]]] = {
    "W": ("W", (220, 210, 170)),
    "U": ("U", (59, 130, 246)),
    "B": ("B", (140, 120, 160)),
    "R": ("R", (210, 70, 50)),
    "G": ("G", (60, 160, 70)),
    "C": ("C", (160, 150, 130)),
    "Colorless": ("C", (160, 150, 130)),
}

# Slightly varied adjacent colors — intentional, not rainbow
_TYPE_COLOURS: dict[str, tuple[int, int, int]] = {
    "Land": (145, 125, 95),
    "Creature": (90, 135, 185),
    "Instant": (80, 165, 145),
    "Sorcery": (120, 100, 175),
    "Enchantment": (165, 110, 150),
    "Artifact": (155, 155, 165),
    "Planeswalker": (95, 160, 185),
    "Battle": (175, 115, 90),
    "Other": (130, 130, 130),
}

# Opening-hand land count: 0=very red, 3=green, 7=very red
_HAND_COLOURS: list[tuple[int, int, int]] = [
    (220, 40, 40),  # 0 lands – very red
    (205, 75, 55),  # 1 land  – red
    (190, 135, 65),  # 2 lands – red fading to green
    (60, 190, 85),  # 3 lands – green
    (130, 185, 70),  # 4 lands – green fading to red
    (200, 130, 55),  # 5 lands – orange-red
    (210, 70, 55),  # 6 lands – red
    (225, 35, 35),  # 7 lands – very red
]

# Mana curve gradient endpoints
_CURVE_WARM = (255, 220, 40)  # yellow at CMC 0
_CURVE_COLD = (30, 50, 180)  # dark blue at CMC 15

_BAR_PAD = 6
_TITLE_H = 20
_VALUE_H = 16
_LABEL_H = 16


def _lerp_colour(
    c1: tuple[int, int, int], c2: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def _curve_colour(bucket: str) -> tuple[int, int, int]:
    if bucket == "X":
        cmc = 12
    elif bucket.endswith("+") and bucket[:-1].isdigit():
        cmc = int(bucket[:-1])
    elif bucket.isdigit():
        cmc = int(bucket)
    else:
        cmc = 0
    t = min(cmc / 15.0, 1.0)
    return _lerp_colour(_CURVE_WARM, _CURVE_COLD, t)


def _hypergeometric_exactly(n_total: int, n_success: int, n_draw: int, k: int) -> float:
    """P(X = k) under the hypergeometric distribution."""
    n_fail = n_total - n_success
    if k < 0 or k > n_success or n_draw - k < 0 or n_draw - k > n_fail:
        return 0.0
    return math.comb(n_success, k) * math.comb(n_fail, n_draw - k) / math.comb(n_total, n_draw)


class BarChartPanel(wx.Panel):
    """Custom panel that draws a vertical bar chart."""

    def __init__(self, parent: wx.Window, title: str = "") -> None:
        super().__init__(parent)
        self.SetBackgroundColour(wx.Colour(*DARK_ALT))
        self._title = title
        # list of (label, display_value, raw_value, bar_colour)
        self._items: list[tuple[str, str, float, tuple[int, int, int]]] = []
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, self._on_size)

    def set_data(
        self,
        items: list[tuple[str, str, float]],
        bar_colour: tuple[int, int, int] = DARK_ACCENT,
        per_item_colours: list[tuple[int, int, int]] | None = None,
    ) -> None:
        """Set chart data and trigger a repaint.

        Args:
            items: List of (label, display_value, raw_value) tuples.
            bar_colour: Default bar colour for all items.
            per_item_colours: Optional per-item override colours.
        """
        self._items = [
            (
                label,
                display_val,
                raw_val,
                per_item_colours[i] if per_item_colours else bar_colour,
            )
            for i, (label, display_val, raw_val) in enumerate(items)
        ]
        self.Refresh()

    def clear(self) -> None:
        self._items = []
        self.Refresh()

    # ---- drawing ----

    def _on_size(self, _evt: wx.SizeEvent) -> None:
        self.Refresh()

    def _on_paint(self, _evt: wx.PaintEvent) -> None:
        dc = wx.BufferedPaintDC(self)
        self._draw(dc)

    def _draw(self, dc: wx.DC) -> None:
        w, h = self.GetClientSize()
        if w <= 0 or h <= 0:
            return

        dc.SetBackground(wx.Brush(wx.Colour(*DARK_ALT)))
        dc.Clear()

        # Title
        title_h = 0
        if self._title:
            dc.SetFont(
                wx.Font(
                    8,
                    wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            )
            dc.SetTextForeground(wx.Colour(*SUBDUED_TEXT))
            dc.DrawText(self._title, _BAR_PAD, 4)
            title_h = _TITLE_H

        if not self._items:
            return

        n = len(self._items)

        # Bar area bounds
        bar_top = title_h + _VALUE_H + 4
        bar_bottom = h - _LABEL_H - _BAR_PAD
        bar_area_h = bar_bottom - bar_top
        if bar_area_h <= 0:
            return

        avail_w = w - _BAR_PAD * 2
        bar_spacing = max(2, avail_w // max(n * 5, 1))
        bar_w = max((avail_w - bar_spacing * (n - 1)) // n, 4)
        total_used = bar_w * n + bar_spacing * (n - 1)
        x_start = _BAR_PAD + max((avail_w - total_used) // 2, 0)

        max_val = max(raw for _, _, raw, _ in self._items) or 1.0

        dc.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        dc.SetPen(wx.TRANSPARENT_PEN)

        for i, (label, display_val, raw_val, colour) in enumerate(self._items):
            x = x_start + i * (bar_w + bar_spacing)

            bar_h = max(int(bar_area_h * raw_val / max_val), 2 if raw_val > 0 else 0)
            bar_y = bar_bottom - bar_h

            # Bar
            dc.SetBrush(wx.Brush(wx.Colour(*colour)))
            if bar_h > 0:
                dc.DrawRoundedRectangle(x, bar_y, bar_w, bar_h, min(3, bar_w // 4))

            # Value above bar
            dc.SetTextForeground(wx.Colour(*LIGHT_TEXT))
            tw, th = dc.GetTextExtent(display_val)
            val_x = x + (bar_w - tw) // 2
            val_y = bar_y - th - 2
            if val_y >= title_h:
                dc.DrawText(display_val, max(val_x, 0), val_y)

            # Label below bar area
            dc.SetTextForeground(wx.Colour(*SUBDUED_TEXT))
            lw, _ = dc.GetTextExtent(label)
            lbl_x = x + (bar_w - lw) // 2
            dc.DrawText(label, max(lbl_x, 0), bar_bottom + _BAR_PAD // 2)


class DeckStatsPanel(wx.Panel):
    """Panel that displays deck statistics and analysis."""

    def __init__(
        self,
        parent: wx.Window,
        card_manager: CardDataManager | None = None,
        deck_service: DeckService | None = None,
    ):
        """
        Initialize the deck stats panel.

        Args:
            parent: Parent window
            card_manager: Card data manager for metadata lookups
            deck_service: Deck service for analysis
        """
        super().__init__(parent)
        self.SetBackgroundColour(DARK_PANEL)

        self.card_manager = card_manager
        self.deck_service = deck_service or get_deck_service()
        self.zone_cards: dict[str, list[dict[str, Any]]] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the panel UI."""
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        # Summary statistics
        self.summary_label = wx.StaticText(self, label="No deck loaded.")
        self.summary_label.SetForegroundColour(LIGHT_TEXT)
        sizer.Add(self.summary_label, 0, wx.ALL, 6)

        # Top row: mana curve, color share, card types
        split = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(split, 3, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)

        self.curve_chart = BarChartPanel(self, title="Mana Curve")
        split.Add(self.curve_chart, 1, wx.EXPAND | wx.RIGHT, 4)

        self.color_chart = BarChartPanel(self, title="Color Share")
        split.Add(self.color_chart, 1, wx.EXPAND | wx.RIGHT, 4)

        self.type_chart = BarChartPanel(self, title="Card Types")
        split.Add(self.type_chart, 1, wx.EXPAND)

        # Bottom row: opening-hand land count odds
        self.hand_odds_chart = BarChartPanel(self, title="Opening Hand — Land Count")
        sizer.Add(self.hand_odds_chart, 2, wx.EXPAND | wx.ALL, 6)

    # ============= Public API =============

    def update_stats(self, deck_text: str, zone_cards: dict[str, list[dict[str, Any]]]) -> None:
        """
        Update the statistics display.

        Args:
            deck_text: Full deck text for analysis
            zone_cards: Dictionary mapping zone names to card lists
        """
        self.zone_cards = zone_cards

        if not deck_text.strip():
            self.summary_label.SetLabel("No deck loaded.")
            self.curve_chart.clear()
            self.color_chart.clear()
            self.type_chart.clear()
            self.hand_odds_chart.clear()
            return

        # Analyze deck
        stats = self.deck_service.analyze_deck(deck_text)

        # Count actual lands from zone_cards using type metadata (includes MDFCs)
        land_count, mdfc_count = self._count_lands()
        total_land_count = land_count + mdfc_count

        # Update summary
        land_label = f"{land_count} land{'s' if land_count != 1 else ''}"
        if mdfc_count:
            land_label += f" + {mdfc_count} MDFC{'s' if mdfc_count != 1 else ''}"
        summary = (
            f"Mainboard: {stats['mainboard_count']} cards ({stats['unique_mainboard']} unique)  |  "
            f"Sideboard: {stats['sideboard_count']} cards ({stats['unique_sideboard']} unique)  |  "
            f"Lands: {land_label}"
        )
        self.summary_label.SetLabel(summary)

        # Render charts
        self._render_curve()
        self._render_color_concentration()
        self._render_type_counts()
        self._render_hand_odds(stats["mainboard_count"], total_land_count)

    def set_card_manager(self, card_manager: CardDataManager) -> None:
        """Set the card data manager for metadata lookups."""
        self.card_manager = card_manager

    def clear(self) -> None:
        """Clear all statistics."""
        self.summary_label.SetLabel("No deck loaded.")
        self.curve_chart.clear()
        self.color_chart.clear()
        self.type_chart.clear()
        self.hand_odds_chart.clear()

    # ============= Private Methods =============

    def _count_lands(self) -> tuple[int, int]:
        """Count lands and MDFC-lands in the mainboard using card type metadata.

        Returns:
            (lands, mdfcs) where lands are cards with Land in front type_line and
            mdfcs are cards with Land only in the back face type_line.
        """
        lands = mdfcs = 0
        for entry in self.zone_cards.get("main", []):
            qty = entry["qty"]
            meta = self.card_manager.get_card(entry["name"]) if self.card_manager else None
            type_line = (meta.get("type_line") or "").lower() if meta else ""
            back_type_line = (meta.get("back_type_line") or "").lower() if meta else ""
            if "land" in type_line:
                lands += qty
            elif "land" in back_type_line:
                mdfcs += qty
        return lands, mdfcs

    def _render_curve(self) -> None:
        """Render the mana curve bar chart."""
        if not self.card_manager:
            self.curve_chart.clear()
            return

        counts: Counter[str] = Counter()
        for entry in self.zone_cards.get("main", []):
            meta = self.card_manager.get_card(entry["name"])
            mana_value = meta.get("mana_value") if meta else None

            if isinstance(mana_value, int | float):
                value = int(mana_value)
                bucket = "7+" if value >= 7 else str(value)
            else:
                bucket = "X"

            counts[bucket] += entry["qty"]

        def curve_key(bucket: str) -> int:
            if bucket == "X":
                return 99
            if bucket.endswith("+") and bucket[:-1].isdigit():
                return int(bucket[:-1]) + 10
            if bucket.isdigit():
                return int(bucket)
            return 98

        items = [
            (bucket, str(counts[bucket]), counts[bucket])
            for bucket in sorted(counts.keys(), key=curve_key)
        ]
        per_item_colours = [_curve_colour(bucket) for bucket, _, _ in items]
        self.curve_chart.set_data(items, per_item_colours=per_item_colours)

    def _render_color_concentration(self) -> None:
        """Render the color concentration bar chart."""
        if not self.card_manager:
            self.color_chart.clear()
            return

        totals: Counter[str] = Counter()
        for entry in self.zone_cards.get("main", []):
            meta = self.card_manager.get_card(entry["name"])
            identity = meta.get("color_identity") if meta else []

            if not identity:
                totals["Colorless"] += entry["qty"]
            else:
                for color in identity:
                    totals[color] += entry["qty"]

        grand_total = sum(totals.values())
        if grand_total == 0:
            self.color_chart.clear()
            return

        sorted_colors = sorted(totals.items(), key=lambda x: x[1], reverse=True)

        items = []
        colours = []
        for color, count in sorted_colors:
            short_name, bar_colour = _COLOR_MAP.get(color, (color, DARK_ACCENT))
            percentage = (count / grand_total) * 100
            items.append((short_name, f"{percentage:.0f}%", count))
            colours.append(bar_colour)

        self.color_chart.set_data(items, per_item_colours=colours)

    def _render_type_counts(self) -> None:
        """Render card type count bar chart for the mainboard."""
        counts: Counter[str] = Counter()
        for entry in self.zone_cards.get("main", []):
            type_line = ""
            if self.card_manager:
                meta = self.card_manager.get_card(entry["name"])
                type_line = (meta.get("type_line") or "") if meta else ""

            matched = False
            for card_type in _CARD_TYPES:
                if card_type.lower() in type_line.lower():
                    counts[card_type] += entry["qty"]
                    matched = True
            if not matched:
                counts["Other"] += entry["qty"]

        display_order = _CARD_TYPES + ["Other"]
        items = [
            (card_type, str(counts[card_type]), counts[card_type])
            for card_type in display_order
            if counts[card_type]
        ]
        per_item_colours = [_TYPE_COLOURS.get(ct, DARK_ACCENT) for ct, _, _ in items]
        self.type_chart.set_data(items, per_item_colours=per_item_colours)

    def _render_hand_odds(self, deck_size: int, land_count: int) -> None:
        """Render opening-hand land count probability as a bar chart."""
        if deck_size <= 0:
            self.hand_odds_chart.clear()
            return

        hand_size = 7
        items: list[tuple[str, str, float]] = []
        for k in range(hand_size + 1):
            prob = _hypergeometric_exactly(deck_size, land_count, hand_size, k)
            pct = prob * 100
            items.append((str(k), f"{pct:.1f}%", pct))

        self.hand_odds_chart.set_data(items, per_item_colours=_HAND_COLOURS)
