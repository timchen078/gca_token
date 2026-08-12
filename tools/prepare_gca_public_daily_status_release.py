#!/usr/bin/env python3
"""Prepare a public-only daily-status release in an isolated site tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from tools.build_gca_daily_status_snapshot import (
        DailyStatusSnapshotError,
        build_snapshot,
        load_summary,
    )
    from tools.sync_basescan_daily_status_references import (
        DailyStatusReferenceSyncError,
        PUBLIC_SITE_TARGET_FILES,
        canonical_reference,
        synchronize_references,
    )
except ImportError:
    from build_gca_daily_status_snapshot import (
        DailyStatusSnapshotError,
        build_snapshot,
        load_summary,
    )
    from sync_basescan_daily_status_references import (
        DailyStatusReferenceSyncError,
        PUBLIC_SITE_TARGET_FILES,
        canonical_reference,
        synchronize_references,
    )


ROOT = Path(__file__).resolve().parents[1]
DAILY_STATUS_FILES = ("site/daily-status.html", "site/daily-status.json")
ALLOWED_RELEASE_FILES = frozenset((*DAILY_STATUS_FILES, *PUBLIC_SITE_TARGET_FILES))
REQUIRED_STEP_IDS = {
    "public-site",
    "registration-api-public",
    "official-pool-market-health",
    "basescan-public-profile-status",
    "basescan-resubmission-preflight-status",
}
FORBIDDEN_PUBLIC_MARKERS = (
    "/Users/",
    "ADMIN_READ_TOKEN",
    "cxy070800@gmail.com",
    "GCAgochina@outlook.com",
)
EPHEMERAL_SUMMARY_KEYS = frozenset({
    "summaryOutput",
    "operatorDigest",
    "publicStatusSnapshot",
})


class PublicDailyStatusReleaseError(RuntimeError):
    """Raised when an automated public release crosses a safety boundary."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_site_tree(site_root: Path) -> dict[str, str]:
    if not site_root.is_dir():
        raise PublicDailyStatusReleaseError(f"site root is missing: {site_root}")
    snapshot: dict[str, str] = {}
    for path in sorted(site_root.rglob("*")):
        if path.is_symlink():
            raise PublicDailyStatusReleaseError(f"site tree must not contain symlinks: {path}")
        if path.is_file():
            snapshot[path.relative_to(site_root).as_posix()] = sha256_file(path)
    return snapshot


def validate_summary(summary: dict[str, Any]) -> tuple[str, list[str]]:
    generated_at = str(summary.get("generatedAt") or "")
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated_at):
        raise PublicDailyStatusReleaseError("daily summary generatedAt is not an ISO UTC timestamp")
    if summary.get("ok") is not True:
        raise PublicDailyStatusReleaseError("daily summary did not pass")
    if summary.get("packetVersion") != "gca_daily_ops_summary_v1":
        raise PublicDailyStatusReleaseError("daily summary packet version is not supported")
    unknown_ephemeral = sorted(EPHEMERAL_SUMMARY_KEYS.intersection(summary))
    for key in unknown_ephemeral:
        summary.pop(key, None)
    for key in ("includeMemberOps", "includeServiceRoutes", "includeHoldingReport"):
        if summary.get(key) is not False:
            raise PublicDailyStatusReleaseError(f"automated public release requires {key}=false")

    boundaries = summary.get("boundaries")
    if not isinstance(boundaries, dict):
        raise PublicDailyStatusReleaseError("daily summary boundaries are missing")
    required_true = (
        "publicOnlyByDefault",
        "baseScanPublicProfileReadOnly",
        "baseScanPreflightStatusOnly",
        "marketHealthReadOnly",
    )
    required_false = (
        "writesProductionData",
        "adminTokenPrinted",
        "walletCalls",
        "requiresSignature",
        "requiresTransaction",
        "automaticTokenTransfer",
        "submitsBaseScanRequest",
        "marketHealthBuildsExecutableQuote",
        "marketHealthSubmitsTrade",
    )
    for key in required_true:
        if boundaries.get(key) is not True:
            raise PublicDailyStatusReleaseError(f"daily summary boundary must be true: {key}")
    for key in required_false:
        if boundaries.get(key) is not False:
            raise PublicDailyStatusReleaseError(f"daily summary boundary must be false: {key}")

    steps = summary.get("steps")
    if not isinstance(steps, list):
        raise PublicDailyStatusReleaseError("daily summary steps are missing")
    step_map = {
        str(step.get("id")): step
        for step in steps
        if isinstance(step, dict) and step.get("id")
    }
    if set(step_map) != REQUIRED_STEP_IDS:
        raise PublicDailyStatusReleaseError("daily summary contains an unexpected public step set")
    failed = sorted(step_id for step_id, step in step_map.items() if step.get("ok") is not True)
    return generated_at, failed


