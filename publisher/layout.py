"""Repository data layout helpers for published scrape artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from publisher.contracts import build_latest_manifest, validate_latest_manifest
from utils.atomic_io import atomic_write_json

DEFAULT_OUTPUT_ROOT = Path("data")
DEFAULT_RETENTION_DAYS = 7
DEFAULT_MAX_STALE_HOURS = 24


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def timestamp_token(timestamp: str) -> str:
    return timestamp.replace(":", "-")


def hourly_snapshot_dir(output_root: Path, generated_at: str) -> Path:
    return output_root / "hourly" / timestamp_token(generated_at)


def daily_snapshot_dir(output_root: Path, generated_for_day: str) -> Path:
    return output_root / "daily" / generated_for_day


def load_latest_manifest(
    output_root: Path, *, generated_at: str, retention_days: int
) -> dict[str, Any]:
    manifest_path = output_root / "latest" / "latest.json"
    if not manifest_path.exists():
        return build_latest_manifest(generated_at=generated_at, retention_days=retention_days)
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    validated = validate_latest_manifest(manifest)
    validated["generated_at"] = generated_at
    validated["retention_days"] = retention_days
    return validated


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload, indent=2)


def relative_posix_path(path: Path, output_root: Path) -> str:
    return path.relative_to(output_root).as_posix()


def update_latest_manifest(
    output_root: Path,
    *,
    generated_at: str,
    retention_days: int,
    category: str,
    discriminator: dict[str, str],
    relative_path: str,
) -> Path:
    manifest = load_latest_manifest(
        output_root,
        generated_at=generated_at,
        retention_days=retention_days,
    )
    entries = manifest["latest"][category]
    filtered_entries = [
        entry for entry in entries if any(entry.get(k) != v for k, v in discriminator.items())
    ]
    filtered_entries.append({**discriminator, "path": relative_path, "updated_at": generated_at})
    filtered_entries.sort(
        key=lambda entry: (
            entry.get("format", ""),
            entry.get("archetype", ""),
            entry.get("path", ""),
        )
    )
    manifest["latest"][category] = filtered_entries
    manifest_path = output_root / "latest" / "latest.json"
    write_json(manifest_path, manifest)
    return manifest_path
