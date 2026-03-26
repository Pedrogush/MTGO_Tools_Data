"""Build a deterministic single-file client bundle from published data."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tarfile
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTPUT_ROOT = Path("data")
DEFAULT_BUNDLE_RELATIVE_PATH = Path("latest") / "client-bundle.tar.gz"


@dataclass(frozen=True)
class BundleSource:
    category: str
    path: Path
    arcname: str


def _sorted_glob(root: Path, pattern: str) -> list[Path]:
    return sorted(
        (path for path in root.glob(pattern) if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def collect_bundle_sources(output_root: Path) -> list[BundleSource]:
    sources: list[BundleSource] = []

    latest_manifest = output_root / "latest" / "latest.json"
    if latest_manifest.exists():
        sources.append(
            BundleSource(
                category="latest_manifest",
                path=latest_manifest,
                arcname=latest_manifest.relative_to(output_root).as_posix(),
            )
        )

    grouped_patterns = (
        ("archetype_lists", "latest/archetypes/*.json"),
        ("archetype_decks", "latest/decks/**/*.json"),
        ("metagame_daily", "latest/metagame/*.json"),
        ("deck_text_blobs", "archive/deck-texts/**/*.json"),
    )
    for category, pattern in grouped_patterns:
        for path in _sorted_glob(output_root, pattern):
            sources.append(
                BundleSource(
                    category=category,
                    path=path,
                    arcname=path.relative_to(output_root).as_posix(),
                )
            )

    return sources


def _sha256_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_client_bundle(
    output_root: Path,
    *,
    bundle_path: Path | None = None,
    compresslevel: int = 9,
) -> dict[str, object]:
    sources = collect_bundle_sources(output_root)
    if not sources:
        raise FileNotFoundError(f"No published files were found beneath {output_root}")

    destination = bundle_path or (output_root / DEFAULT_BUNDLE_RELATIVE_PATH)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        with temp_path.open("wb") as raw_fh:
            with gzip.GzipFile(
                fileobj=raw_fh,
                mode="wb",
                filename="",
                compresslevel=compresslevel,
                mtime=0,
            ) as gzip_fh:
                with tarfile.open(fileobj=gzip_fh, mode="w", format=tarfile.PAX_FORMAT) as tar_fh:
                    for source in sources:
                        tar_info = tarfile.TarInfo(name=source.arcname)
                        tar_info.size = source.path.stat().st_size
                        tar_info.mtime = 0
                        tar_info.mode = 0o644
                        tar_info.uid = 0
                        tar_info.gid = 0
                        tar_info.uname = ""
                        tar_info.gname = ""
                        with source.path.open("rb") as source_fh:
                            tar_fh.addfile(tar_info, source_fh)

        os.replace(temp_path, destination)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    counts = Counter(source.category for source in sources)
    return {
        "bundle_path": destination.as_posix(),
        "file_count": len(sources),
        "source_bytes": sum(source.path.stat().st_size for source in sources),
        "compressed_bytes": destination.stat().st_size,
        "sha256": _sha256_digest(destination),
        "counts": dict(sorted(counts.items())),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a single-file client data bundle")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--bundle-path", help="Override the output bundle path")
    parser.add_argument("--compresslevel", type=int, default=9)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary = build_client_bundle(
        Path(args.output_root),
        bundle_path=Path(args.bundle_path) if args.bundle_path else None,
        compresslevel=args.compresslevel,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
