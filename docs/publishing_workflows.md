# Publishing Workflows

Scheduled publishing is split into two workflows:

- `publish-hourly.yml` runs every two hours at minute `15` and fans out into
  one job per format for `Modern`, `Standard`, `Pioneer`, `Legacy`, `Vintage`,
  and `Pauper`. Each job publishes current archetype/deck metadata plus
  referenced deck-text blobs for just that format, uploads those format-scoped
  results as artifacts, and a single downstream job merges and commits `data/`
  once for the whole workflow.
- `publish-daily.yml` runs at `02:45` UTC, which is `23:45` in
  `America/Sao_Paulo`, and also fans out into one job per format for the daily
  metagame aggregate.

Each format job has its own concurrency group, so a new `Modern` run can block
or wait on another `Modern` run without cancelling unrelated formats. For the
hourly workflow, the per-format jobs no longer push directly, which avoids
rebasing concurrent edits to shared files like `data/latest/latest.json`. Each
format job:

1. Runs the publisher CLI.
2. Uploads only its format-scoped published files as an artifact.

The hourly merge job then:

1. Downloads all format artifacts into the checked-out tree.
2. Prunes the checked-out tree with `python -m publisher.retention`.
3. Rebuilds `data/latest/latest.json` from the merged outputs.
4. Commits and pushes `data/` only when the tree actually changed.

Checked-tree retention is seven days for `data/hourly/` and `data/daily/`.
`data/latest/` remains the stable consumer entrypoint, and deck-text blobs under
`data/archive/` are pruned when they are no longer referenced by any retained or
latest deck snapshot. Git history is not rewritten by this policy.
