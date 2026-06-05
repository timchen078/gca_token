#!/usr/bin/env python3
"""Check whether GCA public materials have switched to the domain email.

This read-only gate uses the critical file list from site/domain-email.json.
It is meant to run after support@gcagochina.com is active, the DNS/evidence
packet is ready, and before the next clean BaseScan resubmission.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "site" / "domain-email.json"
DEFAULT_CURRENT_EMAIL = "GCAgochina@outlook.com"
DEFAULT_TARGET_EMAIL = "support@gcagochina.com"
DEFAULT_FORBIDDEN_LEGACY_EMAILS = (
    DEFAULT_CURRENT_EMAIL,
    "cxy070800@gmail.com",
)


class PublicSwitchCheckError(RuntimeError):
    """Raised for expected operator-facing switch-check errors."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PublicSwitchCheckError(f"config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PublicSwitchCheckError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PublicSwitchCheckError(f"config file must contain a JSON object: {path}")
    return payload


def resolve_config(root: Path, config_path: str | None) -> Path:
    if config_path:
        candidate = Path(config_path)
        if not candidate.is_absolute():
            candidate = root / candidate
        return candidate.resolve()
    return (root / "site" / "domain-email.json").resolve()


def safe_relative_path(root: Path, relative_path: str) -> Path:
    if Path(relative_path).is_absolute():
        raise PublicSwitchCheckError(f"critical file path must be relative: {relative_path}")
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise PublicSwitchCheckError(f"critical file escapes root: {relative_path}") from exc
    return path


