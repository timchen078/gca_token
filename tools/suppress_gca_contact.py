#!/usr/bin/env python3
"""Add a GCA email contact to the local suppression list.

The suppression list is an ignored local JSONL file used by contact export
tools to exclude emails from internal and public-redacted outreach CSV files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.export_gca_email_contacts import DEFAULT_SUPPRESSION_FILE, email_sha256  # noqa: E402
from tools.gca_member_backend import BackendError, iso_now, normalize_email, stable_id  # noqa: E402


def build_suppression_record(email: str, reason: str, source: str, created_at: str) -> dict[str, str | bool]:
    normalized_email = normalize_email(email)
    return {
        "suppressionId": stable_id("gca_suppression", normalized_email, created_at),
        "createdAt": created_at,
        "email": normalized_email,
        "emailSha256": email_sha256(normalized_email),
        "reason": reason.strip()[:160] or "operator_suppression",
        "source": source.strip()[:120] or "operator",
        "contactSuppressed": True,
    }


def append_suppression(path: Path, record: dict[str, str | bool]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add an email to the local GCA contact suppression list.")
    parser.add_argument("--email", required=True, help="Email address to suppress from future contact CSV exports.")
    parser.add_argument("--reason", default="operator_suppression", help="Suppression reason for local operator review.")
    parser.add_argument("--source", default="operator", help="Source of the suppression request.")
    parser.add_argument("--suppression-file", type=Path, default=DEFAULT_SUPPRESSION_FILE, help="Suppression JSONL path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        record = build_suppression_record(
            email=args.email,
            reason=args.reason,
            source=args.source,
            created_at=iso_now(),
        )
        append_suppression(args.suppression_file, record)
    except BackendError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps({
        "ok": True,
        "suppressionFile": str(args.suppression_file),
        "suppressionId": record["suppressionId"],
        "email": record["email"],
        "emailSha256": record["emailSha256"],
        "contactSuppressed": True,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
