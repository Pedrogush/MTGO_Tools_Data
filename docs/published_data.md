# Published Data Contracts

Issue `#1` Step 1 freezes the on-disk publisher contract before workflow logic
changes. All published artifacts are versioned JSON documents under `data/`.

## Repository Layout

- `data/latest/`: stable consumer-facing pointers for the freshest successful
  scrape output.
- `data/latest/latest.json`: top-level manifest listing the latest artifact for
  each format and archetype.
- `data/hourly/<timestamp>/`: hourly snapshots for archetype lists, archetype
  deck metadata, and deck text blobs.
- `data/daily/<date>/`: daily metagame snapshots.
- `data/archive/`: reserved for future compressed exports or hand-curated
  archive manifests.

Checked-tree retention is one week. Consumers should rely on `data/latest/`
instead of scanning historical directories.

## Artifact Kinds

Every artifact includes:

- `schema_version`: currently `"1"`.
- `kind`: one of `latest_manifest`, `archetype_list`, `archetype_decks`,
  `metagame_daily`, or `deck_text_blob`.
- `generated_at`: UTC ISO-8601 timestamp with `Z` suffix.
- `format`: normalized format slug such as `modern` or `pioneer` for all
  non-manifest artifacts.

### `latest_manifest`

Stored at `data/latest/latest.json`.

- `retention_days`: checked-tree retention target, currently `7`.
- `latest.archetype_lists[]`: latest archetype list snapshot per format.
- `latest.archetype_decks[]`: latest deck metadata snapshot per
  format/archetype.
- `latest.metagame_daily[]`: latest metagame daily snapshot per format.
- `latest.deck_text_blobs[]`: latest deck text blob per format/archetype.

Each entry contains `format`, `path`, `updated_at`, and `archetype` when the
artifact is archetype-scoped.

### `archetype_list`

Written to:

- `data/latest/archetypes/<format>.json`
- `data/hourly/<timestamp>/archetypes/<format>.json`

Fields:

- `source`: `mtggoldfish`.
- `archetypes[]`: objects with `name` and `href`.

Freshness target: hourly.

### `archetype_decks`

Written to:

- `data/latest/decks/<format>/<archetype>.json`
- `data/hourly/<timestamp>/decks/<format>/<archetype>.json`

Fields:

- `source`: `mtggoldfish`, `mtgo`, or `both`.
- `archetype`: object with `name` and `href`.
- `decks[]`: deck metadata rows from the scrape surface.

Freshness target: hourly.

### `metagame_daily`

Written to:

- `data/latest/metagame/<format>.json`
- `data/daily/<date>/metagame/<format>.json`

Fields:

- `source`: `mtggoldfish`.
- `generated_for_day`: daily snapshot date.
- `stats[]`: objects with `archetype`, `deck_count`, and `daily_counts`.

Freshness target: daily.

### `deck_text_blob`

Written to:

- `data/latest/deck-texts/<format>/<archetype>.json`
- `data/hourly/<timestamp>/deck-texts/<format>/<archetype>.json`

Fields:

- `source`: `mtggoldfish`, `mtgo`, or `both`.
- `archetype`: object with `name` and `href`.
- `deck_texts[]`: objects with `deck_id`, `deck_name`, `deck_date`, `source`,
  and `deck_text`.

Freshness target: hourly.

## Consumer Expectations

- Consumers should treat missing historical snapshots as normal after the
  seven-day retention window.
- Consumers should use `data/latest/latest.json` to discover current paths.
- Hourly consumers should expect archetype lists, deck metadata, and deck text
  blobs to advance together by timestamp, but only daily consumers should rely
  on `data/daily/`.
- `deck_text_blob` contents may be empty when a run intentionally scopes to no
  matching recent decks; the blob is still valid and deterministic.
