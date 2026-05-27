#!/usr/bin/env python3
"""Build a GCA domain-email DNS entry packet from provider-supplied records.

This owner-side helper turns the exact MX, SPF, DKIM, and DMARC values shown by
the chosen mail provider into a copyable worksheet. It does not write DNS
records, send email, submit BaseScan requests, or touch wallets/contracts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOMAIN = "gcagochina.com"
DEFAULT_MAILBOX = "support"


class DnsEntryPacketError(RuntimeError):
    """Raised for expected operator-facing packet errors."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean(value: str | None) -> str:
    return (value or "").strip()


def reject_multiline(value: str, label: str) -> None:
    if "\n" in value or "\r" in value:
        raise DnsEntryPacketError(f"{label} must be a single DNS value, not multiple lines")


def parse_mx(value: str) -> dict[str, Any]:
    text = clean(value)
    reject_multiline(text, "MX")
    parts = text.split()
    if len(parts) < 2:
        raise DnsEntryPacketError("MX must be formatted as '<priority> <host>', for example '10 mx.example.com'")
    try:
        priority = int(parts[0])
    except ValueError as exc:
        raise DnsEntryPacketError("MX priority must be an integer") from exc
    host = " ".join(parts[1:]).rstrip(".")
    if not host or "." not in host:
        raise DnsEntryPacketError("MX host must look like a provider hostname")
    return {"priority": priority, "value": host}


def validate_spf(value: str) -> str:
    text = clean(value)
    reject_multiline(text, "SPF")
    if not text.lower().startswith("v=spf1"):
        raise DnsEntryPacketError("SPF must start with v=spf1")
    return text


def validate_dkim_selector(value: str) -> str:
    selector = clean(value)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", selector):
        raise DnsEntryPacketError("DKIM selector may contain only letters, numbers, dots, underscores, or hyphens")
    return selector


def normalize_dkim_type(value: str) -> str:
    record_type = clean(value).upper()
    if record_type not in {"TXT", "CNAME"}:
        raise DnsEntryPacketError("DKIM type must be TXT or CNAME")
    return record_type


def validate_dns_value(value: str, label: str) -> str:
    text = clean(value)
    reject_multiline(text, label)
    if not text:
        raise DnsEntryPacketError(f"{label} value is required")
    return text


def validate_dmarc(value: str) -> str:
    text = validate_dns_value(value, "DMARC")
    if not text.lower().startswith("v=dmarc1"):
        raise DnsEntryPacketError("DMARC must start with v=DMARC1")
    return text


