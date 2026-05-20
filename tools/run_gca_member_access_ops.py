#!/usr/bin/env python3
"""Run the local GCA member-access operations pipeline.

This helper combines the live admin export and offline report builder:

1. Read token-protected Cloudflare Worker member-access datasets, or load an
   existing export file with ``--input``.
2. Save the export JSON into the ignored local data directory.
3. Build account, wallet, credit, member, and manual member-benefit review CSVs.

It does not write production data, connect to wallets, request signatures,
send transactions, or automatically transfer GCA.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_gca_member_access_report import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as DEFAULT_REPORT_DIR,
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_REPORT_SUMMARY_OUTPUT,
    ReportError,
    build_report,
    load_export,
)
from tools.export_cloudflare_email_registrations import (  # noqa: E402
    DEFAULT_API_BASE,
    DEFAULT_TOKEN_FILE,
    ExportError,
    load_admin_token,
)
from tools.export_cloudflare_member_access import (  # noqa: E402
    DEFAULT_OUTPUT as DEFAULT_EXPORT_OUTPUT,
    export_datasets,
    write_json,
)
from tools.gca_member_backend import iso_now  # noqa: E402


DEFAULT_PIPELINE_SUMMARY_OUTPUT = ROOT / ".gca_access_data" / "gca_member_access_ops_summary.json"


def run_member_access_ops(
    *,
    export_payload: dict[str, Any] | None = None,
    base_url: str = DEFAULT_API_BASE,
    token: str = "",
    limit: int = 100,
    email: str = "",
    wallet_address: str = "",
    redacted: bool = False,
    timeout: float = 20,
    cafile: str = "",
    export_output: Path = DEFAULT_EXPORT_OUTPUT,
    report_dir: Path = DEFAULT_REPORT_DIR,
    report_summary_output: Path = DEFAULT_REPORT_SUMMARY_OUTPUT,
    pipeline_summary_output: Path = DEFAULT_PIPELINE_SUMMARY_OUTPUT,
    source: str = "",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    if export_payload is None:
        export_payload = export_datasets(
            base_url=base_url,
            token=token,
            dataset="all",
            limit=limit,
            email=email,
            wallet_address=wallet_address,
            redacted=redacted,
            timeout=timeout,
            cafile=cafile,
            opener=opener,
        )
        source = source or f"cloudflare-admin-api:{base_url.rstrip('/')}"
    else:
        source = source or "input-export"

    write_json(export_output, export_payload)
    report_summary = build_report(export_payload, report_dir, report_summary_output)
    summary = {
        "ok": bool(export_payload.get("ok")) and bool(report_summary.get("ok")),
        "packetVersion": "gca_member_access_ops_summary_v1",
        "generatedAt": iso_now(),
        "source": source,
        "exportOutput": str(export_output),
        "reportSummaryOutput": str(report_summary_output),
        "pipelineSummaryOutput": str(pipeline_summary_output),
        "redactedForExternalSharing": bool(export_payload.get("redactedForExternalSharing")),
        "export": {
            "datasetCount": export_payload.get("datasetCount", 0),
            "recordCount": export_payload.get("recordCount", 0),
            "baseUrl": export_payload.get("baseUrl", base_url.rstrip("/")),
        },
        "report": report_summary.get("counts", {}),
        "outputs": report_summary.get("outputs", {}),
        "boundaries": {
            "localOperatorPipelineOnly": True,
            "writesProductionData": False,
            "adminTokenPrinted": False,
            "walletCalls": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTokenTransfer": False,
            "memberBenefitTransferAutomatic": False,
        },
    }
    pipeline_summary_output.parent.mkdir(parents=True, exist_ok=True)
    pipeline_summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch GCA member access data and build local operator CSV reports.",
    )
    parser.add_argument("--input", type=Path, help="Optional existing member access export JSON file.")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE, help=f"Worker API base URL. Default: {DEFAULT_API_BASE}")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE, help="Path to ignored local admin env file.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum records per dataset, 1-100. Default: 100.")
    parser.add_argument("--email", default="", help="Optional email filter for member-access dataset.")
    parser.add_argument("--wallet-address", default="", help="Optional Base wallet filter across member datasets.")
    parser.add_argument("--redact", choices=("none", "public"), default="none", help="Use public before external sharing.")
    parser.add_argument("--timeout", type=float, default=20, help="HTTP timeout in seconds. Default: 20.")
    parser.add_argument("--cafile", default="", help="Optional CA bundle path for live fetches.")
    parser.add_argument("--export-output", type=Path, default=DEFAULT_EXPORT_OUTPUT, help="Local export JSON output.")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR, help="Local CSV report directory.")
    parser.add_argument("--report-summary-output", type=Path, default=DEFAULT_REPORT_SUMMARY_OUTPUT, help="Report summary JSON output.")
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_PIPELINE_SUMMARY_OUTPUT, help="Pipeline summary JSON output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        export_payload = load_export(args.input) if args.input else None
        token = "" if export_payload is not None else load_admin_token(args.token_file)
        summary = run_member_access_ops(
            export_payload=export_payload,
            base_url=args.base_url,
            token=token,
            limit=args.limit,
            email=args.email,
            wallet_address=args.wallet_address,
            redacted=args.redact == "public",
            timeout=args.timeout,
            cafile=args.cafile,
            export_output=args.export_output,
            report_dir=args.report_dir,
            report_summary_output=args.report_summary_output,
            pipeline_summary_output=args.summary_output,
            source=f"input-file:{args.input}" if args.input else "",
        )
    except (ExportError, ReportError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
