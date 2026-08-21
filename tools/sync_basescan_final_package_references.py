#!/usr/bin/env python3
"""Synchronize BaseScan handoff references with the final owner package.

The final submission package is regenerated independently from the public
handoff and reviewer materials. This tool keeps the duplicated package
timestamp and copy/paste blocks aligned without submitting forms, sending
email, signing messages, or touching wallets/contracts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_PATH = ROOT / "launch" / "basescan_final_submission_package.json"
DEFAULT_VALUES_PATH = ROOT / "launch" / "basescan_resubmission_values.json"

DEFAULT_TARGET_FILES = [
    "launch/basescan_final_submission_package.json",
    "launch/basescan_final_submission_package.md",
    "launch/basescan_form_values.json",
    "launch/basescan_resubmission_package.md",
    "launch/basescan_resubmission_values.json",
    "launch/basescan_review_followup.md",
    "launch/basescan_reviewer_checklist.json",
    "launch/basescan_reviewer_checklist.md",
    "launch/basescan_token_submission.md",
    "launch/external_review_followup_tracker.json",
    "site/announcements.html",
    "site/announcements.json",
    "site/basescan-handoff.html",
    "site/basescan-handoff.json",
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
    "site/token-safety.html",
    "site/trust.html",
    "site/trust.json",
    "site/zh-basescan-preflight.html",
    "site/zh-release-gates.html",
    "tests/test_basescan_reviewer_checklist.py",
    "tests/test_launch_package.py",
    "tools/check_public_site.py",
]


class FinalPackageReferenceSyncError(RuntimeError):
    """Raised when final-package references cannot be synchronized safely."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FinalPackageReferenceSyncError(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FinalPackageReferenceSyncError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise FinalPackageReferenceSyncError(f"JSON file must contain an object: {path}")
    return payload


def require_timestamp(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text):
        raise FinalPackageReferenceSyncError(
            f"{label} must be an ISO UTC timestamp ending in Z"
        )
    return text


def canonical_reference(package: dict[str, Any]) -> dict[str, str]:
    if package.get("schema") != "gca-basescan-submission-package-v1":
        raise FinalPackageReferenceSyncError("final package has an unexpected schema")
    if package.get("readyForOwnerSubmission") is not True:
        raise FinalPackageReferenceSyncError(
            "final package must be readyForOwnerSubmission before references are updated"
        )
    guard = package.get("dailyStatusReferenceGuard")
    if not isinstance(guard, dict) or guard.get("aligned") is not True:
        raise FinalPackageReferenceSyncError(
            "final package must include an aligned dailyStatusReferenceGuard"
        )
    package_timestamp = require_timestamp(package.get("generatedAt"), "final-package.generatedAt")
    daily_reference = guard.get("canonicalReference")
    if not isinstance(daily_reference, dict):
        raise FinalPackageReferenceSyncError(
            "final-package.dailyStatusReferenceGuard.canonicalReference must be an object"
        )
    daily_timestamp = require_timestamp(
        daily_reference.get("dailyStatusGeneratedAt"),
        "final-package.dailyStatusReferenceGuard.canonicalReference.dailyStatusGeneratedAt",
    )
    return {
        "finalPackageGeneratedAt": package_timestamp,
        "finalPackageDate": package_timestamp.split("T", 1)[0],
        "dailyStatusGeneratedAt": daily_timestamp,
    }


def previous_reference(values: dict[str, Any]) -> dict[str, str]:
    timestamp = require_timestamp(
        values.get("baseScanFinalSubmissionPackageGeneratedAt"),
        "basescan-resubmission-values.baseScanFinalSubmissionPackageGeneratedAt",
    )
    return {
        "finalPackageGeneratedAt": timestamp,
        "finalPackageDate": timestamp.split("T", 1)[0],
    }


def safe_path(root: Path, relative_path: str) -> Path:
    if Path(relative_path).is_absolute():
        raise FinalPackageReferenceSyncError(f"target path must be relative: {relative_path}")
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise FinalPackageReferenceSyncError(
            f"target path escapes repository: {relative_path}"
        ) from exc
    return path


