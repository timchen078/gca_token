#!/usr/bin/env python3
"""Check that public GCA domain-email snapshot references are aligned.

This is a read-only repository check. It compares public site, launch, and docs
materials against the canonical snapshot in site/domain-email.json so stale DNS
snapshot dates do not leak into the next BaseScan or platform reply packet.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "site" / "domain-email.json"

DEFAULT_MONITORED_FILES = [
    "docs/mainnet_public_profile.md",
    "docs/whitepaper.md",
    "launch/basescan_form_values.json",
    "launch/basescan_resubmission_package.md",
    "launch/basescan_resubmission_values.json",
    "launch/basescan_review_followup.md",
    "launch/domain_email_activation_runbook.md",
    "launch/external_review_followup_tracker.json",
    "launch/external_review_followup_tracker.md",
    "launch/launch_status.md",
    "site/action-plan.html",
    "site/basescan-remediation.html",
    "site/basescan-remediation.json",
    "site/domain-email.html",
    "site/domain-email.json",
    "site/external-reviews.html",
    "site/external-reviews.json",
    "site/platform-replies.html",
    "site/platform-replies.json",
    "site/reviewer-kit.html",
    "site/reviewer-kit.json",
    "site/sitemap.xml",
    "site/status.html",
    "site/trust.html",
    "site/trust.json",
    "site/whitepaper.html",
    "site/zh-domain-email.html",
]

SNAPSHOT_DATE_PATTERNS = [
    re.compile(r"\b(?P<date>20\d{2}-\d{2}-\d{2})\s+(?:read-only\s+|public\s+)?dns\s+snapshot\b", re.I),
    re.compile(r"\b(?P<date>20\d{2}-\d{2}-\d{2})\s+read-only\s+dns\s+check\b", re.I),
    re.compile(r"\blatest\s+read-only\s+dns\s+snapshot\s+\((?P<date>20\d{2}-\d{2}-\d{2})\)", re.I),
    re.compile(r"\bblocked-by-dns-snapshot-(?P<date>20\d{2}-\d{2}-\d{2})\b", re.I),
    re.compile(r"\b(?P<date>20\d{2}-\d{2}-\d{2})\s+dns\s+快照\b", re.I),
    re.compile(r"当前\s+(?P<date>20\d{2}-\d{2}-\d{2})\s+快照"),
]


class SnapshotAlignmentError(RuntimeError):
    """Raised for expected operator-facing snapshot alignment errors."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotAlignmentError(f"config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SnapshotAlignmentError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SnapshotAlignmentError(f"config file must contain a JSON object: {path}")
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
        raise SnapshotAlignmentError(f"monitored file path must be relative: {relative_path}")
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise SnapshotAlignmentError(f"monitored file escapes root: {relative_path}") from exc
    return path


def canonical_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    snapshot = config.get("liveDnsSnapshot")
    if not isinstance(snapshot, dict):
        raise SnapshotAlignmentError("site/domain-email.json is missing liveDnsSnapshot")

    checked_at = str(snapshot.get("checkedAt", "")).strip()
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", checked_at):
        raise SnapshotAlignmentError("liveDnsSnapshot.checkedAt must be an ISO UTC timestamp ending in Z")

    missing_or_blocked = snapshot.get("missingOrBlockedChecks", [])
    if not isinstance(missing_or_blocked, list) or not all(isinstance(item, str) for item in missing_or_blocked):
        raise SnapshotAlignmentError("liveDnsSnapshot.missingOrBlockedChecks must be a list of strings")

    ready = snapshot.get("readyForBaseScanEmailEvidence")
    if not isinstance(ready, bool):
        raise SnapshotAlignmentError("liveDnsSnapshot.readyForBaseScanEmailEvidence must be boolean")

    date = checked_at.split("T", 1)[0]
    return {
        "checkedAt": checked_at,
        "date": date,
        "readyForBaseScanEmailEvidence": ready,
        "missingOrBlockedChecks": missing_or_blocked,
        "gateSlug": f"blocked-by-dns-snapshot-{date}",
    }


def snapshot_marker_dates(text: str) -> list[str]:
    dates: list[str] = []
    for pattern in SNAPSHOT_DATE_PATTERNS:
        dates.extend(match.group("date") for match in pattern.finditer(text))
    return sorted(set(dates))


def inspect_file(root: Path, relative_path: str, canonical: dict[str, Any]) -> dict[str, Any]:
    path = safe_relative_path(root, relative_path)
    if not path.exists():
        return {
            "path": relative_path,
            "exists": False,
            "currentDateOccurrences": 0,
            "currentTimestampOccurrences": 0,
            "snapshotMarkerDates": [],
            "staleSnapshotMarkerDates": [],
            "status": "missing",
            "action": "restore the monitored public artifact or remove it from the alignment check",
        }

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SnapshotAlignmentError(f"monitored file is not UTF-8 text: {relative_path}") from exc

    marker_dates = snapshot_marker_dates(text)
    stale_marker_dates = [date for date in marker_dates if date != canonical["date"]]
    current_date_occurrences = text.count(canonical["date"])
    current_timestamp_occurrences = text.count(canonical["checkedAt"])

    if stale_marker_dates:
        status = "stale-snapshot-marker"
        action = f"replace stale DNS snapshot markers with {canonical['date']}"
    elif current_date_occurrences == 0:
        status = "missing-current-snapshot-date"
        action = f"add the canonical DNS snapshot date {canonical['date']} where this artifact cites the domain-email gate"
    else:
        status = "aligned"
        action = "no action"

    return {
        "path": relative_path,
        "exists": True,
        "currentDateOccurrences": current_date_occurrences,
        "currentTimestampOccurrences": current_timestamp_occurrences,
        "snapshotMarkerDates": marker_dates,
        "staleSnapshotMarkerDates": stale_marker_dates,
        "status": status,
        "action": action,
    }


