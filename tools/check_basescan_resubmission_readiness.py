#!/usr/bin/env python3
"""Check whether GCA is ready for a clean BaseScan token-profile resubmission.

The preflight is read-only. It validates the local BaseScan values packet, the
domain-email evidence packet, public email switch alignment, and public
reviewer URLs. It does not submit BaseScan forms, send email, write DNS
records, or touch wallets/contracts.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

try:
    from tools.check_domain_email_dns import utc_now
    from tools.check_domain_email_public_switch import (
        PublicSwitchCheckError,
        build_report as build_public_switch_report,
    )
    from tools.check_domain_email_snapshot_alignment import (
        SnapshotAlignmentError,
        build_report as build_snapshot_alignment_report,
    )
except ModuleNotFoundError:  # pragma: no cover - used when running from tools/
    from check_domain_email_dns import utc_now
    from check_domain_email_public_switch import (
        PublicSwitchCheckError,
        build_report as build_public_switch_report,
    )
    from check_domain_email_snapshot_alignment import (
        SnapshotAlignmentError,
        build_report as build_snapshot_alignment_report,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VALUES_PATH = ROOT / "launch" / "basescan_resubmission_values.json"
DEFAULT_EVIDENCE_PACKET_PATH = ROOT / "launch" / "domain_email_evidence_packet.json"
TARGET_DOMAIN_EMAIL = "support@gcagochina.com"

REQUIRED_URL_FIELDS = (
    "website",
    "verifyUrl",
    "statusPageUrl",
    "teamPageUrl",
    "timChenProfessionalProfileUrl",
    "domainEmailSetupPlanUrl",
    "domainEmailSetupPlanDataUrl",
    "baseScanRemediationPageUrl",
    "baseScanRemediationUrl",
    "listingKitUrl",
    "brandKitPageUrl",
    "brandKitUrl",
    "communityPageUrl",
    "communityUrl",
    "externalReviewStatusPageUrl",
    "externalReviewStatusUrl",
    "projectJsonUrl",
    "tokenListUrl",
    "wellKnownTokenIdentityUrl",
    "whitepaperUrl",
    "logoSvgUrl",
    "logoPngUrl",
)


class BaseScanReadinessError(RuntimeError):
    """Raised for expected operator-facing readiness errors."""


UrlOpener = Callable[..., Any]


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BaseScanReadinessError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BaseScanReadinessError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BaseScanReadinessError(f"{path} must contain a JSON object")
    return payload


def maybe_load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json_file(path)


def status_entry(key: str, ok: bool, message: str, evidence: Any = None) -> dict[str, Any]:
    return {
        "key": key,
        "ok": ok,
        "message": message,
        "evidence": evidence,
    }


def build_ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore
    except ModuleNotFoundError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def fetch_url(url: str, *, timeout: float, opener: UrlOpener = urllib.request.urlopen) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "GCA-BaseScan-Preflight/1.0"})
    context = build_ssl_context() if url.lower().startswith("https://") else None
    try:
        try:
            response_handle = opener(request, timeout=timeout, context=context) if context else opener(request, timeout=timeout)
        except TypeError:
            response_handle = opener(request, timeout=timeout)
        with response_handle as response:
            status = int(getattr(response, "status", getattr(response, "code", 200)))
            body = response.read(4096)
    except urllib.error.HTTPError as exc:
        return {"url": url, "ok": False, "status": exc.code, "bytesRead": 0, "message": f"HTTP {exc.code}"}
    except urllib.error.URLError as exc:
        return {"url": url, "ok": False, "status": None, "bytesRead": 0, "message": str(exc.reason)}
    except TimeoutError:
        return {"url": url, "ok": False, "status": None, "bytesRead": 0, "message": "timeout"}

    ok = 200 <= status < 400 and len(body) > 0
    return {
        "url": url,
        "ok": ok,
        "status": status,
        "bytesRead": len(body),
        "message": "reachable" if ok else "empty or non-2xx/3xx response",
    }


def check_public_urls(
    values: dict[str, Any],
    *,
    skip: bool = False,
    timeout: float = 15.0,
    opener: UrlOpener = urllib.request.urlopen,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for field in REQUIRED_URL_FIELDS:
        url = str(values.get(field) or "").strip()
        if not url:
            checks.append({"field": field, "url": "", "ok": False, "status": None, "message": "missing URL"})
            continue
        if skip:
            checks.append({"field": field, "url": url, "ok": True, "status": "skipped", "message": "URL check skipped"})
            continue
        result = fetch_url(url, timeout=timeout, opener=opener)
        result["field"] = field
        checks.append(result)
    return checks


def validate_values(values: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        status_entry(
            "package-status",
            values.get("packageStatus") in {"ready-for-resubmission", "remediation-required"},
            "BaseScan values packet has a known package status.",
            values.get("packageStatus"),
        ),
        status_entry(
            "chain-id",
            values.get("chainId") == 8453,
            "BaseScan values must stay on Base Mainnet / chainId 8453.",
            values.get("chainId"),
        ),
        status_entry(
            "contract-address",
            str(values.get("contractAddress", "")).lower() == "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6",
            "Contract address must match the deployed GCA token.",
            values.get("contractAddress"),
        ),
        status_entry(
            "next-submission-ready-flag",
            values.get("nextSubmissionReady") is True,
            "The launch values must be explicitly marked ready before resubmission.",
            values.get("nextSubmissionReady"),
        ),
        status_entry(
            "official-domain-email",
            str(values.get("officialEmail", "")).lower() == TARGET_DOMAIN_EMAIL.lower(),
            "Official BaseScan email should match the activated project-domain email.",
            values.get("officialEmail"),
        ),
        status_entry(
            "tim-chen-profile",
            str(values.get("timChenProfessionalProfileUrl", "")).strip() == "https://gcagochina.com/tim-chen.html",
            "Tim Chen professional profile must be included.",
            values.get("timChenProfessionalProfileUrl"),
        ),
        status_entry(
            "domain-email-plan",
            str(values.get("domainEmailSetupPlanUrl", "")).strip() == "https://gcagochina.com/domain-email.html",
            "Domain email setup plan must remain linked.",
            values.get("domainEmailSetupPlanUrl"),
        ),
    ]
    return checks


def validate_evidence_packet(packet: dict[str, Any] | None) -> list[dict[str, Any]]:
    if packet is None:
        return [
            status_entry(
                "domain-email-evidence-packet",
                False,
                "Missing launch/domain_email_evidence_packet.json.",
                None,
            )
        ]
    return [
        status_entry(
            "domain-email-evidence-packet",
            packet.get("readyForBaseScanResubmission") is True,
            "Domain email evidence packet must be ready.",
            packet.get("status"),
        ),
        status_entry(
            "domain-email-target",
            str(packet.get("targetDomainEmail", "")).lower() == TARGET_DOMAIN_EMAIL.lower(),
            "Evidence packet target email must match support@gcagochina.com.",
            packet.get("targetDomainEmail"),
        ),
        status_entry(
            "domain-email-dns-readiness",
            packet.get("dnsReadiness", {}).get("readyForBaseScanEmailEvidence") is True,
            "Evidence packet must include DNS readiness.",
            packet.get("dnsReadiness", {}).get("missingOrBlockedChecks", []),
        ),
        status_entry(
            "domain-email-website-switch",
            packet.get("websiteEmailUpdatedToTarget") is True,
            "Public website email must be switched to the target domain email.",
            packet.get("websiteEmailUpdatedToTarget"),
        ),
    ]


def validate_public_switch_report(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if report is None:
        return [
            status_entry(
                "domain-email-public-switch-check",
                False,
                "Missing public domain-email switch check.",
                None,
            )
        ]
    return [
        status_entry(
            "domain-email-public-switch-check",
            report.get("readyForBaseScanPublicEmailAlignment") is True,
            "Critical public/support/BaseScan files must be aligned to support@gcagochina.com.",
            report.get("status"),
        ),
        status_entry(
            "domain-email-public-switch-target",
            str(report.get("targetDomainEmail", "")).lower() == TARGET_DOMAIN_EMAIL.lower(),
            "Public switch target email must match support@gcagochina.com.",
            report.get("targetDomainEmail"),
        ),
        status_entry(
            "domain-email-public-switch-old-email",
            report.get("summary", {}).get("filesStillUsingCurrentEmail") == 0,
            "No critical public file should still publish the old Outlook email after the switch.",
            report.get("summary", {}).get("filesStillUsingCurrentEmail"),
        ),
        status_entry(
            "domain-email-public-switch-forbidden-legacy-email",
            report.get("summary", {}).get("filesPublishingForbiddenLegacyEmail", 0) == 0,
            "No critical public file should publish any forbidden legacy personal or non-domain email.",
            report.get("summary", {}).get("filesPublishingForbiddenLegacyEmail", 0),
        ),
    ]


def validate_snapshot_alignment_report(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if report is None:
        return [
            status_entry(
                "domain-email-snapshot-alignment",
                False,
                "Missing domain email snapshot alignment check.",
                None,
            )
        ]
    summary = report.get("summary", {})
    canonical = report.get("canonicalSnapshot", {})
    return [
        status_entry(
            "domain-email-snapshot-alignment",
            report.get("alignedForPublicPlatformPackets") is True,
            "Public site, launch, and docs materials must match the canonical domain-email DNS snapshot.",
            report.get("status"),
        ),
        status_entry(
            "domain-email-snapshot-canonical-date",
            bool(canonical.get("date")) and bool(canonical.get("checkedAt")),
            "Snapshot alignment report must include canonical date and checkedAt values.",
            canonical,
        ),
        status_entry(
            "domain-email-snapshot-stale-markers",
            summary.get("filesWithStaleSnapshotMarkers") == 0,
            "No monitored public artifact should still cite an older DNS snapshot date.",
            summary.get("filesWithStaleSnapshotMarkers"),
        ),
    ]


def missing_keys_from_checks(checks: list[dict[str, Any]]) -> list[str]:
    return [str(check.get("key") or check.get("field") or check.get("url")) for check in checks if not check.get("ok")]


def build_readiness_report(
    *,
    values: dict[str, Any],
    evidence_packet: dict[str, Any] | None,
    public_switch_report: dict[str, Any] | None,
    snapshot_alignment_report: dict[str, Any] | None,
    public_url_checks: list[dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    values_checks = validate_values(values)
    evidence_checks = validate_evidence_packet(evidence_packet)
    public_switch_checks = validate_public_switch_report(public_switch_report)
    snapshot_alignment_checks = validate_snapshot_alignment_report(snapshot_alignment_report)
    public_checks = [
        status_entry(
            f"public-url:{check.get('field')}",
            bool(check.get("ok")),
            str(check.get("message") or ""),
            {"url": check.get("url"), "status": check.get("status")},
        )
        for check in public_url_checks
    ]

    all_checks = values_checks + evidence_checks + public_switch_checks + snapshot_alignment_checks + public_checks
    blocked = missing_keys_from_checks(all_checks)
    ready = not blocked

    return {
        "schema": "gca-basescan-resubmission-readiness-v1",
        "generatedAt": generated_at or utc_now(),
        "project": "GCA",
        "chainId": values.get("chainId"),
        "contractAddress": values.get("contractAddress"),
        "readyForBaseScanResubmission": ready,
        "status": "ready-for-owner-resubmission" if ready else "blocked-before-basescan-resubmission",
        "missingOrBlockedRequirements": blocked,
        "valuesChecks": values_checks,
        "domainEmailEvidenceChecks": evidence_checks,
        "domainEmailPublicSwitchChecks": public_switch_checks,
        "domainEmailPublicSwitchSummary": public_switch_report,
        "domainEmailSnapshotAlignmentChecks": snapshot_alignment_checks,
        "domainEmailSnapshotAlignmentSummary": snapshot_alignment_report,
        "publicUrlChecks": public_url_checks,
        "nextAction": (
            "Owner may proceed with one clean BaseScan resubmission from support@gcagochina.com."
            if ready
            else "Do not resubmit BaseScan yet. Complete the blocked requirements first."
        ),
        "boundaries": {
            "readOnly": True,
            "sendsEmail": False,
            "submitsBaseScanRequest": False,
            "writesDnsRecords": False,
            "touchesWalletOrContract": False,
            "printsSecrets": False,
        },
    }


def print_text_report(report: dict[str, Any]) -> None:
    print("GCA BaseScan resubmission preflight")
    print(f"readyForBaseScanResubmission: {str(report['readyForBaseScanResubmission']).lower()}")
    print(f"status: {report['status']}")
    if report["missingOrBlockedRequirements"]:
        print("missingOrBlockedRequirements:")
        for item in report["missingOrBlockedRequirements"]:
            print(f"- {item}")
    print(f"nextAction: {report['nextAction']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check GCA BaseScan resubmission readiness.")
    parser.add_argument("--values", default=str(DEFAULT_VALUES_PATH), help="Path to BaseScan resubmission values JSON.")
    parser.add_argument("--evidence-packet", default=str(DEFAULT_EVIDENCE_PACKET_PATH), help="Path to domain email evidence packet JSON.")
    parser.add_argument("--public-switch-report", default="", help="Optional saved domain email public switch check JSON. If omitted, the checker scans current files.")
    parser.add_argument("--snapshot-alignment-report", default="", help="Optional saved domain email snapshot alignment JSON. If omitted, the checker scans current files.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Public URL request timeout in seconds.")
    parser.add_argument("--skip-url-checks", action="store_true", help="Skip public URL reachability checks.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--require-ready", action="store_true", help="Exit non-zero when not ready.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        values = load_json_file(Path(args.values))
        evidence_packet = maybe_load_json_file(Path(args.evidence_packet))
        public_switch_report = (
            load_json_file(Path(args.public_switch_report))
            if args.public_switch_report
            else build_public_switch_report()
        )
        snapshot_alignment_report = (
            load_json_file(Path(args.snapshot_alignment_report))
            if args.snapshot_alignment_report
            else build_snapshot_alignment_report()
        )
        public_url_checks = check_public_urls(values, skip=args.skip_url_checks, timeout=args.timeout)
        report = build_readiness_report(
            values=values,
            evidence_packet=evidence_packet,
            public_switch_report=public_switch_report,
            snapshot_alignment_report=snapshot_alignment_report,
            public_url_checks=public_url_checks,
        )
    except (BaseScanReadinessError, PublicSwitchCheckError, SnapshotAlignmentError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text_report(report)

    if args.require_ready and not report["readyForBaseScanResubmission"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
