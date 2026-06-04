"""Build the GCA domain-email public switch plan.

This tool is read-only unless explicit output paths are provided. It scans
public project materials for the current Outlook contact and target domain
mailbox so the owner can switch records only after domain-email evidence is
ready.
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CURRENT_EMAIL = "GCAgochina@outlook.com"
TARGET_EMAIL = "support@gcagochina.com"

SCAN_ROOTS = (
    ROOT / "site",
    ROOT / "launch",
    ROOT / "docs",
)
EXPLICIT_FILES = (
    ROOT / "tools" / "gca_member_backend.py",
)
TEXT_SUFFIXES = {
    ".html",
    ".json",
    ".md",
    ".txt",
    ".py",
    ".toml",
    ".yml",
    ".yaml",
}
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "package-lock.json",
    "assets",
    "brand",
    "token",
    "domain_email_evidence",
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def should_scan(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDED_PARTS:
        return False
    return path.is_file() and path.suffix in TEXT_SUFFIXES


def iter_scan_files() -> list[Path]:
    files: set[Path] = set()
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if should_scan(path):
                files.add(path)
    for path in EXPLICIT_FILES:
        if should_scan(path):
            files.add(path)
    return sorted(files, key=rel)


def classify(path: Path) -> str:
    relative = rel(path)
    if relative.startswith("site/.well-known/"):
        return "well-known identity"
    if relative.startswith("site/") and relative.endswith(".html"):
        return "public page"
    if relative.startswith("site/") and relative.endswith(".json"):
        return "public structured data"
    if relative.startswith("launch/"):
        return "owner launch package"
    if relative.startswith("docs/"):
        return "project documentation"
    if relative.startswith("tools/"):
        return "operator backend/tool"
    return "other"


def scan_file(path: Path, current_email: str, target_email: str) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    current_count = text.count(current_email)
    target_count = text.count(target_email)
    if current_count == 0 and target_count == 0:
        return None
    return {
        "path": rel(path),
        "category": classify(path),
        "currentEmailOccurrences": current_count,
        "targetEmailOccurrences": target_count,
        "switchRequiredAfterActivation": current_count > 0,
        "notes": (
            "Replace or review current public contact references after the domain mailbox is active."
            if current_count
            else "Target domain email is already mentioned as a future or evidence-gated mailbox."
        ),
    }


def public_switch_is_complete() -> bool:
    config_path = ROOT / "site" / "domain-email.json"
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    current_public_email = payload.get("currentPublicEmail")
    target_domain_email = payload.get("targetDomainEmail")
    snapshot = payload.get("currentPublicSwitchSnapshot")
    return (
        current_public_email == target_domain_email == TARGET_EMAIL
        and isinstance(snapshot, dict)
        and snapshot.get("status") == "public-email-switch-complete"
        and snapshot.get("filesStillUsingCurrentEmail") == 0
    )


def build_plan(
    *,
    current_email: str = CURRENT_EMAIL,
    target_email: str = TARGET_EMAIL,
) -> dict[str, Any]:
    legacy_email = current_email
    records = [
        record
        for path in iter_scan_files()
        if (record := scan_file(path, legacy_email, target_email)) is not None
    ]
    switch_required = [record for record in records if record["switchRequiredAfterActivation"]]
    categories: dict[str, int] = {}
    for record in records:
        categories[record["category"]] = categories.get(record["category"], 0) + 1
    switch_complete = public_switch_is_complete()
    if switch_complete:
        for record in records:
            if record["switchRequiredAfterActivation"]:
                record["switchRequiredAfterActivation"] = False
                record["notes"] = "Legacy previous-email reference retained for audit context; public switch is complete."
        switch_required = []

    return {
        "schema": "gca-domain-email-switch-plan-v1",
        "currentEmail": target_email if switch_complete else current_email,
        "legacyEmail": legacy_email,
        "targetDomainEmail": target_email,
        "status": "public-email-switch-complete" if switch_complete else "blocked-until-domain-email-evidence-ready",
        "summary": {
            "scannedFilesWithEmailReferences": len(records),
            "filesRequiringSwitchAfterActivation": len(switch_required),
            "categories": dict(sorted(categories.items())),
        },
        "patchPreview": {
            "command": "python3 tools/build_domain_email_switch_plan.py --patch",
            "ownerArtifactCommand": (
                "python3 tools/build_domain_email_switch_plan.py "
                "--output-patch launch/domain_email_switch_preview.patch"
            ),
            "filesWithExactReplacement": len(switch_required),
            "replacementOccurrences": sum(record["currentEmailOccurrences"] for record in switch_required),
            "exactReplacementOnly": True,
            "appliesChanges": False,
        },
        "requiredPreconditions": [
            "support@gcagochina.com receives external email",
            "support@gcagochina.com sends authenticated external email",
            "MX, SPF, DKIM, and DMARC checks pass",
            "launch/domain_email_evidence_packet.json reports readyForBaseScanResubmission true",
            "tools/check_basescan_resubmission_readiness.py reports readyForBaseScanResubmission true",
        ],
        "switchOrder": [
            "Update public support and user-intake pages first.",
            "Update public structured project/listing/reviewer JSON next.",
            "Update BaseScan launch values and platform reply templates.",
            "Run the full test suite and public site checker.",
            "Submit one clean BaseScan update from the activated domain mailbox where possible.",
        ],
        "records": records,
        "boundaries": {
            "readOnlyScanByDefault": True,
            "writesPublicFiles": False,
            "sendsEmail": False,
            "writesDns": False,
            "submitsBaseScanRequest": False,
            "touchesWalletsOrContracts": False,
        },
    }


def build_patch_preview(plan: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    legacy_email = str(plan.get("legacyEmail") or plan.get("currentEmail") or CURRENT_EMAIL)
    current_email = str(plan.get("currentEmail") or TARGET_EMAIL)
    target_email = str(plan.get("targetDomainEmail") or TARGET_EMAIL)
    diff_lines: list[str] = []
    records: list[dict[str, Any]] = []
    root = root.resolve()

    for record in plan.get("records", []):
        if not isinstance(record, dict) or not record.get("switchRequiredAfterActivation"):
            continue
        relative_path = str(record.get("path") or "")
        if not relative_path or Path(relative_path).is_absolute():
            continue
        path = (root / relative_path).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        try:
            before = path.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError):
            continue
        after = before.replace(legacy_email, target_email)
        if after == before:
            continue
        file_diff = list(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}",
            )
        )
        diff_lines.extend(file_diff)
        records.append({
            "path": relative_path,
            "category": str(record.get("category") or ""),
            "replacementOccurrences": int(record.get("currentEmailOccurrences") or 0),
        })

    return {
        "schema": "gca-domain-email-switch-patch-preview-v1",
        "status": "preview-only-not-applied",
        "currentEmail": current_email,
        "legacyEmail": legacy_email,
        "targetDomainEmail": target_email,
        "summary": {
            "filesWithExactReplacement": len(records),
            "replacementOccurrences": sum(record["replacementOccurrences"] for record in records),
            "diffLines": len(diff_lines),
        },
        "records": records,
        "patch": "".join(diff_lines),
        "boundaries": {
            "previewOnly": True,
            "writesPublicFiles": False,
            "sendsEmail": False,
            "writesDns": False,
            "submitsBaseScanRequest": False,
            "touchesWalletsOrContracts": False,
        },
    }


def render_patch_preview(plan: dict[str, Any]) -> str:
    preview = build_patch_preview(plan)
    return preview["patch"]


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# GCA Domain Email Public Switch Plan",
        "",
        f"- Current public email: `{plan['currentEmail']}`",
        f"- Legacy email scanned: `{plan['legacyEmail']}`",
        f"- Target domain email: `{plan['targetDomainEmail']}`",
        f"- Status: `{plan['status']}`",
        f"- Files requiring switch after activation: `{plan['summary']['filesRequiringSwitchAfterActivation']}`",
        "",
        "## Required Preconditions",
        "",
    ]
    lines.extend(f"- {item}" for item in plan["requiredPreconditions"])
    lines.extend([
        "",
        "## Patch Preview",
        "",
        f"- Command: `{plan['patchPreview']['command']}`",
        f"- Owner artifact: `{plan['patchPreview']['ownerArtifactCommand']}`",
        "- The patch preview is an exact replacement diff only; it is not applied by this tool.",
    ])
    lines.extend(["", "## Switch Order", ""])
    lines.extend(f"{index}. {item}" for index, item in enumerate(plan["switchOrder"], start=1))
    lines.extend(["", "## File Records", ""])
    lines.append("| File | Category | Legacy refs | Target refs | Action |")
    lines.append("| --- | --- | ---: | ---: | --- |")
    for record in plan["records"]:
        action = "switch after evidence" if record["switchRequiredAfterActivation"] else "review target mention"
        lines.append(
            f"| `{record['path']}` | {record['category']} | "
            f"{record['currentEmailOccurrences']} | {record['targetEmailOccurrences']} | {action} |"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- This plan does not change public files by itself.",
            "- The patch preview is a generated diff only and does not write public files.",
            "- This plan does not send email, write DNS, submit BaseScan requests, or touch wallets/contracts.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the GCA domain email public switch plan.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a text summary.")
    parser.add_argument("--markdown", action="store_true", help="Print markdown instead of a text summary.")
    parser.add_argument("--patch", action="store_true", help="Print a unified diff preview for exact email replacements.")
    parser.add_argument("--output-json", help="Optional JSON output path.")
    parser.add_argument("--output-md", help="Optional markdown output path.")
    parser.add_argument("--output-patch", help="Optional unified diff patch preview output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plan()

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(render_markdown(plan), encoding="utf-8")
    if args.output_patch:
        Path(args.output_patch).write_text(render_patch_preview(plan), encoding="utf-8")

    if args.patch:
        print(render_patch_preview(plan), end="")
    elif args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    elif args.markdown:
        print(render_markdown(plan), end="")
    else:
        print("GCA domain email public switch plan")
        print(f"status: {plan['status']}")
        print(f"currentEmail: {plan['currentEmail']}")
        print(f"targetDomainEmail: {plan['targetDomainEmail']}")
        print(f"filesRequiringSwitchAfterActivation: {plan['summary']['filesRequiringSwitchAfterActivation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
