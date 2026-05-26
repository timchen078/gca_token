"""Build the GCA domain email provider decision matrix.

This is an owner-side/read-only helper for choosing a mailbox path before the
next BaseScan resubmission. It does not fetch live prices, write DNS records,
send email, submit BaseScan requests, or touch wallets/contracts.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "site" / "domain-email.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_matrix(config: dict[str, Any] | None = None, *, generated_at: str | None = None) -> dict[str, Any]:
    config = config or load_json(DEFAULT_CONFIG_PATH)
    target_email = config.get("targetDomainEmail", "support@gcagochina.com")
    current_email = config.get("currentPublicEmail", "GCAgochina@outlook.com")
    domain = config.get("domain", "gcagochina.com")

    provider_options = [
        {
            "key": "zoho-mail",
            "label": "Zoho Mail or equivalent low-cost hosted mailbox",
            "fit": "recommended-first-check",
            "why": "Often suitable when the owner wants a lower-cost full mailbox path, provided it creates a real mailbox and publishes MX, SPF, DKIM, and DMARC.",
            "mustProvide": [
                "mailbox UI or authenticated outbound sending as support@gcagochina.com",
                "inbound mail routing for gcagochina.com",
                "provider MX records",
                "provider SPF value",
                "provider DKIM selector and record",
                "DMARC guidance or starter record",
            ],
            "notEnoughIf": [
                "only forwarding inbound mail",
                "no outbound sender as support@gcagochina.com",
                "no DKIM selector or no authenticated sending proof",
            ],
        },
        {
            "key": "google-workspace",
            "label": "Google Workspace",
            "fit": "acceptable-full-mailbox",
            "why": "Acceptable if the custom domain is verified and the mailbox can send and receive as support@gcagochina.com with MX, SPF, DKIM, and DMARC configured.",
            "mustProvide": [
                "domain verification",
                "Gmail mailbox for support@gcagochina.com",
                "Google MX records",
                "Google SPF include merged into one SPF record",
                "Google DKIM selector and TXT record",
                "DMARC TXT record",
            ],
            "notEnoughIf": [
                "domain verification is incomplete",
                "visible outbound sender is still a non-domain Gmail address",
            ],
        },
        {
            "key": "microsoft-365",
            "label": "Microsoft 365",
            "fit": "acceptable-full-mailbox",
            "why": "Acceptable if the custom domain is verified and Outlook sends and receives as support@gcagochina.com with the required mail DNS records.",
            "mustProvide": [
                "domain verification",
                "Exchange mailbox or alias that sends as support@gcagochina.com",
                "Microsoft MX record",
                "Microsoft SPF include merged into one SPF record",
                "Microsoft DKIM records",
                "DMARC TXT record",
            ],
            "notEnoughIf": [
                "support@gcagochina.com is only an unverified alias",
                "outbound sender alignment is not visible in replies",
            ],
        },
        {
            "key": "cloudflare-email-routing-only",
            "label": "Cloudflare Email Routing only",
            "fit": "not-sufficient-alone",
            "why": "Useful for inbound forwarding, but receive-only routing does not prove outbound sender alignment for a clean BaseScan resubmission.",
            "mustProvide": [
                "a separate authenticated outbound sending path if used",
                "clear proof that replies visibly come from support@gcagochina.com",
            ],
            "notEnoughIf": [
                "the setup only forwards inbound mail to Outlook or Gmail",
                "BaseScan replies are still sent from GCAgochina@outlook.com",
            ],
        },
        {
            "key": "smtp-or-api-send-only",
            "label": "Outbound SMTP/API only",
            "fit": "not-sufficient-alone",
            "why": "Send-only services can help with authenticated outbound mail, but BaseScan also needs a contact path that receives external mail at the same domain address.",
            "mustProvide": [
                "inbound mailbox or routing for support@gcagochina.com",
                "authenticated outbound signing",
                "message evidence for both directions",
            ],
            "notEnoughIf": [
                "support@gcagochina.com cannot receive user or reviewer replies",
            ],
        },
    ]

    return {
        "schema": "gca-domain-email-provider-matrix-v1",
        "generatedAt": generated_at or utc_now(),
        "domain": domain,
        "currentPublicEmail": current_email,
        "targetDomainEmail": target_email,
        "status": "choose-full-mailbox-before-basescan-resubmission",
        "noLivePricing": True,
        "pricingNote": "This matrix intentionally does not publish live prices. Check provider dashboards directly before purchase because prices and plans can change.",
        "decisionRule": (
            "Choose the lowest-cost full mailbox path that can receive external mail, send authenticated external mail, "
            "publish MX/SPF/DKIM/DMARC, and produce evidence for support@gcagochina.com."
        ),
        "recommendedDefault": "Start by checking a low-cost full hosted mailbox such as Zoho Mail or an equivalent provider, then use Google Workspace or Microsoft 365 if you prefer those ecosystems.",
        "providerOptions": provider_options,
        "recordsToCollectFromProvider": [
            {
                "record": "MX",
                "ownerInput": "copy provider host, value, and priority exactly",
                "doNotGuess": True,
            },
            {
                "record": "SPF",
                "ownerInput": "copy provider SPF include and merge into one root-domain v=spf1 record",
                "doNotGuess": True,
            },
            {
                "record": "DKIM",
                "ownerInput": "copy provider selector, record type, host, and value exactly",
                "doNotGuess": True,
            },
            {
                "record": "DMARC",
                "ownerInput": "add _dmarc.gcagochina.com, starting with monitoring mode if needed",
                "doNotGuess": False,
            },
        ],
        "ownerQuestionsBeforePurchase": [
            "Can the provider create support@gcagochina.com as a real mailbox or send-as identity?",
            "Can the provider receive external mail at support@gcagochina.com?",
            "Can the provider send replies where the visible sender is support@gcagochina.com?",
            "Does the provider expose MX, SPF, DKIM, and DMARC setup steps for custom domains?",
            "Can the owner access DNS for gcagochina.com to add those records?",
        ],
        "nextCommandsAfterProviderSetup": [
            "python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector <provider-selector> --json",
            "python3 tools/build_domain_email_evidence_packet.py --dkim-selector <provider-selector> --website-email-updated --output-json launch/domain_email_evidence_packet.json --output-md launch/domain_email_evidence_packet.md",
            "python3 tools/build_domain_email_switch_plan.py --json",
            "python3 tools/check_basescan_resubmission_readiness.py --json --require-ready",
            "python3 tools/build_basescan_submission_package.py --json --require-ready --output-json launch/basescan_final_submission_package.json --output-md launch/basescan_final_submission_package.md",
        ],
        "boundaries": {
            "fetchesLivePrices": False,
            "writesDnsRecords": False,
            "sendsEmail": False,
            "submitsBaseScanRequest": False,
            "touchesWalletsOrContracts": False,
            "storesSecrets": False,
        },
    }


def render_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# GCA Domain Email Provider Decision Matrix",
        "",
        f"- Status: `{matrix['status']}`",
        f"- Current public email: `{matrix['currentPublicEmail']}`",
        f"- Target domain email: `{matrix['targetDomainEmail']}`",
        f"- No live pricing: `{str(matrix['noLivePricing']).lower()}`",
        "",
        "## Decision Rule",
        "",
        matrix["decisionRule"],
        "",
        f"Recommended default: {matrix['recommendedDefault']}",
        "",
        "## Provider Options",
        "",
        "| Provider path | Fit | Why |",
        "| --- | --- | --- |",
    ]
    for option in matrix["providerOptions"]:
        lines.append(f"| {option['label']} | `{option['fit']}` | {option['why']} |")
    lines.extend([
        "",
        "## Records To Collect",
        "",
    ])
    for record in matrix["recordsToCollectFromProvider"]:
        guess = "do not guess" if record["doNotGuess"] else "use provider guidance or safe starter policy"
        lines.append(f"- `{record['record']}`: {record['ownerInput']} ({guess}).")
    lines.extend([
        "",
        "## Owner Questions Before Purchase",
        "",
    ])
    for question in matrix["ownerQuestionsBeforePurchase"]:
        lines.append(f"- {question}")
    lines.extend([
        "",
        "## Commands After Provider Setup",
        "",
    ])
    for command in matrix["nextCommandsAfterProviderSetup"]:
        lines.append(f"- `{command}`")
    lines.extend([
        "",
        "## Boundaries",
        "",
        "- This matrix does not fetch live prices.",
        "- This matrix does not write DNS records, send email, submit BaseScan requests, store secrets, or touch wallets/contracts.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the GCA domain email provider decision matrix.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout.")
    parser.add_argument("--markdown", action="store_true", help="Print Markdown to stdout.")
    parser.add_argument("--output-json", type=Path, help="Write JSON artifact.")
    parser.add_argument("--output-md", type=Path, help="Write Markdown artifact.")
    args = parser.parse_args(argv)

    matrix = build_matrix(load_json(args.config))

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(matrix), encoding="utf-8")

    if args.json:
        print(json.dumps(matrix, indent=2, sort_keys=True))
    elif args.markdown:
        print(render_markdown(matrix))
    else:
        print("GCA domain email provider matrix")
        print(f"status: {matrix['status']}")
        print(f"targetDomainEmail: {matrix['targetDomainEmail']}")
        print("recommendedDefault: check a low-cost full hosted mailbox first")
        print("boundary: no DNS writes, no email sends, no BaseScan submission")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
