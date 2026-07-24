"""Time constants and cache aging defaults."""

ONE_HOUR_SECONDS = 60 * 60
ONE_DAY_SECONDS = 24 * 60 * 60

# MTGO background fetch timing
MTGO_BACKGROUND_FETCH_DAYS = 7

# External HTTP request timeouts
MTGO_DECKLISTS_REQUEST_TIMEOUT_SECONDS = 30

# MTGO decklists fetch retry configuration (exponential backoff delays between attempts)
MTGO_DECKLISTS_FETCH_RETRY_DELAYS_SECONDS = (2, 5, 10)

# Metagame stats — lookback window for daily result counts
METAGAME_STATS_LOOKBACK_DAYS = 7

# SQLite cache settings
SQLITE_CONNECTION_TIMEOUT_SECONDS = 30.0
SQLITE_BUSY_TIMEOUT_MS = 30000
