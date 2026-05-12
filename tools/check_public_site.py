#!/usr/bin/env python3
"""Check live GCA public site endpoints for canonical identity drift."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://gcagochina.com/"
MAINNET_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6"
OFFICIAL_POOL_ADDRESS = "0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0"
BASE_USDT_ADDRESS = "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"
OLD_WETH_POOL_ADDRESS = "0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff"
OFFICIAL_GECKOTERMINAL_URL = f"https://www.geckoterminal.com/base/pools/{OFFICIAL_POOL_ADDRESS}"
OFFICIAL_DEXSCREENER_URL = f"https://dexscreener.com/base/{OFFICIAL_POOL_ADDRESS}"
MEMBER_PROGRAM_URL = "https://gcagochina.com/member-program.json"


class SiteCheckError(AssertionError):
    """Raised when a public site check fails."""


EndpointCheck = tuple[str, Callable[[str], None]]


def assert_contains(text: str, expected: str, label: str) -> None:
    if expected not in text:
        raise SiteCheckError(f"{label}: missing {expected!r}")


def assert_not_contains(text: str, forbidden: str, label: str) -> None:
    if forbidden in text:
        raise SiteCheckError(f"{label}: found forbidden {forbidden!r}")


def assert_current_pool_text(text: str, label: str) -> None:
    assert_contains(text, "GCA/USDT", label)
    assert_contains(text, OFFICIAL_POOL_ADDRESS, label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def load_json(text: str, label: str) -> dict:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SiteCheckError(f"{label}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SiteCheckError(f"{label}: expected JSON object")
    return payload


def validate_root(text: str) -> None:
    label = "/"
    assert_contains(text, "GCA", label)
    assert_contains(text, "Verify GCA", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_current_pool_text(text, label)


def validate_verify(text: str) -> None:
    label = "/verify.html"
    assert_contains(text, "Verify GCA", label)
    assert_contains(text, "Submitted, awaiting review", label)
    assert_contains(text, "well-known token identity", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_current_pool_text(text, label)


def validate_markets(text: str) -> None:
    label = "/markets.html"
    assert_contains(text, "Official GCA Markets", label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)


def validate_members(text: str) -> None:
    label = "/members.html"
    assert_contains(text, "GCA Member Pre-Registration", label)
    assert_contains(text, "100 Credit Rules", label)
    assert_contains(text, "Member Rules", label)
    assert_contains(text, "Support Workflow", label)
    assert_contains(text, "member-program.json", label)
    assert_contains(text, "180 days", label)
    assert_contains(text, "30 days", label)
    assert_contains(text, "5-10 business days", label)
    assert_contains(text, "Direct submission is not connected", label)
    assert_contains(text, "No cash, token rebate, income, reimbursement, trading permission, or risk-control bypass", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)


def validate_project_json(text: str) -> None:
    label = "/project.json"
    payload = load_json(text, label)
    market = payload.get("market", {})
    status = payload.get("platformStatus", {})
    member_program = payload.get("memberProgram", {})

    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("memberProgramRulesUrl") != MEMBER_PROGRAM_URL:
        raise SiteCheckError(f"{label}: wrong memberProgramRulesUrl")
    if market.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialPair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if status.get("baseScanTokenProfile") != "submitted-awaiting-review":
        raise SiteCheckError(f"{label}: unexpected BaseScan status")
    if status.get("geckoTerminalTokenInfo") != "approved-2026-05-11":
        raise SiteCheckError(f"{label}: unexpected GeckoTerminal status")
    if member_program.get("status") != "rules-published-public-claim-not-connected":
        raise SiteCheckError(f"{label}: unexpected member program status")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_tokenlist_json(text: str) -> None:
    label = "/tokenlist.json"
    payload = load_json(text, label)
    tokens = payload.get("tokens")
    if not isinstance(tokens, list) or len(tokens) != 1:
        raise SiteCheckError(f"{label}: expected one token")

    token = tokens[0]
    extensions = token.get("extensions", {})
    if token.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if token.get("address") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong address")
    if token.get("symbol") != "GCA":
        raise SiteCheckError(f"{label}: wrong symbol")
    if extensions.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialPair")
    if extensions.get("officialPool") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong officialPool")
    if extensions.get("memberProgramRules") != MEMBER_PROGRAM_URL:
        raise SiteCheckError(f"{label}: wrong memberProgramRules")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_well_known_json(text: str) -> None:
    label = "/.well-known/gca-token.json"
    payload = load_json(text, label)
    network = payload.get("network", {})
    token = payload.get("token", {})
    urls = payload.get("officialUrls", {})
    market = payload.get("market", {})
    security = payload.get("securityFacts", {})

    if network.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if token.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if urls.get("memberProgramRules") != MEMBER_PROGRAM_URL:
        raise SiteCheckError(f"{label}: wrong memberProgramRules")
    if market.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialPair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if security.get("thirdPartyAuditCompleted") is not False:
        raise SiteCheckError(f"{label}: third-party audit status must remain false")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_member_program_json(text: str) -> None:
    label = "/member-program.json"
    payload = load_json(text, label)
    token = payload.get("token", {})
    holder_bonus = payload.get("holderBonus", {})
    member_tier = payload.get("memberTier", {})
    verification = payload.get("verification", {})
    support = payload.get("supportWorkflow", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != MEMBER_PROGRAM_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("status") != "rules-published-public-claim-not-connected":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if token.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if holder_bonus.get("minimumHolding") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder bonus threshold")
    if holder_bonus.get("creditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong credit amount")
    if holder_bonus.get("creditExpiry") != "180 days after ledger activation unless a later published policy extends it":
        raise SiteCheckError(f"{label}: wrong credit expiry")
    if member_tier.get("minimumHolding") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member threshold")
    if member_tier.get("refreshCadence") != "30 days after activation, or earlier if the user requests a manual recheck":
        raise SiteCheckError(f"{label}: wrong member refresh cadence")
    if verification.get("directSubmissionEndpointConfigured") is not False:
        raise SiteCheckError(f"{label}: direct submission must remain false")
    if support.get("contactEmail") != "GCAgochina@outlook.com":
        raise SiteCheckError(f"{label}: wrong support contact")
    if "ledger_recorded" not in support.get("reviewStatuses", []):
        raise SiteCheckError(f"{label}: missing ledger_recorded status")
    if not any("public self-service claiming is not connected" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing not-connected safe claim")
    if not any("credits or membership are cash" in claim for claim in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing cash/token do-not-claim boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_security_txt(text: str) -> None:
    label = "/.well-known/security.txt"
    assert_contains(text, "Contact: mailto:GCAgochina@outlook.com", label)
    assert_contains(text, "Policy: https://gcagochina.com/security.html", label)
    assert_contains(text, "Canonical: https://gcagochina.com/.well-known/security.txt", label)


def validate_sitemap(text: str) -> None:
    label = "/sitemap.xml"
    for expected in (
        "https://gcagochina.com/verify.html",
        "https://gcagochina.com/markets.html",
        "https://gcagochina.com/member-program.json",
        "https://gcagochina.com/project.json",
        "https://gcagochina.com/tokenlist.json",
        "https://gcagochina.com/.well-known/gca-token.json",
        "https://gcagochina.com/.well-known/security.txt",
    ):
        assert_contains(text, expected, label)


def validate_robots(text: str) -> None:
    label = "/robots.txt"
    assert_contains(text, "Allow: /member-program.json", label)
    assert_contains(text, "Allow: /.well-known/gca-token.json", label)
    assert_contains(text, "Allow: /.well-known/security.txt", label)
    assert_contains(text, "Sitemap: https://gcagochina.com/sitemap.xml", label)


CHECKS: list[EndpointCheck] = [
    ("/", validate_root),
    ("/verify.html", validate_verify),
    ("/markets.html", validate_markets),
    ("/members.html", validate_members),
    ("/member-program.json", validate_member_program_json),
    ("/project.json", validate_project_json),
    ("/tokenlist.json", validate_tokenlist_json),
    ("/.well-known/gca-token.json", validate_well_known_json),
    ("/.well-known/security.txt", validate_security_txt),
    ("/sitemap.xml", validate_sitemap),
    ("/robots.txt", validate_robots),
]


def build_ssl_context(allow_insecure_tls: bool) -> ssl.SSLContext | None:
    if allow_insecure_tls:
        return ssl._create_unverified_context()

    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def fetch_text(
    base_url: str,
    path: str,
    timeout: float,
    context: ssl.SSLContext | None,
) -> tuple[str, str]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, headers={"User-Agent": "gca-public-site-check/1.0"})
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            status = getattr(response, "status", None)
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise SiteCheckError(f"{url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise SiteCheckError(f"{url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise SiteCheckError(f"{url}: timeout") from exc

    if status != 200:
        raise SiteCheckError(f"{url}: HTTP {status}")
    return url, body


def run_checks(base_url: str, timeout: float, allow_insecure_tls: bool = False) -> int:
    failures: list[str] = []
    context = build_ssl_context(allow_insecure_tls)
    for path, validator in CHECKS:
        try:
            url, body = fetch_text(base_url, path, timeout, context)
            validator(body)
        except SiteCheckError as exc:
            failures.append(str(exc))
            print(f"[fail] {path}: {exc}", file=sys.stderr)
        else:
            print(f"[ok] {path}: {url}")

    if failures:
        print(f"\n{len(failures)} public site check(s) failed.", file=sys.stderr)
        return 1

    print("\nAll public GCA site checks passed.")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--allow-insecure-tls",
        action="store_true",
        help="Disable TLS certificate verification only for local debugging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    return run_checks(args.base_url, args.timeout, args.allow_insecure_tls)


if __name__ == "__main__":
    raise SystemExit(main())
