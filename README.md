# MTGO_Tools_Data

Metagame data feed for the [MTGO_Tools](https://github.com/Pedrogush/MTGO_Tools)
client: MTGO tournament results from the
[Videre Project API](https://api.videreproject.com), published on a schedule
to the `data-publish` branch (including the single-request
`client-bundle.tar.gz`, which is also mirrored to the rolling `client-bundle`
release).

This repository was carved out of MTGO_Tools — the original full desktop
application — and reduced to its publisher path. Every product (archetype
lists, deck lists, deck texts, radars, card pools, metagame counts) is derived
from Videre API data; nothing is scraped from MTGGoldfish anymore.

![Version](https://img.shields.io/badge/version-0.2-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Platform](https://img.shields.io/badge/platform-headless-lightgrey)
![License](https://img.shields.io/badge/license-MIT-orange)

## Installation

### Quick Start

1. **Prerequisites**:
   - Python 3.11 or newer

2. **Clone the repository**:
   ```bash
   git clone https://github.com/Pedrogush/MTGO_Tools_Data.git
   cd MTGO_Tools_Data
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Run the scraper tests**:
   ```bash
   python -m pytest
   ```

## Architecture

See [docs/scraping_surface.md](docs/scraping_surface.md) for the current scrape-only boundary.

## Published Data

Publisher outputs are written under `data/`:

- `data/latest/` for stable consumer-facing pointers.
- `data/latest/client-bundle.tar.gz` for single-request client bootstrap. The
  bundle contains the stable `latest/` deck, radar, format card-pool, and
  metagame snapshots plus the referenced `archive/deck-texts/` blobs. The same
  file is mirrored to the rolling `client-bundle` release asset, which new
  consumers should prefer:
  <https://github.com/Pedrogush/MTGO_Tools_Data/releases/download/client-bundle/client-bundle.tar.gz>.
  The committed copy is a gzipped tarball that git cannot delta, so one blob per
  publish run is what grew this repository to ~4 GB; it stays only until shipped
  MTGO_Tools clients read the release asset instead.
- `data/latest/mtgo-decklists/<format>.json` for the MTGO events of the last
  seven days (Videre API), with every deck's metadata and deck text. All other
  per-format products below are derived from this snapshot.
- `data/latest/archetypes/<format>.json` for the archetypes present in that
  window. Names are Videre's archetype labels; hrefs are
  `<format>-<normalized name>`. Decks Videre could not classify keep its
  colour-code label (e.g. `BR`) as their archetype; decks with no label at all
  are `Unknown` and are not listed.
- `data/latest/decks/<format>/<archetype>.json` for each archetype's decks
  (`source: "mtgo"`), referencing deck-text blobs by `deck_text_path`.
- `data/latest/radars/<format>/<archetype>.json` for published archetype radar
  snapshots derived from the same decks.
- `data/latest/card-pools/<format>.json` for the format-wide card pool built
  from all published decklists in that format. It includes the unique card list
  and per-card total copies played, sorted descending by copies.
- `data/hourly/<timestamp>/` for hourly snapshots and run manifests.
- `data/daily/<date>/` for daily metagame snapshots.
- `data/archive/deck-texts/<format>/<deck-id>.json` for deduplicated per-deck
  text blobs referenced from deck metadata snapshots.

Each publisher command also writes a run manifest under `data/latest/runs/`.
Single-format runs use `data/latest/runs/<command>-<format>.json`; multi-format
runs keep `data/latest/runs/<command>.json`. These manifests record per-scope
`success`, `skipped`, `stale-fallback`, and `hard-failure` statuses. Commands
only return non-zero when freshness guarantees are violated.

Checked-tree retention is one week. `data/hourly/` and `data/daily/` are pruned
before automated commits, while `data/latest/` remains the stable consumer
entrypoint. Git history is retained separately and is not rewritten by the
publisher workflows.

## Publisher CLI

The headless publisher entrypoint is `python -m publisher.runner`.

```bash
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-mtgo-decklists --format Modern --days 7
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-archetypes --format Modern
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-decks --format Modern --archetype "Temur Rhinos" --days 7
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-deck-texts --format Modern --archetype "Temur Rhinos" --days 7
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-radars --format Modern --archetype "Temur Rhinos"
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-metagame --format Modern --day 2026-03-23
python -m publisher.retention --output-root data --timestamp 2026-03-23T18:00:00Z --retention-days 7
```

`scrape-mtgo-decklists` is the only command that makes network requests (to
the Videre API, with `MTGO_DECKLISTS_ENABLED=true`); the others read
`data/latest/mtgo-decklists/<format>.json`, so run it first.

Outputs are written into repository-managed staging paths under `data/latest/`,
`data/hourly/`, `data/daily/`, and `data/archive/`.
Each command also writes a run manifest under `data/latest/runs/`. Single-format
runs use `data/latest/runs/<command>-<format>.json`; multi-format runs keep
`data/latest/runs/<command>.json`. These manifests store per-scope statuses
(`success`, `skipped`, `stale-fallback`, `hard-failure`) and the command only
returns a non-zero exit code when freshness guarantees are violated.

## Publishing Schedule

See [docs/publishing_workflows.md](docs/publishing_workflows.md) for the exact
workflow behavior. In short:

- `publish-data.yml` runs hourly at minute `15`.
- MTGO decklist ingest (the only Videre API traffic) fans out into one job
  per format for `Modern`, `Standard`, `Pioneer`, `Legacy`, `Vintage`, and
  `Pauper`.
- Deck-list, metagame, and radar publishing then run one job per format each,
  derived from that same-run MTGO artifact.
- A single final merge job downloads every format artifact, prunes retention,
  rebuilds `data/latest/latest.json`, rebuilds
  `data/latest/client-bundle.tar.gz` and mirrors it to the `client-bundle`
  release, and commits `data/` once.
- Each format job keeps its own concurrency key, but only the final merge job
  pushes, so the publish stages stay in sync on one workflow run.

## Development

### Prerequisites

- Python 3.11+
- Black and Ruff for code formatting
- pytest for testing

### Development Workflow

```bash
ruff check .
black --check .
pytest
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_deck_service.py

# Run with verbose output
pytest -v

```

### Code Quality

The project uses:
- **Black**: Code formatting (line length 100)
- **Ruff**: Fast Python linter
- **mypy**: Static type checking (permissive mode)
- **Bandit**: Security linting

Configuration is in `pyproject.toml`.

## Project Structure

```
MTGO_Tools_Data/
├── publisher/              # Publisher CLI, contracts, retention, bundle
│   └── mtgo_archive.py     # Derives every product from the MTGO snapshot
├── scraping/               # Headless scrape facade
├── services/               # MTGO event processing, radar maths
├── navigators/             # External API integrations
│   ├── videre.py           # Videre API client (MTGO events)
│   └── videre_contract.py  # Fields we read from the Videre API, and checks
├── utils/                  # Utility modules
│   ├── deck_text_cache.py
│   └── metagame_stats.py
├── tests/                  # Test suite
└── scripts/                # Utility scripts
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Follow the code style (Black + Ruff)
4. Add tests for new functionality
5. Submit a pull request

## Data Sources

- **MTGO Decklists**: [Videre Project API](https://api.videreproject.com) —
  community REST API over MTGO event data ([videre-project](https://github.com/videre-project)).
  It is the only data source.
- **MTGO Archetypes**: published by the same Videre API alongside each deck.
  Their labels come from the [Badaro/MTGOFormatData](https://github.com/Badaro/MTGOFormatData)
  taxonomy, so this repo no longer vendors those rules or classifies locally.

## Known Limitations

- Paper tournament results are not collected. MTGGoldfish was the only paper
  source and was removed; the feed is MTGO-only
- MTGO decklist coverage is bounded by what Daybreak publishes (Top 32 of
  scheduled events plus a curated selection of league 5-0s), regardless of
  the API serving it
- The Videre API is a community service with no SLA; MTGO publishing falls
  back to the last published snapshots when it is unreachable. The
  `videre-contract` workflow checks its `/openapi.json` daily against the
  fields `navigators/videre.py` reads (`python scripts/check_videre_contract.py`)

## Troubleshooting

### Publisher not collecting data
- Ensure Python 3.11+ is installed
- Check all dependencies are installed: `pip install -r requirements-dev.txt`
- Check https://api.videreproject.com/events?limit=1 responds, and run
  `python scripts/check_videre_contract.py` to see whether a field the client
  reads changed

## License

MIT License - see LICENSE file for details

## Acknowledgments

- **Videre Project**: For the community MTGO data API this repo consumes
- **Badaro**: For the MTGOFormatData archetype taxonomy behind the Videre
  API's classifications

## Support

- **Issues**: [GitHub Issues](https://github.com/Pedrogush/MTGO_Tools_Data/issues)
- **Discussions**: Use GitHub Discussions for questions and ideas

---

**Version**: 0.2
**Author**: yochi (pedrogush@gmail.com)
**Status**: Active Development
