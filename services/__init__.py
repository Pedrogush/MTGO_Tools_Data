"""
Services package facade.

Keep package import headless-safe by avoiding eager imports of modules that pull
in wx-only dependencies. Callers that need a specific service can import its
module directly or access the attribute lazily through this package.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "CollectionService",
    "CollectionStatus",
    "DeckResearchService",
    "DeckService",
    "ImageService",
    "SearchService",
    "StateService",
    "StoreService",
    "ZoneUpdateResult",
    "get_collection_service",
    "get_deck_research_service",
    "get_deck_service",
    "get_image_service",
    "get_search_service",
    "get_state_service",
    "get_store_service",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "CollectionService": ("services.collection_service", "CollectionService"),
    "CollectionStatus": ("services.collection_service", "CollectionStatus"),
    "DeckResearchService": ("services.deck_research_service", "DeckResearchService"),
    "DeckService": ("services.deck_service", "DeckService"),
    "ImageService": ("services.image_service", "ImageService"),
    "SearchService": ("services.search_service", "SearchService"),
    "StateService": ("services.state_service", "StateService"),
    "StoreService": ("services.store_service", "StoreService"),
    "ZoneUpdateResult": ("services.deck_service", "ZoneUpdateResult"),
    "get_collection_service": ("services.collection_service", "get_collection_service"),
    "get_deck_service": ("services.deck_service", "get_deck_service"),
    "get_image_service": ("services.image_service", "get_image_service"),
    "get_search_service": ("services.search_service", "get_search_service"),
    "get_store_service": ("services.store_service", "get_store_service"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


def get_deck_research_service() -> Any:
    return __getattr__("DeckResearchService")()


def get_state_service() -> Any:
    return __getattr__("StateService")()
