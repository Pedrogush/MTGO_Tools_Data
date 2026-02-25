from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from loguru import logger

P = ParamSpec("P")
R = TypeVar("R")


def timed(func: Callable[P, R]) -> Callable[P, R]:
    """Log execution time of *func* at DEBUG level.

    Overhead per call: two ``time.perf_counter()`` syscalls plus one
    ``logger.debug`` guard check (~80–150 ns total). Suitable for methods
    that are called at most a few times per user action; do NOT apply to
    sub-millisecond callbacks firing at 60 FPS.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        logger.debug("{} took {:.4f}s", func.__qualname__, time.perf_counter() - t0)
        return result

    return wrapper
