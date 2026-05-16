#!/usr/bin/env python3
"""Export a local GCA reviewer evidence package from JSONL ledgers.

This is an offline operator helper. It reads local ``.gca_access_data/``
records and never connects to a wallet, asks for signatures, sends tokens,
or calls a network RPC endpoint.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.gca_member_backend import GcaMemberBackend, JsonlLedgerStore, verify_package_digest  # noqa: E402


class OfflineOnlyBalanceReader:
    """Guard against accidental network or wallet work during package export."""

    def get_balance_units(self, wallet: str) -> int:
        raise RuntimeError("offline review package export must not read wallet balances")

    def get_transfer_evidence(self, tx_hash: str, recipient_wallet: str, source_wallet: str = "") -> dict[str, Any]:
        raise RuntimeError("offline review package export must not read transaction receipts")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a GCA local review package from .gca_access_data JSONL ledgers.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / ".gca_access_data",
        help="Path to local GCA JSONL ledger directory. Default: .gca_access_data/",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path. If omitted, the package JSON is written to stdout.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum latest records per ledger to include. Default: 100.",
    )
    parser.add_argument(
        "--redact",
        choices=("none", "public"),
        default="none",
        help="Use 'public' before sharing externally. Default: none.",
    )
    return parser.parse_args(argv)


def export_package(data_dir: Path, limit: int, redacted: bool) -> dict[str, Any]:
    if limit < 1 or limit > 200:
        raise SystemExit("limit must be between 1 and 200")
    if not data_dir.exists():
        raise SystemExit(f"Data directory does not exist: {data_dir}")
    if not data_dir.is_dir():
        raise SystemExit(f"Data directory is not a directory: {data_dir}")

    backend = GcaMemberBackend(
        store=JsonlLedgerStore(data_dir),
        balance_reader=OfflineOnlyBalanceReader(),
    )
    package = backend.review_package(limit=limit, redacted=redacted)
    verification = verify_package_digest(package)
    if not verification["ok"]:
        raise SystemExit(f"Generated package digest verification failed: {verification['status']}")
    return package


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    package = export_package(args.data_dir, args.limit, args.redact == "public")
    if args.output:
        write_json(args.output, package)
        result = {
            "ok": True,
            "output": str(args.output),
            "redactedForExternalSharing": package["redactedForExternalSharing"],
            "packageDigestSha256": package["packageDigestSha256"],
            "recordManifest": package["recordManifest"],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(package, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