def summarize_records(records: list[dict[str, Any]]) -> tuple[str, bool, list[str]]:
    missing = [record for record in records if record["status"] == "missing"]
    stale = [record for record in records if record["status"] == "stale-snapshot-marker"]
    missing_date = [record for record in records if record["status"] == "missing-current-snapshot-date"]

    blockers: list[str] = []
    if missing:
        blockers.append("missing-monitored-files")
    if stale:
        blockers.append("stale-dns-snapshot-markers")
    if missing_date:
        blockers.append("missing-current-snapshot-date")

    if missing:
        return "missing-monitored-files", False, blockers
    if stale:
        return "stale-dns-snapshot-markers", False, blockers
    if missing_date:
        return "missing-current-snapshot-date", False, blockers
    return "aligned", True, []


def build_report(
    *,
    root: Path = ROOT,
    config_path: Path = DEFAULT_CONFIG,
    monitored_files: list[str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    config = read_json(config_path)
    canonical = canonical_snapshot(config)
    files = monitored_files or DEFAULT_MONITORED_FILES
    if not all(isinstance(path, str) and path for path in files):
        raise SnapshotAlignmentError("monitored files must be non-empty relative paths")

    records = [inspect_file(root, path, canonical) for path in files]
    status, aligned, blockers = summarize_records(records)

    return {
        "schema": "gca-domain-email-snapshot-alignment-v1",
        "configFile": str(config_path),
        "canonicalSnapshot": canonical,
        "status": status,
        "alignedForPublicPlatformPackets": aligned,
        "blockedRequirements": blockers,
        "summary": {
            "filesChecked": len(records),
            "filesAligned": sum(1 for record in records if record["status"] == "aligned"),
            "filesWithStaleSnapshotMarkers": sum(
                1 for record in records if record["status"] == "stale-snapshot-marker"
            ),
            "filesMissingCurrentSnapshotDate": sum(
                1 for record in records if record["status"] == "missing-current-snapshot-date"
            ),
            "missingMonitoredFiles": sum(1 for record in records if record["status"] == "missing"),
            "canonicalDateOccurrences": sum(record["currentDateOccurrences"] for record in records),
            "canonicalTimestampOccurrences": sum(record["currentTimestampOccurrences"] for record in records),
        },
        "records": records,
        "nextAction": (
            "Snapshot references are aligned; continue with the final BaseScan preflight before owner resubmission."
            if aligned
            else "Do not reuse platform packets yet. Fix stale or missing domain-email DNS snapshot references first."
        ),
        "boundaries": {
            "readOnly": True,
            "writesPublicFiles": False,
            "sendsEmail": False,
            "writesDns": False,
            "submitsBaseScanRequest": False,
            "touchesWalletsOrContracts": False,
            "printsSecrets": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    canonical = report["canonicalSnapshot"]
    lines = [
        "# GCA Domain Email Snapshot Alignment",
        "",
        f"- Canonical snapshot date: `{canonical['date']}`",
        f"- Checked at: `{canonical['checkedAt']}`",
        f"- readyForBaseScanEmailEvidence: `{str(canonical['readyForBaseScanEmailEvidence']).lower()}`",
        f"- Status: `{report['status']}`",
        f"- Aligned for public platform packets: `{str(report['alignedForPublicPlatformPackets']).lower()}`",
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
        "## Monitored Files",
        "",
        "| File | Status | Date refs | Timestamp refs | Stale marker dates | Action |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ])
    for record in report["records"]:
        stale = ", ".join(record["staleSnapshotMarkerDates"]) or "-"
        lines.append(
            f"| `{record['path']}` | `{record['status']}` | "
            f"{record['currentDateOccurrences']} | {record['currentTimestampOccurrences']} | {stale} | "
            f"{record['action']} |"
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
    parser = argparse.ArgumentParser(description="Check GCA domain-email snapshot alignment.")
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect.")
    parser.add_argument("--config", default="", help="Path to domain-email.json. Defaults to <root>/site/domain-email.json.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--markdown", action="store_true", help="Print Markdown.")
    parser.add_argument("--require-aligned", action="store_true", help="Exit non-zero unless all monitored files align.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    try:
        report = build_report(root=root, config_path=resolve_config(root, args.config))
    except SnapshotAlignmentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.markdown:
        print(render_markdown(report), end="")
    else:
        print("GCA domain email snapshot alignment")
        print(f"canonicalDate: {report['canonicalSnapshot']['date']}")
        print(f"status: {report['status']}")
        print(f"alignedForPublicPlatformPackets: {str(report['alignedForPublicPlatformPackets']).lower()}")
        print(f"filesWithStaleSnapshotMarkers: {report['summary']['filesWithStaleSnapshotMarkers']}")
        print(f"filesMissingCurrentSnapshotDate: {report['summary']['filesMissingCurrentSnapshotDate']}")

    if args.require_aligned and not report["alignedForPublicPlatformPackets"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
