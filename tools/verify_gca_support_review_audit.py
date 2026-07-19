#!/usr/bin/env python3
"""Verify the local GCA support-review JSONL continuity chain."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.gca_member_backend import JsonlLedgerStore, verify_support_review_audit  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the SHA-256 continuity chain for the local support_reviews JSONL ledger.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / ".gca_access_data",
        help="Path to the local GCA JSONL ledger directory. Default: .gca_access_data/",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.data_dir.exists() or not args.data_dir.is_dir():
        raise SystemExit(f"Data directory does not exist or is not a directory: {args.data_dir}")
    result = verify_support_review_audit(JsonlLedgerStore(args.data_dir).read_all("support_reviews"))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
