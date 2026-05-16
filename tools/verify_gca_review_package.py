#!/usr/bin/env python3
"""Verify a locally exported GCA review package digest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.gca_member_backend import verify_package_digest  # noqa: E402


def load_package(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Could not read package: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Package must be valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("Package JSON must be an object")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a GCA review package packageDigestSha256 value.")
    parser.add_argument("package", type=Path, help="Path to a GCA review package JSON file.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = verify_package_digest(load_package(args.package))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
