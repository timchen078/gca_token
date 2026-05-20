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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY_OUTPUT = ROOT / ".gca_access_data" / "gca_daily_ops_summary.json"
DEFAULT_SITE_BASE_URL = "https://gcagochina.com/"
DEFAULT_API_BASE_URL = "https://gca-registration-api.gcagochina.workers.dev"


CommandRunner = Callable[[Sequence[str], Path, float], subprocess.CompletedProcess[str]]


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


def run_step(
    *,
    step_id: str,
    command: Sequence[str],
    cwd: Path,
    timeout: float,
    runner: CommandRunner,
) -> dict[str, Any]:
    try:
        completed = runner(command, cwd, timeout)
        return {
            "id": step_id,
            "ok": completed.returncode == 0,
            "returnCode": completed.returncode,
            "command": shlex.join(str(part) for part in command),
            "stdoutTail": truncate(completed.stdout or ""),
            "stderrTail": truncate(completed.stderr or ""),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "id": step_id,
            "ok": False,
            "returnCode": None,
            "command": shlex.join(str(part) for part in command),
            "stdoutTail": truncate(exc.stdout or ""),
            "stderrTail": truncate(exc.stderr or f"timeout after {timeout} seconds"),
        }


def build_steps(
    *,
    site_base_url: str,
    api_base_url: str,
    timeout: float,
    include_member_ops: bool,
    member_ops_redact: str,
) -> list[tuple[str, list[str], float]]:
    python = sys.executable
    steps: list[tuple[str, list[str], float]] = [
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
        ),
    ]
    if include_member_ops:
        steps.append(
            (
                "member-access-ops",
                [
                    python,
                    "tools/run_gca_member_access_ops.py",
                    "--base-url",
                    api_base_url,
                    "--redact",
                    member_ops_redact,
                    "--timeout",
                    str(timeout),
                ],
                max(timeout * 4, 90),
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
    summary_output: Path = DEFAULT_SUMMARY_OUTPUT,
    runner: CommandRunner = default_runner,
) -> dict[str, Any]:
    steps = [
        run_step(step_id=step_id, command=command, cwd=ROOT, timeout=step_timeout, runner=runner)
        for step_id, command, step_timeout in build_steps(
            site_base_url=site_base_url,
            api_base_url=api_base_url,
            timeout=timeout,
            include_member_ops=include_member_ops,
            member_ops_redact=member_ops_redact,
        )
    ]
    summary = {
        "ok": all(step["ok"] for step in steps),
        "packetVersion": "gca_daily_ops_summary_v1",
        "generatedAt": utc_now(),
        "siteBaseUrl": site_base_url,
        "apiBaseUrl": api_base_url.rstrip("/"),
        "includeMemberOps": include_member_ops,
        "steps": steps,
        "summaryOutput": str(summary_output),
        "boundaries": {
            "publicOnlyByDefault": True,
            "readsTokenProtectedUserRecordsOnlyWhenIncludeMemberOpsIsTrue": True,
            "writesProductionData": False,
            "adminTokenPrinted": False,
            "walletCalls": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTokenTransfer": False,
            "memberBenefitTransferAutomatic": False,
        },
    }
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daily GCA public and optional member-ops health checks.")
    parser.add_argument("--site-base-url", default=DEFAULT_SITE_BASE_URL, help=f"Site base URL. Default: {DEFAULT_SITE_BASE_URL}")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL, help=f"API base URL. Default: {DEFAULT_API_BASE_URL}")
    parser.add_argument("--timeout", type=float, default=20, help="Per-request timeout forwarded to check tools. Default: 20.")
    parser.add_argument("--include-member-ops", action="store_true", help="Also refresh token-protected local member reports.")
    parser.add_argument("--member-ops-redact", choices=("none", "public"), default="none", help="Redaction mode for member ops export.")
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT, help="Daily summary JSON output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run_daily_ops(
        site_base_url=args.site_base_url,
        api_base_url=args.api_base_url,
        timeout=args.timeout,
        include_member_ops=args.include_member_ops,
        member_ops_redact=args.member_ops_redact,
        summary_output=args.summary_output,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