def skipped_release_report(
    *,
    status: str,
    generated_at: str,
    previous_snapshot_generated_at: str,
    failed_observations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "gca-public-daily-status-release-v1",
        "ok": True,
        "status": status,
        "publishRequired": False,
        "previousSnapshotGeneratedAt": previous_snapshot_generated_at,
        "snapshotGeneratedAt": generated_at,
        "failedObservations": failed_observations or [],
        "changedFiles": [],
        "boundaries": {
            "publicSiteFilesOnly": True,
            "writesMainBranch": False,
            "publishesOperatorDigest": False,
            "readsProductionUserData": False,
            "touchesWalletsOrContracts": False,
            "submitsBaseScanRequest": False,
            "requiresSignature": False,
            "requiresTransaction": False,
        },
    }


def validate_public_payload(payload: dict[str, Any]) -> None:
    boundaries = payload.get("boundaries")
    if not isinstance(boundaries, dict):
        raise PublicDailyStatusReleaseError("public snapshot boundaries are missing")
    true_boundaries = ("publicOnly", "readsPublicMarketApiOnly", "readsBaseScanPublicPagesOnly")
    false_boundaries = (
        "adminTokenPrinted",
        "userEmailsPrinted",
        "writesProductionData",
        "submitsBaseScanRequest",
        "sendsEmail",
        "writesDns",
        "requiresSignature",
        "requiresTransaction",
        "touchesWalletsOrContracts",
        "buildsExecutableMarketQuote",
        "submitsTrade",
        "claimsOrganicDemandFromAggregateData",
    )
    for key in true_boundaries:
        if boundaries.get(key) is not True:
            raise PublicDailyStatusReleaseError(f"public snapshot boundary must be true: {key}")
    for key in false_boundaries:
        if boundaries.get(key) is not False:
            raise PublicDailyStatusReleaseError(f"public snapshot boundary must be false: {key}")


def validate_stable_public_state(
    old_payload: dict[str, Any],
    new_payload: dict[str, Any],
) -> None:
    """Block timestamp-only releases when a static reviewer claim must also change."""
    old_profile = old_payload.get("baseScanPublicProfile")
    new_profile = new_payload.get("baseScanPublicProfile")
    if not isinstance(old_profile, dict) or not isinstance(new_profile, dict):
        raise PublicDailyStatusReleaseError("BaseScan profile state is missing from a snapshot")
    profile_fields = (
        "status",
        "profilePublished",
        "tokenRep",
        "sourceVerificationObserved",
        "officialDomainPresent",
        "genericAddressTitle",
        "defaultPreviewImage",
    )
    changed_profile_fields = [
        field for field in profile_fields if old_profile.get(field) != new_profile.get(field)
    ]
    if changed_profile_fields:
        raise PublicDailyStatusReleaseError(
            "BaseScan public profile state changed; update the static reviewer package on main first: "
            + ", ".join(changed_profile_fields)
        )

    old_preflight = old_payload.get("baseScanPreflight")
    new_preflight = new_payload.get("baseScanPreflight")
    if not isinstance(old_preflight, dict) or not isinstance(new_preflight, dict):
        raise PublicDailyStatusReleaseError("BaseScan preflight state is missing from a snapshot")
    preflight_fields = (
        "status",
        "readyForBaseScanResubmission",
        "publicEmailSwitchStatus",
        "snapshotAlignmentStatus",
        "filesStillUsingOldEmail",
        "filesPublishingForbiddenLegacyEmail",
        "missingOrBlockedRequirements",
    )
    changed_preflight_fields = [
        field for field in preflight_fields if old_preflight.get(field) != new_preflight.get(field)
    ]
    if changed_preflight_fields:
        raise PublicDailyStatusReleaseError(
            "BaseScan preflight state changed; update the static reviewer package on main first: "
            + ", ".join(changed_preflight_fields)
        )


def ensure_safe_public_files(release_root: Path, changed_files: list[str]) -> None:
    for relative_path in changed_files:
        path = (release_root / relative_path).resolve()
        try:
            path.relative_to((release_root / "site").resolve())
        except ValueError as exc:
            raise PublicDailyStatusReleaseError(
                f"release output escaped the public site tree: {relative_path}"
            ) from exc
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_PUBLIC_MARKERS:
            if marker.lower() in text.lower():
                raise PublicDailyStatusReleaseError(
                    f"public release contains forbidden marker {marker!r}: {relative_path}"
                )


