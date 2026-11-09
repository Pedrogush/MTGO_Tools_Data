"""The parts of the Videre API this repo depends on, and checks against them.

``navigators/videre.py`` reads a handful of fields from three list endpoints.
They are pinned here once, so that

- ``tests/test_videre_contract.py`` can check the checked-in response fixtures
  (offline, in the normal suite) and the parser against them, and
- ``scripts/check_videre_contract.py`` can compare them against the live
  ``/openapi.json`` and fail loudly when one disappears or changes type.

Types use OpenAPI's vocabulary. A field listed with several types accepts any
of them (``quantity`` is declared ``number`` but we only ever ``int()`` it).
Nullability is not pinned: the parser already tolerates nulls everywhere it
reads, except where noted in ``NON_NULLABLE``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

# path -> query parameters the client sends
REQUIRED_QUERY_PARAMETERS: dict[str, set[str]] = {
    "/events": {"format", "min_date", "max_date", "limit", "offset"},
    "/decks": {"event_id", "limit", "offset"},
    "/standings": {"event_id", "limit", "offset"},
}

# path -> {field: accepted OpenAPI types} for each row in ``data``
REQUIRED_ROW_FIELDS: dict[str, dict[str, set[str]]] = {
    "/events": {
        "id": {"integer"},
        "name": {"string"},
        "date": {"string"},
        "kind": {"string"},
    },
    "/decks": {
        "id": {"integer"},
        "player": {"string"},
        "mainboard": {"array"},
        "sideboard": {"array"},
        "archetype": {"string"},
        "archetype_id": {"integer"},
    },
    "/standings": {
        "player": {"string"},
        "record": {"string"},
    },
}

# Fields of each mainboard/sideboard entry on a /decks row.
REQUIRED_CARD_ENTRY_FIELDS: dict[str, set[str]] = {
    "name": {"string"},
    "quantity": {"integer", "number"},
}

# Pagination envelope (ListResponse.meta) and the error body the client reads
# to tell "no decklists imported yet" (HTTP 400) apart from a real failure.
REQUIRED_META_FIELDS: dict[str, set[str]] = {
    "has_more": {"boolean"},
    "next_offset": {"integer"},
}
REQUIRED_ERROR_FIELDS: dict[str, set[str]] = {"message": {"string"}}

# Row fields the parser cannot survive as null.
NON_NULLABLE: dict[str, set[str]] = {"/events": {"id"}, "/decks": {"id"}}

_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "integer": (int,),
    "number": (int, float),
    "string": (str,),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


# --------------------------------------------------------------------------
# Live spec checks
# --------------------------------------------------------------------------


def _resolve(spec: Mapping[str, Any], schema: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve ``$ref`` and flatten ``allOf`` into one object schema."""
    if "$ref" in schema:
        node: Any = spec
        for part in str(schema["$ref"]).removeprefix("#/").split("/"):
            node = node[part]
        return _resolve(spec, node)
    if "allOf" in schema:
        merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for part in schema["allOf"]:
            resolved = _resolve(spec, part)
            merged["properties"].update(resolved.get("properties", {}))
            merged["required"].extend(resolved.get("required", []))
        return merged
    return dict(schema)


def _type_problems(
    where: str,
    properties: Mapping[str, Any],
    expected: Mapping[str, set[str]],
    spec: Mapping[str, Any],
) -> list[str]:
    problems = []
    for field, accepted in expected.items():
        if field not in properties:
            problems.append(f"{where}: field '{field}' is missing")
            continue
        declared = _resolve(spec, properties[field]).get("type")
        if declared not in accepted:
            problems.append(
                f"{where}: field '{field}' is {declared!r}, expected one of {sorted(accepted)}"
            )
    return problems


