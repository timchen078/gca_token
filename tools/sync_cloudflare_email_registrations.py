#!/usr/bin/env python3
"""Sync Cloudflare email-registration records into the local GCA JSONL ledger."""

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
from tools.gca_member_backend import (  # noqa: E402
    EMAIL_REGISTRATION_VERSION,
    BackendError,
    JsonlLedgerStore,
    iso_now,
    normalize_email,
    stable_id,
)


DEFAULT_DATA_DIR = ROOT / ".gca_access_data"


class SyncError(RuntimeError):
    """Raised for expected operator-facing sync failures."""


def load_export_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SyncError(f"export file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SyncError(f"export file is not valid JSON: {path}") from exc
    if payload.get("redactedForExternalSharing") is True:
        raise SyncError("redacted public exports cannot be synced because email addresses are removed")
    if not isinstance(payload.get("records"), list):
        raise SyncError("export file is missing records[]")
    return payload


def cloudflare_record_to_local(record: dict[str, Any], imported_at: str) -> dict[str, Any]:
    email = normalize_email(str(record.get("email") or ""))
    registration_id = str(record.get("emailRegistrationId") or "").strip() or stable_id("gca_email", email)
    interests = record.get("interests")
    if not isinstance(interests, list):
        interests = ["gca_updates"]
    clean_interests = [str(item).strip()[:64] for item in interests if str(item).strip()]
    return {
        "emailRegistrationId": registration_id,
        "packetVersion": EMAIL_REGISTRATION_VERSION,
        "createdAt": str(record.get("createdAt") or imported_at),
        "updatedAt": str(record.get("updatedAt") or record.get("createdAt") or imported_at),
        "source": str(record.get("source") or "cloudflare-email-registration-api")[:120],
        "status": str(record.get("status") or "received"),
        "email": email,
        "displayName": str(record.get("displayName") or "")[:120],
        "language": str(record.get("language") or "zh-CN")[:32],
        "interests": clean_interests,
        "contactConsentAccepted": True,
        "securityBoundaryAccepted": True,
        "walletRequired": False,
        "requiresSignature": False,
        "requiresTransaction": False,
        "requiresPrivateKey": False,
        "requiresSeedPhrase": False,
        "requiresExchangeApiSecret": False,
        "requiresWithdrawalPermission": False,
        "publicSelfServiceClaim": False,
        "automaticTokenTransfer": False,
        "importedFromCloudflare": True,
        "importedAt": imported_at,
        "nextStep": "GCA support can contact this email when customer registration, member access, or product updates are ready.",
    }


def sync_records(store: JsonlLedgerStore, records: list[dict[str, Any]], imported_at: str) -> dict[str, Any]:
    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for raw_record in records:
        try:
            local_record = cloudflare_record_to_local(raw_record, imported_at)
        except (BackendError, SyncError, ValueError) as exc:
            failed.append({
                "emailRegistrationId": raw_record.get("emailRegistrationId", ""),
                "email": raw_record.get("email", ""),
                "error": str(exc),
            })
            continue

        registration_id = local_record["emailRegistrationId"]
        if store.exists("email_registrations", "emailRegistrationId", registration_id):
            skipped.append({
                "emailRegistrationId": registration_id,
                "email": local_record["email"],
                "reason": "already_present",
            })
            continue
        store.append("email_registrations", local_record)
        created.append({
            "emailRegistrationId": registration_id,
            "email": local_record["email"],
        })
    return {
        "ok": len(failed) == 0,
        "ledger": "email_registrations",
        "created": len(created),
        "skipped": len(skipped),
        "failed": len(failed),
        "createdRecords": created,
        "skippedRecords": skipped,
        "failedRecords": failed,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync GCA Cloudflare email registrations into .gca_access_data/email_registrations.jsonl.",
    )
    parser.add_argument("--input", type=Path, help="Optional full, non-redacted Cloudflare export JSON file.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Local JSONL ledger directory.")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE, help=f"Worker API base URL. Default: {DEFAULT_API_BASE}")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE, help="Path to ignored local admin env file.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum records to fetch when --input is omitted.")
    parser.add_argument("--email", default="", help="Optional email filter when --input is omitted.")
    parser.add_argument("--timeout", type=float, default=20, help="HTTP timeout in seconds. Default: 20.")
    parser.add_argument("--cafile", default="", help="Optional CA bundle path for live fetches.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.input:
            payload = load_export_file(args.input)
        else:
            token = load_admin_token(args.token_file)
            payload = fetch_admin_records(
                base_url=args.base_url,
                token=token,
                limit=args.limit,
                email=args.email,
                timeout=args.timeout,
                cafile=args.cafile,
            )
        result = sync_records(
            JsonlLedgerStore(args.data_dir),
            payload.get("records", []),
            imported_at=iso_now(),
        )
    except (ExportError, SyncError, BackendError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
