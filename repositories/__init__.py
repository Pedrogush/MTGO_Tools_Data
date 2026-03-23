"""Repositories package for scrape/publish data access."""

from repositories.metagame_repository import MetagameRepository, get_metagame_repository

__all__ = [
    "MetagameRepository",
    "get_metagame_repository",
]
