# Publishing Workflows

Scheduled publishing is split into two workflows:

- `publish-hourly.yml` runs every hour at minute `15` and fans out into one job
  per format for `Modern`, `Standard`, `Pioneer`, `Legacy`, `Vintage`, and
  `Pauper`. Each job publishes current archetype/deck metadata plus referenced
  deck-text blobs for just that format.
- `publish-daily.yml` runs at `02:45` UTC, which is `23:45` in
  `America/Sao_Paulo`, and also fans out into one job per format for the daily
  metagame aggregate.

Each format job has its own concurrency group, so a new `Modern` run can block
or wait on another `Modern` run without cancelling unrelated formats. Each
workflow job:

1. Runs the publisher CLI.
2. Prunes the checked-out tree with `python -m publisher.retention`.
3. Commits and pushes `data/` only when the tree actually changed.

Checked-tree retention is seven days for `data/hourly/` and `data/daily/`.
`data/latest/` remains the stable consumer entrypoint, and deck-text blobs under
`data/archive/` are pruned when they are no longer referenced by any retained or
latest deck snapshot. Git history is not rewritten by this policy.
