#!/usr/bin/env python3
"""Synchronize BaseScan packet references with the canonical daily status.

The public daily status is refreshed independently from the static reviewer
pages and owner copy/paste packets. This tool keeps the duplicated snapshot
timestamp and BaseScan public-profile check date aligned without changing any
wallet, contract, DNS, email, or remote platform state.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DAILY_STATUS_PATH = ROOT / "site" / "daily-status.json"
DEFAULT_VALUES_PATH = ROOT / "launch" / "basescan_resubmission_values.json"

DEFAULT_TARGET_FILES = [
    "launch/basescan_form_values.json",
    "launch/basescan_resubmission_package.md",
    "launch/basescan_resubmission_values.json",
    "launch/basescan_review_followup.md",
    "launch/basescan_reviewer_checklist.json",
    "launch/basescan_reviewer_checklist.md",
    "launch/basescan_token_submission.md",
    "launch/external_review_followup_tracker.json",
    "site/basescan-followup.html",
    "site/basescan-followup.json",
    "site/basescan-preflight.html",
    "site/basescan-preflight.json",
    "site/basescan-remediation.html",
    "site/basescan-remediation.json",
    "site/external-reviews.html",
    "site/external-reviews.json",
    "site/listing-readiness.html",
    "site/listing-readiness.json",
    "site/project.json",
    "site/release-gates.html",
    "site/release-gates.json",
    "site/reviewer-kit.html",
    "site/reviewer-kit.json",
    "site/roadmap.html",
    "site/terms.html",
    "site/token-safety.html",
    "site/trust.html",
    "site/trust.json",
    "site/verify.html",
    "site/zh-basescan-followup.html",
    "site/zh-basescan-preflight.html",
    "site/zh-release-gates.html",
    "tests/test_basescan_reviewer_checklist.py",
    "tests/test_launch_package.py",
    "tools/check_public_site.py",
]

DATE_FIELDS = {
    "lastCheckedDate",
    "baseScanTokenProfileLastCheckedDate",
}

PROFILE_DATE_ONLY_TARGET_FILES = {
    "site/basescan-preflight.html",
    "site/zh-basescan-preflight.html",
}


class DailyStatusReferenceSyncError(RuntimeError):
    """Raised when snapshot references cannot be updated safely."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DailyStatusReferenceSyncError(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DailyStatusReferenceSyncError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DailyStatusReferenceSyncError(f"JSON file must contain an object: {path}")
    return payload


def require_timestamp(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text):
        raise DailyStatusReferenceSyncError(f"{label} must be an ISO UTC timestamp ending in Z")
    return text


def canonical_reference(daily_status: dict[str, Any]) -> dict[str, str]:
    snapshot_generated_at = require_timestamp(
        daily_status.get("snapshotGeneratedAt"),
        "daily-status.snapshotGeneratedAt",
    )
    profile = daily_status.get("baseScanPublicProfile")
    if not isinstance(profile, dict):
        raise DailyStatusReferenceSyncError("daily-status.baseScanPublicProfile must be an object")
    profile_checked_at = require_timestamp(
        profile.get("checkedAt"),
        "daily-status.baseScanPublicProfile.checkedAt",
    )
    return {
        "dailyStatusGeneratedAt": snapshot_generated_at,
        "dailyStatusDate": snapshot_generated_at.split("T", 1)[0],
        "baseScanProfileCheckedAt": profile_checked_at,
        "baseScanProfileCheckedDate": profile_checked_at.split("T", 1)[0],
    }


def previous_reference(values: dict[str, Any]) -> dict[str, str]:
    timestamp = require_timestamp(
        values.get("dailyStatusGeneratedAt"),
        "basescan-resubmission-values.dailyStatusGeneratedAt",
    )
    checked_date = str(values.get("lastCheckedDate") or "").strip()
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", checked_date):
        raise DailyStatusReferenceSyncError(
            "basescan-resubmission-values.lastCheckedDate must be YYYY-MM-DD"
        )
    return {
        "dailyStatusGeneratedAt": timestamp,
        "baseScanProfileCheckedDate": checked_date,
    }


def safe_path(root: Path, relative_path: str) -> Path:
    if Path(relative_path).is_absolute():
        raise DailyStatusReferenceSyncError(f"target path must be relative: {relative_path}")
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise DailyStatusReferenceSyncError(f"target path escapes repository: {relative_path}") from exc
    return path