def dedupe_emails(emails: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for email in emails:
        normalized = str(email).strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def inspect_file(
    root: Path,
    relative_path: str,
    current_email: str,
    target_email: str,
    forbidden_legacy_emails: list[str],
) -> dict[str, Any]:
    path = safe_relative_path(root, relative_path)
    if not path.exists():
        return {
            "path": relative_path,
            "exists": False,
            "currentEmailOccurrences": 0,
            "forbiddenLegacyEmailOccurrences": 0,
            "forbiddenLegacyEmailsPresent": [],
            "targetEmailOccurrences": 0,
            "status": "missing",
            "action": "restore or remove this critical file entry before BaseScan resubmission",
        }
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise PublicSwitchCheckError(f"critical file is not UTF-8 text: {relative_path}") from exc
    current_count = text.count(current_email)
    target_count = text.count(target_email)
    forbidden_counts = {
        email: text.count(email)
        for email in forbidden_legacy_emails
        if email.lower() != target_email.lower() and text.count(email)
    }
    forbidden_count = sum(forbidden_counts.values())
    if forbidden_count:
        status = "needs-switch"
        action = "remove or replace forbidden legacy email references with the target domain email before BaseScan resubmission"
    elif target_count:
        status = "switched"
        action = "no action"
    else:
        status = "target-email-missing"
        action = f"confirm whether {target_email} should be present in this critical public file"
    return {
        "path": relative_path,
        "exists": True,
        "currentEmailOccurrences": current_count,
        "forbiddenLegacyEmailOccurrences": forbidden_count,
        "forbiddenLegacyEmailsPresent": sorted(forbidden_counts),
        "targetEmailOccurrences": target_count,
        "status": status,
        "action": action,
    }


def summarize_status(records: list[dict[str, Any]]) -> tuple[str, bool, list[str]]:
    missing = [record["path"] for record in records if record["status"] == "missing"]
    needs_switch = [record["path"] for record in records if record["status"] == "needs-switch"]
    target_missing = [record["path"] for record in records if record["status"] == "target-email-missing"]
    blockers: list[str] = []
    if missing:
        blockers.append("missing-critical-files")
    if needs_switch:
        blockers.append("current-email-still-published")
    if target_missing:
        blockers.append("target-domain-email-missing")
    if missing:
        return "missing-critical-files", False, blockers
    if needs_switch:
        return "public-email-switch-pending", False, blockers
    if target_missing:
        return "target-domain-email-missing", False, blockers
    return "public-email-switch-complete", True, []


def build_report(
    *,
    root: Path = ROOT,
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    root = root.resolve()
    config = read_json(config_path)
    legacy_email = config.get("previousPublicEmail") or config.get("legacyEmail") or DEFAULT_CURRENT_EMAIL
    target_email = config.get("targetDomainEmail") or DEFAULT_TARGET_EMAIL
    configured_forbidden = config.get("forbiddenLegacyEmails", [])
    if configured_forbidden and not (
        isinstance(configured_forbidden, list) and all(isinstance(item, str) for item in configured_forbidden)
    ):
        raise PublicSwitchCheckError("forbiddenLegacyEmails must be a list of email strings when provided")
    forbidden_legacy_emails = dedupe_emails(
        [str(legacy_email), *DEFAULT_FORBIDDEN_LEGACY_EMAILS, *(configured_forbidden or [])]
    )
    critical_files = config.get("filesToUpdateAfterActivation", [])
    if not isinstance(critical_files, list) or not all(isinstance(item, str) for item in critical_files):
        raise PublicSwitchCheckError("filesToUpdateAfterActivation must be a list of relative file paths")

    records = [
        inspect_file(root, path, legacy_email, target_email, forbidden_legacy_emails)
        for path in critical_files
    ]
    status, ready, blockers = summarize_status(records)
    current_refs = sum(record["currentEmailOccurrences"] for record in records)
    forbidden_refs = sum(record["forbiddenLegacyEmailOccurrences"] for record in records)
    target_refs = sum(record["targetEmailOccurrences"] for record in records)
    current_public_email = target_email if ready else str(config.get("currentPublicEmail") or legacy_email)
    return {
        "schema": "gca-domain-email-public-switch-check-v1",
        "configFile": str(config_path),
        "currentEmail": current_public_email,
        "legacyEmail": legacy_email,
        "forbiddenLegacyEmails": forbidden_legacy_emails,
        "targetDomainEmail": target_email,
        "status": status,
        "readyForBaseScanPublicEmailAlignment": ready,
        "blockedRequirements": blockers,
        "summary": {
            "criticalFilesChecked": len(records),
            "filesStillUsingCurrentEmail": sum(1 for record in records if record["currentEmailOccurrences"]),
            "filesPublishingForbiddenLegacyEmail": sum(
                1 for record in records if record["forbiddenLegacyEmailOccurrences"]
            ),
            "filesMissingTargetEmail": sum(1 for record in records if record["status"] == "target-email-missing"),
            "missingCriticalFiles": sum(1 for record in records if record["status"] == "missing"),
            "currentEmailOccurrences": current_refs,
            "forbiddenLegacyEmailOccurrences": forbidden_refs,
            "targetEmailOccurrences": target_refs,
        },
        "records": records,
        "nextAction": (
            "Public email alignment is complete; continue with DNS/evidence and BaseScan readiness checks."
            if ready
            else "Do not resubmit BaseScan yet. Finish the public email switch after domain email evidence is ready."
        ),
        "boundaries": {
            "readOnly": True,
            "writesPublicFiles": False,
            "sendsEmail": False,
            "writesDns": False,
            "submitsBaseScanRequest": False,
            "touchesWalletsOrContracts": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# GCA Domain Email Public Switch Check",
        "",
        f"- Current public email: `{report['currentEmail']}`",
        f"- Legacy email scanned: `{report['legacyEmail']}`",
        "- Forbidden legacy emails scanned: "
        + ", ".join(f"`{email}`" for email in report.get("forbiddenLegacyEmails", [])),
        f"- Target domain email: `{report['targetDomainEmail']}`",
        f"- Status: `{report['status']}`",
        f"- Ready for BaseScan public email alignment: `{str(report['readyForBaseScanPublicEmailAlignment']).lower()}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: `{value}`")
    if report["blockedRequirements"]:
        lines.extend(["", "## Blocked Requirements", ""])
        lines.extend(f"- `{item}`" for item in report["blockedRequirements"])
    lines.extend([
        "",
        "## Critical File Records",
        "",
        "| File | Status | Current refs | Forbidden refs | Target refs | Action |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ])
    for record in report["records"]:
        lines.append(
            f"| `{record['path']}` | `{record['status']}` | "
            f"{record['currentEmailOccurrences']} | {record.get('forbiddenLegacyEmailOccurrences', 0)} | "
            f"{record['targetEmailOccurrences']} | {record['action']} |"
        )
    lines.extend([
        "",
        "## Boundaries",
        "",
        "- This check is read-only.",
        "- This check does not edit files, send email, write DNS, submit BaseScan requests, or touch wallets/contracts.",
        "",
    ])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check GCA public email switch readiness.")
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect.")
    parser.add_argument("--config", default="", help="Path to domain-email.json. Defaults to <root>/site/domain-email.json.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--markdown", action="store_true", help="Print Markdown.")
    parser.add_argument("--require-switched", action="store_true", help="Exit non-zero unless the public switch is complete.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    try:
        report = build_report(root=root, config_path=resolve_config(root, args.config))
    except PublicSwitchCheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.markdown:
        print(render_markdown(report), end="")
    else:
        print("GCA domain email public switch check")
        print(f"status: {report['status']}")
        print(f"readyForBaseScanPublicEmailAlignment: {str(report['readyForBaseScanPublicEmailAlignment']).lower()}")
        print(f"filesStillUsingCurrentEmail: {report['summary']['filesStillUsingCurrentEmail']}")
        print(f"missingCriticalFiles: {report['summary']['missingCriticalFiles']}")

    if args.require_switched and not report["readyForBaseScanPublicEmailAlignment"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
