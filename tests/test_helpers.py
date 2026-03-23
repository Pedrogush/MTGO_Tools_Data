"""Test helper utilities for managing global state in tests.

This module provides utilities for resetting global service and repository
instances to ensure test isolation and prevent state leakage between tests.
"""

import sys
from pathlib import Path

# Add parent directory to sys.path to enable imports from repositories and services
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))


# ruff: noqa: E402
def _optional_reset(module_path: str, attr_name: str):
    """Dynamically import a reset function, falling back to a no-op."""
    try:
        module = __import__(module_path, fromlist=[attr_name])
        return getattr(module, attr_name)
    except Exception:  # pragma: no cover - used in CI without optional deps

        def _noop(*_args, **_kwargs):
            return None

        return _noop


reset_metagame_repository = _optional_reset(
    "repositories.metagame_repository", "reset_metagame_repository"
)


def reset_all_globals() -> None:
    """Reset all global service and repository instances.

    This is the recommended function to call in test teardown or setup
    to ensure complete isolation between tests.
    """
    reset_metagame_repository()