def replace_profile_date_phrases(text: str, old_date: str, new_date: str) -> tuple[str, int]:
    if old_date == new_date:
        return text, 0
    patterns = [
        re.compile(
            rf"(?P<prefix>read-only\s+public(?:-page)?(?:\s+BaseScan)?\s+check\s+on\s+){re.escape(old_date)}",
            re.I,
        ),
        re.compile(rf"(?P<prefix>Read-only\s+check\s+){re.escape(old_date)}(?=\s+still\s+shows)"),
        re.compile(
            rf"(?P<prefix><span class=\"label\">Preflight Refresh</span>\s*<span class=\"value\">){re.escape(old_date)}"
        ),
        re.compile(
            rf"(?P<prefix><span class=\"label\">最终包刷新</span>\s*<span class=\"value\">){re.escape(old_date)}"
        ),
    ]
    replacements = 0
    updated = text
    for pattern in patterns:
        updated, count = pattern.subn(rf"\g<prefix>{new_date}", updated)
        replacements += count
    return updated, replacements


def replace_json_values(
    value: Any,
    *,
    old_timestamp: str,
    new_timestamp: str,
    old_date: str,
    new_date: str,
    key: str = "",
) -> tuple[Any, int, int]:
    timestamp_replacements = 0
    date_replacements = 0
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for child_key, child_value in value.items():
            replacement, timestamp_count, date_count = replace_json_values(
                child_value,
                old_timestamp=old_timestamp,
                new_timestamp=new_timestamp,
                old_date=old_date,
                new_date=new_date,
                key=str(child_key),
            )
            result[child_key] = replacement
            timestamp_replacements += timestamp_count
            date_replacements += date_count
        return result, timestamp_replacements, date_replacements
    if isinstance(value, list):
        result_list: list[Any] = []
        for child_value in value:
            replacement, timestamp_count, date_count = replace_json_values(
                child_value,
                old_timestamp=old_timestamp,
                new_timestamp=new_timestamp,
                old_date=old_date,
                new_date=new_date,
            )
            result_list.append(replacement)
            timestamp_replacements += timestamp_count
            date_replacements += date_count
        return result_list, timestamp_replacements, date_replacements
    if isinstance(value, str):
        updated = value
        if old_timestamp != new_timestamp:
            count = updated.count(old_timestamp)
            updated = updated.replace(old_timestamp, new_timestamp)
            timestamp_replacements += count
        updated, phrase_count = replace_profile_date_phrases(updated, old_date, new_date)
        date_replacements += phrase_count
        if key in DATE_FIELDS and updated == old_date and old_date != new_date:
            updated = new_date
            date_replacements += 1
        return updated, timestamp_replacements, date_replacements
    return value, 0, 0


def synchronize_file(
    *,
    root: Path,
    relative_path: str,
    old_reference: dict[str, str],
    new_reference: dict[str, str],
    write: bool,
) -> dict[str, Any]:
    path = safe_path(root, relative_path)
    if not path.exists():
        return {
            "path": relative_path,
            "status": "missing",
            "changed": False,
            "timestampReplacements": 0,
            "profileDateReplacements": 0,
        }

    old_timestamp = old_reference["dailyStatusGeneratedAt"]
    new_timestamp = new_reference["dailyStatusGeneratedAt"]
    old_date = old_reference["baseScanProfileCheckedDate"]
    new_date = new_reference["baseScanProfileCheckedDate"]

    if path.suffix == ".json":
        payload = read_json(path)
        updated_payload, timestamp_count, date_count = replace_json_values(
            payload,
            old_timestamp=old_timestamp,
            new_timestamp=new_timestamp,
            old_date=old_date,
            new_date=new_date,
        )
        original = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        updated = json.dumps(updated_payload, ensure_ascii=False, indent=2) + "\n"
        changed = updated != original
    else:
        original = path.read_text(encoding="utf-8")
        updated = original
        timestamp_count = 0
        date_count = 0
        if old_timestamp != new_timestamp:
            timestamp_count = updated.count(old_timestamp)
            updated = updated.replace(old_timestamp, new_timestamp)
        updated, phrase_count = replace_profile_date_phrases(updated, old_date, new_date)
        date_count += phrase_count
        if path.suffix == ".py" and old_date != new_date:
            quoted_old_date = f'"{old_date}"'
            exact_date_count = updated.count(quoted_old_date)
            updated = updated.replace(quoted_old_date, f'"{new_date}"')
            date_count += exact_date_count
        changed = updated != original

    expected_marker = (
        new_date if relative_path in PROFILE_DATE_ONLY_TARGET_FILES else new_timestamp
    )
    canonical_occurrences = updated.count(expected_marker)

    if changed and write:
        path.write_text(updated, encoding="utf-8")
    return {
        "path": relative_path,
        "status": (
            "missing-canonical-reference"
            if canonical_occurrences == 0
            else ("updated" if changed else "aligned")
        ),
        "changed": changed,
        "timestampReplacements": timestamp_count,
        "profileDateReplacements": date_count,
        "canonicalReferenceOccurrences": canonical_occurrences,
    }


