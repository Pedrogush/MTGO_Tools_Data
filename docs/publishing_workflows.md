# Publishing Workflows

Scheduled publishing now runs through a single workflow: `publish-data.yml`.

The workflow runs hourly at minute `15` and keeps all publish stages inside the
same workflow run so they do not race each other on `main`.

It has four phases:

1. Decklist publishing fans out into one job per format for `Modern`,
   `Standard`, `Pioneer`, `Legacy`, `Vintage`, and `Pauper`. Each job publishes
   current archetype/deck metadata plus referenced deck-text blobs for just
   that format and uploads those format-scoped results as artifacts.
2. Metagame publishing also fans out into one job per format and uploads its
   format-scoped artifacts.
3. Radar publishing fans out into one job per format, downloads the matching
   same-run decklist artifact for that format, publishes archetype radar
   snapshots plus one format-wide card-pool artifact, and uploads those results
   as artifacts.
4. A single final merge job downloads every artifact set, prunes `data/` with
   `python -m publisher.retention`, rebuilds `data/latest/latest.json`, rebuilds
   `data/latest/client-bundle.tar.gz`, and commits `data/` once for the whole
   workflow.

Each format job has its own concurrency group, so a new `Modern` run can block
or wait on another `Modern` run without cancelling unrelated formats. For the
single workflow, the per-format jobs never push directly, which avoids rebasing
concurrent edits to shared files like `data/latest/latest.json`. Each format
job:

1. Runs the publisher CLI.
2. Uploads only its format-scoped published files as an artifact.

The final merge job then:

1. Downloads all decklist, metagame, and radar artifacts into the checked-out tree.
2. Prunes the checked-out tree with `python -m publisher.retention`.
3. Rebuilds `data/latest/latest.json` from the merged outputs, including
   `archetype_radars` and `format_card_pools`.
4. Rebuilds the deterministic client bundle.
5. Commits and pushes `data/` only when the tree actually changed.

Checked-tree retention is seven days for `data/hourly/` and `data/daily/`.
`data/latest/` remains the stable consumer entrypoint, and deck-text blobs under
`data/archive/` are pruned when they are no longer referenced by any retained or
latest deck snapshot. Git history is not rewritten by this policy.

## Local warmup run

To run the hourly deck-text publisher locally without the workflow's remote
`3` second deck download delay, use:

```bash
./scripts/run_publish_hourly_local.sh
```

This helper runs all hourly formats (`Modern`, `Standard`, `Pioneer`,
`Legacy`, `Vintage`, `Pauper`) and traverses all archetypes for each format.
It uses the same `publisher.runner scrape-deck-texts` command path as the
decklist stage inside `publish-data.yml`, but pins
`--deck-download-delay-seconds 0` for local warmups.

Optional environment variables:

- `PUBLISH_WARMUP_DAYS` (default: `7`)
- `PUBLISH_OUTPUT_ROOT` (default: `data`)
- `PUBLISH_RETENTION_DAYS` (default: `7`)
