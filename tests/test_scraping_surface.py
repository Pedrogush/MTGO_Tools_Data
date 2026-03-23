from __future__ import annotations

import importlib
import sys


def test_services_mtgo_background_service_imports_without_wx() -> None:
    sys.modules.pop("services", None)
    sys.modules.pop("services.mtgo_background_service", None)
    sys.modules.pop("wx", None)

    module = importlib.import_module("services.mtgo_background_service")

    assert module.parse_mtgo_deck is not None
    assert "wx" not in sys.modules


def test_scraping_surface_imports_without_wx() -> None:
    sys.modules.pop("scraping", None)
    sys.modules.pop("scraping.mtggoldfish", None)
    sys.modules.pop("scraping.mtgo", None)
    sys.modules.pop("scraping.metagame", None)
    sys.modules.pop("wx", None)

    module = importlib.import_module("scraping")

    assert module.fetch_archetypes is not None
    assert module.fetch_event_index is not None
    assert module.ScrapingMetagameRepository is not None
    assert "wx" not in sys.modules
