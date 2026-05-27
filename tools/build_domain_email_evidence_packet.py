#!/usr/bin/env python3
"""Build the owner-side GCA domain email evidence packet.

This tool is local-only. It can run the read-only DNS checker or consume a
saved DNS-check JSON file, then combines that result with owner-provided
evidence references. It does not send email, submit BaseScan requests, or touch
wallets/contracts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from tools.check_domain_email_dns import DomainEmailDnsError, run_checks, utc_now
except ModuleNotFoundError:  # pragma: no cover - used when running from tools/
    from check_domain_email_dns import DomainEmailDnsError, run_checks, utc_now


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "site" / "domain-email.json"
DEFAULT_EVIDENCE_DIR = ROOT / "launch" / "domain_email_evidence"
EVIDENCE_README_FILENAME = "README.txt"

EVIDENCE_FIELDS = (
    (
        "providerActive",
        "Mail provider dashboard shows support@gcagochina.com as verified or active.",
        "domain-email-provider-active.png",
    ),
    (
        "dnsProof",
        "MX, SPF, DKIM, and DMARC lookup proof is saved after propagation.",
        "domain-email-dns-mx-spf-dkim-dmarc.txt",
    ),
    (
        "inboundTest",
        "Inbound test from Gmail or Outlook to support@gcagochina.com is received.",
        "domain-email-inbound-test.png",
    ),
    (
        "outboundTest",
        "Outbound reply from support@gcagochina.com shows the visible domain sender.",
        "domain-email-outbound-test.png",
    ),
    (
        "supportPageProof",
        "Updated support page shows the same domain email used in the BaseScan form.",
        "support-page-domain-email.png",
    ),
)


class EvidencePacketError(RuntimeError):
    """Raised for expected operator-facing packet build failures."""


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidencePacketError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidencePacketError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise EvidencePacketError(f"{path} must contain a JSON object")
    return payload


def clean_reference(value: str | None) -> str:
    return (value or "").strip()


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_references_from_evidence_dir(evidence_dir: Path) -> dict[str, str]:
    references: dict[str, str] = {}
    for key, _label, recommended_filename in EVIDENCE_FIELDS:
        candidate = evidence_dir / recommended_filename
        if candidate.is_file():
            references[key] = display_path(candidate)
    return references


def build_evidence_directory_status(evidence_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for key, label, recommended_filename in EVIDENCE_FIELDS:
        candidate = evidence_dir / recommended_filename
        rows.append({
            "key": key,
            "label": label,
            "fileName": recommended_filename,
            "path": display_path(candidate),
            "exists": candidate.is_file(),
        })
    missing = [row["fileName"] for row in rows if not row["exists"]]
    readme = evidence_dir / EVIDENCE_README_FILENAME
    evidence_dir_path = evidence_dir.resolve()
    default_evidence_path = DEFAULT_EVIDENCE_DIR.resolve()
    return {
        "path": display_path(evidence_dir),
        "exists": evidence_dir.is_dir(),
        "readmeFile": display_path(readme),
        "readmeExists": readme.is_file(),
        "complete": not missing,
        "missingFiles": missing,
        "requiredFiles": rows,
        "ignoredByGit": evidence_dir_path == default_evidence_path or evidence_dir_path.is_relative_to(default_evidence_path),
    }


def render_evidence_directory_readme(status: dict[str, Any]) -> str:
    lines = [
        "GCA Domain Email Evidence Directory",
        "",
        "Place the five owner-side proof files in this directory before building the BaseScan evidence packet.",
        "These files may contain mailbox screenshots or other private operational evidence, so this directory is ignored by git.",
        "",
        "Required files:",
    ]
    for row in status["requiredFiles"]:
        lines.append(f"- {row['fileName']}: {row['label']}")
    lines.extend([
        "",
        "After all five files are saved, run:",
        "python3 tools/build_domain_email_evidence_packet.py --dkim-selector <provider-selector> --evidence-dir launch/domain_email_evidence --website-email-updated --output-json launch/domain_email_evidence_packet.json --output-md launch/domain_email_evidence_packet.md --json",
        "",
        "Boundaries:",
        "- This local folder does not send email.",
        "- This local folder does not submit BaseScan requests.",
        "- This local folder does not write DNS records.",
        "- This local folder does not touch wallets, contracts, liquidity, or private keys.",
    ])
    return "\n".join(lines) + "\n"


def initialize_evidence_directory(evidence_dir: Path) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    status = build_evidence_directory_status(evidence_dir)
    write_text(evidence_dir / EVIDENCE_README_FILENAME, render_evidence_directory_readme(status))
    return build_evidence_directory_status(evidence_dir)


def merge_evidence_references(cli_references: dict[str, str], evidence_dir: Path | None) -> dict[str, str]:
    references = build_references_from_evidence_dir(evidence_dir) if evidence_dir else {}
    for key, value in cli_references.items():
        cleaned = clean_reference(value)
        if cleaned:
            references[key] = cleaned
    return references


def build_manual_evidence(references: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, label, recommended_filename in EVIDENCE_FIELDS:
        reference = clean_reference(references.get(key))
        rows.append({
            "key": key,
            "label": label,
            "recommendedFilename": recommended_filename,
            "reference": reference,
            "provided": bool(reference),
        })
    return rows


def build_packet(
    *,
    domain_email_config: dict[str, Any],
    dns_result: dict[str, Any],
    manual_evidence: list[dict[str, Any]],
    website_email_updated: bool,
    evidence_directory: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    target_email = str(domain_email_config.get("targetDomainEmail") or dns_result.get("targetMailbox") or "")
    current_email = str(domain_email_config.get("currentPublicEmail") or "")
    dns_ready = bool(dns_result.get("readyForBaseScanEmailEvidence"))
    missing_or_blocked: list[str] = []

    if not dns_ready:
        missing_or_blocked.append("dns-ready")
    if not website_email_updated:
        missing_or_blocked.append("website-email-updated")
    for item in manual_evidence:
        if not item.get("provided"):
            missing_or_blocked.append(str(item["key"]))

    ready = not missing_or_blocked
    status = "ready-for-owner-resubmission" if ready else "blocked-before-basescan-resubmission"

    return {
        "schema": "gca-domain-email-evidence-packet-v1",
        "generatedAt": generated_at or utc_now(),
        "project": "GCA",
        "domain": domain_email_config.get("domain") or dns_result.get("domain"),
        "currentPublicEmail": current_email,
        "targetDomainEmail": target_email,
        "status": status,
        "readyForBaseScanResubmission": ready,
        "missingOrBlockedRequirements": missing_or_blocked,
        "dnsReadiness": {
            "readyForBaseScanEmailEvidence": dns_ready,
            "checkedAt": dns_result.get("checkedAt"),
            "dkimSelector": dns_result.get("dkimSelector"),
            "missingOrBlockedChecks": dns_result.get("missingOrBlockedChecks", []),
            "checks": dns_result.get("checks", {}),
        },
        "manualEvidence": manual_evidence,
        "evidenceDirectory": evidence_directory or {},
        "websiteEmailUpdatedToTarget": website_email_updated,
        "nextAction": (
            "Archive this packet and resubmit BaseScan only from the matching domain email."
            if ready
            else "Do not resubmit BaseScan yet. Complete the missing requirements first."
        ),
        "baseScanSubmissionPolicy": {
            "nextCleanSubmissionSender": target_email,
            "includeProfessionalProfile": "https://gcagochina.com/tim-chen.html",
            "includeDomainEmailPlan": "https://gcagochina.com/domain-email.html",
            "includeDomainEmailData": "https://gcagochina.com/domain-email.json",
        },
        "boundaries": {
            "sendsEmail": False,
            "submitsBaseScanRequest": False,
            "touchesWalletOrContract": False,
            "changesDns": False,
            "printsSecrets": False,
        },
    }


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# GCA Domain Email Evidence Packet",
        "",
        f"- Generated: `{packet['generatedAt']}`",
        f"- Domain: `{packet['domain']}`",
        f"- Current public email: `{packet['currentPublicEmail']}`",
        f"- Target domain email: `{packet['targetDomainEmail']}`",
        f"- Status: `{packet['status']}`",
        f"- Ready for BaseScan resubmission: `{str(packet['readyForBaseScanResubmission']).lower()}`",
        "",
        "## DNS Readiness",
        "",
        f"- DNS ready: `{str(packet['dnsReadiness']['readyForBaseScanEmailEvidence']).lower()}`",
        f"- Checked at: `{packet['dnsReadiness'].get('checkedAt')}`",
        f"- DKIM selector: `{packet['dnsReadiness'].get('dkimSelector')}`",
        f"- Missing or blocked DNS checks: `{', '.join(packet['dnsReadiness'].get('missingOrBlockedChecks') or []) or 'none'}`",
        "",
        "## Manual Evidence",
        "",
    ]
    for item in packet["manualEvidence"]:
        marker = "complete" if item.get("provided") else "missing"
        reference = item.get("reference") or item.get("recommendedFilename")
        lines.append(f"- `{marker}` {item['key']}: {item['label']} Reference: `{reference}`")

    lines.extend([
        "",
        "## Submission Gate",
        "",
        f"- Website email updated to target: `{str(packet['websiteEmailUpdatedToTarget']).lower()}`",
        f"- Missing or blocked requirements: `{', '.join(packet['missingOrBlockedRequirements']) or 'none'}`",
        f"- Next action: {packet['nextAction']}",
        "",
        "## Boundaries",
        "",
        "- This packet does not send email.",
        "- This packet does not submit a BaseScan request.",
        "- This packet does not touch wallets, contracts, liquidity, or DNS records.",
    ])
    return "\n".join(lines) + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a GCA domain email evidence packet for BaseScan readiness.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to site/domain-email.json.")
    parser.add_argument("--dns-json", default="", help="Use a saved tools/check_domain_email_dns.py --json output.")
    parser.add_argument("--domain", default="gcagochina.com", help="Domain to check if --dns-json is not supplied.")
    parser.add_argument("--mailbox", default="support", help="Mailbox to check if --dns-json is not supplied.")
    parser.add_argument("--dkim-selector", default="", help="DKIM selector to check if --dns-json is not supplied.")
    parser.add_argument("--timeout", type=float, default=10.0, help="DNS query timeout.")
    parser.add_argument("--provider-active", default="", help="Evidence reference for provider active screenshot.")
    parser.add_argument("--dns-proof", default="", help="Evidence reference for DNS proof file or screenshot.")
    parser.add_argument("--inbound-test", default="", help="Evidence reference for inbound mail test.")
    parser.add_argument("--outbound-test", default="", help="Evidence reference for outbound mail test.")
    parser.add_argument("--support-page-proof", default="", help="Evidence reference for updated support page proof.")
    parser.add_argument(
        "--evidence-dir",
        default="",
        help=(
            "Optional directory containing the five recommended evidence files. "
            f"Defaults can be placed under {DEFAULT_EVIDENCE_DIR.relative_to(ROOT).as_posix()}."
        ),
    )
    parser.add_argument(
        "--init-evidence-dir",
        action="store_true",
        help="Create the local evidence directory and README checklist, then print directory status JSON.",
    )
    parser.add_argument("--website-email-updated", action="store_true", help="Confirm public website email now matches target.")
    parser.add_argument("--output-json", default="", help="Write packet JSON to this path.")
    parser.add_argument("--output-md", default="", help="Write packet Markdown to this path.")
    parser.add_argument("--json", action="store_true", help="Print packet JSON to stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    evidence_dir = Path(args.evidence_dir) if args.evidence_dir else DEFAULT_EVIDENCE_DIR

    if args.init_evidence_dir:
        status = initialize_evidence_directory(evidence_dir)
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0

    try:
        config = load_json_file(Path(args.config))
        if args.dns_json:
            dns_result = load_json_file(Path(args.dns_json))
        else:
            dns_result = run_checks(
                domain=args.domain,
                mailbox=args.mailbox,
                dkim_selector=args.dkim_selector,
                timeout=args.timeout,
            )
        evidence_references = merge_evidence_references({
            "providerActive": args.provider_active,
            "dnsProof": args.dns_proof,
            "inboundTest": args.inbound_test,
            "outboundTest": args.outbound_test,
            "supportPageProof": args.support_page_proof,
        }, evidence_dir if args.evidence_dir else None)
        manual_evidence = build_manual_evidence(evidence_references)
        packet = build_packet(
            domain_email_config=config,
            dns_result=dns_result,
            manual_evidence=manual_evidence,
            evidence_directory=build_evidence_directory_status(evidence_dir) if args.evidence_dir else None,
            website_email_updated=args.website_email_updated,
        )
    except (DomainEmailDnsError, EvidencePacketError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output_json:
        write_text(Path(args.output_json), json.dumps(packet, indent=2, sort_keys=True) + "\n")
    if args.output_md:
        write_text(Path(args.output_md), render_markdown(packet))
    if args.json or not (args.output_json or args.output_md):
        print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
