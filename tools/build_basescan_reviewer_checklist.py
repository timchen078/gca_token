"""Build a GCA BaseScan reviewer checklist from published local evidence.

The checklist is an owner-side/read-only helper. It maps BaseScan's common
return reasons to GCA evidence pages and identifies the remaining blocker
before a clean token-profile resubmission.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from tools.check_site_links import scan_site
except ModuleNotFoundError:  # pragma: no cover - used when running from tools/
    from check_site_links import scan_site


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
REMEDIATION_PATH = ROOT / "site" / "basescan-remediation.json"
VALUES_PATH = ROOT / "launch" / "basescan_resubmission_values.json"
DOMAIN_EMAIL_PATH = ROOT / "site" / "domain-email.json"
REVIEWER_KIT_PATH = ROOT / "site" / "reviewer-kit.json"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return payload


def checklist_item(
    key: str,
    title: str,
    status: str,
    evidence: str,
    links: list[str],
    action: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "status": status,
        "evidence": evidence,
        "links": links,
        "action": action,
    }


def build_checklist(
    *,
    remediation_path: Path = REMEDIATION_PATH,
    values_path: Path = VALUES_PATH,
    domain_email_path: Path = DOMAIN_EMAIL_PATH,
    reviewer_kit_path: Path = REVIEWER_KIT_PATH,
    site_root: Path = SITE_ROOT,
) -> dict[str, Any]:
    remediation = load_json(remediation_path)
    values = load_json(values_path)
    domain_email = load_json(domain_email_path)
    reviewer_kit = load_json(reviewer_kit_path)
    identity = remediation["officialIdentity"]
    email_state = remediation["currentEmailState"]
    market = values["officialMarketPool"]
    external_status = reviewer_kit["externalReviewStatus"]
    link_report = scan_site(site_root)

    domain_email_ready = domain_email["baseScanUse"].get("resubmissionReady") is True
    sender_status = "implemented-domain-email-evidence-ready" if domain_email_ready else "blocked-owner-action-required"
    sender_evidence = (
        "The official project-domain mailbox support@gcagochina.com is active, public DNS records pass MX/SPF/DKIM/DMARC checks, inbound and outbound tests are archived privately, and public support/BaseScan materials publish the same domain email."
        if domain_email_ready
        else "Current public email is still GCAgochina@outlook.com. Domain email setup is published, but the latest DNS snapshot is not ready for BaseScan evidence."
    )
    sender_action = (
        "Submit one clean BaseScan token-profile update from support@gcagochina.com, attaching the public evidence links and retaining private mailbox screenshots for reviewer follow-up."
        if domain_email_ready
        else "Activate support@gcagochina.com, add MX/SPF/DKIM/DMARC, verify inbound/outbound tests, switch public email, then archive the evidence packet."
    )
    link_status = "implemented-with-automated-check" if link_report.ok else "blocked-link-integrity-failed"
    link_evidence = (
        f"tools/check_site_links.py parsed {link_report.page_count} HTML pages and "
        f"{link_report.reference_count} URL references, verified {len(link_report.internal_urls)} unique "
        "internal targets, fragments, duplicate IDs, placeholder schemes, and safe external-link attributes, "
        "and found no errors."
        if link_report.ok
        else f"The site link-integrity gate found {len(link_report.errors)} error(s); clean resubmission is blocked until they are fixed."
    )

    items = [
        checklist_item(
            "website-accessible",
            "Website accessible and safe to visit",
            "implemented",
            "Public HTTPS website, start page, verification page, sitemap, and robots file are published and checked by tools/check_public_site.py.",
            [identity["website"], identity["startPage"], identity["verify"]],
            "Keep public site checks passing before every resubmission.",
        ),
        checklist_item(
            "clear-project-information",
            "Clear token and project information",
            "implemented",
            "About, status, whitepaper, product, trust, and reviewer pages describe GCA without claiming approval, audit completion, or guaranteed market outcomes.",
            [
                identity["about"],
                identity["whitepaper"],
                identity["support"],
                remediation["pageUrl"],
                "https://gcagochina.com/reviewer-kit.html",
            ],
            "Use the readable pages first; raw JSON only when a reviewer asks for machine-readable data.",
        ),
        checklist_item(
            "placeholder-and-link-review",
            "No obvious placeholders or broken reviewer links",
            link_status,
            link_evidence,
            ["https://gcagochina.com/data.html", "https://gcagochina.com/site-map.html"],
            "Run the local link-integrity check before deployment, then run its live HTTPS mode and tools/check_public_site.py after deployment.",
        ),
        checklist_item(
            "team-responsibility-transparency",
            "Team responsibility transparency",
            "implemented-official-domain-equivalent",
            "GCA operating roles and responsibilities are published on the official domain with official X, Telegram, and project evidence links.",
            [
                identity["team"],
                identity["teamResponsibilities"],
                identity["projectProfileSource"],
                identity["telegram"],
                identity["x"],
            ],
            "If BaseScan specifically requests external organization evidence, publish an official organization profile on a recognized business network.",
        ),
        checklist_item(
            "sender-domain-email",
            "Sender email matches project domain",
            sender_status,
            sender_evidence,
            [
                email_state["domainEmailSetupPlan"],
                email_state["domainEmailDnsWorksheet"],
                email_state["domainEmailSetupPlanData"],
            ],
            sender_action,
        ),
        checklist_item(
            "source-and-contract",
            "Verified source and fixed-supply token facts",
            "implemented",
            "BaseScan source verification and deployer-wallet ownership verification are complete; the contract has fixed supply and no post-deployment mint function.",
            [values["baseScanContract"], "https://gcagochina.com/onchain-proofs.html", "https://gcagochina.com/token-safety.html"],
            "Keep the chain as Base Mainnet / chainId 8453 and contract address unchanged.",
        ),
        checklist_item(
            "brand-logo-whitepaper",
            "Logo, brand kit, and whitepaper",
            "implemented",
            "SVG/PNG logos, social card, brand kit, and whitepaper are published over HTTPS.",
            [identity["brandKit"], identity["logoSvg"], identity["logoPng"], identity["whitepaper"]],
            "Use the same 32x32 SVG logo URL and whitepaper URL in BaseScan.",
        ),
        checklist_item(
            "social-and-market-links",
            "Official social links and market route",
            "implemented",
            "Telegram, X, project profile, and the official Base Mainnet GCA/USDT market route are published. GeckoTerminal token information is approved.",
            [
                identity["telegram"],
                identity["x"],
                identity["projectProfileSource"],
                market["geckoTerminalUrl"],
                market["dexScreenerUrl"],
            ],
            "Keep all public materials pointed to the GCA/USDT route, not the older WETH pilot pool.",
        ),
    ]

    blocked = [item["key"] for item in items if item["status"].startswith("blocked")]
    return {
        "schema": "gca-basescan-reviewer-checklist-v1",
        "status": "blocked-before-basescan-resubmission" if blocked else "ready-for-owner-review",
        "readyForCleanResubmission": not blocked and values.get("nextSubmissionReady") is True,
        "blockedItems": blocked,
        "baseScanTokenProfileStatus": external_status["baseScanTokenProfile"],
        "latestReturnNoticeDate": values["latestReturnNoticeDate"],
        "baseScanFinalSubmissionPackageGeneratedAt": values["baseScanFinalSubmissionPackageGeneratedAt"],
        "dailyStatusGeneratedAt": values["dailyStatusGeneratedAt"],
        "officialEmail": values["officialEmail"],
        "targetDomainEmail": domain_email["targetDomainEmail"],
        "domainEmailReady": domain_email["baseScanUse"]["resubmissionReady"],
        "siteLinkIntegrity": {
            "ok": link_report.ok,
            "pageCount": link_report.page_count,
            "referenceCount": link_report.reference_count,
            "uniqueInternalTargetCount": len(link_report.internal_urls),
            "errors": list(link_report.errors),
        },
        "checklist": items,
        "preflightCommands": [
            "python3 tools/check_site_links.py --site-root site",
            "python3 tools/check_site_links.py --site-root site --base-url https://gcagochina.com/ --check-live --timeout 30",
            "python3 tools/sync_basescan_daily_status_references.py --check --json",
            "python3 tools/sync_basescan_final_package_references.py --check --json",
            "python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector <provider-selector> --json",
            "python3 tools/build_domain_email_evidence_packet.py --dkim-selector <provider-selector> --evidence-dir launch/domain_email_evidence --website-email-updated --output-json launch/domain_email_evidence_packet.json --output-md launch/domain_email_evidence_packet.md",
            "python3 tools/build_domain_email_switch_plan.py --json",
            "python3 tools/check_basescan_resubmission_readiness.py --json --require-ready",
            "python3 tools/build_basescan_submission_package.py --json --require-ready --output-json launch/basescan_final_submission_package.json --output-md launch/basescan_final_submission_package.md",
        ],
        "boundaries": {
            "readOnlyByDefault": True,
            "writesPublicFiles": False,
            "sendsEmail": False,
            "writesDns": False,
            "submitsBaseScanRequest": False,
            "signsWalletMessage": False,
            "touchesWalletsOrContracts": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# GCA BaseScan Reviewer Checklist",
        "",
        f"- Status: `{report['status']}`",
        f"- Ready for clean resubmission: `{str(report['readyForCleanResubmission']).lower()}`",
        f"- Latest return notice: `{report['latestReturnNoticeDate']}`",
        f"- Final submission package: `{report['baseScanFinalSubmissionPackageGeneratedAt']}`",
        f"- Daily public status: `{report['dailyStatusGeneratedAt']}`",
        f"- Current official email: `{report['officialEmail']}`",
        f"- Target domain email: `{report['targetDomainEmail']}`",
        "",
        "## Checklist",
        "",
        "| Item | Status | Evidence | Action |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["checklist"]:
        lines.append(f"| {item['title']} | `{item['status']}` | {item['evidence']} | {item['action']} |")
    lines.extend(["", "## Preflight Commands", ""])
    for command in report["preflightCommands"]:
        lines.append(f"- `{command}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- This checklist does not submit BaseScan requests.",
            "- This checklist does not send email, write DNS, sign wallet messages, or touch wallets/contracts.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the GCA BaseScan reviewer checklist.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--markdown", action="store_true", help="Print markdown output.")
    parser.add_argument("--output-json", help="Optional JSON output path.")
    parser.add_argument("--output-md", help="Optional markdown output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_checklist()
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.markdown:
        print(render_markdown(report), end="")
    else:
        print("GCA BaseScan reviewer checklist")
        print(f"status: {report['status']}")
        print(f"readyForCleanResubmission: {str(report['readyForCleanResubmission']).lower()}")
        if report["blockedItems"]:
            print("blockedItems:")
            for item in report["blockedItems"]:
                print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
