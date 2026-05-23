#!/usr/bin/env python3
"""Check public DNS readiness for the GCA project-domain mailbox.

The check is read-only. It queries public DNS records with `dig` and does not
send email, submit forms, write files, or touch wallets/contracts.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Callable


DEFAULT_DOMAIN = "gcagochina.com"
DEFAULT_MAILBOX_LOCAL_PART = "support"
DEFAULT_TIMEOUT = 10.0


class DomainEmailDnsError(RuntimeError):
    """Raised for expected operator-facing DNS check failures."""


Runner = Callable[..., Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_domain(domain: str) -> str:
    cleaned = domain.strip().lower().rstrip(".")
    if not cleaned or "://" in cleaned or "/" in cleaned or " " in cleaned:
        raise DomainEmailDnsError("domain must be a bare DNS name such as gcagochina.com")
    if "." not in cleaned:
        raise DomainEmailDnsError("domain must contain a public suffix")
    return cleaned


def normalize_mailbox(mailbox: str, domain: str) -> str:
    cleaned = mailbox.strip().lower()
    if not cleaned:
        cleaned = DEFAULT_MAILBOX_LOCAL_PART
    if "@" not in cleaned:
        cleaned = f"{cleaned}@{domain}"
    local_part, _, mailbox_domain = cleaned.partition("@")
    if not local_part or mailbox_domain != domain:
        raise DomainEmailDnsError(f"mailbox must be on {domain}")
    return cleaned


def normalize_txt_line(line: str) -> str:
    stripped = line.strip()
    chunks = re.findall(r'"([^"]*)"', stripped)
    if chunks:
        return "".join(chunks)
    return stripped.rstrip(".")


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def run_dig(
    *,
    name: str,
    record_type: str,
    timeout: float,
    runner: Runner = subprocess.run,
) -> list[str]:
    command = ["dig", "+short", record_type, name]
    try:
        completed = runner(command, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise DomainEmailDnsError("dig is not installed or not available on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise DomainEmailDnsError(f"DNS query timed out for {record_type} {name}") from exc

    returncode = int(getattr(completed, "returncode", 0))
    if returncode != 0:
        stderr = str(getattr(completed, "stderr", "") or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise DomainEmailDnsError(f"dig failed for {record_type} {name}{detail}")

    return nonempty_lines(str(getattr(completed, "stdout", "") or ""))


def find_prefixed_txt_records(lines: list[str], prefix: str) -> list[str]:
    normalized = [normalize_txt_line(line) for line in lines]
    return [record for record in normalized if record.lower().startswith(prefix.lower())]


def build_check(status: str, records: list[str] | None = None, message: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "records": records or [],
        "message": message,
    }


def run_checks(
    *,
    domain: str = DEFAULT_DOMAIN,
    mailbox: str = DEFAULT_MAILBOX_LOCAL_PART,
    dkim_selector: str = "",
    timeout: float = DEFAULT_TIMEOUT,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    domain = normalize_domain(domain)
    mailbox = normalize_mailbox(mailbox, domain)
    selector = dkim_selector.strip().lower()
    if selector and not re.fullmatch(r"[a-z0-9._-]+", selector):
        raise DomainEmailDnsError("dkim selector contains unsupported characters")

    mx_records = run_dig(name=domain, record_type="MX", timeout=timeout, runner=runner)
    domain_txt = run_dig(name=domain, record_type="TXT", timeout=timeout, runner=runner)
    dmarc_name = f"_dmarc.{domain}"
    dmarc_txt = run_dig(name=dmarc_name, record_type="TXT", timeout=timeout, runner=runner)

    spf_records = find_prefixed_txt_records(domain_txt, "v=spf1")
    dmarc_records = find_prefixed_txt_records(dmarc_txt, "v=DMARC1")

    checks: dict[str, dict[str, Any]] = {
        "mx": build_check(
            "present" if mx_records else "missing",
            mx_records,
            "MX routes inbound mail for the project domain.",
        ),
        "spf": build_check(
            "present" if spf_records else "missing",
            spf_records,
            "SPF authorizes outbound mail sources for the project domain.",
        ),
        "dmarc": build_check(
            "present" if dmarc_records else "missing",
            dmarc_records,
            "DMARC publishes domain-level email authentication policy.",
        ),
    }

    if len(spf_records) > 1:
        checks["spf"]["status"] = "multiple"
        checks["spf"]["message"] = "Multiple SPF records are usually invalid; merge them into one TXT record."

    if selector:
        dkim_name = f"{selector}._domainkey.{domain}"
        dkim_txt = run_dig(name=dkim_name, record_type="TXT", timeout=timeout, runner=runner)
        dkim_records = find_prefixed_txt_records(dkim_txt, "v=DKIM1")
        checks["dkim"] = build_check(
            "present" if dkim_records else "missing",
            dkim_records,
            f"DKIM selector checked at {dkim_name}.",
        )
    else:
        checks["dkim"] = build_check(
            "selector-required",
            [],
            "Pass --dkim-selector from the mail provider before treating the evidence packet as ready.",
        )

    ready = (
        checks["mx"]["status"] == "present"
        and checks["spf"]["status"] == "present"
        and checks["dmarc"]["status"] == "present"
        and checks["dkim"]["status"] == "present"
    )
    missing_or_blocked = [name for name, check in checks.items() if check["status"] != "present"]

    return {
        "ok": True,
        "service": "gca-domain-email-dns-check",
        "checkedAt": utc_now(),
        "domain": domain,
        "targetMailbox": mailbox,
        "targetDomainEmail": f"{DEFAULT_MAILBOX_LOCAL_PART}@{domain}",
        "dkimSelector": selector or None,
        "readyForBaseScanEmailEvidence": ready,
        "missingOrBlockedChecks": missing_or_blocked,
        "checks": checks,
        "boundaries": {
            "readOnlyDnsCheck": True,
            "sendsEmail": False,
            "writesFiles": False,
            "submitsBaseScanRequest": False,
            "touchesWalletOrContract": False,
            "printsSecrets": False,
        },
    }


def print_text_report(result: dict[str, Any]) -> None:
    print(f"GCA domain email DNS readiness for {result['targetMailbox']}")
    print(f"domain: {result['domain']}")
    print(f"readyForBaseScanEmailEvidence: {str(result['readyForBaseScanEmailEvidence']).lower()}")
    for name in ("mx", "spf", "dmarc", "dkim"):
        check = result["checks"][name]
        print(f"- {name}: {check['status']}")
        if check.get("message"):
            print(f"  {check['message']}")
        for record in check.get("records", []):
            print(f"  record: {record}")
    if result["missingOrBlockedChecks"]:
        print("missingOrBlockedChecks: " + ", ".join(result["missingOrBlockedChecks"]))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check GCA project-domain email DNS readiness.")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help=f"Domain to check. Default: {DEFAULT_DOMAIN}")
    parser.add_argument(
        "--mailbox",
        default=DEFAULT_MAILBOX_LOCAL_PART,
        help="Mailbox local-part or full address. Default: support",
    )
    parser.add_argument(
        "--dkim-selector",
        default="",
        help="DKIM selector from the mail provider. Required before the evidence packet can be ready.",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="DNS query timeout in seconds.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Exit non-zero if MX, SPF, DMARC, and DKIM are not all present.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_checks(
            domain=args.domain,
            mailbox=args.mailbox,
            dkim_selector=args.dkim_selector,
            timeout=args.timeout,
        )
    except DomainEmailDnsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_text_report(result)

    if args.require_ready and not result["readyForBaseScanEmailEvidence"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
