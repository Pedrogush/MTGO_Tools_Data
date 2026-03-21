"""Deck construction rules and defaults."""

MAINBOARD_MIN_CARDS = 60
MAINBOARD_TARGET_CARDS = 60
SIDEBOARD_MAX_CARDS = 15
DEFAULT_MAX_DECKS = 10

# Deck Stats Panel — mana curve analysis
STATS_CURVE_HIGH_CMC_BUCKET = 7  # mana values >= this are grouped into a "7+" bucket
STATS_CURVE_X_SORT_KEY = 99  # sort sentinel for "X" mana value bucket
STATS_CURVE_UNKNOWN_SORT_KEY = 98  # sort sentinel for unrecognised bucket labels
STATS_CURVE_X_CMC_FOR_COLOUR = 12  # CMC used when computing gradient colour for the X bucket
STATS_CURVE_COLOUR_LERP_MAX_CMC = 15.0  # CMC at which the lerp colour gradient is fully cold

# Deck Stats Panel — opening-hand probability analysis
STATS_HAND_SIZE = 7  # standard MTG opening hand size
STATS_HAND_COLLAPSE_THRESHOLD = 6  # land counts >= this are collapsed into a single "6+" bar

# Hypergeometric calculator — spin ctrl bounds and defaults
CALC_DECK_SIZE_MIN = 1
CALC_DECK_SIZE_MAX = 250
CALC_DECK_SIZE_DEFAULT = 60
CALC_COPIES_MAX = 60
CALC_COPIES_DEFAULT = 4  # typical 4-of playset
CALC_DRAWN_DEFAULT = 7  # standard opening hand size
CALC_TARGET_DEFAULT = 1  # default: at least 1 copy

# Hypergeometric calculator — preset configurations (deck_size, cards_drawn)
CALC_PRESET_OPEN_60_DECK = 60
CALC_PRESET_OPEN_60_DRAWN = 7
CALC_PRESET_OPEN_40_DECK = 40
CALC_PRESET_OPEN_40_DRAWN = 7
CALC_PRESET_T3_PLAY_DECK = 60
CALC_PRESET_T3_PLAY_DRAWN = 9
CALC_PRESET_T3_DRAW_DECK = 60
CALC_PRESET_T3_DRAW_DRAWN = 10
