#!/usr/bin/env python3
"""Run the local GCA email-registration operations pipeline.

This is an operator helper for the public email registration backend. It syncs
Cloudflare Worker registration records into the local JSONL ledger, then exports
both internal and public-redacted contact CSV files. It never calls wallets,
never requests signatures, and never prints the admin token.
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

from tools.export_cloudflare_email_registrations import (  # noqa: E402
    DEFAULT_API_BASE,
    DEFAULT_TOKEN_FILE,
    ExportError,
    fetch_admin_records,
    load_admin_token,
)
from tools.export_gca_email_contacts import (  # noqa: E402
    DEFAULT_OUTPUT as DEFAULT_CONTACT_OUTPUT,
    DEFAULT_REDACTED_OUTPUT as DEFAULT_REDACTED_CONTACT_OUTPUT,
    DEFAULT_SUPPRESSION_FILE,
    build_contact_rows,
    load_suppressed_emails,
    write_csv,
)
from tools.gca_member_backend import BackendError, JsonlLedgerStore, iso_now  # noqa: E402
from tools.sync_cloudflare_email_registrations import SyncError, load_export_file, sync_records  # noqa: E402


DEFAULT_DATA_DIR = ROOT / ".gca_access_data"
DEFAULT_SUMMARY_OUTPUT = ROOT / ".gca_access_data" / "gca_registration_ops_summary.json"


def export_contact_csvs(
    store: JsonlLedgerStore,
    *,
    contact_output: Path,
    redacted_contact_output: Path,
    suppression_file: Path,
) -> dict[str, Any]:
    records = store.read_all("email_registrations")
    suppressed_emails, skipped_suppressions = load_suppressed_emails(suppression_file)
    contact_rows, skipped = build_contact_rows(records, redacted=False, suppressed_emails=suppressed_emails)
    redacted_rows, redacted_skipped = build_contact_rows(records, redacted=True, suppressed_emails=suppressed_emails)
    write_csv(contact_output, contact_rows, redacted=False)
    write_csv(redacted_contact_output, redacted_rows, redacted=True)
    return {
        "sourceLedger": "email_registrations",
        "sourceRecords": len(records),
        "contactsExported": len(contact_rows),
        "suppressionFile": str(suppression_file),
        "suppressedEmails": len(suppressed_emails),
        "recordsSkipped": len(skipped),
        "skippedRecords": skipped,
        "suppressionRecordsSkipped": skipped_suppressions,
        "publicRedactedRecordsSkipped": len(redacted_skipped),
        "contactCsv": str(contact_output),
        "publicRedactedContactCsv": str(redacted_contact_output),
    }


def write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def run_registration_ops(
    *,
    payload: dict[str, Any],
    data_dir: Path,
    contact_output: Path,
    redacted_contact_output: Path,
    suppression_file: Path,
    summary_output: Path,
    source: str,
    imported_at: str,
) -> dict[str, Any]:
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise SyncError("registration source payload is missing records[]")

    store = JsonlLedgerStore(data_dir)
    sync_result = sync_records(store, records, imported_at=imported_at)
    contact_result = export_contact_csvs(
        store,
        contact_output=contact_output,
        redacted_contact_output=redacted_contact_output,
        suppression_file=suppression_file,
    )
    summary = {
        "ok": bool(sync_result.get("ok")),
        "generatedAt": iso_now(),
        "importedAt": imported_at,
        "source": source,
        "sourceRecords": len(records),
        "sync": sync_result,
        "contactExports": contact_result,
        "summaryOutput": str(summary_output),
        "boundaries": {
            "localOperatorPipelineOnly": True,
            "adminTokenPrinted": False,
            "walletCalls": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTokenTransfer": False,
            "publicRedactedCsvRequiredBeforeExternalSharing": True,
            "contactSuppressionApplied": True,
        },
    }
    write_summary(summary_output, summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync GCA Cloudflare registrations and export internal plus public-redacted contact CSVs.",
    )
    parser.add_argument("--input", type=Path, help="Optional full, non-redacted Cloudflare export JSON file.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Local JSONL ledger directory.")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE, help=f"Worker API base URL. Default: {DEFAULT_API_BASE}")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE, help="Path to ignored local admin env file.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum records to fetch when --input is omitted.")
    parser.add_argument("--email", default="", help="Optional email filter when --input is omitted.")
    parser.add_argument("--timeout", type=float, default=20, help="HTTP timeout in seconds. Default: 20.")
    parser.add_argument("--cafile", default="", help="Optional CA bundle path for live fetches.")
    parser.add_argument("--contact-output", type=Path, default=DEFAULT_CONTACT_OUTPUT, help="Internal contact CSV output.")
    parser.add_argument(
        "--public-redacted-contact-output",
        type=Path,
        default=DEFAULT_REDACTED_CONTACT_OUTPUT,
        help="Public-redacted contact CSV output for external reporting.",
    )
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT, help="Pipeline summary JSON output.")
    parser.add_argument("--suppression-file", type=Path, default=DEFAULT_SUPPRESSION_FILE, help="Local contact suppression JSONL file.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.input:
            source_payload = load_export_file(args.input)
            source = f"input-file:{args.input}"
        else:
            token = load_admin_token(args.token_file)
            source_payload = fetch_admin_records(
                base_url=args.base_url,
                token=token,
                limit=args.limit,
                email=args.email,
                timeout=args.timeout,
                cafile=args.cafile,
            )
            source = f"cloudflare-admin-api:{args.base_url.rstrip('/')}/gca/email-registrations"

        summary = run_registration_ops(
            payload=source_payload,
            data_dir=args.data_dir,
            contact_output=args.contact_output,
            redacted_contact_output=args.public_redacted_contact_output,
            suppression_file=args.suppression_file,
            summary_output=args.summary_output,
            source=source,
            imported_at=iso_now(),
        )
    except (ExportError, SyncError, BackendError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
