#!/usr/bin/env python3
"""Export live GCA member-access records for local operator review.

This helper reads token-protected Cloudflare Worker admin endpoints for the
live member access flow. It is read-only: it never writes production data,
never connects to a wallet, never requests signatures or transactions, and
never prints the admin token.
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.export_cloudflare_email_registrations import (  # noqa: E402
    DEFAULT_API_BASE,
    DEFAULT_CA_FILE,
    DEFAULT_TOKEN_FILE,
    ExportError,
    load_admin_token,
)


DEFAULT_OUTPUT = ROOT / ".gca_access_data" / "cloudflare_member_access_export.json"
DATASET_PATHS = {
    "member-access": "/gca/member-access",
    "wallet-verifications": "/gca/wallet-verifications",
    "credit-ledger": "/gca/credit-ledger",
    "member-ledger": "/gca/member-ledger",
}
DATASET_FILTERS = {
    "member-access": {"email", "walletAddress"},
    "wallet-verifications": {"walletAddress"},
    "credit-ledger": {"walletAddress"},
    "member-ledger": {"walletAddress"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_wallet(value: str) -> str:
    return value.strip().lower()


def normalize_email(value: str) -> str:
    return value.strip().lower()


def email_digest(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()


def build_admin_url(
    base_url: str,
    dataset: str,
    limit: int,
    *,
    email: str = "",
    wallet_address: str = "",
) -> str:
    if dataset not in DATASET_PATHS:
        raise ExportError(f"unsupported dataset: {dataset}")
    if limit < 1 or limit > 100:
        raise ExportError("limit must be between 1 and 100")

    allowed_filters = DATASET_FILTERS[dataset]
    query: dict[str, str] = {"limit": str(limit)}
    if email:
        if "email" not in allowed_filters:
            raise ExportError(f"email filter is not supported for {dataset}")
        query["email"] = normalize_email(email)
    if wallet_address:
        if "walletAddress" not in allowed_filters:
            raise ExportError(f"walletAddress filter is not supported for {dataset}")
        query["walletAddress"] = normalize_wallet(wallet_address)

    return f"{base_url.rstrip('/')}{DATASET_PATHS[dataset]}?{urlencode(query)}"


def fetch_admin_records(
    *,
    base_url: str,
    dataset: str,
    token: str,
    limit: int,
    email: str = "",
    wallet_address: str = "",
    timeout: float = 20,
    cafile: str = "",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    url = build_admin_url(base_url, dataset, limit, email=email, wallet_address=wallet_address)
    request = Request(
        url,
        headers={
            "authorization": f"Bearer {token}",
            "user-agent": "GCA-Operator-Member-Access-Export/1.0",
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
        raise ExportError(f"Cloudflare admin API returned HTTP {exc.code} for {dataset}") from exc
    except URLError as exc:
        raise ExportError(f"Cloudflare admin API request failed for {dataset}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ExportError(f"Cloudflare admin API returned invalid JSON for {dataset}") from exc

    if payload.get("ok") is not True:
        raise ExportError(f"Cloudflare admin API did not return ok=true for {dataset}")
    if not isinstance(payload.get("records"), list):
        raise ExportError(f"Cloudflare admin API response for {dataset} is missing records[]")
    return payload


def redact_record(record: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(record)
    email = str(record.get("email", ""))
    if email and not redacted.get("emailSha256"):
        redacted["emailSha256"] = email_digest(email)
    if "email" in redacted:
        redacted["email"] = ""
    if "displayName" in redacted:
        redacted["displayName"] = ""
    redacted["redactedForExternalSharing"] = True
    redacted["walletAddressRetainedForOnchainReview"] = bool(redacted.get("walletAddress"))
    return redacted


def build_dataset_payload(
    *,
    dataset: str,
    response_payload: dict[str, Any],
    source_url: str,
    redacted: bool,
) -> dict[str, Any]:
    records = response_payload.get("records", [])
    if redacted:
        records = [redact_record(record) for record in records]
    return {
        "dataset": dataset,
        "sourceEndpoint": source_url,
        "count": response_payload.get("count", len(records)),
        "recordsReturned": len(records),
        "records": records,
    }


def build_export_payload(
    *,
    datasets: dict[str, dict[str, Any]],
    base_url: str,
    redacted: bool,
) -> dict[str, Any]:
    return {
        "ok": True,
        "packetVersion": "gca_cloudflare_member_access_export_v1",
        "exportedAt": utc_now(),
        "baseUrl": base_url.rstrip("/"),
        "redactedForExternalSharing": redacted,
        "datasets": datasets,
        "datasetCount": len(datasets),
        "recordCount": sum(int(item.get("recordsReturned", 0)) for item in datasets.values()),
        "boundaries": {
            "localOperatorExportOnly": True,
            "adminTokenPrinted": False,
            "writesProductionData": False,
            "walletConnectionRequired": False,
            "signatureRequired": False,
            "transactionRequired": False,
            "automaticTokenTransfer": False,
            "memberBenefitTransferAutomatic": False,
        },
    }


def export_datasets(
    *,
    base_url: str,
    token: str,
    dataset: str,
    limit: int,
    email: str = "",
    wallet_address: str = "",
    redacted: bool = False,
    timeout: float = 20,
    cafile: str = "",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    dataset_names = tuple(DATASET_PATHS) if dataset == "all" else (dataset,)
    datasets: dict[str, dict[str, Any]] = {}
    for dataset_name in dataset_names:
        source_url = build_admin_url(
            base_url,
            dataset_name,
            limit,
            email=email if dataset_name == "member-access" else "",
            wallet_address=wallet_address,
        )
        response_payload = fetch_admin_records(
            base_url=base_url,
            dataset=dataset_name,
            token=token,
            limit=limit,
            email=email if dataset_name == "member-access" else "",
            wallet_address=wallet_address,
            timeout=timeout,
            cafile=cafile,
            opener=opener,
        )
        datasets[dataset_name] = build_dataset_payload(
            dataset=dataset_name,
            response_payload=response_payload,
            source_url=source_url,
            redacted=redacted,
        )
    return build_export_payload(datasets=datasets, base_url=base_url, redacted=redacted)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export token-protected GCA member access, wallet verification, credit, and member ledger records.",
    )
    parser.add_argument("--base-url", default=DEFAULT_API_BASE, help=f"Worker API base URL. Default: {DEFAULT_API_BASE}")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE, help="Path to ignored local admin env file.")
    parser.add_argument(
        "--dataset",
        choices=("all", *DATASET_PATHS.keys()),
        default="all",
        help="Dataset to export. Default: all.",
    )
    parser.add_argument("--limit", type=int, default=100, help="Maximum records per dataset, 1-100. Default: 100.")
    parser.add_argument("--email", default="", help="Optional email filter. Supported only by member-access.")
    parser.add_argument("--wallet-address", default="", help="Optional Base wallet filter for member datasets.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON file path.")
    parser.add_argument("--redact", choices=("none", "public"), default="none", help="Use public before external sharing.")
    parser.add_argument("--timeout", type=float, default=20, help="HTTP timeout in seconds. Default: 20.")
    parser.add_argument("--cafile", default="", help=f"Optional CA bundle path. Default fallback: {DEFAULT_CA_FILE}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        token = load_admin_token(args.token_file)
        export_payload = export_datasets(
            base_url=args.base_url,
            token=token,
            dataset=args.dataset,
            limit=args.limit,
            email=args.email,
            wallet_address=args.wallet_address,
            redacted=args.redact == "public",
            timeout=args.timeout,
            cafile=args.cafile,
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
                "datasetCount": export_payload["datasetCount"],
                "recordCount": export_payload["recordCount"],
                "redactedForExternalSharing": export_payload["redactedForExternalSharing"],
                "recordsPrinted": False,
                "adminTokenPrinted": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
