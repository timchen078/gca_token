#!/usr/bin/env python3
"""Sync Cloudflare contact-suppression records into the local GCA JSONL file."""

from __future__ import annotations

import json
import ssl
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.export_cloudflare_email_registrations import DEFAULT_API_BASE, DEFAULT_CA_FILE, DEFAULT_TOKEN_FILE, ExportError, load_admin_token  # noqa: E402
from tools.export_gca_email_contacts import DEFAULT_SUPPRESSION_FILE, email_sha256  # noqa: E402
from tools.gca_member_backend import BackendError, iso_now, normalize_email, stable_id  # noqa: E402


class SuppressionSyncError(RuntimeError):
    """Raised for expected contact-suppression sync failures."""


def build_admin_url(base_url: str, limit: int, email: str = "") -> str:
    if limit < 1 or limit > 100:
        raise SuppressionSyncError("limit must be between 1 and 100")
    clean_base = base_url.rstrip("/")
    query: dict[str, str] = {"limit": str(limit)}
    if email:
        query["email"] = email.strip().lower()
    return f"{clean_base}/gca/contact-suppressions?{urlencode(query)}"


def fetch_admin_suppressions(
    *,
    base_url: str,
    token: str,
    limit: int,
    email: str = "",
    timeout: float = 20,
    cafile: str = "",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    url = build_admin_url(base_url, limit, email)
    request = Request(
        url,
        headers={
            "authorization": f"Bearer {token}",
            "user-agent": "GCA-Operator-Contact-Suppression-Sync/1.0",
        },
    )
    try:
        kwargs: dict[str, Any] = {"timeout": timeout}
        if opener is urlopen:
            ca_path = cafile
            if not ca_path and Path(DEFAULT_CA_FILE).exists():
                ca_path = DEFAULT_CA_FILE
            if ca_path:
                kwargs["context"] = ssl.create_default_context(cafile=ca_path)
        with opener(request, **kwargs) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise SuppressionSyncError(f"Cloudflare contact suppression API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise SuppressionSyncError(f"Cloudflare contact suppression API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise SuppressionSyncError("Cloudflare contact suppression API returned invalid JSON") from exc

    if payload.get("ok") is not True:
        raise SuppressionSyncError("Cloudflare contact suppression API did not return ok=true")
    if not isinstance(payload.get("records"), list):
        raise SuppressionSyncError("Cloudflare contact suppression API response is missing records[]")
    return payload


def load_suppression_export_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SuppressionSyncError(f"suppression export file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SuppressionSyncError(f"suppression export file is not valid JSON: {path}") from exc
    if not isinstance(payload.get("records"), list):
        raise SuppressionSyncError("suppression export file is missing records[]")
    return payload


def cloudflare_suppression_to_local(record: dict[str, Any], imported_at: str) -> dict[str, Any]:
    email = normalize_email(str(record.get("email") or ""))
    created_at = str(record.get("createdAt") or imported_at)
    suppression_id = str(record.get("suppressionId") or "").strip() or stable_id("gca_suppression", email, created_at)
    return {
        "suppressionId": suppression_id,
        "createdAt": created_at,
        "updatedAt": str(record.get("updatedAt") or created_at),
        "email": email,
        "emailSha256": str(record.get("emailSha256") or email_sha256(email)),
        "reason": str(record.get("reason") or "unsubscribe_request")[:160],
        "source": str(record.get("source") or "cloudflare-contact-suppression-api")[:120],
        "status": str(record.get("status") or "suppressed"),
        "contactSuppressed": True,
        "importedFromCloudflare": True,
        "importedAt": imported_at,
    }


def read_local_suppression_keys(path: Path) -> tuple[set[str], set[str]]:
    if not path.exists():
        return set(), set()
    ids: set[str] = set()
    emails: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if record.get("suppressionId"):
            ids.add(str(record["suppressionId"]))
        if record.get("email"):
            try:
                emails.add(normalize_email(str(record["email"])))
            except BackendError:
                continue
    return ids, emails


def sync_suppressions(path: Path, records: list[dict[str, Any]], imported_at: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids, existing_emails = read_local_suppression_keys(path)
    created: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    with path.open("a", encoding="utf-8") as handle:
        for raw_record in records:
            try:
                local_record = cloudflare_suppression_to_local(raw_record, imported_at)
            except (BackendError, ValueError) as exc:
                failed.append({
                    "suppressionId": str(raw_record.get("suppressionId") or ""),
                    "email": str(raw_record.get("email") or ""),
                    "error": str(exc),
                })
                continue
            suppression_id = str(local_record["suppressionId"])
            email = str(local_record["email"])
            if suppression_id in existing_ids or email in existing_emails:
                skipped.append({"suppressionId": suppression_id, "email": email, "reason": "already_present"})
                continue
            handle.write(json.dumps(local_record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
            existing_ids.add(suppression_id)
            existing_emails.add(email)
            created.append({"suppressionId": suppression_id, "email": email})
    return {
        "ok": len(failed) == 0,
        "suppressionFile": str(path),
        "created": len(created),
        "skipped": len(skipped),
        "failed": len(failed),
        "createdRecords": created,
        "skippedRecords": skipped,
        "failedRecords": failed,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sync GCA Cloudflare contact suppressions into the local suppression JSONL file.")
    parser.add_argument("--input", type=Path, help="Optional contact-suppression export JSON file.")
    parser.add_argument("--suppression-file", type=Path, default=DEFAULT_SUPPRESSION_FILE, help="Local suppression JSONL file.")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE, help=f"Worker API base URL. Default: {DEFAULT_API_BASE}")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE, help="Path to ignored local admin env file.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum records to fetch when --input is omitted.")
    parser.add_argument("--email", default="", help="Optional email filter when --input is omitted.")
    parser.add_argument("--timeout", type=float, default=20, help="HTTP timeout in seconds. Default: 20.")
    parser.add_argument("--cafile", default="", help="Optional CA bundle path for live fetches.")
    args = parser.parse_args(argv)
    try:
        if args.input:
            payload = load_suppression_export_file(args.input)
        else:
            token = load_admin_token(args.token_file)
            payload = fetch_admin_suppressions(
                base_url=args.base_url,
                token=token,
                limit=args.limit,
                email=args.email,
                timeout=args.timeout,
                cafile=args.cafile,
            )
        result = sync_suppressions(args.suppression_file, payload.get("records", []), imported_at=iso_now())
    except (ExportError, SuppressionSyncError, BackendError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
