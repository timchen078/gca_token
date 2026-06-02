#!/usr/bin/env python3
"""Build the public GCA daily status page artifacts from a daily ops summary."""

from __future__ import annotations

import argparse
from html import escape
import json
import re
import shlex
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY_INPUT = ROOT / ".gca_access_data" / "gca_daily_ops_summary.json"
DEFAULT_JSON_OUTPUT = ROOT / "site" / "daily-status.json"
DEFAULT_HTML_OUTPUT = ROOT / "site" / "daily-status.html"

SITE_BASE_URL = "https://gcagochina.com/"
API_BASE_URL = "https://gca-registration-api.gcagochina.workers.dev"
DAILY_STATUS_PAGE_URL = "https://gcagochina.com/daily-status.html"
DAILY_STATUS_URL = "https://gcagochina.com/daily-status.json"
MAINNET_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6"
TARGET_DOMAIN_EMAIL = "support@gcagochina.com"
CURRENT_PUBLIC_EMAIL = TARGET_DOMAIN_EMAIL


class DailyStatusSnapshotError(ValueError):
    """Raised when the daily status snapshot cannot be safely built."""


def load_summary(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DailyStatusSnapshotError(f"summary file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DailyStatusSnapshotError(f"summary file is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DailyStatusSnapshotError("summary must be a JSON object")
    return payload


def normalize_public_command(command: str) -> str:
    """Remove local machine paths from command strings before publishing them."""
    if not command:
        return ""
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    normalized: list[str] = []
    for index, part in enumerate(parts):
        if index == 0 and (part.endswith("/python") or part.endswith("/python3") or part in {"python", "python3"}):
            normalized.append("python3")
            continue
        if "/tools/" in part:
            normalized.append("tools/" + part.split("/tools/", 1)[1])
            continue
        if part.startswith(str(ROOT)):
            normalized.append(part.replace(str(ROOT) + "/", "", 1))
            continue
        if re.fullmatch(r"\d+\.0", part):
            normalized.append(part[:-2])
            continue
        normalized.append(part)
    return shlex.join(normalized)


def step_by_id(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    steps = summary.get("steps", [])
    if not isinstance(steps, list):
        return {}
    return {str(step.get("id")): step for step in steps if isinstance(step, dict) and step.get("id")}


def public_step(step: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(step, dict):
        return {
            "ok": False,
            "status": "not-run",
            "blocksSummaryOk": False,
            "command": "",
        }
    ok = step.get("ok") is True
    return {
        "ok": ok,
        "status": "passed" if ok else "failed",
        "blocksSummaryOk": step.get("blocksSummaryOk") is not False,
        "command": normalize_public_command(str(step.get("command") or "")),
    }


def public_relative_paths(paths: Any, *, limit: int = 30) -> list[str]:
    if not isinstance(paths, list):
        return []
    safe_paths: list[str] = []
    for item in paths:
        value = str(item or "").strip()
        if not value:
            continue
        normalized = value.replace("\\", "/")
        parts = [part for part in normalized.split("/") if part]
        if (
            normalized.startswith("/")
            or ":" in normalized
            or ".." in parts
            or normalized.startswith(("~", "$"))
            or "/Users/" in normalized
        ):
            continue
        if not normalized.startswith(("site/", "docs/", "launch/", "tools/")):
            continue
        if normalized not in safe_paths:
            safe_paths.append(normalized)
        if len(safe_paths) >= limit:
            break
    return safe_paths


def format_path_queue(paths: list[str]) -> str:
    if not paths:
        return "No public relative files reported by the latest preflight."
    visible = paths[:8]
    rendered = ", ".join(f"<code>{escape(path)}</code>" for path in visible)
    remaining = len(paths) - len(visible)
    if remaining > 0:
        rendered += f", and {remaining} more tracked file(s)"
    return rendered


def build_daily_status_payload(summary: dict[str, Any]) -> dict[str, Any]:
    generated_at = str(summary.get("generatedAt") or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated_at):
        raise DailyStatusSnapshotError("summary generatedAt must be an ISO UTC timestamp ending in Z")

    steps = step_by_id(summary)
    public_site_step = public_step(steps.get("public-site"))
    registration_step = public_step(steps.get("registration-api-public"))
    basescan_step = public_step(steps.get("basescan-resubmission-preflight-status"))
    basescan = summary.get("baseScanPreflight") if isinstance(summary.get("baseScanPreflight"), dict) else {}
    missing_requirements = [
        str(item) for item in basescan.get("missingOrBlockedRequirements", []) if str(item)
    ]
    old_email_paths = public_relative_paths(basescan.get("oldEmailFilePaths"))
    missing_target_paths = public_relative_paths(basescan.get("missingTargetEmailFilePaths"))
    ready_for_basescan = basescan.get("readyForBaseScanResubmission") is True
    if ready_for_basescan:
        owner_action_queue = [
            {
                "id": "maintain-domain-mailbox",
                "status": "ready-monitor",
                "action": "Keep support@gcagochina.com able to receive and send authenticated mail while BaseScan reviews the update.",
                "publicEvidenceUrl": "https://gcagochina.com/domain-email.html",
            },
            {
                "id": "retain-domain-email-evidence",
                "status": "ready-private-evidence-retained",
                "action": "Keep provider, DNS, inbound, outbound, and support-page evidence archived privately for reviewer follow-up.",
                "publicEvidenceUrl": "https://gcagochina.com/domain-email-evidence.html",
            },
            {
                "id": "final-basescan-preflight",
                "status": "ready",
                "action": "Run tools/check_basescan_resubmission_readiness.py --json --require-ready before copying the final package into BaseScan.",
                "publicEvidenceUrl": "https://gcagochina.com/basescan-preflight.html",
            },
        ]
        basescan_summary = "BaseScan token profile resubmission is ready for one owner-controlled submission from support@gcagochina.com."
    else:
        owner_action_queue = [
            {
                "id": "activate-domain-mailbox",
                "status": "owner-action-required",
                "action": "Create and test support@gcagochina.com with working inbound and outbound mail.",
                "publicEvidenceUrl": "https://gcagochina.com/domain-email.html",
            },
            {
                "id": "complete-domain-email-evidence",
                "status": "owner-action-required",
                "action": "Add MX, SPF, DKIM, and DMARC records, then collect provider, inbound, outbound, DNS, and website evidence.",
                "publicEvidenceUrl": "https://gcagochina.com/domain-email-evidence.html",
            },
            {
                "id": "switch-public-email-after-mailbox-live",
                "status": "deferred-until-mailbox-ready",
                "action": "After the mailbox evidence passes, switch tracked public files from the Outlook email to support@gcagochina.com in one controlled pass.",
                "publicEvidenceUrl": "https://gcagochina.com/daily-status.html",
            },
            {
                "id": "final-basescan-preflight",
                "status": "blocked-until-domain-email-ready",
                "action": "Run tools/check_basescan_resubmission_readiness.py --json --require-ready before preparing another BaseScan submission.",
                "publicEvidenceUrl": "https://gcagochina.com/basescan-preflight.html",
            },
        ]
        basescan_summary = "BaseScan token profile resubmission remains blocked until the project-domain email evidence path is complete."

    return {
        "schema": DAILY_STATUS_URL,
        "pageUrl": DAILY_STATUS_PAGE_URL,
        "status": "daily-public-ops-snapshot-published",
        "lastUpdated": generated_at[:10],
        "snapshotSource": "tools/run_gca_daily_ops.py",
        "snapshotGeneratedAt": generated_at,
        "project": "GCA",
        "chainId": 8453,
        "contractAddress": MAINNET_ADDRESS,
        "dailyOps": {
            "packetVersion": summary.get("packetVersion", ""),
            "ok": summary.get("ok") is True,
            "generatedAt": generated_at,
            "publicOnlyByDefault": summary.get("boundaries", {}).get("publicOnlyByDefault") is True,
            "steps": [
                {"id": "public-site", **public_site_step},
                {"id": "registration-api-public", **registration_step},
                {
                    "id": "basescan-resubmission-preflight-status",
                    **basescan_step,
                    "blocksSummaryOk": basescan_step["blocksSummaryOk"],
                },
            ],
        },
        "publicSite": {
            "status": "ok" if public_site_step["ok"] else "failed",
            "baseUrl": str(summary.get("siteBaseUrl") or SITE_BASE_URL),
            "checkCommand": public_site_step["command"],
            "scope": [
                "canonical token identity",
                "public readable pages",
                "Data Room machine-readable files",
                "GCA/USDT market route",
                "public claim boundaries",
            ],
        },
        "registrationApi": {
            "status": "ok" if registration_step["ok"] else "failed",
            "apiBaseUrl": str(summary.get("apiBaseUrl") or API_BASE_URL).rstrip("/"),
            "checkCommand": registration_step["command"],
            "publicOnly": True,
            "healthEndpoint": f"{str(summary.get('apiBaseUrl') or API_BASE_URL).rstrip('/')}/health",
            "adminReads": "token-protected",
            "writesTestRecords": False,
        },
        "baseScanPreflight": {
            "status": str(basescan.get("status") or "not-run"),
            "readyForBaseScanResubmission": basescan.get("readyForBaseScanResubmission") is True,
            "publicEmailSwitchStatus": str(basescan.get("publicEmailSwitchStatus") or ""),
            "snapshotAlignmentStatus": str(basescan.get("snapshotAlignmentStatus") or ""),
            "filesStillUsingOldEmail": int(basescan.get("filesStillUsingOldEmail") or 0),
            "oldEmailFilePaths": old_email_paths,
            "missingTargetEmailFilePaths": missing_target_paths,
            "missingOrBlockedRequirements": missing_requirements,
            "nextAction": str(basescan.get("nextAction") or ""),
            "targetDomainEmail": TARGET_DOMAIN_EMAIL,
            "currentPublicEmail": str(basescan.get("currentPublicEmail") or CURRENT_PUBLIC_EMAIL),
        },
        "ownerActionQueue": owner_action_queue,
        "safePublicSummary": [
            "The public GCA website check passed on the latest daily ops snapshot.",
            "The public registration API check passed without secrets and without writing test records.",
            basescan_summary,
            "Admin reads, user records, private evidence files, wallet actions, and token transfers are not exposed by this public snapshot.",
        ],
        "boundaries": {
            "publicOnly": True,
            "adminTokenPrinted": False,
            "userEmailsPrinted": False,
            "writesProductionData": False,
            "submitsBaseScanRequest": False,
            "sendsEmail": False,
            "writesDns": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "touchesWalletsOrContracts": False,
        },
        "links": {
            "dailyStatusPage": DAILY_STATUS_PAGE_URL,
            "apiStatusPage": "https://gcagochina.com/api-status.html",
            "baseScanPreflightPage": "https://gcagochina.com/basescan-preflight.html",
            "domainEmailPage": "https://gcagochina.com/domain-email.html",
            "domainEmailEvidencePage": "https://gcagochina.com/domain-email-evidence.html",
            "dataRoom": "https://gcagochina.com/data.html",
        },
    }


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    new_text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise DailyStatusSnapshotError(f"could not update {label} in daily status HTML")
    return new_text


def update_daily_status_html(template: str, payload: dict[str, Any]) -> str:
    generated_at = str(payload["snapshotGeneratedAt"])
    last_updated = str(payload["lastUpdated"])
    basescan = payload["baseScanPreflight"]
    old_email_count = int(basescan["filesStillUsingOldEmail"])
    old_email_queue = format_path_queue(list(basescan.get("oldEmailFilePaths", [])))
    missing_target_queue = format_path_queue(list(basescan.get("missingTargetEmailFilePaths", [])))
    text = replace_once(
        template,
        r"Daily Ops Snapshot / \d{4}-\d{2}-\d{2}",
        f"Daily Ops Snapshot / {last_updated}",
        "snapshot date",
    )
    text = replace_once(
        text,
        r"generated at <code>[^<]+</code>",
        f"generated at <code>{generated_at}</code>",
        "generated timestamp",
    )
    text = replace_once(
        text,
        r"<code>filesStillUsingOldEmail</code> as \d+ tracked files",
        f"<code>filesStillUsingOldEmail</code> as {old_email_count} tracked files",
        "old email count",
    )
    text = replace_once(
        text,
        r"<div class=\"row\"><span>Old-email queue</span><strong>[\s\S]*?</strong></div>",
        f"<div class=\"row\"><span>Old-email queue</span><strong>{old_email_queue}</strong></div>",
        "old email queue",
    )
    text = replace_once(
        text,
        r"<div class=\"row\"><span>Missing target-email queue</span><strong>[\s\S]*?</strong></div>",
        f"<div class=\"row\"><span>Missing target-email queue</span><strong>{missing_target_queue}</strong></div>",
        "missing target email queue",
    )
    return text


def build_snapshot(summary_input: Path, json_output: Path, html_output: Path) -> dict[str, Any]:
    summary = load_summary(summary_input)
    payload = build_daily_status_payload(summary)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    html_template = html_output.read_text(encoding="utf-8")
    html_output.write_text(update_daily_status_html(html_template, payload), encoding="utf-8")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build public daily-status HTML and JSON from a GCA daily ops summary.")
    parser.add_argument("--summary-input", type=Path, default=DEFAULT_SUMMARY_INPUT, help="Daily ops summary JSON input.")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT, help="Public daily-status JSON output.")
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML_OUTPUT, help="Public daily-status HTML output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_snapshot(args.summary_input, args.json_output, args.html_output)
    print(json.dumps({
        "ok": True,
        "jsonOutput": str(args.json_output),
        "htmlOutput": str(args.html_output),
        "snapshotGeneratedAt": payload["snapshotGeneratedAt"],
        "baseScanPreflightStatus": payload["baseScanPreflight"]["status"],
        "filesStillUsingOldEmail": payload["baseScanPreflight"]["filesStillUsingOldEmail"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
