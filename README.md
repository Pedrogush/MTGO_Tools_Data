# MTGO Scrapes Repository

Headless MTGO and MTGGoldfish scraping surface for scheduled publishing.

![Version](https://img.shields.io/badge/version-0.2-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Platform](https://img.shields.io/badge/platform-headless-lightgrey)
![License](https://img.shields.io/badge/license-MIT-orange)

This repository is being reduced from a desktop application clone to a scrape
publisher. The supported surface is the scraper and publisher path only.

## Screenshots

*(Coming soon)*

## Installation

### Quick Start

1. **Prerequisites**:
   - Python 3.11 or newer

2. **Clone the repository**:
   ```bash
   git clone https://github.com/Pedrogush/MTGO_Scrapes_Repository.git
   cd MTGO_Scrapes_Repository
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Run the scraper tests**:
   ```bash
   python -m pytest tests/test_mtggoldfish.py tests/test_metagame_repository.py tests/test_metagame_stats.py tests/test_scraping_surface.py
   ```

## Architecture

See [docs/scraping_surface.md](docs/scraping_surface.md) for the current scrape-only boundary.

## Published Data

Publisher outputs are written under `data/`:

- `data/latest/` for stable consumer-facing pointers.
- `data/latest/client-bundle.tar.gz` for single-request client bootstrap. The
  bundle contains the stable `latest/` deck and metagame snapshots plus the
  referenced `archive/deck-texts/` blobs.
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
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-archetypes --format Modern
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-decks --format Modern --archetype "Temur Rhinos" --days 7
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-deck-texts --format Modern --archetype "Temur Rhinos" --days 7
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-metagame --format Modern --day 2026-03-23
python -m publisher.retention --output-root data --timestamp 2026-03-23T18:00:00Z --retention-days 7
```

Outputs are written into repository-managed staging paths under `data/latest/`,
`data/hourly/`, `data/daily/`, and `data/archive/`.
Each command also writes a run manifest under `data/latest/runs/`. Single-format
runs use `data/latest/runs/<command>-<format>.json`; multi-format runs keep
`data/latest/runs/<command>.json`. These manifests store per-scope statuses
(`success`, `skipped`, `stale-fallback`, `hard-failure`) and the command only
returns a non-zero exit code when freshness guarantees are violated.

## Publishing Schedules

See [docs/publishing_workflows.md](docs/publishing_workflows.md) for the exact
workflow behavior. In short:

- Hourly publishing runs every two hours at minute `15`, fans out into one job
  per format, uploads per-format artifacts, then commits the merged result once
  after all format jobs finish. It writes deck metadata plus deck text blobs for
  `Modern`, `Standard`, `Pioneer`, `Legacy`, `Vintage`, and `Pauper`.
- Daily metagame publishing runs at `02:45` UTC, which is `23:45` in
  `America/Sao_Paulo`, also as one job per format.
- Each format job has its own concurrency key, but only the final merge job
  pushes when `data/` changed.

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
magic_online_metagame_crawler/
├── scraping/               # Headless scrape facade
├── services/               # MTGO event processing
├── repositories/           # Metagame repository
├── navigators/             # External API integrations
│   ├── mtggoldfish.py      # MTGGoldfish scraper
│   └── mtgo_decklists.py   # MTGO.com parser
├── utils/                  # Utility modules
│   ├── archetype_classifier.py
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

- **Metagame Data**: [MTGGoldfish](https://www.mtggoldfish.com/)
- **Card Data**: [Scryfall API](https://scryfall.com/docs/api)
- **Card Images**: Scryfall bulk data
- **MTGO Data**: [MTGOSDK](https://github.com/videre-project/MTGOSDK)

## Known Limitations

- Windows only (due to wxPython and MTGO dependencies)
- MTGO Bridge requires Magic Online to be installed
- Collection import requires MTGO to be running
- Some features require internet connection for metagame data

## Troubleshooting

### Application won't start
- Ensure Python 3.11+ is installed
- Check all dependencies are installed: `pip install -r requirements-dev.txt`
- Verify wxPython is properly installed for Windows

### Card images not loading
- Run `python -m scripts.fetch_mana_assets` to download mana symbols
- Check internet connection for Scryfall API access
- Use "Download Missing Images" from the Collection menu

### MTGO Bridge not working
- Ensure .NET 9.0 SDK is installed
- Build the bridge: `cd dotnet/MTGOBridge && dotnet build`
- MTGO must be running when using the bridge

### Tests failing on Windows
- Ensure pytest is installed
- Some UI tests require a display (run locally, not over SSH)

## License

MIT License - see LICENSE file for details

## Acknowledgments

- **MTGOSDK**: For providing MTGO integration capabilities
- **Scryfall**: For comprehensive card data and images
- **MTGGoldfish**: For metagame statistics and decklists
- **wxPython**: For the GUI framework

## Support

- **Issues**: [GitHub Issues](https://github.com/Pedrogush/MTGO_Tools/issues)
- **Discussions**: Use GitHub Discussions for questions and ideas

---

**Version**: 0.2
**Author**: yochi (pedrogush@gmail.com)
**Status**: Active Development
