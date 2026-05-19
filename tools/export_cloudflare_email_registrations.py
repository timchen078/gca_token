#!/usr/bin/env python3
"""Export GCA Cloudflare email-registration records for local operator review.

This helper reads the token-protected Cloudflare Worker admin endpoint and
writes the result into a local file. It never connects to a wallet, never asks
for signatures, and never prints the admin token.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOKEN_FILE = ROOT / "cloudflare" / "gca-registration-worker" / ".env.admin.local"
DEFAULT_OUTPUT = ROOT / ".gca_access_data" / "cloudflare_email_registrations_export.json"
DEFAULT_API_BASE = "https://gca-registration-api.gcagochina.workers.dev"
DEFAULT_CA_FILE = "/etc/ssl/cert.pem"


class ExportError(RuntimeError):
    """Raised for expected operator-facing export failures."""


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_admin_token(token_file: Path, explicit_token: str = "") -> str:
    token = explicit_token.strip()
    if token:
        return token
    values = parse_env_file(token_file)
    token = values.get("ADMIN_READ_TOKEN", "").strip()
    if not token:
        raise ExportError(f"ADMIN_READ_TOKEN not found in {token_file}")
    return token


def build_admin_url(base_url: str, limit: int, email: str = "") -> str:
    if limit < 1 or limit > 100:
        raise ExportError("limit must be between 1 and 100")
    clean_base = base_url.rstrip("/")
    query: dict[str, str] = {"limit": str(limit)}
    if email:
        query["email"] = email.strip().lower()
    return f"{clean_base}/gca/email-registrations?{urlencode(query)}"


def fetch_admin_records(
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
            "user-agent": "GCA-Operator-Registration-Export/1.0",
        },
    )
    try:
        kwargs: dict[str, Any] = {"timeout": timeout}
        if opener is urlopen:
            ca_path = cafile or os.environ.get("SSL_CERT_FILE", "")
            if not ca_path and Path(DEFAULT_CA_FILE).exists():
                ca_path = DEFAULT_CA_FILE
            if ca_path:
                kwargs["context"] = ssl.create_default_context(cafile=ca_path)
        with opener(request, **kwargs) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ExportError(f"Cloudflare admin API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise ExportError(f"Cloudflare admin API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ExportError("Cloudflare admin API returned invalid JSON") from exc

    if payload.get("ok") is not True:
        raise ExportError("Cloudflare admin API did not return ok=true")
    if not isinstance(payload.get("records"), list):
        raise ExportError("Cloudflare admin API response is missing records[]")
    return payload


def email_digest(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def redact_record(record: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(record)
    email = str(record.get("email", ""))
    if email:
        redacted["emailSha256"] = email_digest(email)
    redacted["email"] = ""
    redacted["displayName"] = ""
    redacted["redactedForExternalSharing"] = True
    return redacted


def build_export_payload(
    *,
    response_payload: dict[str, Any],
    source_url: str,
    redacted: bool,
) -> dict[str, Any]:
    records = response_payload.get("records", [])
    if redacted:
        records = [redact_record(record) for record in records]
    return {
        "ok": True,
        "packetVersion": "gca_cloudflare_email_registrations_export_v1",
        "exportedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "sourceEndpoint": source_url,
        "redactedForExternalSharing": redacted,
        "count": response_payload.get("count", len(records)),
        "recordsReturned": len(records),
        "records": records,
        "boundaries": {
            "localOperatorExportOnly": True,
            "adminTokenPrinted": False,
            "walletConnectionRequired": False,
            "signatureRequired": False,
            "transactionRequired": False,
            "automaticTokenTransfer": False,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export token-protected GCA Cloudflare email registrations into a local JSON file.",
    )
    parser.add_argument("--base-url", default=DEFAULT_API_BASE, help=f"Worker API base URL. Default: {DEFAULT_API_BASE}")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE, help="Path to ignored local admin env file.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum records to fetch, 1-100. Default: 100.")
    parser.add_argument("--email", default="", help="Optional email filter for a single registration lookup.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON file path.")
    parser.add_argument("--redact", choices=("none", "public"), default="none", help="Use public before external sharing.")
    parser.add_argument("--timeout", type=float, default=20, help="HTTP timeout in seconds. Default: 20.")
    parser.add_argument("--cafile", default="", help=f"Optional CA bundle path. Default fallback: {DEFAULT_CA_FILE}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        token = load_admin_token(args.token_file)
        source_url = build_admin_url(args.base_url, args.limit, args.email)
        response_payload = fetch_admin_records(
            base_url=args.base_url,
            token=token,
            limit=args.limit,
            email=args.email,
            timeout=args.timeout,
            cafile=args.cafile,
        )
        export_payload = build_export_payload(
            response_payload=response_payload,
            source_url=source_url,
            redacted=args.redact == "public",
        )
        write_json(args.output, export_payload)
    except ExportError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "recordsReturned": export_payload["recordsReturned"],
                "redactedForExternalSharing": export_payload["redactedForExternalSharing"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
