"""Headless metagame repository facade for scrape-only workflows."""

from __future__ import annotations

from repositories.metagame_repository import MetagameRepository


class ScrapingMetagameRepository(MetagameRepository):
    """Named headless facade for scrape/publish entrypoints."""