def check_openapi(spec: Mapping[str, Any]) -> list[str]:
    """Return human-readable problems; an empty list means the contract holds."""
    problems: list[str] = []
    paths = spec.get("paths", {})
    for path, fields in REQUIRED_ROW_FIELDS.items():
        operation = paths.get(path, {}).get("get")
        if operation is None:
            problems.append(f"GET {path} is missing")
            continue

        params = {param.get("name") for param in operation.get("parameters", [])}
        for name in sorted(REQUIRED_QUERY_PARAMETERS[path] - params):
            problems.append(f"GET {path}: query parameter '{name}' is missing")

        try:
            body = operation["responses"]["200"]["content"]["application/json"]["schema"]
        except KeyError:
            problems.append(f"GET {path}: 200 application/json response schema is missing")
            continue
        envelope = _resolve(spec, body)
        envelope_props = envelope.get("properties", {})
        meta = _resolve(spec, envelope_props.get("meta", {})).get("properties", {})
        problems += _type_problems(f"GET {path} meta", meta, REQUIRED_META_FIELDS, spec)

        data = _resolve(spec, envelope_props.get("data", {}))
        row = _resolve(spec, data.get("items", {}))
        row_props = row.get("properties", {})
        problems += _type_problems(f"GET {path} row", row_props, fields, spec)

        if path == "/decks":
            for board in ("mainboard", "sideboard"):
                if board not in row_props:
                    continue
                board_schema = _resolve(spec, row_props[board])
                entry = _resolve(spec, board_schema.get("items", {}))
                problems += _type_problems(
                    f"GET {path} {board}[]",
                    entry.get("properties", {}),
                    REQUIRED_CARD_ENTRY_FIELDS,
                    spec,
                )

        error_ref = paths.get(path, {}).get("get", {}).get("responses", {}).get("400")
        if error_ref is not None:
            error_response = _resolve(spec, error_ref)
            try:
                error_schema = error_response["content"]["application/json"]["schema"]
            except KeyError:
                problems.append(f"GET {path}: 400 response schema is missing")
            else:
                problems += _type_problems(
                    f"GET {path} 400 body",
                    _resolve(spec, error_schema).get("properties", {}),
                    REQUIRED_ERROR_FIELDS,
                    spec,
                )
    return problems


# --------------------------------------------------------------------------
# Response-row checks (used against fixtures)
# --------------------------------------------------------------------------


def _value_problems(where: str, row: Mapping[str, Any], expected: Mapping[str, set[str]]) -> list[str]:
    if not isinstance(row, Mapping):
        return [f"{where}: expected an object, got {type(row).__name__}"]
    problems = []
    for field, accepted in expected.items():
        if field not in row:
            problems.append(f"{where}: field '{field}' is missing")
            continue
        value = row[field]
        if value is None:
            continue
        python_types = tuple(t for name in accepted for t in _JSON_TYPES[name])
        if isinstance(value, bool) and "boolean" not in accepted:
            problems.append(f"{where}: field '{field}' is a boolean")
        elif not isinstance(value, python_types):
            problems.append(
                f"{where}: field '{field}' is {type(value).__name__}, expected {sorted(accepted)}"
            )
    return problems


def check_rows(path: str, rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """Check API response rows for ``path`` against the pinned fields."""
    problems: list[str] = []
    for index, row in enumerate(rows):
        where = f"{path} data[{index}]"
        problems += _value_problems(where, row, REQUIRED_ROW_FIELDS[path])
        for field in NON_NULLABLE.get(path, set()):
            if field in row and row[field] is None:
                problems.append(f"{where}: field '{field}' is null")
        if path == "/decks":
            for board in ("mainboard", "sideboard"):
                for entry_index, entry in enumerate(row.get(board) or []):
                    problems += _value_problems(
                        f"{where}.{board}[{entry_index}]", entry, REQUIRED_CARD_ENTRY_FIELDS
                    )
    return problems


def check_envelope(path: str, payload: Mapping[str, Any]) -> list[str]:
    """Check a full list response (envelope plus rows)."""
    problems = _value_problems(f"{path} meta", payload.get("meta", {}), REQUIRED_META_FIELDS)
    data = payload.get("data")
    if not isinstance(data, list):
        return [*problems, f"{path}: 'data' is not a list"]
    return problems + check_rows(path, data)
