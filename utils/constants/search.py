"""Search limits and defaults."""

DEFAULT_SEARCH_LIMIT = 50
DEFAULT_SUGGESTION_LIMIT = 10
MIN_PARTIAL_NAME_LENGTH = 2

# MTGGoldfish player page scraping
GOLDFISH_PLAYER_TABLE_COLUMNS = 8  # expected number of <td> cells in a valid result row

# MTGGoldfish archetype deck table column indices
GOLDFISH_DECK_TABLE_COL_DATE = 0
GOLDFISH_DECK_TABLE_COL_NUMBER = 1
GOLDFISH_DECK_TABLE_COL_PLAYER = 2
GOLDFISH_DECK_TABLE_COL_EVENT = 3
GOLDFISH_DECK_TABLE_COL_RESULT = 4
