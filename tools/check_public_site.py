#!/usr/bin/env python3
"""Check live GCA public site endpoints for canonical identity drift."""

from __future__ import annotations

import argparse
import json
import re
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
MEMBER_LEDGER_PAGE_URL = "https://gcagochina.com/member-ledger.html"
MEMBER_LEDGER_URL = "https://gcagochina.com/member-ledger.json"
WALLET_WARNING_PAGE_URL = "https://gcagochina.com/wallet-warning.html"
WALLET_WARNING_URL = "https://gcagochina.com/wallet-warning.json"
EXTERNAL_REVIEW_PAGE_URL = "https://gcagochina.com/external-reviews.html"
EXTERNAL_REVIEW_URL = "https://gcagochina.com/external-reviews.json"
LISTING_READINESS_PAGE_URL = "https://gcagochina.com/listing-readiness.html"
LISTING_READINESS_URL = "https://gcagochina.com/listing-readiness.json"
MARKET_QUALITY_PAGE_URL = "https://gcagochina.com/market-quality.html"
MARKET_QUALITY_URL = "https://gcagochina.com/market-quality.json"
ONCHAIN_PROOFS_PAGE_URL = "https://gcagochina.com/onchain-proofs.html"
ONCHAIN_PROOFS_URL = "https://gcagochina.com/onchain-proofs.json"
SUPPLY_DISCLOSURE_URL = "https://gcagochina.com/supply.json"
BRAND_KIT_PAGE_URL = "https://gcagochina.com/brand-kit.html"
BRAND_KIT_URL = "https://gcagochina.com/brand-kit.json"
DEPLOYMENT_TX = "0xae8ae4d0bd89c03b39946564a5b63bb20cd38879a1aa1fdcb20a6f1c4802e74e"
RESERVE_WALLET = "0x5e8F84748612B913aAcC937492AC25dc5630E246"
RESERVE_TX_1 = "0x4c342e1f4c969d0a73018637b778d5a76bd05f54749ff1fd2d19327fd5c01c67"
RESERVE_TX_2 = "0xfffb674448abdbd3af45bb0a30c48e5fbb0e675542b971f031381254b5dc5317"
SWAP_TEST_BUY_TX = "0xf79e52ea56a299a30c2d297be99c970295864ed262c01fdcb7e3f60ca669b040"
SWAP_TEST_SELL_TX = "0x0ff618062abc6e28933699d4e3bd723026f8505e4a0155db3068073b6fdc86e7"
FORBIDDEN_PUBLIC_CLAIM_PATTERNS = [
    r"\bguaranteed returns?\b",
    r"\bprofit sharing\b",
    r"\brisk[- ]?free\b",
    "稳赚",
    "保本",
    "拉盘",
    "炒币",
    "刷量",
    "对倒",
]


class SiteCheckError(AssertionError):
    """Raised when a public site check fails."""


EndpointCheck = tuple[str, Callable[[str], None]]


def assert_contains(text: str, expected: str, label: str) -> None:
    if expected not in text:
        raise SiteCheckError(f"{label}: missing {expected!r}")


def assert_not_contains(text: str, forbidden: str, label: str) -> None:
    if forbidden in text:
        raise SiteCheckError(f"{label}: found forbidden {forbidden!r}")


