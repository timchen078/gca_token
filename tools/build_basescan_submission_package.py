#!/usr/bin/env python3
"""Build the final GCA BaseScan token-profile submission package.

This tool is local-only and gated by the BaseScan resubmission preflight. It
does not submit BaseScan forms, sign messages, send email, write DNS records,
or touch wallets/contracts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from tools.check_basescan_resubmission_readiness import (
        BaseScanReadinessError,
        check_public_urls,
        build_readiness_report,
        load_json_file,
        maybe_load_json_file,
    )
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
    from check_basescan_resubmission_readiness import (
        BaseScanReadinessError,
        check_public_urls,
        build_readiness_report,
        load_json_file,
        maybe_load_json_file,
    )
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


def format_lines(items: list[str]) -> str:
    return "\n".join(items)


def build_form_fields(values: dict[str, Any]) -> dict[str, Any]:
    market = values.get("officialMarketPool", {})
    supply = values.get("supplyDisclosure", {})
    supply_page = supply.get("supplyDisclosurePageUrl") or supply.get("supplyDisclosureUrl")
    access_boundary = {
        "accessPortal": "https://gcagochina.com/access.html",
        "accessApi": "https://gcagochina.com/access-api.html",
        "reviewQueue": "https://gcagochina.com/review-queue.html",
        "releaseGates": "https://gcagochina.com/release-gates.html",
        "memberBenefit": "https://gcagochina.com/member-benefit.html",
        "summary": (
            "Public account intake and eligibility submission are live, but 100 GCA AI Quant Access credits "
            "are account-level service records, not cash or transferable tokens. GCA Member review requires "
            "1,000,000 GCA plus 30 consecutive days of holding evidence, and any 10,000 GCA member benefit "
            "remains manual reserve-wallet processing after support approval."
        ),
        "notAutomatic": (
            "No automatic token claim, no self-service member-benefit transfer, no custody, no withdrawal path, "
            "no trading permission, and no price or liquidity support is claimed."
        ),
    }
    return {
        "basicInformation": {
            "contractAddress": values.get("contractAddress"),
            "projectName": values.get("tokenName"),
            "projectWebsite": values.get("website"),
            "projectEmailAddress": values.get("officialEmail"),
            "logoSvg32x32": values.get("logoSvgUrl"),
            "projectDescription": values.get("descriptionLong"),
            "projectSector": "Web3 education and non-custodial trading risk tools",
            "network": values.get("network"),
            "chainId": values.get("chainId"),
            "tokenSymbol": values.get("tokenSymbol"),
            "decimals": values.get("decimals"),
            "totalSupply": values.get("totalSupply"),
        },
        "socialProfiles": {
            "telegram": values.get("officialTelegram"),
            "x": values.get("officialX"),
            "github": values.get("githubRepoUrl"),
            "team": values.get("teamPageUrl"),
            "timChenProfessionalProfile": values.get("timChenProfessionalProfileUrl"),
            "whitepaper": values.get("whitepaperUrl"),
            "support": values.get("supportPageUrl") or "https://gcagochina.com/support.html",
            "brandKit": values.get("brandKitPageUrl"),
            "community": values.get("communityPageUrl"),
            "externalReviewStatus": values.get("externalReviewStatusPageUrl"),
            "domainEmailEvidencePlan": values.get("domainEmailSetupPlanUrl"),
            "baseScanRemediation": values.get("baseScanRemediationPageUrl"),
        },
        "priceData": {
            "officialMarketRoute": market.get("pair"),
            "dex": market.get("dex"),
            "poolAddress": market.get("poolAddress"),
            "geckoTerminal": market.get("geckoTerminalUrl"),
            "dexScreener": market.get("dexScreenerUrl"),
        },
        "saleDetails": {
            "publicSale": "Not applicable. No ICO/IEO or public token sale has been conducted.",
            "privateSale": "Not applicable. No private sale details are being claimed.",
            "burnEvents": "Not applicable. No token burn events are being claimed.",
        },
        "supplyContext": {
            "targetPublicAllocation": supply.get("targetPublicAllocation"),
            "ownerHeldReserve": supply.get("ownerHeldReserve"),
            "ownerReserveWallet": supply.get("ownerReserveWallet"),
            "supplyDisclosure": supply_page,
            "supplyDisclosureData": supply.get("supplyDisclosureUrl"),
            "reserveBoundary": "Do not describe the reserve as locked, vested, or multisig-controlled unless custody changes on-chain.",
        },
        "accessClaimBoundary": access_boundary,
    }


def build_copy_paste_blocks(
    *,
    values: dict[str, Any],
    readiness_report: dict[str, Any],
    form_fields: dict[str, Any],
) -> dict[str, str]:
    basic = form_fields["basicInformation"]
    social = form_fields["socialProfiles"]
    price = form_fields["priceData"]
    supply = form_fields["supplyContext"]
    access = form_fields["accessClaimBoundary"]
    missing = [str(item) for item in readiness_report.get("missingOrBlockedRequirements", [])]
    ready = bool(readiness_report.get("readyForBaseScanResubmission"))
    email_guard = build_public_email_guard(readiness_report)

    basic_block = format_lines([
        f"Contract Address: {basic['contractAddress']}",
        f"Project Name: {basic['projectName']}",
        f"Project Website: {basic['projectWebsite']}",
        f"Project Email Address: {basic['projectEmailAddress']}",
        f"32x32 SVG Logo: {basic['logoSvg32x32']}",
        f"Project Description: {basic['projectDescription']}",
        f"Project Sector: {basic['projectSector']}",
        f"Network: {basic['network']} / chainId {basic['chainId']}",
        f"Token Symbol: {basic['tokenSymbol']}",
        f"Decimals: {basic['decimals']}",
        f"Total Supply: {basic['totalSupply']}",
    ])
    evidence_block = format_lines([
        f"Team page: {social['team']}",
        f"Tim Chen professional profile: {social['timChenProfessionalProfile']}",
        f"Whitepaper: {social['whitepaper']}",
        f"Support: {social['support']}",
        f"Brand Kit: {social['brandKit']}",
        f"Community: {social['community']}",
        f"External review status: {social['externalReviewStatus']}",
        f"Domain email evidence plan: {social['domainEmailEvidencePlan']}",
        f"BaseScan remediation tracker: {social['baseScanRemediation']}",
        f"GitHub source repository: {social['github']}",
        f"Telegram: {social['telegram']}",
        f"X: {social['x']}",
        f"Access portal: {access['accessPortal']}",
        f"Review queue contract: {access['reviewQueue']}",
        f"Release gates: {access['releaseGates']}",
        f"Member benefit rules: {access['memberBenefit']}",
    ])
    market_block = format_lines([
        f"Official market route: {price['officialMarketRoute']}",
        f"DEX: {price['dex']}",
        f"Pool: {price['poolAddress']}",
        f"GeckoTerminal: {price['geckoTerminal']}",
        f"DEX Screener: {price['dexScreener']}",
        f"Target public allocation: {supply['targetPublicAllocation']}",
        f"Owner-held reserve: {supply['ownerHeldReserve']}",
        f"Owner reserve wallet: {supply['ownerReserveWallet']}",
        f"Supply disclosure: {supply['supplyDisclosure']}",
        f"Reserve boundary: {supply['reserveBoundary']}",
    ])
    access_block = format_lines([
        f"Access portal: {access['accessPortal']}",
        f"Access API: {access['accessApi']}",
        f"Review queue contract: {access['reviewQueue']}",
        f"Release gates: {access['releaseGates']}",
        f"Member benefit rules: {access['memberBenefit']}",
        f"Access boundary: {access['summary']}",
        f"Not automatic: {access['notAutomatic']}",
    ])

    if ready:
        reviewer_comment = format_lines([
            "Hello BaseScan team,",
            "",
            "Please review the updated GCA token profile metadata for Base Mainnet / chainId 8453.",
            "",
            "This resubmission directly addresses the prior information-insufficient return reasons:",
            f"- Official website and support path: {basic['projectWebsite']} and {social['support']}",
            f"- Official project-domain email: {basic['projectEmailAddress']}",
            f"- Founder/team transparency: {social['team']} and {social['timChenProfessionalProfile']}",
            f"- Project documentation and status: {social['whitepaper']} and {social['externalReviewStatus']}",
            f"- Logo, brand, and metadata evidence: {social['brandKit']}",
            f"- Contract/source and remediation evidence: {social['baseScanRemediation']}",
            f"- Access and member-benefit boundaries: {access['reviewQueue']} and {access['releaseGates']}",
            "- Public email guard: the current preflight reports "
            f"{email_guard['filesStillUsingOldEmail']} tracked public files publishing the old Outlook email "
            f"and {email_guard['filesPublishingForbiddenLegacyEmail']} tracked public files publishing forbidden legacy personal/non-domain email.",
            "",
            f"Contract: {basic['contractAddress']}",
            f"Official website: {basic['projectWebsite']}",
            f"Official project email: {basic['projectEmailAddress']}",
            f"Founder/team transparency: {social['team']} and {social['timChenProfessionalProfile']}",
            f"Whitepaper: {social['whitepaper']}",
            f"Public remediation tracker: {social['baseScanRemediation']}",
            f"Domain email evidence plan: {social['domainEmailEvidencePlan']}",
            f"Source repository: {social['github']}",
            f"Official market route: {price['officialMarketRoute']} on {price['dex']}",
            f"Pool: {price['poolAddress']}",
            f"Access boundary: {access['summary']}",
            f"Not automatic: {access['notAutomatic']}",
            "",
            "The contract source is verified on BaseScan and deployer-wallet ownership has previously been verified. "
            "This request is only for token profile metadata.",
            "",
            "We are not claiming BaseScan token profile approval before publication, third-party audit completion, "
            "locked reserve custody, deep liquidity, or price support.",
            "",
            "Thank you.",
        ])
    else:
        reviewer_comment = format_lines([
            "DRAFT ONLY - DO NOT SUBMIT BASESCAN YET.",
            "",
            "The local preflight is still blocked, so this text is for owner preparation only.",
            "",
            "Blocked requirements:",
            *(f"- {item}" for item in missing),
            "",
            str(readiness_report.get("nextAction") or "Resolve the blocked requirements and rerun the preflight."),
        ])

    return {
        "baseScanReviewerComment": reviewer_comment,
        "basicInformationPlainText": basic_block,
        "evidenceLinksPlainText": evidence_block,
        "marketAndSupplyPlainText": market_block,
        "accessAndClaimBoundaryPlainText": access_block,
    }


def build_reviewer_remediation_summary(form_fields: dict[str, Any]) -> list[dict[str, str]]:
    basic = form_fields["basicInformation"]
    social = form_fields["socialProfiles"]
    return [
        {
            "returnReason": "official website, support path, or project information was unclear",
            "response": "Published a readable website, support page, whitepaper, external review status, and project documentation.",
            "primaryEvidence": f"{basic['projectWebsite']} | {social['support']} | {social['whitepaper']} | {social['externalReviewStatus']}",
        },
        {
            "returnReason": "sender email did not match the official project domain",
            "response": "Switched the official project contact to the active domain mailbox support@gcagochina.com.",
            "primaryEvidence": f"{basic['projectEmailAddress']} | {social['domainEmailEvidencePlan']}",
        },
        {
            "returnReason": "founder and team transparency needed more public evidence",
            "response": "Published the team page and Tim Chen official-domain professional profile for reviewer use.",
            "primaryEvidence": f"{social['team']} | {social['timChenProfessionalProfile']}",
        },
        {
            "returnReason": "logo, links, metadata, or contract evidence needed a cleaner route",
            "response": "Published the brand kit, remediation tracker, GitHub repository, and market/supply evidence links in one package.",
            "primaryEvidence": f"{social['brandKit']} | {social['baseScanRemediation']} | {social['github']}",
        },
    ]


def redact_forbidden_legacy_email(email: str) -> str:
    normalized = email.strip().lower()
    if normalized == "gcagochina@outlook.com":
        return "redacted-legacy-outlook-inbox"
    if normalized == "cxy070800@gmail.com":
        return "redacted-non-domain-legacy-inbox"
    return "redacted-forbidden-legacy-email"


def build_public_email_guard(readiness_report: dict[str, Any]) -> dict[str, Any]:
    public_switch = readiness_report.get("domainEmailPublicSwitchSummary", {})
    summary = public_switch.get("summary", {})
    legacy_email = public_switch.get("legacyEmail")
    forbidden_legacy_email_labels = sorted({
        redact_forbidden_legacy_email(str(email))
        for email in public_switch.get("forbiddenLegacyEmails", [])
    })
    return {
        "status": public_switch.get("status"),
        "readyForBaseScanPublicEmailAlignment": public_switch.get("readyForBaseScanPublicEmailAlignment") is True,
        "targetDomainEmail": public_switch.get("targetDomainEmail"),
        "currentPublicEmail": public_switch.get("currentEmail"),
        "legacyEmailLabel": redact_forbidden_legacy_email(str(legacy_email)) if legacy_email else None,
        "forbiddenLegacyEmailCount": len(public_switch.get("forbiddenLegacyEmails", [])),
        "forbiddenLegacyEmailLabels": forbidden_legacy_email_labels,
        "filesStillUsingOldEmail": int(summary.get("filesStillUsingCurrentEmail") or 0),
        "filesPublishingForbiddenLegacyEmail": int(summary.get("filesPublishingForbiddenLegacyEmail") or 0),
        "currentEmailOccurrences": int(summary.get("currentEmailOccurrences") or 0),
        "forbiddenLegacyEmailOccurrences": int(summary.get("forbiddenLegacyEmailOccurrences") or 0),
        "boundary": (
            "This guard is a read-only public-file scan. It does not send email, submit BaseScan requests, "
            "write DNS records, or touch wallets/contracts."
        ),
    }


def build_submission_package(
    *,
    values: dict[str, Any],
    readiness_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    ready = bool(readiness_report.get("readyForBaseScanResubmission"))
    form_fields = build_form_fields(values)
    public_email_guard = build_public_email_guard(readiness_report)
    return {
        "schema": "gca-basescan-submission-package-v1",
        "generatedAt": generated_at or utc_now(),
        "project": "GCA",
        "status": "ready-for-owner-submission" if ready else "blocked-before-basescan-submission",
        "readyForOwnerSubmission": ready,
        "missingOrBlockedRequirements": readiness_report.get("missingOrBlockedRequirements", []),
        "nextAction": (
            "Owner may copy this package into one clean BaseScan token profile update."
            if ready
            else "Do not submit BaseScan yet. Resolve the blocked requirements and rerun the preflight."
        ),
        "preflightSummary": {
            "status": readiness_report.get("status"),
            "readyForBaseScanResubmission": ready,
            "generatedAt": readiness_report.get("generatedAt"),
            "filesStillUsingOldEmail": public_email_guard["filesStillUsingOldEmail"],
            "filesPublishingForbiddenLegacyEmail": public_email_guard["filesPublishingForbiddenLegacyEmail"],
        },
        "publicEmailGuard": public_email_guard,
        "reviewerRemediationSummary": build_reviewer_remediation_summary(form_fields),
        "formFields": form_fields,
        "copyPasteBlocks": build_copy_paste_blocks(
            values=values,
            readiness_report=readiness_report,
            form_fields=form_fields,
        ),
        "safeSubmissionNote": (
            "BaseScan source verification and deployer-wallet ownership verification are complete. "
            "This is a token profile metadata update request only."
        ),
        "doNotClaim": values.get("doNotClaim", []),
        "boundaries": {
            "localDraftOnly": True,
            "submitsBaseScanRequest": False,
            "signsWalletMessage": False,
            "sendsEmail": False,
            "writesDnsRecords": False,
            "touchesWalletOrContract": False,
            "printsSecrets": False,
        },
    }


def render_markdown(package: dict[str, Any]) -> str:
    fields = package["formFields"]
    basic = fields["basicInformation"]
    social = fields["socialProfiles"]
    price = fields["priceData"]
    sale = fields["saleDetails"]
    supply = fields["supplyContext"]
    access = fields["accessClaimBoundary"]
    copy_blocks = package["copyPasteBlocks"]
    remediation_summary = package.get("reviewerRemediationSummary", [])
    public_email_guard = package.get("publicEmailGuard", {})

    lines = [
        "# GCA BaseScan Submission Package",
        "",
        f"- Generated: `{package['generatedAt']}`",
        f"- Status: `{package['status']}`",
        f"- Ready for owner submission: `{str(package['readyForOwnerSubmission']).lower()}`",
        f"- Next action: {package['nextAction']}",
        "",
    ]
    if package["missingOrBlockedRequirements"]:
        lines.append("## Missing Or Blocked Requirements")
        lines.append("")
        for item in package["missingOrBlockedRequirements"]:
            lines.append(f"- `{item}`")
        lines.append("")

    lines.extend([
        "## Reviewer Remediation Summary",
        "",
    ])
    for item in remediation_summary:
        lines.extend([
            f"- Return reason: {item['returnReason']}",
            f"  Response: {item['response']}",
            f"  Evidence: {item['primaryEvidence']}",
        ])
    lines.append("")

    lines.extend([
        "## Public Email Guard",
        "",
        f"- Status: `{public_email_guard.get('status')}`",
        f"- Target domain email: `{public_email_guard.get('targetDomainEmail')}`",
        f"- Current public email: `{public_email_guard.get('currentPublicEmail')}`",
        f"- Files still publishing old email: `{public_email_guard.get('filesStillUsingOldEmail')}`",
        f"- Files publishing forbidden legacy email: `{public_email_guard.get('filesPublishingForbiddenLegacyEmail')}`",
        f"- Forbidden legacy email labels scanned: `{', '.join(public_email_guard.get('forbiddenLegacyEmailLabels') or [])}`",
        f"- Boundary: {public_email_guard.get('boundary')}",
        "",
    ])

    lines.extend([
        "## Copy/Paste Reviewer Comment",
        "",
        "```text",
        copy_blocks["baseScanReviewerComment"],
        "```",
        "",
        "## Copy/Paste Basic Information",
        "",
        "```text",
        copy_blocks["basicInformationPlainText"],
        "```",
        "",
        "## Copy/Paste Evidence Links",
        "",
        "```text",
        copy_blocks["evidenceLinksPlainText"],
        "```",
        "",
        "## Copy/Paste Market And Supply",
        "",
        "```text",
        copy_blocks["marketAndSupplyPlainText"],
        "```",
        "",
        "## Copy/Paste Access And Claim Boundary",
        "",
        "```text",
        copy_blocks["accessAndClaimBoundaryPlainText"],
        "```",
        "",
    ])

    lines.extend([
        "## Basic Information",
        "",
        f"1. Contract Address: `{basic['contractAddress']}`",
        f"2. Project Name: `{basic['projectName']}`",
        f"3. Project Website: `{basic['projectWebsite']}`",
        f"4. Project Email Address: `{basic['projectEmailAddress']}`",
        f"5. Link to download a 32x32 SVG icon logo: `{basic['logoSvg32x32']}`",
        f"6. Project Description: {basic['projectDescription']}",
        f"7. Project Sector: {basic['projectSector']}",
        "",
        "## Social Profiles",
        "",
        f"- Telegram: `{social['telegram']}`",
        f"- X: `{social['x']}`",
        f"- GitHub: `{social['github']}`",
        f"- Team: `{social['team']}`",
        f"- Tim Chen professional profile: `{social['timChenProfessionalProfile']}`",
        f"- Whitepaper: `{social['whitepaper']}`",
        f"- Support: `{social['support']}`",
        f"- Brand Kit: `{social['brandKit']}`",
        f"- Domain email evidence plan: `{social['domainEmailEvidencePlan']}`",
        f"- BaseScan remediation: `{social['baseScanRemediation']}`",
        "",
        "## Price Data",
        "",
        f"- Official market route: `{price['officialMarketRoute']}`",
        f"- DEX: `{price['dex']}`",
        f"- Pool: `{price['poolAddress']}`",
        f"- GeckoTerminal: `{price['geckoTerminal']}`",
        f"- DEX Screener: `{price['dexScreener']}`",
        "",
        "## Sale / Supply Context",
        "",
        f"- Public Sale: {sale['publicSale']}",
        f"- Private Sale: {sale['privateSale']}",
        f"- Burn Events: {sale['burnEvents']}",
        f"- Target public allocation: `{supply['targetPublicAllocation']}`",
        f"- Owner-held reserve: `{supply['ownerHeldReserve']}`",
        f"- Owner reserve wallet: `{supply['ownerReserveWallet']}`",
        f"- Supply disclosure: `{supply['supplyDisclosure']}`",
        f"- Reserve boundary: {supply['reserveBoundary']}",
        "",
        "## Access And Claim Boundary",
        "",
        f"- Access portal: `{access['accessPortal']}`",
        f"- Access API: `{access['accessApi']}`",
        f"- Review queue contract: `{access['reviewQueue']}`",
        f"- Release gates: `{access['releaseGates']}`",
        f"- Member benefit rules: `{access['memberBenefit']}`",
        f"- Access boundary: {access['summary']}",
        f"- Not automatic: {access['notAutomatic']}",
        "",
        "## Boundaries",
        "",
        "- This package is a local draft only.",
        "- This package does not submit a BaseScan request.",
        "- This package does not sign wallet messages, send email, write DNS records, or touch wallets/contracts.",
    ])
    return "\n".join(lines) + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a gated GCA BaseScan submission package.")
    parser.add_argument("--values", default=str(DEFAULT_VALUES_PATH), help="Path to BaseScan resubmission values JSON.")
    parser.add_argument("--evidence-packet", default=str(DEFAULT_EVIDENCE_PACKET_PATH), help="Path to domain email evidence packet JSON.")
    parser.add_argument("--public-switch-report", default="", help="Optional saved domain email public switch check JSON. If omitted, the checker scans current files.")
    parser.add_argument("--snapshot-alignment-report", default="", help="Optional saved domain email snapshot alignment JSON. If omitted, the checker scans current files.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Public URL request timeout in seconds.")
    parser.add_argument("--skip-url-checks", action="store_true", help="Skip public URL reachability checks.")
    parser.add_argument("--output-json", default="", help="Write submission package JSON to this path.")
    parser.add_argument("--output-md", default="", help="Write submission package Markdown to this path.")
    parser.add_argument("--generated-at", default="", help="Override generatedAt timestamp for deterministic owner packages.")
    parser.add_argument("--json", action="store_true", help="Print package JSON to stdout.")
    parser.add_argument("--require-ready", action="store_true", help="Exit non-zero when package is not ready.")
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
        readiness_report = build_readiness_report(
            values=values,
            evidence_packet=evidence_packet,
            public_switch_report=public_switch_report,
            snapshot_alignment_report=snapshot_alignment_report,
            public_url_checks=public_url_checks,
            generated_at=args.generated_at or None,
        )
        package = build_submission_package(
            values=values,
            readiness_report=readiness_report,
            generated_at=args.generated_at or None,
        )
    except (BaseScanReadinessError, PublicSwitchCheckError, SnapshotAlignmentError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output_json:
        write_text(Path(args.output_json), json.dumps(package, indent=2, sort_keys=True) + "\n")
    if args.output_md:
        write_text(Path(args.output_md), render_markdown(package))
    if args.json or not (args.output_json or args.output_md):
        print(json.dumps(package, indent=2, sort_keys=True))

    if args.require_ready and not package["readyForOwnerSubmission"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
