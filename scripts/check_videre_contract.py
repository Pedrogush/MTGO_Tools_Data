"""Fail if the live Videre API spec drops or retypes a field the publisher reads.

    python scripts/check_videre_contract.py [--spec-url URL | --spec-file PATH]

Exit codes: 0 contract holds, 1 contract broken, 2 spec could not be fetched
or parsed. The pinned fields live in ``navigators/videre_contract.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from navigators.videre_contract import check_openapi  # noqa: E402
from utils.constants import VIDERE_API_BASE_URL, VIDERE_REQUEST_TIMEOUT_SECONDS  # noqa: E402

USER_AGENT = "MTGO_Tools_Data/0.2 (+https://github.com/Pedrogush/MTGO_Tools_Data)"


def _load_spec(args: argparse.Namespace) -> dict:
    if args.spec_file:
        return json.loads(Path(args.spec_file).read_text(encoding="utf-8"))
    from curl_cffi import requests

    response = requests.get(
        args.spec_url,
        timeout=VIDERE_REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.json()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--spec-url", default=f"{VIDERE_API_BASE_URL}/openapi.json")
    source.add_argument("--spec-file")
    args = parser.parse_args(argv)

    where = args.spec_file or args.spec_url
    try:
        spec = _load_spec(args)
    except Exception as exc:  # noqa: BLE001
        print(f"::error::Could not load the Videre OpenAPI spec from {where}: {exc}")
        return 2

    version = spec.get("info", {}).get("version", "?")
    problems = check_openapi(spec)
    if problems:
        print(f"::error::Videre API contract broken ({where}, spec version {version}):")
        for problem in problems:
            print(f"  - {problem}")
        print(
            "The publisher's Videre client (navigators/videre.py) reads these fields; "
            "update it and navigators/videre_contract.py together."
        )
        return 1
    print(f"Videre API contract holds ({where}, spec version {version}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