def build_packet(
    *,
    provider: str,
    domain: str = DEFAULT_DOMAIN,
    mailbox: str = DEFAULT_MAILBOX,
    mx_records: list[str] | None = None,
    spf: str = "",
    dkim_selector: str = "",
    dkim_type: str = "",
    dkim_value: str = "",
    dkim_host: str = "",
    dmarc: str = "",
    generated_at: str | None = None,
) -> dict[str, Any]:
    mx_input = mx_records or []
    records: list[dict[str, Any]] = []
    missing_or_blocked: list[str] = []

    parsed_mx: list[dict[str, Any]] = []
    for item in mx_input:
        if clean(item):
            parsed_mx.append(parse_mx(item))
    if not parsed_mx:
        missing_or_blocked.append("mx")
    for mx in parsed_mx:
        records.append({
            "record": "MX",
            "type": "MX",
            "nameOrHost": "@",
            "priority": mx["priority"],
            "value": mx["value"],
            "copyExactly": True,
        })

    if clean(spf):
        records.append({
            "record": "SPF",
            "type": "TXT",
            "nameOrHost": "@",
            "value": validate_spf(spf),
            "copyExactly": True,
            "note": "Keep one root-domain SPF TXT record; merge provider includes if another SPF record exists.",
        })
    else:
        missing_or_blocked.append("spf")

    if clean(dkim_selector) and clean(dkim_type) and clean(dkim_value):
        selector = validate_dkim_selector(dkim_selector)
        record_type = normalize_dkim_type(dkim_type)
        records.append({
            "record": "DKIM",
            "type": record_type,
            "nameOrHost": clean(dkim_host) or f"{selector}._domainkey",
            "selector": selector,
            "value": validate_dns_value(dkim_value, "DKIM"),
            "copyExactly": True,
            "note": "Use the provider's exact selector, host, record type, and value.",
        })
    else:
        missing_or_blocked.append("dkim")

    if clean(dmarc):
        records.append({
            "record": "DMARC",
            "type": "TXT",
            "nameOrHost": "_dmarc",
            "value": validate_dmarc(dmarc),
            "copyExactly": True,
            "note": "Monitoring mode is acceptable for first activation if delivery is not yet stable.",
        })
    else:
        missing_or_blocked.append("dmarc")

    ready = not missing_or_blocked
    target_email = f"{mailbox}@{domain}"
    return {
        "schema": "gca-domain-email-dns-entry-packet-v1",
        "generatedAt": generated_at or utc_now(),
        "provider": clean(provider) or "mail-provider-not-specified",
        "domain": domain,
        "targetDomainEmail": target_email,
        "status": "ready-for-owner-dns-entry-review" if ready else "missing-provider-dns-values",
        "readyForOwnerDnsEntryReview": ready,
        "missingOrBlockedRequirements": missing_or_blocked,
        "records": records,
        "nextCommandsAfterDnsEntry": [
            "python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector <provider-selector> --json",
            "python3 tools/build_domain_email_evidence_packet.py --dkim-selector <provider-selector> --evidence-dir launch/domain_email_evidence --website-email-updated --output-json launch/domain_email_evidence_packet.json --output-md launch/domain_email_evidence_packet.md",
            "python3 tools/check_basescan_resubmission_readiness.py --json --require-ready",
        ],
        "boundaries": {
            "writesDnsRecords": False,
            "sendsEmail": False,
            "submitsBaseScanRequest": False,
            "touchesWalletsOrContracts": False,
            "storesSecrets": False,
        },
    }


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# GCA Domain Email DNS Entry Packet",
        "",
        f"- Provider: `{packet['provider']}`",
        f"- Domain: `{packet['domain']}`",
        f"- Target email: `{packet['targetDomainEmail']}`",
        f"- Status: `{packet['status']}`",
        f"- Ready for owner DNS entry review: `{str(packet['readyForOwnerDnsEntryReview']).lower()}`",
        "",
    ]
    if packet["missingOrBlockedRequirements"]:
        lines.extend(["## Missing Provider Values", ""])
        lines.extend(f"- `{item}`" for item in packet["missingOrBlockedRequirements"])
        lines.append("")

    lines.extend([
        "## DNS Records To Enter",
        "",
        "| Record | Type | Name / Host | Priority | Value |",
        "| --- | --- | --- | ---: | --- |",
    ])
    for record in packet["records"]:
        priority = record.get("priority", "")
        value = str(record["value"]).replace("|", "\\|")
        lines.append(
            f"| {record['record']} | `{record['type']}` | `{record['nameOrHost']}` | "
            f"{priority} | `{value}` |"
        )

    lines.extend([
        "",
        "## After DNS Entry",
        "",
    ])
    lines.extend(f"- `{command}`" for command in packet["nextCommandsAfterDnsEntry"])
    lines.extend([
        "",
        "## Boundaries",
        "",
        "- This packet does not write DNS records.",
        "- This packet does not send email, submit BaseScan requests, store secrets, or touch wallets/contracts.",
        "",
    ])
    return "\n".join(lines)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a GCA domain email DNS entry packet.")
    parser.add_argument("--provider", default="", help="Mail provider name, for example Zoho Mail.")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--mailbox", default=DEFAULT_MAILBOX)
    parser.add_argument("--mx", action="append", default=[], help="Provider MX as '<priority> <host>'. Repeat for multiple MX records.")
    parser.add_argument("--spf", default="", help="Provider SPF TXT value.")
    parser.add_argument("--dkim-selector", default="", help="Provider DKIM selector.")
    parser.add_argument("--dkim-type", default="", help="Provider DKIM record type: TXT or CNAME.")
    parser.add_argument("--dkim-host", default="", help="Provider DKIM host/name. Defaults to <selector>._domainkey.")
    parser.add_argument("--dkim-value", default="", help="Provider DKIM TXT or CNAME value.")
    parser.add_argument("--dmarc", default="", help="DMARC TXT value.")
    parser.add_argument("--output-json", default="", help="Write packet JSON to this path.")
    parser.add_argument("--output-md", default="", help="Write packet Markdown to this path.")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout.")
    parser.add_argument("--markdown", action="store_true", help="Print Markdown to stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        packet = build_packet(
            provider=args.provider,
            domain=args.domain,
            mailbox=args.mailbox,
            mx_records=args.mx,
            spf=args.spf,
            dkim_selector=args.dkim_selector,
            dkim_type=args.dkim_type,
            dkim_host=args.dkim_host,
            dkim_value=args.dkim_value,
            dmarc=args.dmarc,
        )
    except DnsEntryPacketError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output_json:
        write_text(Path(args.output_json), json.dumps(packet, indent=2, sort_keys=True) + "\n")
    if args.output_md:
        write_text(Path(args.output_md), render_markdown(packet))
    if args.json:
        print(json.dumps(packet, indent=2, sort_keys=True))
    elif args.markdown or not (args.output_json or args.output_md):
        print(render_markdown(packet), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
