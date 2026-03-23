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
See [docs/published_data.md](docs/published_data.md) for the publisher artifact
contract and repository data layout.

## Publisher CLI

The headless publisher entrypoint is `python -m publisher.runner`.

```bash
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-archetypes --format Modern
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-decks --format Modern --archetype "Temur Rhinos" --days 7
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-deck-texts --format Modern --archetype "Temur Rhinos" --days 7
python -m publisher.runner --output-root data --timestamp 2026-03-23T12:00:00Z scrape-metagame --format Modern --day 2026-03-23
```

Outputs are written into repository-managed staging paths under `data/latest/`,
`data/hourly/`, `data/daily/`, and `data/archive/`.
Each command also writes `data/latest/runs/<command>.json`, with per-scope
statuses (`success`, `skipped`, `stale-fallback`, `hard-failure`) and returns a
non-zero exit code only when freshness guarantees are violated.

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