def assert_no_forbidden_public_claims(text: str, label: str) -> None:
    for pattern in FORBIDDEN_PUBLIC_CLAIM_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise SiteCheckError(f"{label}: forbidden public claim pattern {pattern!r}")


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
    assert_contains(text, "Wallet Warning", label)
    assert_contains(text, "External Reviews", label)
    assert_contains(text, "Listing Readiness", label)
    assert_contains(text, "On-chain Proofs", label)
    assert_contains(text, "Brand Kit", label)
    assert_contains(text, "Member Ledger", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_current_pool_text(text, label)


def validate_verify(text: str) -> None:
    label = "/verify.html"
    assert_contains(text, "Verify GCA", label)
    assert_contains(text, "Submitted, awaiting review", label)
    assert_contains(text, "well-known token identity", label)
    assert_contains(text, "Wallet Warning", label)
    assert_contains(text, "External Reviews", label)
    assert_contains(text, "On-chain Proofs", label)
    assert_contains(text, "Brand Kit", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_current_pool_text(text, label)


def validate_markets(text: str) -> None:
    label = "/markets.html"
    assert_contains(text, "Official GCA Markets", label)
    assert_contains(text, "Market Quality", label)
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
    assert_contains(text, "member-ledger.html", label)
    assert_contains(text, "member-ledger.json", label)
    assert_contains(text, "180 days", label)
    assert_contains(text, "30 days", label)
    assert_contains(text, "5-10 business days", label)
    assert_contains(text, "Direct submission is not connected", label)
    assert_contains(text, "No cash, token rebate, income, reimbursement, trading permission, or risk-control bypass", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)


def validate_supply_page(text: str) -> None:
    label = "/supply.html"
    assert_contains(text, "GCA Supply and Reserve", label)
    assert_contains(text, "Supply JSON", label)
    assert_contains(text, "1,000,000,000 GCA", label)
    assert_contains(text, "400,000,000 GCA / 40%", label)
    assert_contains(text, "600,000,000 GCA / 60%", label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_contains(text, RESERVE_TX_1, label)
    assert_contains(text, RESERVE_TX_2, label)
    assert_contains(text, "not be described as locked, vested, or multisig-controlled", label)
    assert_contains(text, "Do not claim the reserve provides price support", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)


def validate_supply_json(text: str) -> None:
    label = "/supply.json"
    payload = load_json(text, label)
    allocation = payload.get("allocationTarget", {})
    transfers = payload.get("reserveTransferEvidence", [])
    reporting = payload.get("dataPlatformReporting", {})
    links = payload.get("officialLinks", {})

    if payload.get("schema") != SUPPLY_DISCLOSURE_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != "https://gcagochina.com/supply.html":
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-supply-disclosure-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("totalSupply") != "1000000000":
        raise SiteCheckError(f"{label}: wrong totalSupply")
    if payload.get("fixedSupply") is not True:
        raise SiteCheckError(f"{label}: fixedSupply must be true")
    if payload.get("postDeploymentMintFunction") is not False:
        raise SiteCheckError(f"{label}: postDeploymentMintFunction must be false")
    if allocation.get("publicAllocationTarget") != "400000000":
        raise SiteCheckError(f"{label}: wrong public allocation target")
    if allocation.get("ownerHeldReserve") != "600000000":
        raise SiteCheckError(f"{label}: wrong owner reserve")
    if allocation.get("ownerReserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong reserve wallet")
    if allocation.get("ownerReserveCustodyType") != "normal-owner-controlled-wallet":
        raise SiteCheckError(f"{label}: wrong reserve custody type")
    transfer_hashes = [entry.get("transactionHash") for entry in transfers if isinstance(entry, dict)]
    if transfer_hashes != [RESERVE_TX_1, RESERVE_TX_2]:
        raise SiteCheckError(f"{label}: wrong reserve transfer evidence")
    if reporting.get("preferredTerm") != "target public allocation":
        raise SiteCheckError(f"{label}: wrong preferred term")
    if links.get("supplyDisclosure") != SUPPLY_DISCLOSURE_URL:
        raise SiteCheckError(f"{label}: wrong supplyDisclosure link")
    if "The current reserve is not locked." not in reporting.get("ifAskedForLockedReserve", ""):
        raise SiteCheckError(f"{label}: missing reserve-lock caveat")
    if "GCA total supply is fixed at 1,000,000,000 GCA." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing fixed-supply safe claim")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_brand_kit_json(text: str) -> None:
    label = "/brand-kit.json"
    payload = load_json(text, label)
    logo_assets = payload.get("logoAssets", {})
    visual = payload.get("visualIdentity", {})
    links = payload.get("officialLinks", {})
    metadata = payload.get("metadataUse", {})
    market = payload.get("officialMarket", {})

    if payload.get("schema") != BRAND_KIT_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != BRAND_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-brand-kit-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong market pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if market.get("geckoTerminal") != OFFICIAL_GECKOTERMINAL_URL:
        raise SiteCheckError(f"{label}: wrong geckoTerminal")
    if market.get("dexScreener") != OFFICIAL_DEXSCREENER_URL:
        raise SiteCheckError(f"{label}: wrong dexScreener")
    if logo_assets.get("svg", {}).get("url") != "https://gcagochina.com/assets/gca-logo.svg":
        raise SiteCheckError(f"{label}: wrong svg logo")
    if logo_assets.get("svg", {}).get("width") != 32:
        raise SiteCheckError(f"{label}: wrong svg width")
    if logo_assets.get("png", {}).get("url") != "https://gcagochina.com/assets/gca-logo.png":
        raise SiteCheckError(f"{label}: wrong png logo")
    if logo_assets.get("png", {}).get("width") != 512:
        raise SiteCheckError(f"{label}: wrong png width")
    if visual.get("primaryInk") != "#111111":
        raise SiteCheckError(f"{label}: wrong primary ink")
    if links.get("brandKit") != BRAND_KIT_URL:
        raise SiteCheckError(f"{label}: wrong brandKit link")
    if links.get("tokenList") != "https://gcagochina.com/tokenlist.json":
        raise SiteCheckError(f"{label}: wrong tokenList link")
    if "token logo display" not in metadata.get("safeUse", []):
        raise SiteCheckError(f"{label}: missing safe logo use")
    if "third-party audit completion" not in metadata.get("doNotUseToImply", []):
        raise SiteCheckError(f"{label}: missing audit boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_brand_kit_page(text: str) -> None:
    label = "/brand-kit.html"
    assert_contains(text, "GCA Brand Kit", label)
    assert_contains(text, "Brand Kit JSON", label)
    assert_contains(text, "Logo SVG", label)
    assert_contains(text, "Logo PNG", label)
    assert_contains(text, "32 x 32", label)
    assert_contains(text, "512 x 512", label)
    assert_contains(text, "#111111", label)
    assert_contains(text, "#D71920", label)
    assert_contains(text, "#0052FF", label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "Do not use this logo to imply third-party audit completion", label)
    assert_contains(text, "Do not submit the frozen X account", label)
    assert_current_pool_text(text, label)


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
    if payload.get("memberLedgerPageUrl") != MEMBER_LEDGER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberLedgerPageUrl")
    if payload.get("memberLedgerSchemaUrl") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedgerSchemaUrl")
    if payload.get("walletWarningEvidencePageUrl") != WALLET_WARNING_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidencePageUrl")
    if payload.get("walletWarningEvidenceUrl") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidenceUrl")
    if payload.get("externalReviewStatusPageUrl") != EXTERNAL_REVIEW_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatusPageUrl")
    if payload.get("externalReviewStatusUrl") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatusUrl")
    if payload.get("listingReadinessPageUrl") != LISTING_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong listingReadinessPageUrl")
    if payload.get("listingReadinessUrl") != LISTING_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong listingReadinessUrl")
    if payload.get("brandKitPageUrl") != BRAND_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong brandKitPageUrl")
    if payload.get("brandKitUrl") != BRAND_KIT_URL:
        raise SiteCheckError(f"{label}: wrong brandKitUrl")
    if payload.get("marketQualityPageUrl") != MARKET_QUALITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong marketQualityPageUrl")
    if payload.get("marketQualityUrl") != MARKET_QUALITY_URL:
        raise SiteCheckError(f"{label}: wrong marketQualityUrl")
    if payload.get("supplyDisclosureUrl") != SUPPLY_DISCLOSURE_URL:
        raise SiteCheckError(f"{label}: wrong supplyDisclosureUrl")
    if payload.get("onchainProofsPageUrl") != ONCHAIN_PROOFS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsPageUrl")
    if payload.get("onchainProofsUrl") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsUrl")
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
    if member_program.get("ledgerSchema", {}).get("status") != "public-member-ledger-schema-published":
        raise SiteCheckError(f"{label}: unexpected member ledger schema status")
    if payload.get("listingReadiness", {}).get("status") != "not-ready":
        raise SiteCheckError(f"{label}: unexpected listing readiness status")
    if payload.get("marketQuality", {}).get("status") != "early-stage-market-quality-plan":
        raise SiteCheckError(f"{label}: unexpected market quality status")
    if payload.get("externalReviewStatus", {}).get("status") != "external-review-status-active":
        raise SiteCheckError(f"{label}: unexpected external review status")
    if payload.get("walletWarningEvidence", {}).get("status") != "warning-report-submitted-removal-not-confirmed":
        raise SiteCheckError(f"{label}: unexpected wallet warning status")
    if payload.get("onchainProofs", {}).get("status") != "public-onchain-proofs-published":
        raise SiteCheckError(f"{label}: unexpected onchain proofs status")
    if payload.get("supplyDisclosure", {}).get("status") != "public-supply-disclosure-published":
        raise SiteCheckError(f"{label}: unexpected supply disclosure status")
    if payload.get("brandKit", {}).get("status") != "public-brand-kit-published":
        raise SiteCheckError(f"{label}: unexpected brand kit status")
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
    if extensions.get("memberLedgerPage") != MEMBER_LEDGER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberLedgerPage")
    if extensions.get("memberLedgerSchema") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedgerSchema")
    if extensions.get("walletWarningEvidencePage") != WALLET_WARNING_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidencePage")
    if extensions.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidence")
    if extensions.get("externalReviewStatusPage") != EXTERNAL_REVIEW_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatusPage")
    if extensions.get("externalReviewStatus") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatus")
    if extensions.get("listingReadinessPage") != LISTING_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong listingReadinessPage")
    if extensions.get("listingReadiness") != LISTING_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong listingReadiness")
    if extensions.get("brandKitPage") != BRAND_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong brandKitPage")
    if extensions.get("brandKit") != BRAND_KIT_URL:
        raise SiteCheckError(f"{label}: wrong brandKit")
    if extensions.get("marketQualityPage") != MARKET_QUALITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong marketQualityPage")
    if extensions.get("marketQuality") != MARKET_QUALITY_URL:
        raise SiteCheckError(f"{label}: wrong marketQuality")
    if extensions.get("supplyDisclosure") != SUPPLY_DISCLOSURE_URL:
        raise SiteCheckError(f"{label}: wrong supplyDisclosure")
    if extensions.get("onchainProofsPage") != ONCHAIN_PROOFS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsPage")
    if extensions.get("onchainProofs") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofs")
    if extensions.get("supplyDisclosureStatus") != "public-supply-disclosure-published":
        raise SiteCheckError(f"{label}: wrong supplyDisclosureStatus")
    if extensions.get("brandKitStatus") != "public-brand-kit-published":
        raise SiteCheckError(f"{label}: wrong brandKitStatus")
    if extensions.get("memberLedgerStatus") != "public-member-ledger-schema-published":
        raise SiteCheckError(f"{label}: wrong memberLedgerStatus")
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
    if urls.get("memberLedgerPage") != MEMBER_LEDGER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberLedgerPage")
    if urls.get("memberLedgerSchema") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedgerSchema")
    if urls.get("walletWarningEvidencePage") != WALLET_WARNING_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidencePage")
    if urls.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidence")
    if urls.get("externalReviewStatusPage") != EXTERNAL_REVIEW_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatusPage")
    if urls.get("externalReviewStatus") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatus")
    if urls.get("listingReadinessPage") != LISTING_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong listingReadinessPage")
    if urls.get("listingReadiness") != LISTING_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong listingReadiness")
    if urls.get("brandKitPage") != BRAND_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong brandKitPage")
    if urls.get("brandKit") != BRAND_KIT_URL:
        raise SiteCheckError(f"{label}: wrong brandKit")
    if urls.get("marketQualityPage") != MARKET_QUALITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong marketQualityPage")
    if urls.get("marketQuality") != MARKET_QUALITY_URL:
        raise SiteCheckError(f"{label}: wrong marketQuality")
    if urls.get("supplyDisclosure") != SUPPLY_DISCLOSURE_URL:
        raise SiteCheckError(f"{label}: wrong supplyDisclosure")
    if urls.get("onchainProofsPage") != ONCHAIN_PROOFS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsPage")
    if urls.get("onchainProofs") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofs")
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
    public_pages = payload.get("publicPages", {})
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
    if public_pages.get("memberLedger") != MEMBER_LEDGER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberLedger page")
    if public_pages.get("memberLedgerSchema") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedger schema")
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
    if verification.get("publicLedgerSchemaUrl") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong public ledger schema URL")
    if support.get("contactEmail") != "GCAgochina@outlook.com":
        raise SiteCheckError(f"{label}: wrong support contact")
    if "ledger_recorded" not in support.get("reviewStatuses", []):
        raise SiteCheckError(f"{label}: missing ledger_recorded status")
    if not any("public self-service claiming is not connected" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing not-connected safe claim")
    if not any("credits or membership are cash" in claim for claim in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing cash/token do-not-claim boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_member_ledger_json(text: str) -> None:
    label = "/member-ledger.json"
    payload = load_json(text, label)
    token = payload.get("token", {})
    urls = payload.get("publicUrls", {})
    paths = payload.get("preparedPaths", {})
    thresholds = payload.get("thresholds", {})
    schemas = payload.get("recordSchemas", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != MEMBER_LEDGER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-member-ledger-schema-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if token.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if urls.get("memberProgramRules") != MEMBER_PROGRAM_URL:
        raise SiteCheckError(f"{label}: wrong memberProgramRules")
    if urls.get("memberLedgerPage") != MEMBER_LEDGER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberLedgerPage")
    if urls.get("memberLedgerSchema") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedgerSchema")
    if paths.get("memberAccessPage") != "/gca/member-access":
        raise SiteCheckError(f"{label}: wrong member access path")
    if paths.get("walletVerifications") != "/gca/wallet-verifications":
        raise SiteCheckError(f"{label}: wrong wallet verification path")
    if paths.get("creditLedger") != "/gca/credit-ledger":
        raise SiteCheckError(f"{label}: wrong credit ledger path")
    if paths.get("memberLedger") != "/gca/member-ledger":
        raise SiteCheckError(f"{label}: wrong member ledger path")
    if thresholds.get("holderBonusMinimum") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder threshold")
    if thresholds.get("holderBonusCreditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong credit amount")
    if thresholds.get("creditExpiryDaysAfterLedgerActivation") != 180:
        raise SiteCheckError(f"{label}: wrong credit expiry")
    if thresholds.get("gcaMemberMinimum") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member threshold")
    if thresholds.get("memberRefreshDays") != 30:
        raise SiteCheckError(f"{label}: wrong member refresh")
    if "walletVerificationRecord" not in schemas:
        raise SiteCheckError(f"{label}: missing wallet verification schema")
    if "creditLedgerRecord" not in schemas:
        raise SiteCheckError(f"{label}: missing credit ledger schema")
    if "memberLedgerRecord" not in schemas:
        raise SiteCheckError(f"{label}: missing member ledger schema")
    if "supportReviewRecord" not in schemas:
        raise SiteCheckError(f"{label}: missing support review schema")
    if "ledger_recorded" not in schemas.get("supportReviewRecord", {}).get("allowedStatuses", []):
        raise SiteCheckError(f"{label}: missing ledger_recorded status")
    if not any("Public self-service claiming is not connected yet" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing not-connected safe claim")
    if not any("self-service claimable before controlled HTTPS account UI is live" in claim for claim in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing self-service boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_member_ledger_page(text: str) -> None:
    label = "/member-ledger.html"
    assert_contains(text, "GCA Member Ledger Schema", label)
    assert_contains(text, "Member Ledger JSON", label)
    assert_contains(text, "Wallet Verification Record", label)
    assert_contains(text, "100 Credit Ledger", label)
    assert_contains(text, "GCA Member Ledger", label)
    assert_contains(text, "Support Review Record", label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "/gca/member-access", label)
    assert_contains(text, "/gca/wallet-verifications", label)
    assert_contains(text, "/gca/credit-ledger", label)
    assert_contains(text, "/gca/member-ledger", label)
    assert_contains(text, "10,000 GCA", label)
    assert_contains(text, "1,000,000 GCA", label)
    assert_contains(text, "180 days", label)
    assert_contains(text, "30 days", label)
    assert_contains(text, "Do not say 100 Web3 Radar utility credits are self-service claimable", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)


def validate_listing_readiness_json(text: str) -> None:
    label = "/listing-readiness.json"
    payload = load_json(text, label)
    market = payload.get("market", {})
    platforms = payload.get("platformDecisions", {})
    checks = payload.get("readinessChecks", [])

    if payload.get("schema") != LISTING_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != LISTING_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "not-ready":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if market.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialPair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if payload.get("canonicalLinks", {}).get("marketQualityPage") != MARKET_QUALITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong marketQualityPage")
    if payload.get("canonicalLinks", {}).get("marketQuality") != MARKET_QUALITY_URL:
        raise SiteCheckError(f"{label}: wrong marketQuality")
    if payload.get("canonicalLinks", {}).get("walletWarningEvidencePage") != WALLET_WARNING_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidencePage")
    if payload.get("canonicalLinks", {}).get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidence")
    if payload.get("canonicalLinks", {}).get("externalReviewStatusPage") != EXTERNAL_REVIEW_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatusPage")
    if payload.get("canonicalLinks", {}).get("externalReviewStatus") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatus")
    if payload.get("canonicalLinks", {}).get("onchainProofsPage") != ONCHAIN_PROOFS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsPage")
    if payload.get("canonicalLinks", {}).get("onchainProofs") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofs")
    if platforms.get("geckoTerminal", {}).get("status") != "approved":
        raise SiteCheckError(f"{label}: wrong GeckoTerminal status")
    if platforms.get("coinGecko", {}).get("status") != "defer":
        raise SiteCheckError(f"{label}: wrong CoinGecko status")
    if platforms.get("coinMarketCap", {}).get("status") != "defer":
        raise SiteCheckError(f"{label}: wrong CoinMarketCap status")
    if not any(check.get("id") == "no-artificial-activity-policy" for check in checks):
        raise SiteCheckError(f"{label}: missing artificial activity policy")
    if "CoinGecko tracked listing request" not in payload.get("notReadyFor", []):
        raise SiteCheckError(f"{label}: missing CoinGecko defer boundary")
    if "CoinMarketCap tracked listing request" not in payload.get("notReadyFor", []):
        raise SiteCheckError(f"{label}: missing CoinMarketCap defer boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_market_quality_json(text: str) -> None:
    label = "/market-quality.json"
    payload = load_json(text, label)
    market = payload.get("officialMarket", {})
    current = payload.get("currentState", {})

    if payload.get("schema") != MARKET_QUALITY_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != MARKET_QUALITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "early-stage-market-quality-plan":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if current.get("liquidityDepth") != "starter-depth-only":
        raise SiteCheckError(f"{label}: wrong liquidity depth")
    if current.get("coinGeckoTrackedListing") != "defer":
        raise SiteCheckError(f"{label}: wrong CoinGecko status")
    if current.get("coinMarketCapTrackedListing") != "defer":
        raise SiteCheckError(f"{label}: wrong CoinMarketCap status")
    if "artificial activity" not in payload.get("doNotUse", []):
        raise SiteCheckError(f"{label}: missing artificial activity boundary")
    if "wash trading" not in payload.get("doNotUse", []):
        raise SiteCheckError(f"{label}: missing wash trading boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_market_quality_page(text: str) -> None:
    label = "/market-quality.html"
    assert_contains(text, "GCA Market Quality Plan", label)
    assert_contains(text, "transparent liquidity", label)
    assert_contains(text, "legitimate public participation", label)
    assert_contains(text, "Starter-depth only", label)
    assert_contains(text, "Market Quality JSON", label)
    assert_contains(text, "Do not use artificial activity", label)
    assert_contains(text, "Self-trading or wash trading", label)
    assert_contains(text, "Misleading volume", label)
    assert_contains(text, "CoinGecko or CoinMarketCap submission", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)


def validate_onchain_proofs_json(text: str) -> None:
    label = "/onchain-proofs.json"
    payload = load_json(text, label)
    deployment = payload.get("deploymentProof", {})
    source = payload.get("sourceVerificationProof", {})
    supply = payload.get("supplyProof", {})
    reserve = payload.get("ownerReserveProof", {})
    market = payload.get("officialMarketProof", {})
    functional = payload.get("historicalFunctionalSwapProof", {})

    if payload.get("schema") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != ONCHAIN_PROOFS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-onchain-proofs-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if deployment.get("transactionHash") != DEPLOYMENT_TX:
        raise SiteCheckError(f"{label}: wrong deployment transaction")
    if source.get("status") != "verified":
        raise SiteCheckError(f"{label}: source verification must be verified")
    if supply.get("fixedSupply") is not True:
        raise SiteCheckError(f"{label}: fixedSupply must be true")
    if supply.get("postDeploymentMintFunction") is not False:
        raise SiteCheckError(f"{label}: postDeploymentMintFunction must be false")
    if reserve.get("ownerReserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong owner reserve wallet")
    reserve_text = json.dumps(reserve)
    if RESERVE_TX_1 not in reserve_text or RESERVE_TX_2 not in reserve_text:
        raise SiteCheckError(f"{label}: missing reserve transfer transaction")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong official market pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong official market pool")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quote asset")
    if payload.get("officialLinks", {}).get("supplyDisclosure") != SUPPLY_DISCLOSURE_URL:
        raise SiteCheckError(f"{label}: wrong supplyDisclosure")
    if SWAP_TEST_BUY_TX not in functional.get("buyTestTransactions", []):
        raise SiteCheckError(f"{label}: missing buy test transaction")
    if SWAP_TEST_SELL_TX not in functional.get("sellTestTransactions", []):
        raise SiteCheckError(f"{label}: missing sell test transaction")
    if "No third-party audit has been completed." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    assert_current_pool_text(json.dumps(payload), label)


def validate_onchain_proofs_page(text: str) -> None:
    label = "/onchain-proofs.html"
    assert_contains(text, "GCA On-chain Proofs", label)
    assert_contains(text, "On-chain Proofs JSON", label)
    assert_contains(text, "Deployment Proof", label)
    assert_contains(text, "Source Verification", label)
    assert_contains(text, "Fixed Supply And Reserve Proof", label)
    assert_contains(text, "Official Market Proof", label)
    assert_contains(text, "Historical Functional Buy/Sell Evidence", label)
    assert_contains(text, "Public Claim Boundaries", label)
    assert_contains(text, DEPLOYMENT_TX, label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_contains(text, RESERVE_TX_1, label)
    assert_contains(text, RESERVE_TX_2, label)
    assert_contains(text, SWAP_TEST_BUY_TX, label)
    assert_contains(text, SWAP_TEST_SELL_TX, label)
    assert_contains(text, "No third-party audit has been completed", label)
    assert_contains(text, "not a lock, vesting contract, or multisig", label)
    assert_current_pool_text(text, label)


def validate_external_reviews_json(text: str) -> None:
    label = "/external-reviews.json"
    payload = load_json(text, label)
    market = payload.get("market", {})
    reviews = payload.get("reviews", {})
    links = payload.get("officialLinks", {})

    if payload.get("schema") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != EXTERNAL_REVIEW_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "external-review-status-active":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if links.get("listingReadinessPage") != LISTING_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong listingReadinessPage")
    if links.get("walletWarningEvidencePage") != WALLET_WARNING_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidencePage")
    if links.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidence")
    if links.get("marketQualityPage") != MARKET_QUALITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong marketQualityPage")
    if links.get("onchainProofsPage") != ONCHAIN_PROOFS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsPage")
    if links.get("onchainProofs") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofs")
    if market.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialPair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if reviews.get("baseScanSource", {}).get("status") != "verified":
        raise SiteCheckError(f"{label}: wrong BaseScan source status")
    if reviews.get("baseScanTokenProfile", {}).get("status") != "submitted-awaiting-review":
        raise SiteCheckError(f"{label}: wrong BaseScan profile status")
    if reviews.get("blockaidMetaMask", {}).get("status") != "submitted-warning-removal-not-confirmed":
        raise SiteCheckError(f"{label}: wrong Blockaid status")
    if reviews.get("geckoTerminal", {}).get("status") != "approved":
        raise SiteCheckError(f"{label}: wrong GeckoTerminal status")
    if reviews.get("coinGecko", {}).get("status") != "deferred":
        raise SiteCheckError(f"{label}: wrong CoinGecko status")
    if reviews.get("coinMarketCap", {}).get("status") != "deferred":
        raise SiteCheckError(f"{label}: wrong CoinMarketCap status")
    if reviews.get("thirdPartyAudit", {}).get("status") != "not-completed-deferred":
        raise SiteCheckError(f"{label}: wrong audit status")
    if "No third-party audit has been completed." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_external_reviews_page(text: str) -> None:
    label = "/external-reviews.html"
    assert_contains(text, "GCA External Review Status", label)
    assert_contains(text, "Wallet Warning Evidence", label)
    assert_contains(text, "External Reviews JSON", label)
    assert_contains(text, "Submitted, awaiting review", label)
    assert_contains(text, "Submitted 2026-05-10; removal not confirmed", label)
    assert_contains(text, "Approved 2026-05-11", label)
    assert_contains(text, "CoinGecko tracked listing submission", label)
    assert_contains(text, "CoinMarketCap tracked listing submission", label)
    assert_contains(text, "No third-party audit has been completed", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)


def validate_wallet_warning_json(text: str) -> None:
    label = "/wallet-warning.json"
    payload = load_json(text, label)
    market = payload.get("currentOfficialMarket", {})
    facts = payload.get("contractFacts", {})
    report = payload.get("blockaidReport", {})
    evidence = payload.get("historicalFunctionalSwapEvidence", {})
    links = payload.get("officialLinks", {})

    if payload.get("schema") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != WALLET_WARNING_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "warning-report-submitted-removal-not-confirmed":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if links.get("onchainProofsPage") != ONCHAIN_PROOFS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsPage")
    if links.get("onchainProofs") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofs")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if report.get("status") != "submitted-warning-removal-not-confirmed":
        raise SiteCheckError(f"{label}: wrong Blockaid report status")
    if facts.get("sourceVerifiedOnBaseScan") is not True:
        raise SiteCheckError(f"{label}: source verification must be true")
    if facts.get("postDeploymentMintFunction") is not False:
        raise SiteCheckError(f"{label}: mint function must be false")
    if facts.get("ownerOrAdminRole") is not False:
        raise SiteCheckError(f"{label}: owner/admin role must be false")
    if facts.get("thirdPartyAuditCompleted") is not False:
        raise SiteCheckError(f"{label}: third-party audit status must remain false")
    if evidence.get("status") != "observed-historical-functional-evidence-only":
        raise SiteCheckError(f"{label}: wrong functional evidence status")
    if "0xf79e52ea56a299a30c2d297be99c970295864ed262c01fdcb7e3f60ca669b040" not in evidence.get("buyTestTransactions", []):
        raise SiteCheckError(f"{label}: missing buy test transaction")
    if "0x0ff618062abc6e28933699d4e3bd723026f8505e4a0155db3068073b6fdc86e7" not in evidence.get("sellTestTransactions", []):
        raise SiteCheckError(f"{label}: missing sell test transaction")
    if "No third-party audit has been completed." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_wallet_warning_page(text: str) -> None:
    label = "/wallet-warning.html"
    assert_contains(text, "GCA Wallet Warning Evidence", label)
    assert_contains(text, "Wallet Warning JSON", label)
    assert_contains(text, "Submitted 2026-05-10", label)
    assert_contains(text, "Not confirmed", label)
    assert_contains(text, "Verified on BaseScan", label)
    assert_contains(text, "Contract Facts For Review", label)
    assert_contains(text, "Historical Functional Swap Evidence", label)
    assert_contains(text, "Blockaid false-positive report", label)
    assert_contains(text, "No third-party audit has been completed", label)
    assert_contains(text, "0xf79e52ea56a299a30c2d297be99c970295864ed262c01fdcb7e3f60ca669b040", label)
    assert_contains(text, "0x0ff618062abc6e28933699d4e3bd723026f8505e4a0155db3068073b6fdc86e7", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)


def validate_listing_readiness_page(text: str) -> None:
    label = "/listing-readiness.html"
    assert_contains(text, "GCA Listing Readiness", label)
    assert_contains(text, "Status: Not Ready", label)
    assert_contains(text, "DEX metadata and wallet identity review", label)
    assert_contains(text, "CoinGecko tracked listing request", label)
    assert_contains(text, "CoinMarketCap tracked listing request", label)
    assert_contains(text, "Pending external review", label)
    assert_contains(text, "Approved 2026-05-11", label)
    assert_contains(text, "No artificial activity policy", label)
    assert_contains(text, "listing-readiness.json", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)


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
        "https://gcagochina.com/wallet-warning.html",
        "https://gcagochina.com/wallet-warning.json",
        "https://gcagochina.com/market-quality.html",
        "https://gcagochina.com/market-quality.json",
        "https://gcagochina.com/brand-kit.html",
        "https://gcagochina.com/brand-kit.json",
        "https://gcagochina.com/onchain-proofs.html",
        "https://gcagochina.com/onchain-proofs.json",
        "https://gcagochina.com/external-reviews.html",
        "https://gcagochina.com/external-reviews.json",
        "https://gcagochina.com/member-program.json",
        "https://gcagochina.com/member-ledger.html",
        "https://gcagochina.com/member-ledger.json",
        "https://gcagochina.com/supply.json",
        "https://gcagochina.com/listing-readiness.html",
        "https://gcagochina.com/listing-readiness.json",
        "https://gcagochina.com/project.json",
        "https://gcagochina.com/tokenlist.json",
        "https://gcagochina.com/.well-known/gca-token.json",
        "https://gcagochina.com/.well-known/security.txt",
    ):
        assert_contains(text, expected, label)


def validate_robots(text: str) -> None:
    label = "/robots.txt"
    assert_contains(text, "Allow: /wallet-warning.html", label)
    assert_contains(text, "Allow: /brand-kit.html", label)
    assert_contains(text, "Allow: /brand-kit.json", label)
    assert_contains(text, "Allow: /wallet-warning.json", label)
    assert_contains(text, "Allow: /listing-readiness.html", label)
    assert_contains(text, "Allow: /listing-readiness.json", label)
    assert_contains(text, "Allow: /external-reviews.html", label)
    assert_contains(text, "Allow: /external-reviews.json", label)
    assert_contains(text, "Allow: /market-quality.html", label)
    assert_contains(text, "Allow: /market-quality.json", label)
    assert_contains(text, "Allow: /supply.json", label)
    assert_contains(text, "Allow: /onchain-proofs.html", label)
    assert_contains(text, "Allow: /onchain-proofs.json", label)
    assert_contains(text, "Allow: /member-ledger.html", label)
    assert_contains(text, "Allow: /member-ledger.json", label)
    assert_contains(text, "Allow: /member-program.json", label)
    assert_contains(text, "Allow: /.well-known/gca-token.json", label)
    assert_contains(text, "Allow: /.well-known/security.txt", label)
    assert_contains(text, "Sitemap: https://gcagochina.com/sitemap.xml", label)


CHECKS: list[EndpointCheck] = [
    ("/", validate_root),
    ("/verify.html", validate_verify),
    ("/markets.html", validate_markets),
    ("/wallet-warning.html", validate_wallet_warning_page),
    ("/wallet-warning.json", validate_wallet_warning_json),
    ("/external-reviews.html", validate_external_reviews_page),
    ("/external-reviews.json", validate_external_reviews_json),
    ("/market-quality.html", validate_market_quality_page),
    ("/market-quality.json", validate_market_quality_json),
    ("/brand-kit.html", validate_brand_kit_page),
    ("/brand-kit.json", validate_brand_kit_json),
    ("/onchain-proofs.html", validate_onchain_proofs_page),
    ("/onchain-proofs.json", validate_onchain_proofs_json),
    ("/supply.html", validate_supply_page),
    ("/supply.json", validate_supply_json),
    ("/members.html", validate_members),
    ("/member-program.json", validate_member_program_json),
    ("/member-ledger.html", validate_member_ledger_page),
    ("/member-ledger.json", validate_member_ledger_json),
    ("/listing-readiness.html", validate_listing_readiness_page),
    ("/listing-readiness.json", validate_listing_readiness_json),
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
            assert_no_forbidden_public_claims(body, path)
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