def replace_package_date_phrases(
    text: str,
    old_date: str,
    new_date: str,
) -> tuple[str, int]:
    if old_date == new_date:
        return text, 0
    pattern = re.compile(
        rf"(?P<prefix>(?:final|latest)\s+"
        rf"(?:(?:BaseScan)\s+)?(?:(?:owner)\s+)?(?:(?:submission)\s+)?"
        rf"package(?:\s+was)?\s+(?:generated|regenerated|refreshed)"
        rf"(?:\s+(?:on|at))?\s+){re.escape(old_date)}",
        re.I,
    )
    return pattern.subn(rf"\g<prefix>{new_date}", text)


def replace_values(
    value: Any,
    *,
    old_timestamp: str,
    new_timestamp: str,
    old_date: str,
    new_date: str,
) -> tuple[Any, int, int]:
    timestamp_replacements = 0
    date_replacements = 0
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            replacement, timestamp_count, date_count = replace_values(
                child,
                old_timestamp=old_timestamp,
                new_timestamp=new_timestamp,
                old_date=old_date,
                new_date=new_date,
            )
            result[key] = replacement
            timestamp_replacements += timestamp_count
            date_replacements += date_count
        return result, timestamp_replacements, date_replacements
    if isinstance(value, list):
        result_list: list[Any] = []
        for child in value:
            replacement, timestamp_count, date_count = replace_values(
                child,
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
        updated, count = replace_package_date_phrases(updated, old_date, new_date)
        date_replacements += count
        return updated, timestamp_replacements, date_replacements
    return value, 0, 0


def update_handoff_payload(
    payload: dict[str, Any],
    package: dict[str, Any],
) -> dict[str, Any]:
    final_package = payload.get("finalSubmissionPackage")
    if not isinstance(final_package, dict):
        raise FinalPackageReferenceSyncError(
            "site/basescan-handoff.json finalSubmissionPackage must be an object"
        )
    final_package["status"] = package.get("status")
    final_package["generatedAt"] = package.get("generatedAt")
    final_package["copyPasteContent"] = package.get("copyPasteBlocks", {})
    final_package["preflightSummary"] = package.get("preflightSummary", {})
    final_package["dailyStatusReferenceGuard"] = package.get(
        "dailyStatusReferenceGuard", {}
    )
    final_package["referenceSynchronization"] = {
        "tool": "tools/sync_basescan_final_package_references.py",
        "status": "aligned-after-canonical-build",
        "canonicalGeneratedAt": package.get("generatedAt"),
        "checkCommand": (
            "python3 tools/sync_basescan_final_package_references.py --check --json"
        ),
    }
    package_date = str(package.get("generatedAt") or "").split("T", 1)[0]
    current_date = str(payload.get("lastUpdated") or "")
    payload["lastUpdated"] = (
        max(current_date, package_date)
        if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", current_date)
        else package_date
    )
    return payload


def update_preflight_payload(
    payload: dict[str, Any],
    package: dict[str, Any],
) -> dict[str, Any]:
    refresh = payload.get("preflightRefresh")
    if not isinstance(refresh, dict):
        raise FinalPackageReferenceSyncError(
            "site/basescan-preflight.json preflightRefresh must be an object"
        )
    generated_at = str(package.get("generatedAt") or "")
    refresh["refreshedAt"] = generated_at.split("T", 1)[0]
    refresh["finalSubmissionPackageGeneratedAt"] = generated_at
    refresh["finalPackageReferenceAlignment"] = {
        "tool": "tools/sync_basescan_final_package_references.py",
        "status": "aligned-after-canonical-build",
        "checkCommand": (
            "python3 tools/sync_basescan_final_package_references.py --check --json"
        ),
    }
    return payload


def synchronize_file(
    *,
    root: Path,
    relative_path: str,
    old_reference: dict[str, str],
    new_reference: dict[str, str],
    package: dict[str, Any],
    write: bool,
) -> dict[str, Any]:
    path = safe_path(root, relative_path)
    if not path.exists():
        return {
            "path": relative_path,
            "status": "missing",
            "changed": False,
            "timestampReplacements": 0,
            "packageDateReplacements": 0,
        }

    old_timestamp = old_reference["finalPackageGeneratedAt"]
    new_timestamp = new_reference["finalPackageGeneratedAt"]
    old_date = old_reference["finalPackageDate"]
    new_date = new_reference["finalPackageDate"]

    if path.suffix == ".json":
        payload = read_json(path)
        updated_payload, timestamp_count, date_count = replace_values(
            payload,
            old_timestamp=old_timestamp,
            new_timestamp=new_timestamp,
            old_date=old_date,
            new_date=new_date,
        )
        if relative_path == "site/basescan-handoff.json":
            updated_payload = update_handoff_payload(updated_payload, package)
        elif relative_path == "site/basescan-preflight.json":
            updated_payload = update_preflight_payload(updated_payload, package)
        original = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        updated = json.dumps(updated_payload, ensure_ascii=False, indent=2) + "\n"
    else:
        original = path.read_text(encoding="utf-8")
        updated = original
        timestamp_count = 0
        date_count = 0
        if old_timestamp != new_timestamp:
            timestamp_count = updated.count(old_timestamp)
            updated = updated.replace(old_timestamp, new_timestamp)
        updated, date_count = replace_package_date_phrases(updated, old_date, new_date)

    changed = updated != original
    canonical_occurrences = updated.count(new_timestamp)
    status = "missing-canonical-reference" if canonical_occurrences == 0 else (
        "updated" if changed else "aligned"
    )
    if changed and write:
        path.write_text(updated, encoding="utf-8")
    return {
        "path": relative_path,
        "status": status,
        "changed": changed,
        "timestampReplacements": timestamp_count,
        "packageDateReplacements": date_count,
        "canonicalReferenceOccurrences": canonical_occurrences,
    }


def synchronize_references(
    *,
    root: Path = ROOT,
    package_path: Path = DEFAULT_PACKAGE_PATH,
    values_path: Path = DEFAULT_VALUES_PATH,
    target_files: list[str] | None = None,
    write: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    package = read_json(package_path)
    values = read_json(values_path)
    canonical = canonical_reference(package)
    previous = previous_reference(values)
    files = target_files or DEFAULT_TARGET_FILES
    records = [
        synchronize_file(
            root=root,
            relative_path=relative_path,
            old_reference=previous,
            new_reference=canonical,
            package=package,
            write=False,
        )
        for relative_path in files
    ]
    missing = [record["path"] for record in records if record["status"] == "missing"]
    missing_canonical = [
        record["path"]
        for record in records
        if record["status"] == "missing-canonical-reference"
    ]
    changed = [record["path"] for record in records if record["changed"]]
    if write and not missing and not missing_canonical:
        records = [
            synchronize_file(
                root=root,
                relative_path=relative_path,
                old_reference=previous,
                new_reference=canonical,
                package=package,
                write=True,
            )
            for relative_path in files
        ]
    if missing:
        status = "missing-target-files"
    elif missing_canonical:
        status = "missing-canonical-references"
    else:
        status = "updated" if changed else "aligned"
    return {
        "schema": "gca-basescan-final-package-reference-sync-v1",
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
            "timestampReplacements": sum(
                record["timestampReplacements"] for record in records
            ),
            "packageDateReplacements": sum(
                record["packageDateReplacements"] for record in records
            ),
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
        description="Synchronize BaseScan reviewer materials with the final owner package."
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root.")
    parser.add_argument(
        "--package",
        default="launch/basescan_final_submission_package.json",
        help="Final BaseScan package JSON path.",
    )
    parser.add_argument(
        "--values",
        default="launch/basescan_resubmission_values.json",
        help="BaseScan values JSON path containing the previous package timestamp.",
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
            package_path=resolve_under_root(root, args.package),
            values_path=resolve_under_root(root, args.values),
            write=not args.check,
        )
    except FinalPackageReferenceSyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("GCA BaseScan final-package reference sync")
        print(f"status: {report['status']}")
        print(f"filesChanged: {report['summary']['filesChanged']}")
        print(f"timestampReplacements: {report['summary']['timestampReplacements']}")
        print(f"packageDateReplacements: {report['summary']['packageDateReplacements']}")

    if not report["ok"]:
        return 2
    if args.check and report["summary"]["filesChanged"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
