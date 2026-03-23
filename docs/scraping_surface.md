# Scraping Surface

This repository started as a desktop application clone, but the scheduled
publisher only needs a headless scrape surface.

## Step 0 Boundary

Keep these modules in the scrape/publish path:

- `navigators/mtggoldfish.py`
- `navigators/mtgo_decklists.py`
- `repositories/metagame_repository.py`
- `services/mtgo_background_service.py`
- `utils/metagame_stats.py`
- `utils/archetype_classifier.py`
- `utils/deck_text_cache.py`
- `utils/atomic_io.py`
- `utils/json_io.py`
- `utils/constants/`
- `scraping/`

Treat these areas as desktop-only and keep them out of supported scrape entrypoints:

- `main.py`
- `controllers/`
- `widgets/`
- `utils/ui_helpers.py`
- `utils/stylize.py`
- `utils/mana_icon_factory.py`
- `utils/mana_resources.py`
- `tests/ui/`

## Headless Entry Surface

Use the `scraping/` package for scrape-only workflows:

- `scraping.mtggoldfish`
- `scraping.mtgo`
- `scraping.metagame`

The `scraping` package is intentionally small and must remain importable without
`wx`.

## Current Isolation Work

- `services/__init__.py` is now lazy so `services.mtgo_background_service` can
  be imported without loading UI-bound service modules.
- `tests/test_scraping_surface.py` verifies that the scrape surface imports
  without `wx`.
- `services/mtgo_background_service.py` now has a working Python 3.10 UTC
  fallback, which is required for Linux headless test runs.