def prepare_release(
    *,
    summary_input: Path,
    release_root: Path,
) -> dict[str, Any]:
    release_root = release_root.resolve()
    if release_root == ROOT.resolve():
        raise PublicDailyStatusReleaseError("release root must be an isolated staging tree")
    site_root = release_root / "site"
    before = snapshot_site_tree(site_root)
    summary = load_summary(summary_input)
    generated_at, failed_observations = validate_summary(summary)

    daily_json = site_root / "daily-status.json"
    daily_html = site_root / "daily-status.html"
    for path in (daily_json, daily_html):
        if not path.is_file() or path.is_symlink():
            raise PublicDailyStatusReleaseError(f"required regular file is missing: {path}")

    old_payload = json.loads(daily_json.read_text(encoding="utf-8"))
    old_reference = canonical_reference(old_payload)
    if failed_observations:
        return skipped_release_report(
            status="incomplete-public-observation-skipped",
            generated_at=generated_at,
            previous_snapshot_generated_at=old_reference["dailyStatusGeneratedAt"],
            failed_observations=failed_observations,
        )
    if generated_at <= old_reference["dailyStatusGeneratedAt"]:
        return skipped_release_report(
            status="stale-or-duplicate-summary-skipped",
            generated_at=generated_at,
            previous_snapshot_generated_at=old_reference["dailyStatusGeneratedAt"],
        )

    sanitized_summary_path = release_root / "gca_public_daily_ops_summary.json"
    sanitized_summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    values_path = release_root / "launch" / "basescan_resubmission_values.json"
    values_path.parent.mkdir(parents=True, exist_ok=True)
    values_path.write_text(
        json.dumps(
            {
                "dailyStatusGeneratedAt": old_reference["dailyStatusGeneratedAt"],
                "lastCheckedDate": old_reference["baseScanProfileCheckedDate"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_snapshot(sanitized_summary_path, daily_json, daily_html)
    validate_public_payload(payload)
    validate_stable_public_state(old_payload, payload)
    sync_report = synchronize_references(
        root=release_root,
        daily_status_path=daily_json,
        values_path=values_path,
        target_files=PUBLIC_SITE_TARGET_FILES,
        write=True,
    )
    if not sync_report.get("ok"):
        raise PublicDailyStatusReleaseError(
            "public BaseScan reference synchronization did not complete safely"
        )

    after = snapshot_site_tree(site_root)
    changed_relative = sorted(
        path for path in set(before) | set(after) if before.get(path) != after.get(path)
    )
    changed_files = [f"site/{path}" for path in changed_relative]
    unexpected = sorted(set(changed_files) - ALLOWED_RELEASE_FILES)
    if unexpected:
        raise PublicDailyStatusReleaseError(
            "release changed files outside the public allowlist: " + ", ".join(unexpected)
        )
    for required in DAILY_STATUS_FILES:
        if required not in changed_files:
            raise PublicDailyStatusReleaseError(f"release did not refresh required file: {required}")
    ensure_safe_public_files(release_root, changed_files)

    return {
        "schema": "gca-public-daily-status-release-v1",
        "ok": True,
        "status": "prepared",
        "publishRequired": True,
        "previousSnapshotGeneratedAt": old_reference["dailyStatusGeneratedAt"],
        "snapshotGeneratedAt": payload["snapshotGeneratedAt"],
        "baseScanProfileCheckedAt": payload["baseScanPublicProfile"]["checkedAt"],
        "changedFiles": changed_files,
        "referenceSync": {
            "status": sync_report["status"],
            "filesChanged": sync_report["summary"]["filesChanged"],
            "timestampReplacements": sync_report["summary"]["timestampReplacements"],
            "profileDateReplacements": sync_report["summary"]["profileDateReplacements"],
        },
        "boundaries": {
            "publicSiteFilesOnly": True,
            "writesMainBranch": False,
            "publishesOperatorDigest": False,
            "readsProductionUserData": False,
            "touchesWalletsOrContracts": False,
            "submitsBaseScanRequest": False,
            "requiresSignature": False,
            "requiresTransaction": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-input", type=Path, required=True)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--report-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = prepare_release(
            summary_input=args.summary_input,
            release_root=args.release_root,
        )
    except (
        DailyStatusSnapshotError,
        DailyStatusReferenceSyncError,
        PublicDailyStatusReleaseError,
        json.JSONDecodeError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report_output:
        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
