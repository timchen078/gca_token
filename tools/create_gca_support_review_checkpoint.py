#!/usr/bin/env python3
"""Export an unsigned GCA support-review chain-head checkpoint receipt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.gca_member_backend import (  # noqa: E402
    BackendError,
    JsonlLedgerStore,
    create_support_review_checkpoint,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export an unsigned support-review chain-head checkpoint. Store the output "
            "outside the ledger directory so it can be used for later comparison."
        ),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / ".gca_access_data",
        help="Path to the local GCA JSONL ledger directory. Default: .gca_access_data/",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Receipt output path. It must be outside --data-dir.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing output file. Existing receipts are preserved by default.",
    )
    return parser.parse_args(argv)


def is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data_dir = args.data_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not data_dir.exists() or not data_dir.is_dir():
        raise SystemExit(f"Data directory does not exist or is not a directory: {data_dir}")
    if is_within(output, data_dir):
        raise SystemExit("Checkpoint output must be stored outside the ledger data directory.")
    if output.exists() and not args.force:
        raise SystemExit(f"Checkpoint output already exists; use --force to replace it: {output}")

    try:
        checkpoint = create_support_review_checkpoint(
            JsonlLedgerStore(data_dir).read_all("support_reviews"),
        )
    except BackendError as exc:
        raise SystemExit(str(exc)) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(checkpoint, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(checkpoint, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
