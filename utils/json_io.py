"""Fast JSON I/O utilities backed by msgspec.

Drop-in replacements for stdlib ``json.load`` / ``json.loads`` that use
msgspec's C-level parser.  Pre-instantiated :class:`msgspec.json.Decoder`
objects are reused across calls so there is no per-call overhead from
building a decoder.

Usage::

    from utils.json_io import fast_load, fast_decode

    # Untyped (produces regular Python dicts/lists)
    data = fast_load(some_path)
    data = fast_decode(raw_bytes_or_str)

    # Typed (msgspec validates structure against the given type)
    from typing import Any
    import msgspec

    class MyStruct(msgspec.Struct):
        name: str
        value: int

    obj = fast_load(some_path, type=MyStruct)
    obj = fast_decode(raw_bytes, type=list[MyStruct])
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import msgspec
import msgspec.json

__all__ = ["fast_load", "fast_decode"]

T = TypeVar("T")

# Re-usable decoder for the common ``Any`` case (avoids rebuilding every call)
_decoder_any: msgspec.json.Decoder[Any] = msgspec.json.Decoder(Any)


def fast_load(path: Path, *, type: type = Any) -> Any:  # noqa: A002
    """Read *path* as bytes and decode the JSON content.

    Parameters
    ----------
    path:
        File to read.
    type:
        Optional msgspec type annotation.  When omitted (or ``Any``) the
        result is plain Python built-ins (``dict``, ``list``, …).  Pass a
        :class:`msgspec.Struct` subclass or a composite type such as
        ``list[MyStruct]`` to get typed, validated output.

    Returns
    -------
    Any
        Decoded JSON value.
    """
    data = path.read_bytes()
    return fast_decode(data, type=type)


def fast_decode(data: bytes | str | bytearray, *, type: type = Any) -> Any:  # noqa: A002
    """Decode *data* as JSON.

    Parameters
    ----------
    data:
        Raw JSON bytes, bytearray, or UTF-8 string.
    type:
        Optional msgspec type annotation (see :func:`fast_load`).

    Returns
    -------
    Any
        Decoded JSON value.
    """
    if isinstance(data, str):
        data = data.encode()
    if type is Any:
        return _decoder_any.decode(data)
    return msgspec.json.decode(data, type=type)
