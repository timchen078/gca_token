#!/usr/bin/env python3
"""Run daily GCA public and operator health checks.

Default mode is public-only: it checks the live website and live public API
surface without reading token-protected user records. Add ``--include-member-ops``
only when the local ADMIN_READ_TOKEN is available and an operator wants to
refresh ignored local member reports.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

try:
    from tools.build_gca_operator_digest import (
        DEFAULT_DIGEST_OUTPUT,
        DEFAULT_JSON_OUTPUT as DEFAULT_DIGEST_JSON_OUTPUT,
        DigestError,
        build_operator_digest,
    )
except ImportError:
    from build_gca_operator_digest import (
        DEFAULT_DIGEST_OUTPUT,
        DEFAULT_JSON_OUTPUT as DEFAULT_DIGEST_JSON_OUTPUT,
        DigestError,
        build_operator_digest,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY_OUTPUT = ROOT / ".gca_access_data" / "gca_daily_ops_summary.json"
DEFAULT_SITE_BASE_URL = "https://gcagochina.com/"
DEFAULT_API_BASE_URL = "https://gca-registration-api.gcagochina.workers.dev"


CommandRunner = Callable[[Sequence[str], Path, float], subprocess.CompletedProcess[str]]
BASESCAN_PREFLIGHT_STEP_ID = "basescan-resubmission-preflight-status"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def truncate(text: str, limit: int = 6000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def default_runner(command: Sequence[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        timeout=timeout,
        check=False,
        capture_output=True,
        text=True,
    )


def summarize_basescan_preflight(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout or "{}")
    except json.JSONDecodeError as exc:
        return {
            "available": False,
            "readyForBaseScanResubmission": None,
            "status": "unreadable-preflight-output",
            "missingOrBlockedRequirements": [],
            "publicEmailSwitchStatus": "",
            "filesStillUsingOldEmail": 0,
            "snapshotAlignmentStatus": "",
            "snapshotAlignmentStaleMarkers": 0,
            "snapshotAlignmentMissingCurrentDate": 0,
            "error": f"invalid JSON: {exc}",
        }
    if not isinstance(payload, dict):
        return {
            "available": False,
            "readyForBaseScanResubmission": None,
            "status": "unreadable-preflight-output",
            "missingOrBlockedRequirements": [],
            "publicEmailSwitchStatus": "",
            "filesStillUsingOldEmail": 0,
            "snapshotAlignmentStatus": "",
            "snapshotAlignmentStaleMarkers": 0,
            "snapshotAlignmentMissingCurrentDate": 0,
            "error": "preflight output must be a JSON object",
        }

    switch = payload.get("domainEmailPublicSwitchSummary")
    switch_summary = switch.get("summary") if isinstance(switch, dict) and isinstance(switch.get("summary"), dict) else {}
    snapshot = payload.get("domainEmailSnapshotAlignmentSummary")
    snapshot_summary = (
        snapshot.get("summary")
        if isinstance(snapshot, dict) and isinstance(snapshot.get("summary"), dict)
        else {}
    )
    return {
        "available": True,
        "readyForBaseScanResubmission": payload.get("readyForBaseScanResubmission") is True,
        "status": str(payload.get("status") or ""),
        "missingOrBlockedRequirements": [
            str(item) for item in payload.get("missingOrBlockedRequirements", []) if str(item)
        ],
        "publicEmailSwitchStatus": str(switch.get("status") or "") if isinstance(switch, dict) else "",
        "filesStillUsingOldEmail": switch_summary.get("filesStillUsingCurrentEmail", 0),
        "snapshotAlignmentStatus": str(snapshot.get("status") or "") if isinstance(snapshot, dict) else "",
        "snapshotAlignmentStaleMarkers": snapshot_summary.get("filesWithStaleSnapshotMarkers", 0),
        "snapshotAlignmentMissingCurrentDate": snapshot_summary.get("filesMissingCurrentSnapshotDate", 0),
        "nextAction": str(payload.get("nextAction") or ""),
    }


def run_step(
    *,
    step_id: str,
    command: Sequence[str],
    cwd: Path,
    timeout: float,
    runner: CommandRunner,
    blocks_summary_ok: bool = True,
) -> dict[str, Any]:
    try:
        completed = runner(command, cwd, timeout)
        result = {
            "id": step_id,
            "ok": completed.returncode == 0,
            "blocksSummaryOk": blocks_summary_ok,
            "returnCode": completed.returncode,
            "command": shlex.join(str(part) for part in command),
            "stdoutTail": truncate(completed.stdout or ""),
            "stderrTail": truncate(completed.stderr or ""),
        }
        if step_id == BASESCAN_PREFLIGHT_STEP_ID:
            result["statusSummary"] = summarize_basescan_preflight(completed.stdout or "")
        return result
    except subprocess.TimeoutExpired as exc:
        return {
            "id": step_id,
            "ok": False,
            "blocksSummaryOk": blocks_summary_ok,
            "returnCode": None,
            "command": shlex.join(str(part) for part in command),
            "stdoutTail": truncate(exc.stdout or ""),
            "stderrTail": truncate(exc.stderr or f"timeout after {timeout} seconds"),
            **(
                {
                    "statusSummary": {
                        "available": False,
                        "readyForBaseScanResubmission": None,
                        "status": "preflight-timeout",
                        "missingOrBlockedRequirements": [],
                        "publicEmailSwitchStatus": "",
                        "filesStillUsingOldEmail": 0,
                        "snapshotAlignmentStatus": "",
                        "snapshotAlignmentStaleMarkers": 0,
                        "snapshotAlignmentMissingCurrentDate": 0,
                        "error": f"timeout after {timeout} seconds",
                    }
                }
                if step_id == BASESCAN_PREFLIGHT_STEP_ID
                else {}
            ),
        }


def build_steps(
    *,
    site_base_url: str,
    api_base_url: str,
    timeout: float,
    include_member_ops: bool,
    member_ops_redact: str,
    include_holding_report: bool,
    holding_no_live_read: bool,
    holding_force_same_day: bool,
    include_basescan_preflight_status: bool,
) -> list[tuple[str, list[str], float, bool]]:
    if include_holding_report and not include_member_ops:
        raise ValueError("--include-holding-report requires --include-member-ops")
    python = sys.executable
    steps: list[tuple[str, list[str], float, bool]] = [
        (
            "public-site",
            [
                python,
                "tools/check_public_site.py",
                "--base-url",
                site_base_url,
                "--timeout",
                str(timeout),
            ],
            max(timeout * 8, 120),
            True,
        ),
        (
            "registration-api-public",
            [
                python,
                "tools/check_gca_registration_api.py",
                "--base-url",
                api_base_url,
                "--public-only",
                "--timeout",
                str(timeout),
            ],
            max(timeout * 3, 60),
            True,
        ),
    ]
    if include_basescan_preflight_status:
        steps.append(
            (
                BASESCAN_PREFLIGHT_STEP_ID,
                [
                    python,
                    "tools/check_basescan_resubmission_readiness.py",
                    "--skip-url-checks",
                    "--json",
                ],
                max(timeout * 3, 60),
                False,
            )
        )
    if include_member_ops:
        member_command = [
            python,
            "tools/run_gca_member_access_ops.py",
            "--base-url",
            api_base_url,
            "--redact",
            member_ops_redact,
            "--timeout",
            str(timeout),
        ]
        if include_holding_report:
            member_command.append("--include-holding-report")
            if holding_no_live_read:
                member_command.append("--holding-no-live-read")
            if holding_force_same_day:
                member_command.append("--holding-force-same-day")
        steps.append(
            (
                "member-access-ops",
                member_command,
                max(timeout * 4, 90),
                True,
            )
        )
    return steps


def run_daily_ops(
    *,
    site_base_url: str = DEFAULT_SITE_BASE_URL,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout: float = 20,
    include_member_ops: bool = False,
    member_ops_redact: str = "none",
    include_holding_report: bool = False,
    holding_no_live_read: bool = False,
    holding_force_same_day: bool = False,
    include_basescan_preflight_status: bool = True,
    summary_output: Path = DEFAULT_SUMMARY_OUTPUT,
    build_digest: bool = False,
    digest_output: Path = DEFAULT_DIGEST_OUTPUT,
    digest_json_output: Path = DEFAULT_DIGEST_JSON_OUTPUT,
    runner: CommandRunner = default_runner,
) -> dict[str, Any]:
    steps = [
        run_step(
            step_id=step_id,
            command=command,
            cwd=ROOT,
            timeout=step_timeout,
            runner=runner,
            blocks_summary_ok=blocks_summary_ok,
        )
        for step_id, command, step_timeout, blocks_summary_ok in build_steps(
            site_base_url=site_base_url,
            api_base_url=api_base_url,
            timeout=timeout,
            include_member_ops=include_member_ops,
            member_ops_redact=member_ops_redact,
            include_holding_report=include_holding_report,
            holding_no_live_read=holding_no_live_read,
            holding_force_same_day=holding_force_same_day,
            include_basescan_preflight_status=include_basescan_preflight_status,
        )
    ]
    basescan_preflight = next(
        (
            step.get("statusSummary")
            for step in steps
            if step.get("id") == BASESCAN_PREFLIGHT_STEP_ID and isinstance(step.get("statusSummary"), dict)
        ),
        {
            "available": False,
            "readyForBaseScanResubmission": None,
            "status": "not-run",
            "missingOrBlockedRequirements": [],
            "publicEmailSwitchStatus": "",
            "filesStillUsingOldEmail": 0,
            "snapshotAlignmentStatus": "",
            "snapshotAlignmentStaleMarkers": 0,
            "snapshotAlignmentMissingCurrentDate": 0,
        },
    )
    summary = {
        "ok": all(step["ok"] for step in steps if step.get("blocksSummaryOk", True)),
        "packetVersion": "gca_daily_ops_summary_v1",
        "generatedAt": utc_now(),
        "siteBaseUrl": site_base_url,
        "apiBaseUrl": api_base_url.rstrip("/"),
        "includeMemberOps": include_member_ops,
        "includeHoldingReport": include_holding_report,
        "holdingNoLiveRead": holding_no_live_read,
        "holdingForceSameDay": holding_force_same_day,
        "includeBaseScanPreflightStatus": include_basescan_preflight_status,
        "baseScanPreflight": basescan_preflight,
        "buildDigest": build_digest,
        "steps": steps,
        "summaryOutput": str(summary_output),
        "operatorDigest": {
            "requested": build_digest,
            "built": False,
            "ok": None,
            "markdownOutput": str(digest_output),
            "jsonOutput": str(digest_json_output),
        },
        "boundaries": {
            "publicOnlyByDefault": True,
            "readsTokenProtectedUserRecordsOnlyWhenIncludeMemberOpsIsTrue": True,
            "holdingReportRequiresMemberOps": True,
            "writesProductionData": False,
            "adminTokenPrinted": False,
            "walletCalls": bool(include_member_ops and include_holding_report and not holding_no_live_read),
            "readOnlyPublicChainBalanceCheck": bool(include_member_ops and include_holding_report and not holding_no_live_read),
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTokenTransfer": False,
            "memberBenefitTransferAutomatic": False,
            "baseScanPreflightStatusOnly": True,
            "baseScanPreflightBlocksDailyOps": False,
            "submitsBaseScanRequest": False,
        },
    }
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if build_digest:
        try:
            digest = build_operator_digest(
                daily_summary=summary_output,
                digest_output=digest_output,
                json_output=digest_json_output,
            )
            summary["operatorDigest"].update({
                "built": True,
                "ok": bool(digest.get("ok")),
                "packetVersion": digest.get("packetVersion", ""),
                "generatedAt": digest.get("generatedAt", ""),
            })
        except DigestError as exc:
            summary["ok"] = False
            summary["operatorDigest"].update({
                "built": False,
                "ok": False,
                "error": str(exc),
            })
        summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daily GCA public and optional member-ops health checks.")
    parser.add_argument("--site-base-url", default=DEFAULT_SITE_BASE_URL, help=f"Site base URL. Default: {DEFAULT_SITE_BASE_URL}")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL, help=f"API base URL. Default: {DEFAULT_API_BASE_URL}")
    parser.add_argument("--timeout", type=float, default=20, help="Per-request timeout forwarded to check tools. Default: 20.")
    parser.add_argument("--include-member-ops", action="store_true", help="Also refresh token-protected local member reports.")
    parser.add_argument("--member-ops-redact", choices=("none", "public"), default="none", help="Redaction mode for member ops export.")
    parser.add_argument("--include-holding-report", action="store_true", help="Also refresh the local GCA Member 30-day holding report.")
    parser.add_argument("--holding-no-live-read", action="store_true", help="Build holding report from existing snapshots without RPC reads.")
    parser.add_argument("--holding-force-same-day", action="store_true", help="Append a fresh holding snapshot even if today already exists.")
    parser.add_argument("--skip-basescan-preflight-status", action="store_true", help="Skip the non-blocking BaseScan resubmission preflight status step.")
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT, help="Daily summary JSON output.")
    parser.add_argument("--build-digest", action="store_true", help="Also build the redacted local operator digest from summary files.")
    parser.add_argument("--digest-output", type=Path, default=DEFAULT_DIGEST_OUTPUT, help="Markdown operator digest output path.")
    parser.add_argument("--digest-json-output", type=Path, default=DEFAULT_DIGEST_JSON_OUTPUT, help="JSON operator digest output path.")
    args = parser.parse_args(argv)
    if args.include_holding_report and not args.include_member_ops:
        parser.error("--include-holding-report requires --include-member-ops")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run_daily_ops(
        site_base_url=args.site_base_url,
        api_base_url=args.api_base_url,
        timeout=args.timeout,
        include_member_ops=args.include_member_ops,
        member_ops_redact=args.member_ops_redact,
        include_holding_report=args.include_holding_report,
        holding_no_live_read=args.holding_no_live_read,
        holding_force_same_day=args.holding_force_same_day,
        include_basescan_preflight_status=not args.skip_basescan_preflight_status,
        summary_output=args.summary_output,
        build_digest=args.build_digest,
        digest_output=args.digest_output,
        digest_json_output=args.digest_json_output,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
