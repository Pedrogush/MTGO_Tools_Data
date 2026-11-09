# Publishing Workflows

Scheduled publishing now runs through a single workflow: `publish-data.yml`.

The workflow runs hourly at minute `15` and keeps all publish stages inside the
same workflow run so they do not race each other on `main`.

Every product is sourced from the Videre Project API. It has four phases:

1. `publish-decklists-mtgo` fans out into one job per format for `Modern`,
   `Standard`, `Pioneer`, `Legacy`, `Vintage`, and `Pauper`. Each job fetches
   the last seven days of MTGO events from the Videre API (the only network
   traffic in the workflow), archives them under
   `data/archive/mtgo-decklists/<format>/`, publishes
   `data/latest/mtgo-decklists/<format>.json`, and uploads both as an artifact.
2. `publish-decklists`, `publish-metagame`, and `publish-radars` each fan out
   into one job per format after that, download the same-format MTGO artifact,
   and derive their products from its snapshot: archetype list, per-archetype
   deck lists and deck-text blobs; metagame daily counts; archetype radars and
   the format card pool. They run with `always()` so a failed MTGO ingest still
   republishes from its stale-fallback snapshot (or, with no artifact at all,
   from the snapshot committed on `data-publish`).
3. Each of those jobs uploads its format-scoped results as an artifact.
4. A single final merge job downloads every artifact set, prunes `data/` with
   `python -m publisher.retention`, rebuilds `data/latest/latest.json`, rebuilds
   `data/latest/client-bundle.tar.gz` and mirrors it to the rolling
   `client-bundle` release asset, and commits `data/` once for the whole
   workflow. The bundle is a gzipped tarball, so git cannot delta it and each
   run adds a fresh multi-MB blob; 1392 of them grew this repository to ~4 GB,
   96% of its size. It is still committed because shipped MTGO_Tools clients
   fetch it from the raw `data-publish` path at startup and treat a 404 as a
   hard failure. The release asset exists so they can migrate, after which the
   committed copy should be dropped.

Each format job has its own concurrency group, so a new `Modern` run can block
or wait on another `Modern` run without cancelling unrelated formats. For the
single workflow, the per-format jobs never push directly, which avoids rebasing
concurrent edits to shared files like `data/latest/latest.json`. Each format
job:

1. Runs the publisher CLI.
2. Uploads only its format-scoped published files as an artifact.

The final merge job then:

1. Downloads all decklist, metagame, and radar artifacts into the checked-out tree.
2. Prunes the checked-out tree with `python -m publisher.retention`, including
   deck and radar snapshots for archetypes no longer in their format's list.
3. Rebuilds `data/latest/latest.json` from the merged outputs, including
   `archetype_radars` and `format_card_pools`.
4. Rebuilds the deterministic client bundle.
5. Commits and pushes `data/` only when the tree actually changed.

Checked-tree retention is seven days for `data/hourly/` and `data/daily/`.
`data/latest/` remains the stable consumer entrypoint, and deck-text blobs under
`data/archive/` are pruned when they are no longer referenced by any retained or
latest deck snapshot. Git history is not rewritten by this policy.

## Local warmup run

To run the MTGO + deck-text publisher locally, use:

```bash
./scripts/run_publish_hourly_local.sh
```

This helper runs all hourly formats (`Modern`, `Standard`, `Pioneer`,
`Legacy`, `Vintage`, `Pauper`) and traverses all archetypes for each format.
It first runs `publisher.runner scrape-mtgo-decklists`, then
`publisher.runner scrape-deck-texts`, matching the decklist stage inside
`publish-data.yml`, with a lower Videre event delay by default.

Optional environment variables:

- `PUBLISH_WARMUP_DAYS` (default: `7`)
- `PUBLISH_OUTPUT_ROOT` (default: `data`)
- `PUBLISH_RETENTION_DAYS` (default: `7`)
- `PUBLISH_MTGO_EVENT_DELAY_SECONDS` (default: `0.5`)

## Videre API contract

`.github/workflows/videre-contract.yml` runs `scripts/check_videre_contract.py`
daily (and on pull requests touching the Videre client). It fetches
`https://api.videreproject.com/openapi.json` and fails if any field pinned in
`navigators/videre_contract.py` disappears or changes type. It is deliberately
not a dependency of `publish-data.yml`: an API change should alert, not stop the
scheduled publish. `tests/test_videre_contract.py` checks the same pins offline
against the response fixtures in `tests/fixtures/videre/`.
