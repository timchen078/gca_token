#!/usr/bin/env python3
"""Export local GCA email-registration ledger contacts to CSV.

This is an offline operator helper. It reads the local JSONL ledger generated
by ``tools/sync_cloudflare_email_registrations.py`` and never calls wallets,
RPC endpoints, or Cloudflare.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.gca_member_backend import JsonlLedgerStore, normalize_email  # noqa: E402


DEFAULT_DATA_DIR = ROOT / ".gca_access_data"
DEFAULT_OUTPUT = ROOT / ".gca_access_data" / "gca_email_contacts.csv"
DEFAULT_REDACTED_OUTPUT = ROOT / ".gca_access_data" / "gca_email_contacts_public_redacted.csv"


FULL_FIELDNAMES = [
    "email",
    "displayName",
    "language",
    "interests",
    "source",
    "status",
    "createdAt",
    "updatedAt",
    "emailRegistrationId",
    "importedFromCloudflare",
]

REDACTED_FIELDNAMES = [
    "emailSha256",
    "language",
    "interests",
    "source",
    "status",
    "createdAt",
    "updatedAt",
    "emailRegistrationId",
]


def email_sha256(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def latest_contact_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    latest_by_email: dict[str, dict[str, Any]] = {}
    skipped: list[dict[str, Any]] = []
    for record in records:
        try:
            email = normalize_email(str(record.get("email") or ""))
        except Exception as exc:  # noqa: BLE001 - produce operator-facing skip records
            skipped.append({
                "emailRegistrationId": record.get("emailRegistrationId", ""),
                "reason": f"invalid_email: {exc}",
            })
            continue
        if record.get("contactConsentAccepted") is not True:
            skipped.append({
                "emailRegistrationId": record.get("emailRegistrationId", ""),
                "email": email,
                "reason": "contact_consent_missing",
            })
            continue
        current = latest_by_email.get(email)
        if not current or str(record.get("updatedAt") or record.get("createdAt") or "") >= str(current.get("updatedAt") or current.get("createdAt") or ""):
            latest_by_email[email] = {**record, "email": email}
    return sorted(latest_by_email.values(), key=lambda item: str(item.get("email") or "")), skipped


def record_to_row(record: dict[str, Any], redacted: bool) -> dict[str, str]:
    interests = record.get("interests")
    if not isinstance(interests, list):
        interests = []
    common = {
        "language": str(record.get("language") or ""),
        "interests": ";".join(str(item).strip() for item in interests if str(item).strip()),
        "source": str(record.get("source") or ""),
        "status": str(record.get("status") or ""),
        "createdAt": str(record.get("createdAt") or ""),
        "updatedAt": str(record.get("updatedAt") or ""),
        "emailRegistrationId": str(record.get("emailRegistrationId") or ""),
    }
    email = str(record.get("email") or "").strip().lower()
    if redacted:
        return {
            "emailSha256": email_sha256(email),
            **common,
        }
    return {
        "email": email,
        "displayName": str(record.get("displayName") or ""),
        **common,
        "importedFromCloudflare": "true" if record.get("importedFromCloudflare") is True else "false",
    }


def build_contact_rows(records: list[dict[str, Any]], redacted: bool) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    contact_records, skipped = latest_contact_records(records)
    return [record_to_row(record, redacted) for record in contact_records], skipped


def write_csv(path: Path, rows: list[dict[str, str]], redacted: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = REDACTED_FIELDNAMES if redacted else FULL_FIELDNAMES
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export contact-consented GCA email registrations from local JSONL ledger to CSV.",
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Local JSONL ledger directory.")
    parser.add_argument("--output", type=Path, help="Output CSV path. Defaults to ignored .gca_access_data output.")
    parser.add_argument("--redact", choices=("none", "public"), default="none", help="Use public before external sharing.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    redacted = args.redact == "public"
    output = args.output or (DEFAULT_REDACTED_OUTPUT if redacted else DEFAULT_OUTPUT)
    store = JsonlLedgerStore(args.data_dir)
    records = store.read_all("email_registrations")
    rows, skipped = build_contact_rows(records, redacted)
    write_csv(output, rows, redacted)
    print(json.dumps({
        "ok": True,
        "output": str(output),
        "redactedForExternalSharing": redacted,
        "sourceRecords": len(records),
        "contactsExported": len(rows),
        "recordsSkipped": len(skipped),
        "skippedRecords": skipped,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
