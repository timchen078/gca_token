#!/usr/bin/env python3
"""Read the public BaseScan pages and classify GCA token-profile publication.

This checker is deliberately read-only. It does not log in, sign a message,
submit a token update, or interact with the GCA contract.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import ssl
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:  # pragma: no cover - CI images may already expose a working system CA store.
    certifi = None


CONTRACT_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6"
TOKEN_URL = f"https://basescan.org/token/{CONTRACT_ADDRESS}"
ADDRESS_URL = f"https://basescan.org/address/{CONTRACT_ADDRESS}#code"
OFFICIAL_DOMAIN = "gcagochina.com"
DEFAULT_PREVIEW_PATH = "/assets/base/images/og-preview"
USER_AGENT = (
    "Mozilla/5.0 (compatible; GCA-Public-Profile-Checker/1.0; "
    "+https://gcagochina.com/)"
)


class BaseScanProfileCheckError(RuntimeError):
    """Raised when a public BaseScan page cannot be read or classified."""


class MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        normalized = {
            str(key).lower(): str(value or "")
            for key, value in attrs
            if key
        }
        key = normalized.get("name") or normalized.get("property")
        content = normalized.get("content", "")
        if key and content:
            self.meta[key.lower()] = content.strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_html_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise BaseScanProfileCheckError(f"HTML fixture not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise BaseScanProfileCheckError(f"HTML fixture is not UTF-8: {path}") from exc


def fetch_html(url: str, timeout: float) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    ssl_context = (
        ssl.create_default_context(cafile=certifi.where())
        if certifi is not None
        else ssl.create_default_context()
    )
    try:
        with urlopen(request, timeout=timeout, context=ssl_context) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise BaseScanProfileCheckError(f"BaseScan returned HTTP {status}: {url}")
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise BaseScanProfileCheckError(f"BaseScan returned HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise BaseScanProfileCheckError(f"Could not read BaseScan: {exc.reason}") from exc
    except TimeoutError as exc:
        raise BaseScanProfileCheckError(f"BaseScan request timed out after {timeout:g} seconds") from exc


def parse_meta(html: str) -> dict[str, str]:
    parser = MetaParser()
    parser.feed(html)
    return parser.meta


def parse_token_rep(description: str) -> str:
    match = re.search(r"\bToken\s+Rep:\s*([^|<]+)", description, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_holders(description: str) -> int | None:
    match = re.search(r"\bHolders:\s*([\d,]+)", description, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def classify_profile(token_html: str, address_html: str, *, checked_at: str | None = None) -> dict[str, Any]:
    meta = parse_meta(token_html)
    description = meta.get("description", "")
    og_title = meta.get("og:title", "")
    og_image = meta.get("og:image", "")
    token_rep = parse_token_rep(description)
    holders = parse_holders(description)
    token_html_lower = token_html.lower()
    address_html_lower = address_html.lower()

    token_rep_unknown = token_rep.lower() in {"", "unknown"}
    official_domain_present = OFFICIAL_DOMAIN in token_html_lower
    generic_title = og_title.lower().startswith("erc-20 token | address:")
    default_preview = DEFAULT_PREVIEW_PATH in og_image.lower()
    source_verified = (
        "source code verified" in address_html_lower
        and "exact match" in address_html_lower
    )

    profile_published = (
        not token_rep_unknown
        and official_domain_present
        and not generic_title
        and not default_preview
    )
    clearly_unpublished = (
        token_rep_unknown
        and not official_domain_present
        and generic_title
        and default_preview
    )
    if profile_published:
        status = "profile-published"
        next_action = (
            "Keep the official website, logo, team profile, and domain mailbox live; "
            "monitor the public BaseScan profile for regressions."
        )
    elif clearly_unpublished:
        status = "token-profile-not-published"
        next_action = (
            "Use one owner-controlled BaseScan token update from support@gcagochina.com "
            "after the final local preflight passes, then wait for official review."
        )
    else:
        status = "partial-or-ambiguous"
        next_action = (
            "Review the public BaseScan page manually before making any approval claim; "
            "the observed signals do not prove full token-profile publication."
        )

    return {
        "ok": True,
        "packetVersion": "gca_basescan_public_profile_check_v1",
        "checkedAt": checked_at or utc_now(),
        "status": status,
        "profilePublished": profile_published,
        "contractAddress": CONTRACT_ADDRESS,
        "tokenUrl": TOKEN_URL,
        "addressUrl": ADDRESS_URL,
        "tokenRep": token_rep or "not-observed",
        "holders": holders,
        "sourceVerificationObserved": source_verified,
        "signals": {
            "officialDomainPresent": official_domain_present,
            "genericAddressTitle": generic_title,
            "defaultPreviewImage": default_preview,
            "tokenRepUnknown": token_rep_unknown,
            "ogTitle": og_title,
            "ogImage": og_image,
        },
        "nextAction": next_action,
        "boundaries": {
            "readOnlyPublicPages": True,
            "logsInToBaseScan": False,
            "submitsTokenUpdate": False,
            "signsWalletMessage": False,
            "requiresTransaction": False,
            "touchesContract": False,
            "claimsSourceVerificationImpliesSafety": False,
        },
    }


def check_profile(
    *,
    token_url: str = TOKEN_URL,
    address_url: str = ADDRESS_URL,
    token_html_file: Path | None = None,
    address_html_file: Path | None = None,
    timeout: float = 20,
    checked_at: str | None = None,
) -> dict[str, Any]:
    if (token_html_file is None) != (address_html_file is None):
        raise BaseScanProfileCheckError(
            "--token-html-file and --address-html-file must be supplied together"
        )
    if token_html_file is not None and address_html_file is not None:
        token_html = read_html_file(token_html_file)
        address_html = read_html_file(address_html_file)
    else:
        token_html = fetch_html(token_url, timeout)
        address_html = fetch_html(address_url, timeout)

    payload = classify_profile(token_html, address_html, checked_at=checked_at)
    payload["tokenUrl"] = token_url
    payload["addressUrl"] = address_url
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read public BaseScan pages and classify GCA token-profile publication."
    )
    parser.add_argument("--token-url", default=TOKEN_URL)
    parser.add_argument("--address-url", default=ADDRESS_URL)
    parser.add_argument("--token-html-file", type=Path)
    parser.add_argument("--address-html-file", type=Path)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--checked-at", help="Override the UTC timestamp for deterministic fixtures.")
    parser.add_argument("--json", action="store_true", help="Print the complete JSON result.")
    parser.add_argument(
        "--require-published",
        action="store_true",
        help="Exit non-zero unless the public token profile is classified as published.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = check_profile(
            token_url=args.token_url,
            address_url=args.address_url,
            token_html_file=args.token_html_file,
            address_html_file=args.address_html_file,
            timeout=args.timeout,
            checked_at=args.checked_at,
        )
    except BaseScanProfileCheckError as exc:
        payload = {
            "ok": False,
            "packetVersion": "gca_basescan_public_profile_check_v1",
            "checkedAt": utc_now(),
            "status": "check-failed",
            "profilePublished": False,
            "error": str(exc),
            "boundaries": {
                "readOnlyPublicPages": True,
                "logsInToBaseScan": False,
                "submitsTokenUpdate": False,
                "signsWalletMessage": False,
                "requiresTransaction": False,
                "touchesContract": False,
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 2

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"{payload['status']}: Token Rep {payload['tokenRep']}; "
            f"official domain present={payload['signals']['officialDomainPresent']}; "
            f"source verified={payload['sourceVerificationObserved']}"
        )
    if args.require_published and not payload["profilePublished"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