def synchronize_references(
    *,
    root: Path = ROOT,
    daily_status_path: Path = DEFAULT_DAILY_STATUS_PATH,
    values_path: Path = DEFAULT_VALUES_PATH,
    target_files: list[str] | None = None,
    write: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    daily_status = read_json(daily_status_path)
    values = read_json(values_path)
    canonical = canonical_reference(daily_status)
    previous = previous_reference(values)
    files = target_files or DEFAULT_TARGET_FILES
    records = [
        synchronize_file(
            root=root,
            relative_path=relative_path,
            old_reference=previous,
            new_reference=canonical,
            write=write,
        )
        for relative_path in files
    ]
    missing = [record["path"] for record in records if record["status"] == "missing"]
    missing_canonical = [
        record["path"] for record in records if record["status"] == "missing-canonical-reference"
    ]
    changed = [record["path"] for record in records if record["changed"]]
    if missing:
        status = "missing-target-files"
    elif missing_canonical:
        status = "missing-canonical-references"
    else:
        status = "updated" if changed else "aligned"
    return {
        "schema": "gca-basescan-daily-status-reference-sync-v1",
        "status": status,
        "ok": not missing and not missing_canonical,
        "writeMode": write,
        "previousReference": previous,
        "canonicalReference": canonical,
        "summary": {
            "filesChecked": len(records),
            "filesChanged": len(changed),
            "missingFiles": len(missing),
            "filesMissingCanonicalReference": len(missing_canonical),
            "timestampReplacements": sum(record["timestampReplacements"] for record in records),
            "profileDateReplacements": sum(record["profileDateReplacements"] for record in records),
        },
        "changedFiles": changed,
        "missingFilePaths": missing,
        "missingCanonicalReferencePaths": missing_canonical,
        "records": records,
        "boundaries": {
            "repositoryFilesOnly": True,
            "submitsBaseScanRequest": False,
            "sendsEmail": False,
            "writesDns": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "touchesWalletsOrContracts": False,
            "readsProductionUserData": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize BaseScan reviewer materials with site/daily-status.json."
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root.")
    parser.add_argument("--daily-status", default="site/daily-status.json", help="Daily status JSON path.")
    parser.add_argument(
        "--values",
        default="launch/basescan_resubmission_values.json",
        help="BaseScan values JSON path containing the previous reference.",
    )
    parser.add_argument("--check", action="store_true", help="Report required changes without writing files.")
    parser.add_argument("--json", action="store_true", help="Print the complete JSON report.")
    return parser.parse_args(argv)


def resolve_under_root(root: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else safe_path(root, value)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    try:
        report = synchronize_references(
            root=root,
            daily_status_path=resolve_under_root(root, args.daily_status),
            values_path=resolve_under_root(root, args.values),
            write=not args.check,
        )
    except DailyStatusReferenceSyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("GCA BaseScan daily-status reference sync")
        print(f"status: {report['status']}")
        print(f"filesChanged: {report['summary']['filesChanged']}")
        print(f"timestampReplacements: {report['summary']['timestampReplacements']}")
        print(f"profileDateReplacements: {report['summary']['profileDateReplacements']}")

    if not report["ok"]:
        return 2
    if args.check and report["summary"]["filesChanged"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
