# Publishing Workflows

Scheduled publishing is split into three workflows:

- `publish-decklists.yml` runs hourly at minute `15` and fans out into
  one job per format for `Modern`, `Standard`, `Pioneer`, `Legacy`, `Vintage`,
  and `Pauper`. Each job publishes current archetype/deck metadata plus
  referenced deck-text blobs for just that format, uploads those format-scoped
  results as artifacts, and a single downstream job merges and commits `data/`
  once for the whole workflow.
- `publish-client-bundle.yml` runs hourly at minute `30`, repackages the latest
  committed client-facing deck snapshots, metagame snapshots, and deck-text
  archive blobs into `data/latest/client-bundle.tar.gz`, and commits only when
  the deterministic bundle bytes change.
- `publish-client-bundle.yml` runs hourly at minute `30`, repackages the latest
  committed client-facing deck snapshots, metagame snapshots, and deck-text
  archive blobs into `data/latest/client-bundle.tar.gz`, and commits only when
  the deterministic bundle bytes change.
- `publish-metagame.yml` runs hourly at minute `45` and also fans out into one
  job per format for the metagame aggregate.

Each format job has its own concurrency group, so a new `Modern` run can block
or wait on another `Modern` run without cancelling unrelated formats. For the
decklists workflow, the per-format jobs no longer push directly, which avoids
rebasing concurrent edits to shared files like `data/latest/latest.json`. Each
format job:

1. Runs the publisher CLI.
2. Uploads only its format-scoped published files as an artifact.

The decklists merge job then:

1. Downloads all format artifacts into the checked-out tree.
2. Prunes the checked-out tree with `python -m publisher.retention`.
3. Rebuilds `data/latest/latest.json` from the merged outputs.
4. Commits and pushes `data/` only when the tree actually changed.

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
It uses the same `publisher.runner scrape-deck-texts` command path as
`publish-decklists.yml`, but pins `--deck-download-delay-seconds 0` for local
warmups.

Optional environment variables:

- `PUBLISH_WARMUP_DAYS` (default: `7`)
- `PUBLISH_OUTPUT_ROOT` (default: `data`)
- `PUBLISH_RETENTION_DAYS` (default: `7`)
