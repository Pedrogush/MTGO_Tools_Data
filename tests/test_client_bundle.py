import hashlib
import importlib.util
import json
import sys
import tarfile
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "publisher" / "client_bundle.py"
MODULE_SPEC = importlib.util.spec_from_file_location("publisher_client_bundle", MODULE_PATH)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
client_bundle = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = client_bundle
MODULE_SPEC.loader.exec_module(client_bundle)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_client_bundle_includes_expected_paths(tmp_path):
    _write_json(tmp_path / "latest" / "latest.json", {"kind": "latest_manifest"})
    _write_json(tmp_path / "latest" / "archetypes" / "modern.json", {"kind": "archetype_list"})
    _write_json(
        tmp_path / "latest" / "decks" / "modern" / "temur-rhinos.json",
        {"kind": "archetype_decks"},
    )
    _write_json(tmp_path / "latest" / "metagame" / "modern.json", {"kind": "metagame_daily"})
    _write_json(
        tmp_path / "archive" / "deck-texts" / "modern" / "123.json",
        {"kind": "deck_text_blob"},
    )

    summary = client_bundle.build_client_bundle(tmp_path)
    bundle_path = tmp_path / "latest" / "client-bundle.tar.gz"

    assert summary["bundle_path"] == bundle_path.as_posix()
    assert summary["file_count"] == 5
    assert summary["counts"] == {
        "archetype_decks": 1,
        "archetype_lists": 1,
        "deck_text_blobs": 1,
        "latest_manifest": 1,
        "metagame_daily": 1,
    }

    with tarfile.open(bundle_path, "r:gz") as tar_fh:
        names = tar_fh.getnames()
        assert names == [
            "latest/latest.json",
            "latest/archetypes/modern.json",
            "latest/decks/modern/temur-rhinos.json",
            "latest/metagame/modern.json",
            "archive/deck-texts/modern/123.json",
        ]
        payload = json.loads(
            tar_fh.extractfile("archive/deck-texts/modern/123.json").read().decode("utf-8")
        )
        assert payload["kind"] == "deck_text_blob"


def test_build_client_bundle_is_deterministic(tmp_path):
    _write_json(tmp_path / "latest" / "latest.json", {"kind": "latest_manifest"})
    _write_json(
        tmp_path / "archive" / "deck-texts" / "modern" / "123.json",
        {"kind": "deck_text_blob", "deck_text": "4 Lightning Bolt"},
    )
    _write_json(
        tmp_path / "latest" / "metagame" / "modern.json",
        {"kind": "metagame_daily", "stats": [{"archetype": "Temur Rhinos"}]},
    )

    first = client_bundle.build_client_bundle(tmp_path)
    digest_one = _sha256(tmp_path / "latest" / "client-bundle.tar.gz")

    second = client_bundle.build_client_bundle(tmp_path)
    digest_two = _sha256(tmp_path / "latest" / "client-bundle.tar.gz")

    assert first["sha256"] == second["sha256"] == digest_one == digest_two
