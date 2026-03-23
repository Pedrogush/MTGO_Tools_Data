# Publishing Workflows

Scheduled publishing is split into two workflows:

- `publish-hourly.yml` runs every hour at minute `15` and publishes the current
  archetype/deck metadata plus referenced deck-text blobs for `Modern`,
  `Standard`, `Pioneer`, `Legacy`, `Vintage`, and `Pauper`.
- `publish-daily.yml` runs at `02:45` UTC, which is `23:45` in
  `America/Sao_Paulo`, and publishes the daily metagame aggregate for the same
  formats.

Both workflows share the same concurrency group so only one publish job writes
to `data/` at a time. Each workflow:

1. Runs the publisher CLI.
2. Prunes the checked-out tree with `python -m publisher.retention`.
3. Commits and pushes `data/` only when the tree actually changed.

Checked-tree retention is seven days for `data/hourly/` and `data/daily/`.
`data/latest/` remains the stable consumer entrypoint, and deck-text blobs under
`data/archive/` are pruned when they are no longer referenced by any retained or
latest deck snapshot. Git history is not rewritten by this policy.
