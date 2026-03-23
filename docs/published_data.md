# Published Data Contracts

Issue `#1` Step 1 freezes the on-disk publisher contract before workflow logic
changes. All published artifacts are versioned JSON documents under `data/`.

## Repository Layout

- `data/latest/`: stable consumer-facing pointers for the freshest successful
  scrape output.
- `data/latest/latest.json`: top-level manifest listing the latest artifact for
  each format and archetype.
- `data/hourly/<timestamp>/`: hourly snapshots for archetype lists, archetype
  deck metadata, and run manifests.
- `data/daily/<date>/`: daily metagame snapshots.
- `data/archive/deck-texts/<format>/<deck-id>.json`: deduplicated shared deck
  text blobs keyed by deck ID.
- `data/latest/runs/<command>.json`: latest machine-readable publisher run
  manifest.

Checked-tree retention is one week. Consumers should rely on `data/latest/`
instead of scanning historical directories.

## Artifact Kinds

Every artifact includes:

- `schema_version`: currently `"1"`.
- `kind`: one of `latest_manifest`, `archetype_list`, `archetype_decks`,
  `metagame_daily`, `deck_text_blob`, or `publisher_run`.
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
- `latest.runs[]`: latest run manifest per publisher command.

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
- `decks[].deck_text_path`: stable shared deck-text reference under
  `data/archive/deck-texts/`.

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

- `data/archive/deck-texts/<format>/<deck-id>.json`

Fields:

- `source`: `mtggoldfish`, `mtgo`, or `both`.
- `deck_id`: stable deck identifier.
- `deck_name`: latest known deck name for that deck ID.
- `deck_text`: deck content.

Freshness target: hourly, but the storage path is stable across hourly runs so
unchanged deck texts are deduplicated by `deck_id`.

### `publisher_run`

Written to:

- `data/latest/runs/<command>.json`
- `data/hourly/<timestamp>/runs/<command>.json`

Fields:

- `status`: overall command status.
- `max_stale_hours`: freshness window for stale fallback acceptance.
- `summary`: count of `success`, `skipped`, `stale-fallback`, and
  `hard-failure`.
- `results[]`: per-scope entries with `scope`, `status`, optional `format`,
  optional `archetype` or `deck_id`, `path`, and `message`.

Commands return non-zero only when at least one scope is a `hard-failure`. A
transient scrape problem that can reuse a still-fresh existing latest artifact
is recorded as `stale-fallback` and remains workflow-safe.

## Consumer Expectations

- Consumers should treat missing historical snapshots as normal after the
  seven-day retention window.
- Consumers should use `data/latest/latest.json` to discover current paths.
- Consumers should use `data/latest/runs/<command>.json` when they need machine
  readable scrape health for automation or Actions summaries.
- Hourly consumers should expect archetype lists and deck metadata to advance
  together by timestamp, while deck text is resolved through stable per-deck
  references in `data/archive/deck-texts/`.
- A `stale-fallback` run result means the scrape failed but the previous latest
  artifact was still within the documented freshness window.
