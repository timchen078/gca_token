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

from tools.gca_member_backend import (  # noqa: E402
    JsonlLedgerStore,
    verify_support_review_audit,
    verify_support_review_checkpoint,
)


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
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help="Optional independently retained checkpoint JSON to compare with the current ledger.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.data_dir.exists() or not args.data_dir.is_dir():
        raise SystemExit(f"Data directory does not exist or is not a directory: {args.data_dir}")
    records = JsonlLedgerStore(args.data_dir).read_all("support_reviews")
    if args.checkpoint:
        checkpoint_path = args.checkpoint.expanduser()
        if not checkpoint_path.exists() or not checkpoint_path.is_file():
            raise SystemExit(f"Checkpoint file does not exist or is not a file: {checkpoint_path}")
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Checkpoint file must contain valid JSON: {checkpoint_path}") from exc
        result = verify_support_review_checkpoint(records, checkpoint)
    else:
        result = verify_support_review_audit(records)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
