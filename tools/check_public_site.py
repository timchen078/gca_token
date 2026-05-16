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
X_URL = "https://x.com/GCAAIGoChina"
FIRST_X_POST_URL = "https://x.com/GCAAIGoChina/status/2054660559124255151"
OFFICIAL_POOL_ADDRESS = "0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0"
BASE_USDT_ADDRESS = "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"
OLD_WETH_POOL_ADDRESS = "0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff"
OFFICIAL_GECKOTERMINAL_URL = f"https://www.geckoterminal.com/base/pools/{OFFICIAL_POOL_ADDRESS}"
OFFICIAL_DEXSCREENER_URL = f"https://dexscreener.com/base/{OFFICIAL_POOL_ADDRESS}"
BUY_PAGE_URL = "https://gcagochina.com/buy.html"
STATUS_PAGE_URL = "https://gcagochina.com/status.html"
LISTING_KIT_PAGE_URL = "https://gcagochina.com/listing-kit.html"
SECURITY_PAGE_URL = "https://gcagochina.com/security.html"
RISK_PAGE_URL = "https://gcagochina.com/risk.html"
FAQ_PAGE_URL = "https://gcagochina.com/faq.html"
WHITEPAPER_PAGE_URL = "https://gcagochina.com/whitepaper.html"
MEMBER_PROGRAM_URL = "https://gcagochina.com/member-program.json"
MEMBER_LEDGER_PAGE_URL = "https://gcagochina.com/member-ledger.html"
MEMBER_LEDGER_URL = "https://gcagochina.com/member-ledger.json"
MEMBER_BENEFIT_PAGE_URL = "https://gcagochina.com/member-benefit.html"
MEMBER_BENEFIT_URL = "https://gcagochina.com/member-benefit.json"
MEMBER_BENEFIT_TRANSFER_PAGE_URL = "https://gcagochina.com/member-benefit-transfer.html"
MEMBER_BENEFIT_TRANSFER_URL = "https://gcagochina.com/member-benefit-transfer.json"
OPERATOR_PAGE_URL = "https://gcagochina.com/operator.html"
SUPPORT_PAGE_URL = "https://gcagochina.com/support.html"
SUPPORT_URL = "https://gcagochina.com/support.json"
ROADMAP_PAGE_URL = "https://gcagochina.com/roadmap.html"
ROADMAP_URL = "https://gcagochina.com/roadmap.json"
COMMUNITY_PAGE_URL = "https://gcagochina.com/community.html"
COMMUNITY_URL = "https://gcagochina.com/community.json"
NARRATIVE_PAGE_URL = "https://gcagochina.com/narrative.html"
NARRATIVE_URL = "https://gcagochina.com/narrative.json"
RADAR_PAGE_URL = "https://gcagochina.com/radar.html"
RADAR_URL = "https://gcagochina.com/radar.json"
UTILITY_PAGE_URL = "https://gcagochina.com/utility.html"
UTILITY_URL = "https://gcagochina.com/utility.json"
PRODUCT_PAGE_URL = "https://gcagochina.com/product.html"
PRODUCT_URL = "https://gcagochina.com/product.json"
ACCESS_PAGE_URL = "https://gcagochina.com/access.html"
ACCESS_URL = "https://gcagochina.com/access.json"
OPERATIONS_PAGE_URL = "https://gcagochina.com/operations.html"
OPERATIONS_URL = "https://gcagochina.com/operations.json"
ACCESS_API_PAGE_URL = "https://gcagochina.com/access-api.html"
ACCESS_API_URL = "https://gcagochina.com/access-api.json"
REVIEW_QUEUE_PAGE_URL = "https://gcagochina.com/review-queue.html"
REVIEW_QUEUE_URL = "https://gcagochina.com/review-queue.json"
CREDITS_PAGE_URL = "https://gcagochina.com/credits.html"
CREDITS_URL = "https://gcagochina.com/credits.json"
RELEASE_GATES_PAGE_URL = "https://gcagochina.com/release-gates.html"
RELEASE_GATES_URL = "https://gcagochina.com/release-gates.json"
PRIVACY_NOTICE_PAGE_URL = "https://gcagochina.com/privacy.html"
PRIVACY_NOTICE_URL = "https://gcagochina.com/privacy.json"
PARTICIPATION_TERMS_PAGE_URL = "https://gcagochina.com/terms.html"
PARTICIPATION_TERMS_URL = "https://gcagochina.com/terms.json"
WALLET_WARNING_PAGE_URL = "https://gcagochina.com/wallet-warning.html"
WALLET_WARNING_URL = "https://gcagochina.com/wallet-warning.json"
WALLET_SECURITY_PROFILE_URL = "https://gcagochina.com/.well-known/wallet-security.json"
TOKEN_SAFETY_PAGE_URL = "https://gcagochina.com/token-safety.html"
TOKEN_SAFETY_URL = "https://gcagochina.com/token-safety.json"
BLOCKAID_FOLLOWUP_PAGE_URL = "https://gcagochina.com/blockaid-followup.html"
BLOCKAID_FOLLOWUP_URL = "https://gcagochina.com/blockaid-followup.json"
TECHNICAL_REPORT_PAGE_URL = "https://gcagochina.com/technical-report.html"
TECHNICAL_REPORT_URL = "https://gcagochina.com/technical-report.json"
RESERVE_STATEMENT_PAGE_URL = "https://gcagochina.com/reserve-statement.html"
RESERVE_STATEMENT_URL = "https://gcagochina.com/reserve-statement.json"
EXTERNAL_REVIEW_PAGE_URL = "https://gcagochina.com/external-reviews.html"
EXTERNAL_REVIEW_URL = "https://gcagochina.com/external-reviews.json"
REVIEWER_KIT_PAGE_URL = "https://gcagochina.com/reviewer-kit.html"
REVIEWER_KIT_URL = "https://gcagochina.com/reviewer-kit.json"
PLATFORM_REPLIES_PAGE_URL = "https://gcagochina.com/platform-replies.html"
PLATFORM_REPLIES_URL = "https://gcagochina.com/platform-replies.json"
TRUST_CENTER_PAGE_URL = "https://gcagochina.com/trust.html"
TRUST_CENTER_URL = "https://gcagochina.com/trust.json"
LISTING_READINESS_PAGE_URL = "https://gcagochina.com/listing-readiness.html"
LISTING_READINESS_URL = "https://gcagochina.com/listing-readiness.json"
MARKET_QUALITY_PAGE_URL = "https://gcagochina.com/market-quality.html"
MARKET_QUALITY_URL = "https://gcagochina.com/market-quality.json"
ONCHAIN_PROOFS_PAGE_URL = "https://gcagochina.com/onchain-proofs.html"
ONCHAIN_PROOFS_URL = "https://gcagochina.com/onchain-proofs.json"
SUPPLY_DISCLOSURE_URL = "https://gcagochina.com/supply.json"
BRAND_KIT_PAGE_URL = "https://gcagochina.com/brand-kit.html"
BRAND_KIT_URL = "https://gcagochina.com/brand-kit.json"
SOCIAL_CARD_PNG_URL = "https://gcagochina.com/assets/gca-social-card.png"
SOCIAL_CARD_SVG_URL = "https://gcagochina.com/assets/gca-social-card.svg"
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


def assert_social_preview_meta(text: str, label: str, canonical_url: str) -> None:
    assert_contains(text, f'<link rel="canonical" href="{canonical_url}">', label)
    assert_contains(text, '<meta property="og:type" content="website">', label)
    assert_contains(text, '<meta property="og:site_name" content="GCA | Go China Access">', label)
    assert_contains(text, f'<meta property="og:url" content="{canonical_url}">', label)
    assert_contains(text, f'<meta property="og:image" content="{SOCIAL_CARD_PNG_URL}">', label)
    assert_contains(text, '<meta property="og:image:width" content="1200">', label)
    assert_contains(text, '<meta property="og:image:height" content="630">', label)
    assert_contains(text, '<meta name="twitter:card" content="summary_large_image">', label)
    assert_contains(text, f'<meta name="twitter:image" content="{SOCIAL_CARD_PNG_URL}">', label)


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
    assert_contains(text, "Platform Replies", label)
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "Token Safety", label)
    assert_contains(text, "Blockaid Follow-up", label)
    assert_contains(text, "Technical Report", label)
    assert_contains(text, "Reserve Statement", label)
    assert_contains(text, "Listing Readiness", label)
    assert_contains(text, "On-chain Proofs", label)
    assert_contains(text, "Brand Kit", label)
    assert_contains(text, "Member Ledger", label)
    assert_contains(text, "Benefit Transfer Runbook", label)
    assert_contains(text, "member-benefit-transfer.html", label)
    assert_contains(text, "member-benefit-transfer.json", label)
    assert_contains(text, "Operator Console", label)
    assert_contains(text, "operator.html", label)
    assert_contains(text, "Support & Intake", label)
    assert_contains(text, "Roadmap", label)
    assert_contains(text, "Community Kit", label)
    assert_contains(text, "Narrative System", label)
    assert_contains(text, "Weekly Radar", label)
    assert_contains(text, "Utility JSON", label)
    assert_contains(text, "Product Spec", label)
    assert_contains(text, "Access Portal", label)
    assert_contains(text, "Operations", label)
    assert_contains(text, "Access API", label)
    assert_contains(text, "Review Queue", label)
    assert_contains(text, "Operations Runbook", label)
    assert_contains(text, "Credits Catalog", label)
    assert_contains(text, "Release Gates", label)
    assert_contains(text, "Privacy Notice", label)
    assert_contains(text, "Participation Terms", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_current_pool_text(text, label)


def validate_verify(text: str) -> None:
    label = "/verify.html"
    assert_contains(text, "Verify GCA", label)
    assert_contains(text, "Resubmitted: awaiting review", label)
    assert_contains(text, "well-known token identity", label)
    assert_contains(text, "Wallet Warning", label)
    assert_contains(text, "External Reviews", label)
    assert_contains(text, "Trust Center", label)
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


def validate_buy_page(text: str) -> None:
    label = "/buy.html"
    assert_social_preview_meta(text, label, BUY_PAGE_URL)
    assert_contains(text, "Buy GCA", label)
    assert_contains(text, "Open Uniswap Swap", label)
    assert_contains(text, "This is not investment advice", label)
    assert_contains(text, "starter-depth only", label)
    assert_contains(text, "no third-party audit has been completed", label)
    assert_contains(text, "permanent warning-free status", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)


def validate_status_page(text: str) -> None:
    label = "/status.html"
    assert_social_preview_meta(text, label, STATUS_PAGE_URL)
    assert_contains(text, "GCA Project Status", label)
    assert_contains(text, "Contract source verified on BaseScan", label)
    assert_contains(text, "Deployer-wallet ownership verified on BaseScan", label)
    assert_contains(text, "BaseScan public token profile publication", label)
    assert_contains(text, "Awaiting review", label)
    assert_contains(text, "GeckoTerminal token information update", label)
    assert_contains(text, "Approved", label)
    assert_contains(text, "No third-party audit has been completed", label)
    assert_contains(text, "Do not say the BaseScan token profile is approved", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_current_pool_text(text, label)


def validate_listing_kit_page(text: str) -> None:
    label = "/listing-kit.html"
    assert_social_preview_meta(text, label, LISTING_KIT_PAGE_URL)
    assert_contains(text, "GCA Listing Kit", label)
    assert_contains(text, "Public URLs", label)
    assert_contains(text, "Descriptions", label)
    assert_contains(text, "Official GCA/USDT route", label)
    assert_contains(text, "BaseScan", label)
    assert_contains(text, "awaiting BaseScan email/review", label)
    assert_contains(text, "GeckoTerminal", label)
    assert_contains(text, "Approved", label)
    assert_contains(text, "no completed third-party audit", label)
    assert_contains(text, "Do not claim BaseScan profile approval", label)
    assert_contains(text, "GCAgochina@outlook.com", label)
    assert_contains(text, X_URL, label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_current_pool_text(text, label)


def validate_security_page(text: str) -> None:
    label = "/security.html"
    assert_social_preview_meta(text, label, SECURITY_PAGE_URL)
    assert_contains(text, "GCA Security", label)
    assert_contains(text, "Verified on BaseScan", label)
    assert_contains(text, "fixed-supply ERC-20 contract on Base Mainnet", label)
    assert_contains(text, "No independent third-party audit has been completed", label)
    assert_contains(text, "GCA/USDT pool has starter-depth liquidity", label)
    assert_contains(text, "not permanent security-vendor approval", label)
    assert_contains(text, "Do not say: third-party audited", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "GCA/USDT", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def validate_risk_page(text: str) -> None:
    label = "/risk.html"
    assert_social_preview_meta(text, label, RISK_PAGE_URL)
    assert_contains(text, "GCA Risk Disclosures", label)
    assert_contains(text, "No third-party audit", label)
    assert_contains(text, "official GCA/USDT pool on Base Mainnet", label)
    assert_contains(text, "report submission does not mean warnings have been removed", label)
    assert_contains(text, "not be described as externally audited", label)
    assert_contains(text, "not submitted because current liquidity and public activity are still weak", label)
    assert_contains(text, "starter-depth liquidity", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def validate_faq_page(text: str) -> None:
    label = "/faq.html"
    assert_social_preview_meta(text, label, FAQ_PAGE_URL)
    assert_contains(text, "GCA FAQ", label)
    assert_contains(text, "Why do I see a high-risk warning?", label)
    assert_contains(text, "Is GCA externally audited?", label)
    assert_contains(text, "Why does BaseScan show 1B supply?", label)
    assert_contains(text, "No third-party audit", label)
    assert_contains(text, "not permanent security-vendor approval", label)
    assert_contains(text, "Earlier pilot liquidity is historical", label)
    assert_contains(text, "Do not claim BaseScan token profile approval", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_current_pool_text(text, label)


def validate_whitepaper_page(text: str) -> None:
    label = "/whitepaper.html"
    assert_social_preview_meta(text, label, WHITEPAPER_PAGE_URL)
    assert_contains(text, "GCA Whitepaper", label)
    assert_contains(text, "Narrative meets risk control", label)
    assert_contains(text, "not live market data, financial advice, a buy/sell recommendation, or a price forecast", label)
    assert_contains(text, "Until those gates are live, 100 utility credits, GCA Member status, and the 10,000 GCA member benefit are not self-service claimable", label)
    assert_contains(text, "not as a yield product", label)
    assert_contains(text, "not automatic claiming or new minting", label)
    assert_contains(text, "This is not a substitute for a third-party audit", label)
    assert_contains(text, "no third-party audit has been completed", label)
    assert_contains(text, "awaiting BaseScan email/review", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_current_pool_text(text, label)


def validate_token_safety_page(text: str) -> None:
    label = "/token-safety.html"
    assert_contains(text, "GCA Token Safety Checklist", label)
    assert_contains(text, "Token Safety JSON", label)
    assert_contains(text, "Wallet Security JSON", label)
    assert_contains(text, "Verified Positive Controls", label)
    assert_contains(text, "Pending Or Not Claimed", label)
    assert_contains(text, "No mint function", label)
    assert_contains(text, "No third-party audit", label)
    assert_contains(text, "permanent warning-free status", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_current_pool_text(text, label)


def validate_token_safety_json(text: str) -> None:
    label = "/token-safety.json"
    payload = load_json(text, label)
    controls = payload.get("verifiedPositiveControls", {})
    pending = payload.get("pendingOrNotClaimed", {})
    market = payload.get("officialMarket", {})
    links = payload.get("reviewLinks", {})

    if payload.get("schema") != TOKEN_SAFETY_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != TOKEN_SAFETY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-token-safety-checklist-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if controls.get("sourceVerifiedOnBaseScan") is not True:
        raise SiteCheckError(f"{label}: source verification must be true")
    if controls.get("fixedSupply") is not True:
        raise SiteCheckError(f"{label}: fixed supply must be true")
    for key in (
        "postDeploymentMintFunction",
        "ownerOrAdminRole",
        "proxyOrUpgradePath",
        "blacklistFunction",
        "pauseFunction",
        "transferTaxOrHiddenFee",
        "custodyOrWithdrawalPath",
    ):
        if controls.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if pending.get("baseScanTokenProfile") != "resubmitted-awaiting-review":
        raise SiteCheckError(f"{label}: wrong BaseScan profile status")
    if pending.get("blockaidMetaMaskWarning") != "owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong wallet warning status")
    if pending.get("thirdPartyAudit") != "not-completed":
        raise SiteCheckError(f"{label}: wrong audit status")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if links.get("tokenSafetyPage") != TOKEN_SAFETY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafetyPage")
    if links.get("tokenSafety") != TOKEN_SAFETY_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafety")
    if links.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup")
    if links.get("technicalReport") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technicalReport")
    if links.get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatement")
    if links.get("walletSecurityProfile") != WALLET_SECURITY_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong walletSecurityProfile")
    if links.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidence")
    if "No third-party audit has been completed." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "security-vendor approval, permanent warning-free status, or cross-wallet warning removal before vendor/current wallet UI confirms it" not in payload.get("publicClaimBoundaries", {}).get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing warning-removal boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_blockaid_followup_page(text: str) -> None:
    label = "/blockaid-followup.html"
    assert_contains(text, "GCA Blockaid Follow-up", label)
    assert_contains(text, "Blockaid Follow-up JSON", label)
    assert_contains(text, "Risk Factor Response", label)
    assert_contains(text, "Price Volatility", label)
    assert_contains(text, "LP Lock", label)
    assert_contains(text, "Supply Concentration", label)
    assert_contains(text, "Third-party Audit", label)
    assert_contains(text, "No LP lock is currently claimed", label)
    assert_contains(text, "No third-party audit has been completed", label)
    assert_contains(text, "Technical Report", label)
    assert_contains(text, "Reserve Statement", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, OFFICIAL_POOL_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_blockaid_followup_json(text: str) -> None:
    label = "/blockaid-followup.json"
    payload = load_json(text, label)
    controls = payload.get("contractControlSummary", {})
    responses = payload.get("riskFactorResponses", {})
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})

    if payload.get("schema") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != BLOCKAID_FOLLOWUP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-blockaid-followup-package-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if controls.get("sourceVerifiedOnBaseScan") is not True:
        raise SiteCheckError(f"{label}: source verification must be true")
    if controls.get("fixedSupply") is not True:
        raise SiteCheckError(f"{label}: fixed supply must be true")
    for key in (
        "postDeploymentMintFunction",
        "ownerOrAdminRole",
        "proxyOrUpgradePath",
        "blacklistFunction",
        "pauseFunction",
        "transferTaxOrHiddenFee",
        "custodyOrWithdrawalPath",
        "customTransferRestrictions",
        "adminTradingControls",
    ):
        if controls.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if responses.get("priceVolatility", {}).get("status") != "acknowledged":
        raise SiteCheckError(f"{label}: wrong price volatility response")
    if responses.get("lpLock", {}).get("status") != "not-locked-not-claimed":
        raise SiteCheckError(f"{label}: wrong LP lock response")
    if responses.get("supplyConcentration", {}).get("reserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong reserve wallet")
    if responses.get("thirdPartyAudit", {}).get("status") != "not-completed":
        raise SiteCheckError(f"{label}: wrong audit response")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong pool")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quote asset")
    if links.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup")
    if links.get("technicalReport") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technicalReport")
    if links.get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatement")
    if "GCA has published an internal technical report and reserve address statement for reviewer triage." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing triage safe claim")
    if "LP lock before a verifiable lock exists" not in payload.get("publicClaimBoundaries", {}).get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing LP lock boundary")
    assert_current_pool_text(json.dumps(payload), label)
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_technical_report_page(text: str) -> None:
    label = "/technical-report.html"
    assert_contains(text, "GCA Technical Report", label)
    assert_contains(text, "Technical Report JSON", label)
    assert_contains(text, "internal technical report", label)
    assert_contains(text, "not a third-party audit", label)
    assert_contains(text, "Verified Positive Controls", label)
    assert_contains(text, "Absent Controls", label)
    assert_contains(text, "Post-deployment mint function", label)
    assert_contains(text, "Owner/admin role", label)
    assert_contains(text, "Transfer tax or hidden fee", label)
    assert_contains(text, "LP lock claimed", label)
    assert_contains(text, "Reserve Statement", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_contains(text, DEPLOYMENT_TX, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_technical_report_json(text: str) -> None:
    label = "/technical-report.json"
    payload = load_json(text, label)
    controls = payload.get("contractControlReview", {})
    market = payload.get("marketAndLiquidityDisclosure", {})
    reserve = payload.get("reserveDisclosure", {})

    if payload.get("schema") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != TECHNICAL_REPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-internal-technical-report-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("reportType") != "internal-technical-report-not-third-party-audit":
        raise SiteCheckError(f"{label}: wrong report type")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("sourceVerification", {}).get("sourceVerifiedOnBaseScan") is not True:
        raise SiteCheckError(f"{label}: source verification must be true")
    if controls.get("fixedSupply") is not True:
        raise SiteCheckError(f"{label}: fixedSupply must be true")
    for key in (
        "postDeploymentMintFunction",
        "burnFunction",
        "ownerOrAdminRole",
        "proxyOrUpgradePath",
        "blacklistFunction",
        "pauseFunction",
        "transferTaxOrHiddenFee",
        "customTransferRestrictions",
        "custodyOrWithdrawalPath",
        "externalCallDuringTransfer",
        "adminTradingControls",
    ):
        if controls.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong pool")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quote asset")
    if market.get("lpLockClaimed") is not False:
        raise SiteCheckError(f"{label}: LP lock must not be claimed")
    if reserve.get("ownerReserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong reserve wallet")
    if reserve.get("reserveLocked") is not False:
        raise SiteCheckError(f"{label}: reserve lock must not be claimed")
    if reserve.get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserve statement URL")
    if "This report is an internal technical report, not an independent third-party audit." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing internal report boundary")
    assert_current_pool_text(json.dumps(payload), label)
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_reserve_statement_page(text: str) -> None:
    label = "/reserve-statement.html"
    assert_contains(text, "GCA Reserve Address Statement", label)
    assert_contains(text, "Reserve Statement JSON", label)
    assert_contains(text, "Owner-controlled, not locked", label)
    assert_contains(text, "Custody Boundary", label)
    assert_contains(text, "On-chain Reserve Transfer Proofs", label)
    assert_contains(text, "LP lock claimed", label)
    assert_contains(text, "No LP lock is currently claimed", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_contains(text, RESERVE_TX_1, label)
    assert_contains(text, RESERVE_TX_2, label)
    assert_no_forbidden_public_claims(text, label)


def validate_reserve_statement_json(text: str) -> None:
    label = "/reserve-statement.json"
    payload = load_json(text, label)
    allocation = payload.get("allocationStatement", {})
    boundaries = payload.get("reserveUseBoundaries", {})
    links = payload.get("officialLinks", {})

    if payload.get("schema") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != RESERVE_STATEMENT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-reserve-address-statement-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if allocation.get("ownerReserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong reserve wallet")
    if allocation.get("ownerHeldReserve") != "600000000":
        raise SiteCheckError(f"{label}: wrong reserve amount")
    if allocation.get("reserveLocked") is not False:
        raise SiteCheckError(f"{label}: reserveLocked must be false")
    if allocation.get("vestingContract") is not False:
        raise SiteCheckError(f"{label}: vestingContract must be false")
    if allocation.get("multisig") is not False:
        raise SiteCheckError(f"{label}: multisig must be false")
    transfer_text = json.dumps(payload.get("reserveTransferProofs", []))
    if RESERVE_TX_1 not in transfer_text or RESERVE_TX_2 not in transfer_text:
        raise SiteCheckError(f"{label}: missing reserve transfer tx")
    if boundaries.get("lpLockStatus") != "not-locked-not-claimed":
        raise SiteCheckError(f"{label}: wrong LP lock status")
    if links.get("technicalReport") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technical report link")
    if "No LP lock is currently claimed." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing LP lock safe claim")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_members(text: str) -> None:
    label = "/members.html"
    assert_contains(text, "GCA Member Pre-Registration", label)
    assert_contains(text, "member access preview", label)
    assert_contains(text, "gca/member-access/", label)
    assert_contains(text, "100 Credit Rules", label)
    assert_contains(text, "Member Rules", label)
    assert_contains(text, "Support Workflow", label)
    assert_contains(text, "Check On-chain Balance", label)
    assert_contains(text, "GCA Member Holding Start Date", label)
    assert_contains(text, "Public Purchase or Transfer Tx Hash", label)
    assert_contains(text, "memberBenefitReviewEvidence", label)
    assert_contains(text, "evidenceTxHashFormatOk", label)
    assert_contains(text, "holdingPeriodPreviewEligible", label)
    assert_contains(text, "browser-only preview reads GCA balance", label)
    assert_contains(text, "eth_call", label)
    assert_contains(text, "wallet_switchEthereumChain", label)
    assert_contains(text, "doesNotCreateLedgerRecord", label)
    assert_contains(text, "member-program.json", label)
    assert_contains(text, "member-ledger.html", label)
    assert_contains(text, "member-ledger.json", label)
    assert_contains(text, "tools/gca_member_backend.py", label)
    assert_contains(text, "LOCAL_BACKEND_HOSTS", label)
    assert_contains(text, "local JSONL ledger records", label)
    assert_contains(text, "support.html", label)
    assert_contains(text, "privacy.html", label)
    assert_contains(text, "terms.html", label)
    assert_contains(text, "180 days", label)
    assert_contains(text, "30 days", label)
    assert_contains(text, "5-10 business days", label)
    assert_contains(text, "Direct submission is not connected", label)
    assert_contains(text, "No cash, income, reimbursement, trading permission, or risk-control bypass", label)
    assert_contains(text, "10,000 GCA member benefit", label)
    assert_contains(text, "Public transaction hash + holding start date", label)
    assert_not_contains(text, "eth_sendTransaction", label)
    assert_not_contains(text, "personal_sign", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)


def validate_member_access_page(text: str) -> None:
    label = "/gca/member-access/"
    assert_contains(text, "GCA Member Access Preview", label)
    assert_contains(text, "static same-origin preview", label)
    assert_contains(text, "Wallet Balance Preview", label)
    assert_contains(text, "Packet Review", label)
    assert_contains(text, "Local Review", label)
    assert_contains(text, "Access Boundaries", label)
    assert_contains(text, "Check GCA Balance", label)
    assert_contains(text, "MetaMask eth_call", label)
    assert_contains(text, "ERC-20 balanceOf", label)
    assert_contains(text, "wallet_switchEthereumChain", label)
    assert_contains(text, "wallet_addEthereumChain", label)
    assert_contains(text, "10,000 GCA", label)
    assert_contains(text, "1,000,000 GCA", label)
    assert_contains(text, "100 Web3 Radar utility credits", label)
    assert_contains(text, "does not create a live account", label)
    assert_contains(text, "does not activate GCA Member status", label)
    assert_not_contains(text, "eth_sendTransaction", label)
    assert_not_contains(text, "personal_sign", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def validate_operator_page(text: str) -> None:
    label = "/operator.html"
    assert_contains(text, "GCA Local Operator Console", label)
    assert_contains(text, "Local-only GCA operator console", label)
    assert_contains(text, "tools/gca_member_backend.py", label)
    assert_contains(text, "tools/export_gca_review_package.py", label)
    assert_contains(text, "http://127.0.0.1:8787/operator.html", label)
    assert_contains(text, "LOCAL_BACKEND_HOSTS", label)
    assert_contains(text, 'const OPERATOR_SUMMARY_ENDPOINT_PATH = "/gca/operator-summary";', label)
    assert_contains(text, 'const REVIEW_PACKAGE_ENDPOINT_PATH = "/gca/review-package";', label)
    assert_contains(text, 'const MEMBER_BENEFIT_TRANSFER_ENDPOINT_PATH = "/gca/member-benefit-transfers";', label)
    assert_contains(text, "Local operator backend connected", label)
    assert_contains(text, "Export Full Review Package", label)
    assert_contains(text, "Export Full Review Package (Internal Only)", label)
    assert_contains(text, 'id="exportButton" type="button" disabled', label)
    assert_contains(text, "Export Public Redacted Package", label)
    assert_contains(text, 'id="exportPublicButton" type="button" disabled', label)
    assert_contains(text, "Copy Handoff Reply", label)
    assert_contains(text, "Full local review package exported", label)
    assert_contains(text, "Public redacted review package exported", label)
    assert_contains(text, "Review Package Handoff", label)
    assert_contains(text, "Last package mode", label)
    assert_contains(text, "Local verify command", label)
    assert_contains(text, "Reviewer handoff reply", label)
    assert_contains(text, "External sharing is allowed only for", label)
    assert_contains(text, "Full-local package exported for internal operator review only", label)
    assert_contains(text, "Ready for redacted-public handoff after local digest verification", label)
    assert_contains(text, "buildHandoffReply", label)
    assert_contains(text, "renderReviewPackageHandoff", label)
    assert_contains(text, "navigator.clipboard.writeText", label)
    assert_contains(text, "let backendConnected = false", label)
    assert_contains(text, "function setBackendControlsEnabled", label)
    assert_contains(text, "function confirmFullLocalExport", label)
    assert_contains(text, "window.confirm", label)
    assert_contains(text, "Full-local review packages may include local user email", label)
    assert_contains(text, "Do not send full-local packages to platforms", label)
    assert_contains(text, "Full local review package export cancelled", label)
    assert_contains(text, "Use public redacted export for external handoff", label)
    assert_contains(text, "Local backend unavailable; export and record controls disabled", label)
    assert_contains(text, "Export disabled until local backend is connected", label)
    assert_contains(text, "packageDigestSha256", label)
    assert_contains(text, "recordManifest", label)
    assert_contains(text, "tools/verify_gca_review_package.py", label)
    assert_contains(text, "?redact=public", label)
    assert_contains(text, "Public website view: local backend not connected", label)
    assert_contains(text, "local JSONL ledger records", label)
    assert_contains(text, ".gca_access_data/", label)
    assert_contains(text, "Pre-registrations", label)
    assert_contains(text, "100 credits records", label)
    assert_contains(text, "Active GCA Members", label)
    assert_contains(text, "Pending reserve transfers", label)
    assert_contains(text, "Recorded transfers", label)
    assert_contains(text, "Record Manual Member Benefit Transfer", label)
    assert_contains(text, "Member Ledger ID", label)
    assert_contains(text, "Manual Transfer Tx Hash", label)
    assert_contains(text, "Record Transfer", label)
    assert_contains(text, 'id="recordTransferButton" type="submit" disabled', label)
    assert_contains(text, "Latest Support Review Records", label)
    assert_contains(text, "/gca/pre-registrations", label)
    assert_contains(text, "/gca/wallet-verifications", label)
    assert_contains(text, "/gca/credit-ledger", label)
    assert_contains(text, "/gca/member-ledger", label)
    assert_contains(text, "/gca/review-package", label)
    assert_contains(text, "/gca/member-benefit-transfers", label)
    assert_contains(text, "/gca/member-review", label)
    assert_contains(text, "manual reserve-wallet transfer review", label)
    assert_contains(text, "records the public Base transaction hash", label)
    assert_contains(text, "never sends tokens", label)
    assert_not_contains(text, "eth_sendTransaction", label)
    assert_not_contains(text, "personal_sign", label)
    assert_no_forbidden_public_claims(text, label)


def validate_support_page(text: str) -> None:
    label = "/support.html"
    assert_contains(text, "GCA Support & Intake", label)
    assert_contains(text, "Support JSON", label)
    assert_contains(text, "Reviewer Kit", label)
    assert_contains(text, "Platform Replies", label)
    assert_contains(text, "Review Queue", label)
    assert_contains(text, "Operations Runbook", label)
    assert_contains(text, "GCAgochina@outlook.com", label)
    assert_contains(text, "Direct Submit", label)
    assert_contains(text, "Not connected", label)
    assert_contains(text, "Private key or seed phrase", label)
    assert_contains(text, "Exchange API secret or withdrawal permission", label)
    assert_contains(text, "Support Workflow", label)
    assert_contains(text, "Support Cannot Do", label)
    assert_contains(text, "Base Mainnet / chainId 8453", label)
    assert_contains(text, "GCA/USDT", label)
    assert_contains(text, "gca_member_preregistration_v2", label)
    assert_contains(text, "memberBenefitReviewEvidence", label)
    assert_contains(text, "GCA Member holding start date", label)
    assert_contains(text, "GCA Member evidence note", label)
    assert_contains(text, "Redacted Review Package Handoff", label)
    assert_contains(text, "redacted-public", label)
    assert_contains(text, "tools/export_gca_review_package.py", label)
    assert_contains(text, "tools/verify_gca_review_package.py", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def validate_support_json(text: str) -> None:
    label = "/support.json"
    payload = load_json(text, label)
    submission = payload.get("currentSubmissionMode", {})
    workflow = payload.get("supportWorkflow", {})
    handoff = workflow.get("platformReviewPackageHandoff", {})
    identity = payload.get("officialIdentity", {})
    links = payload.get("publicLinks", {})

    if payload.get("schema") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-support-intake-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("officialEmail") != "GCAgochina@outlook.com":
        raise SiteCheckError(f"{label}: wrong officialEmail")
    if submission.get("directSubmissionEndpointConfigured") is not False:
        raise SiteCheckError(f"{label}: direct submission must remain false")
    if submission.get("controlledHttpsAccountUiLive") is not False:
        raise SiteCheckError(f"{label}: account UI must remain false")
    if "private key" not in payload.get("doNotSend", []):
        raise SiteCheckError(f"{label}: missing private key boundary")
    if "seed phrase" not in payload.get("doNotSend", []):
        raise SiteCheckError(f"{label}: missing seed phrase boundary")
    if "exchange API secret" not in payload.get("doNotSend", []):
        raise SiteCheckError(f"{label}: missing API secret boundary")
    if "withdrawal permission" not in payload.get("doNotSend", []):
        raise SiteCheckError(f"{label}: missing withdrawal permission boundary")
    if workflow.get("preparedIntakeEndpoint") != "/gca/pre-registrations":
        raise SiteCheckError(f"{label}: wrong prepared intake endpoint")
    if "ledger_recorded" not in workflow.get("reviewStatuses", []):
        raise SiteCheckError(f"{label}: missing ledger status")
    if workflow.get("memberPacketVersion") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong member packet version")
    if "redacted local review package request" not in payload.get("supportedRequestTypes", []):
        raise SiteCheckError(f"{label}: missing review package request type")
    for field in (
        "holdingStartDate",
        "daysSinceHoldingStartPreview",
        "holdingPeriodPreviewEligible",
        "evidenceTxHash",
        "evidenceTxHashFormatOk",
        "evidenceNote",
    ):
        if field not in workflow.get("memberBenefitReviewEvidenceFields", []):
            raise SiteCheckError(f"{label}: missing member evidence field {field}")
    for field in (
        "GCA Member holding start date",
        "GCA Member evidence note",
        "gca_member_preregistration_v2 memberBenefitReviewEvidence packet fields",
        "public redacted local review package digest",
    ):
        if field not in payload.get("safeIntakeFields", []):
            raise SiteCheckError(f"{label}: missing safe intake field {field}")
    if handoff.get("externalSharingMode") != "redacted-public":
        raise SiteCheckError(f"{label}: wrong handoff external mode")
    if handoff.get("internalOnlyMode") != "full-local":
        raise SiteCheckError(f"{label}: wrong handoff internal mode")
    if handoff.get("localDataDirectory") != ".gca_access_data/":
        raise SiteCheckError(f"{label}: wrong handoff data directory")
    if "tools/export_gca_review_package.py" not in handoff.get("exportCommand", ""):
        raise SiteCheckError(f"{label}: missing handoff export command")
    if "tools/verify_gca_review_package.py" not in handoff.get("verifyCommand", ""):
        raise SiteCheckError(f"{label}: missing handoff verify command")
    if handoff.get("replyTemplatePage") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong handoff reply template page")
    if "userEmail" not in handoff.get("redactedFields", []):
        raise SiteCheckError(f"{label}: missing handoff redacted field")
    if "full-local package" not in handoff.get("neverShareExternally", []):
        raise SiteCheckError(f"{label}: missing full-local sharing boundary")
    if identity.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong official pair")
    if identity.get("officialPool") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong official pool")
    if links.get("supportPage") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong support page link")
    if links.get("supportJson") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong support json link")
    if links.get("reviewQueuePage") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueuePage")
    if links.get("reviewQueue") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueue")
    if links.get("operationsRunbookPage") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbookPage")
    if links.get("operationsRunbook") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbook")
    if links.get("privacyNotice") != PRIVACY_NOTICE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong privacy link")
    if links.get("participationTerms") != PARTICIPATION_TERMS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong terms link")
    if links.get("memberBenefitReview") != MEMBER_BENEFIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong member benefit page")
    if links.get("memberBenefitReviewJson") != MEMBER_BENEFIT_URL:
        raise SiteCheckError(f"{label}: wrong member benefit json")
    if links.get("memberBenefitTransfer") != MEMBER_BENEFIT_TRANSFER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong member benefit transfer page")
    if links.get("memberBenefitTransferJson") != MEMBER_BENEFIT_TRANSFER_URL:
        raise SiteCheckError(f"{label}: wrong member benefit transfer json")
    if links.get("reviewerKitPage") != REVIEWER_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKitPage")
    if links.get("reviewerKit") != REVIEWER_KIT_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKit")
    if links.get("platformRepliesPage") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesPage")
    if links.get("platformReplies") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong platformReplies")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_roadmap_page(text: str) -> None:
    label = "/roadmap.html"
    assert_contains(text, "GCA Roadmap", label)
    assert_contains(text, "Roadmap JSON", label)
    assert_contains(text, "Concept-stage utility buildout", label)
    assert_contains(text, "Controlled HTTPS member account UI", label)
    assert_contains(text, "Read-only GCA balance verification", label)
    assert_contains(text, "100 Web3 Radar utility credit records", label)
    assert_contains(text, "GCA Member records", label)
    assert_contains(text, "External Dependencies", label)
    assert_contains(text, "Resubmitted: awaiting review", label)
    assert_contains(text, "Owner observed no warning visible", label)
    assert_contains(text, "Not completed", label)
    assert_contains(text, "public self-service member claiming is live", label)
    assert_contains(text, "Base Mainnet / chainId 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_current_pool_text(text, label)


def validate_roadmap_json(text: str) -> None:
    label = "/roadmap.json"
    payload = load_json(text, label)
    market = payload.get("officialMarket", {})
    dependencies = payload.get("externalDependencies", {})
    links = payload.get("publicLinks", {})

    if payload.get("schema") != ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-roadmap-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("currentStage") != "concept-stage-utility-buildout":
        raise SiteCheckError(f"{label}: wrong currentStage")
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
    if market.get("liquidityDepth") != "starter-depth-only":
        raise SiteCheckError(f"{label}: wrong liquidityDepth")
    if dependencies.get("baseScanTokenProfile") != "resubmitted-awaiting-review":
        raise SiteCheckError(f"{label}: wrong BaseScan status")
    if dependencies.get("blockaidMetaMaskWarning") != "owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong wallet warning status")
    if dependencies.get("thirdPartyAudit") != "not-completed-deferred":
        raise SiteCheckError(f"{label}: wrong audit status")
    if not any(priority.get("id") == "controlled-account-ui" for priority in payload.get("nextBuildPriorities", [])):
        raise SiteCheckError(f"{label}: missing controlled account UI priority")
    if not any(priority.get("id") == "utility-credit-ledger" for priority in payload.get("nextBuildPriorities", [])):
        raise SiteCheckError(f"{label}: missing utility credit ledger priority")
    if "GCA is concept-stage and is building public identity, safer support intake, and planned non-custodial quant research access." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing concept-stage safe claim")
    if "public self-service member or 10,000 GCA member benefit claiming is live before controlled HTTPS UI and holding-period review are connected" not in payload.get("publicClaimBoundaries", {}).get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing self-service do-not-claim")
    if links.get("roadmapPage") != ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong roadmapPage")
    if links.get("roadmapJson") != ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong roadmapJson")
    if links.get("narrativePage") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong narrativePage")
    if links.get("narrative") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong narrative")
    if links.get("weeklyRadarPage") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarPage")
    if links.get("weeklyRadar") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadar")
    if links.get("support") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong support")
    if links.get("listingReadiness") != LISTING_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong listingReadiness")
    if any(priority.get("id") == "weekly-go-china-radar" for priority in payload.get("nextBuildPriorities", [])):
        raise SiteCheckError(f"{label}: weekly radar should not remain a next priority")
    if not any(milestone.get("id") == "weekly-go-china-radar-issue-002" for milestone in payload.get("completedMilestones", [])):
        raise SiteCheckError(f"{label}: missing weekly radar completed milestone")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_community_page(text: str) -> None:
    label = "/community.html"
    assert_contains(text, "GCA Community Kit", label)
    assert_contains(text, "Community JSON", label)
    assert_contains(text, "Official Telegram", label)
    assert_contains(text, "Safe Announcement Copy", label)
    assert_contains(text, "X Launch Pack", label)
    assert_contains(text, "First X Post", label)
    assert_contains(text, "Pinned X Post Draft", label)
    assert_contains(text, "First official X post", label)
    assert_contains(text, FIRST_X_POST_URL, label)
    assert_contains(text, "Moderator replies", label)
    assert_contains(text, "Wallet Warning Reply", label)
    assert_contains(text, "Price Display Reply", label)
    assert_contains(text, "Member Access Reply", label)
    assert_contains(text, "Do Not Post", label)
    assert_contains(text, "private keys, seed phrases, exchange API secrets", label)
    assert_contains(text, "Base Mainnet / chainId 8453", label)
    assert_contains(text, "https://t.me/gcagochinaofficial", label)
    assert_contains(text, X_URL, label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_current_pool_text(text, label)


def validate_community_json(text: str) -> None:
    label = "/community.json"
    payload = load_json(text, label)
    market = payload.get("officialMarket", {})
    links = payload.get("publicLinks", {})
    templates = payload.get("moderatorReplyTemplates", {})
    x_launch = payload.get("xLaunchPack", {})

    if payload.get("schema") != COMMUNITY_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != COMMUNITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-community-kit-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("currentStage") != "early-public-operations":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("officialTelegram") != "https://t.me/gcagochinaofficial":
        raise SiteCheckError(f"{label}: wrong officialTelegram")
    if payload.get("officialX") != X_URL:
        raise SiteCheckError(f"{label}: wrong officialX")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if market.get("liquidityDepth") != "starter-depth-only":
        raise SiteCheckError(f"{label}: wrong liquidityDepth")
    if not any("BaseScan token profile was returned as information-insufficient on 2026-05-13 and resubmitted on 2026-05-13" in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing BaseScan pending announcement")
    if not any("Narrative meets risk control" in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing narrative announcement")
    if not any("Weekly Go China Radar: https://gcagochina.com/radar.html" in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing weekly radar announcement")
    if not any(FIRST_X_POST_URL in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing first X post announcement")
    if x_launch.get("status") != "first-post-published":
        raise SiteCheckError(f"{label}: wrong xLaunchPack status")
    if x_launch.get("officialProfile") != X_URL:
        raise SiteCheckError(f"{label}: wrong xLaunchPack officialProfile")
    if x_launch.get("profilePhotoAsset") != "https://gcagochina.com/assets/gca-logo.png":
        raise SiteCheckError(f"{label}: wrong xLaunchPack profilePhotoAsset")
    if x_launch.get("firstPostUrl") != FIRST_X_POST_URL:
        raise SiteCheckError(f"{label}: wrong firstPostUrl")
    if x_launch.get("firstPostPublishedDate") != "2026-05-14":
        raise SiteCheckError(f"{label}: wrong firstPostPublishedDate")
    if not any("GCA is building Go China Access" in item for item in x_launch.get("firstPostText", [])):
        raise SiteCheckError(f"{label}: missing X first post text")
    if not any("Verify: https://gcagochina.com/verify.html" in item for item in x_launch.get("pinnedPostDraft", [])):
        raise SiteCheckError(f"{label}: missing X pinned post draft")
    if not any("Do not post market-price claims" in item for item in x_launch.get("postingChecklist", [])):
        raise SiteCheckError(f"{label}: missing X posting checklist boundary")
    if "walletWarning" not in templates:
        raise SiteCheckError(f"{label}: missing wallet warning template")
    if "priceDisplay" not in templates:
        raise SiteCheckError(f"{label}: missing price display template")
    if "memberAccess" not in templates:
        raise SiteCheckError(f"{label}: missing member access template")
    if "third-party audit completion before an independent report is published" not in payload.get("doNotPost", []):
        raise SiteCheckError(f"{label}: missing audit do-not-post")
    if links.get("communityPage") != COMMUNITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong communityPage")
    if links.get("communityJson") != COMMUNITY_URL:
        raise SiteCheckError(f"{label}: wrong communityJson")
    if links.get("narrativePage") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong narrativePage")
    if links.get("narrative") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong narrative")
    if links.get("weeklyRadarPage") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarPage")
    if links.get("weeklyRadar") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadar")
    if links.get("telegram") != "https://t.me/gcagochinaofficial":
        raise SiteCheckError(f"{label}: wrong telegram")
    if links.get("x") != X_URL:
        raise SiteCheckError(f"{label}: wrong x")
    if links.get("roadmap") != ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong roadmap")
    if links.get("support") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong support")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_narrative_page(text: str) -> None:
    label = "/narrative.html"
    assert_contains(text, "GCA Narrative System", label)
    assert_contains(text, "Narrative JSON", label)
    assert_contains(text, "Narrative meets risk control", label)
    assert_contains(text, "China Narrative Radar", label)
    assert_contains(text, "Weekly Go China Radar", label)
    assert_contains(text, "Liquidation Replay", label)
    assert_contains(text, "ENTRY_READY Review", label)
    assert_contains(text, "GCA Member Club", label)
    assert_contains(text, "Risk First Trading", label)
    assert_contains(text, "without return promises", label)
    assert_contains(text, "Do not claim price support", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_current_pool_text(text, label)


def validate_narrative_json(text: str) -> None:
    label = "/narrative.json"
    payload = load_json(text, label)
    positioning = payload.get("positioning", {})
    market = payload.get("officialMarket", {})
    boundaries = payload.get("publicClaimBoundaries", {})
    links = payload.get("officialLinks", {})

    if payload.get("schema") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-narrative-system-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if positioning.get("tagline") != "Narrative meets risk control.":
        raise SiteCheckError(f"{label}: wrong tagline")
    for item in (
        "China Narrative Radar",
        "Weekly Go China Radar",
        "Liquidation Replay",
        "ENTRY_READY Review",
        "GCA Member Club",
        "Risk First Trading",
    ):
        if item not in payload.get("publicNamingSystem", []):
            raise SiteCheckError(f"{label}: missing naming item {item}")
    if payload.get("memberHooks", {}).get("holderBonus", {}).get("minimumHolding") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder bonus threshold")
    if payload.get("memberHooks", {}).get("gcaMember", {}).get("minimumHolding") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member threshold")
    if payload.get("memberHooks", {}).get("gcaMember", {}).get("minimumHoldingPeriod") != "30 consecutive days":
        raise SiteCheckError(f"{label}: wrong member holding period")
    if payload.get("memberHooks", {}).get("gcaMember", {}).get("memberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit amount")
    if payload.get("weeklyRadar", {}).get("status") != "weekly-go-china-radar-issue-002-published":
        raise SiteCheckError(f"{label}: wrong weekly radar status")
    if payload.get("weeklyRadar", {}).get("pageUrl") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weekly radar page")
    if payload.get("weeklyRadar", {}).get("url") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weekly radar url")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if "Narrative meets risk control." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing tagline safe claim")
    if "return guarantees" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing return boundary")
    if links.get("narrativePage") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong narrativePage")
    if links.get("narrative") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong narrative")
    if links.get("weeklyRadarPage") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarPage")
    if links.get("weeklyRadar") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadar")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_radar_page(text: str) -> None:
    label = "/radar.html"
    assert_contains(text, "Weekly Go China Radar", label)
    assert_contains(text, "Radar JSON", label)
    assert_contains(text, "Issue 002 / 2026-05-14", label)
    assert_contains(text, "not live market data", label)
    assert_contains(text, "not financial advice", label)
    assert_contains(text, "Narrative Radar Board", label)
    assert_contains(text, "Go China trust stack", label)
    assert_contains(text, "Base ecosystem access", label)
    assert_contains(text, "Risk-first growth", label)
    assert_contains(text, "Liquidation Replay", label)
    assert_contains(text, "ENTRY_READY Review", label)
    assert_contains(text, "GCA Member Club", label)
    assert_contains(text, "No third-party audit has been completed", label)
    assert_contains(text, "buy/sell signal", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_current_pool_text(text, label)


def validate_radar_json(text: str) -> None:
    label = "/radar.json"
    payload = load_json(text, label)
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "weekly-go-china-radar-issue-002-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("issue") != "issue-002":
        raise SiteCheckError(f"{label}: wrong issue")
    if payload.get("issueDate") != "2026-05-14":
        raise SiteCheckError(f"{label}: wrong issueDate")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if "not live market data" not in payload.get("scope", ""):
        raise SiteCheckError(f"{label}: missing market-data boundary")
    for theme in ("Go China trust stack", "Base ecosystem access", "Risk-first growth"):
        if theme not in {item.get("name") for item in payload.get("narrativeThemes", [])}:
            raise SiteCheckError(f"{label}: missing theme {theme}")
    for hook in ("China Narrative Radar", "Liquidation Replay", "ENTRY_READY Review", "GCA Member Club"):
        if hook not in {item.get("name") for item in payload.get("utilityHooks", [])}:
            raise SiteCheckError(f"{label}: missing utility hook {hook}")
    if "No third-party audit has been completed." not in payload.get("riskNotes", []):
        raise SiteCheckError(f"{label}: missing audit risk note")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if "Weekly Go China Radar is the official GCA content format for narrative research and risk education." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing content safe claim")
    if "buy or sell recommendation" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing recommendation boundary")
    if "return promise" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing return boundary")
    if links.get("radarPage") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong radarPage")
    if links.get("radar") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong radar")
    if links.get("narrativePage") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong narrativePage")
    if links.get("narrative") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong narrative")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_utility_page(text: str) -> None:
    label = "/utility.html"
    assert_contains(text, "GCA Utility Thesis", label)
    assert_contains(text, "Utility JSON", label)
    assert_contains(text, "Utility Bridge Specification", label)
    assert_contains(text, "Web3 Radar-style non-custodial quant tools", label)
    assert_contains(text, "read-only wallet verification", label)
    assert_contains(text, "no custody", label)
    assert_contains(text, "no withdrawal permission", label)
    assert_contains(text, "no exchange API secret collection", label)
    assert_contains(text, "no platform revenue distribution", label)
    assert_contains(text, "controlled HTTPS account UI", label)
    assert_contains(text, "100 Web3 Radar utility credits", label)
    assert_contains(text, "GCA Member status", label)
    assert_contains(text, "10,000 GCA member benefit", label)
    assert_contains(text, "Credits Catalog", label)
    assert_contains(text, "credits.html", label)
    assert_contains(text, "credits.json", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_no_forbidden_public_claims(text, label)


def validate_utility_json(text: str) -> None:
    label = "/utility.json"
    payload = load_json(text, label)
    positioning = payload.get("positioning", {})
    holder_bonus = payload.get("holderBonus", {})
    member = payload.get("gcaMember", {})
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != UTILITY_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != UTILITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-utility-bridge-spec-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if positioning.get("connectedProduct") != "Web3 Radar non-custodial quant risk toolkit":
        raise SiteCheckError(f"{label}: wrong connectedProduct")
    if "read-only ERC-20 balance checks" not in " ".join(payload.get("bridgePrinciples", [])):
        raise SiteCheckError(f"{label}: missing read-only verification principle")
    if holder_bonus.get("minimumHolding") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder bonus minimum")
    if holder_bonus.get("creditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong holder bonus credit amount")
    if "risk-control bypass" not in holder_bonus.get("notCreditUse", ""):
        raise SiteCheckError(f"{label}: missing holder bonus risk boundary")
    if member.get("minimumHolding") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member minimum")
    if member.get("minimumHoldingPeriod") != "30 consecutive days":
        raise SiteCheckError(f"{label}: wrong member holding period")
    if member.get("memberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    if "higher utility credit limits" not in member.get("memberAccess", ""):
        raise SiteCheckError(f"{label}: missing member access scope")
    for item in ("custody", "withdrawal permission", "exchange API secret collection", "platform revenue distribution", "return promise", "risk-control bypass"):
        if item not in payload.get("notUtility", []):
            raise SiteCheckError(f"{label}: missing notUtility item {item}")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if links.get("utilityPage") != UTILITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong utilityPage")
    if links.get("utilityJson") != UTILITY_URL:
        raise SiteCheckError(f"{label}: wrong utilityJson")
    if links.get("creditsCatalogPage") != CREDITS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalogPage")
    if links.get("creditsCatalog") != CREDITS_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalog")
    if links.get("accessPortalPage") != ACCESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessPortalPage")
    if links.get("accessPortal") != ACCESS_URL:
        raise SiteCheckError(f"{label}: wrong accessPortal")
    if links.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if links.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if "GCA has published a public utility bridge specification." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing utility safe claim")
    if not any("credits or member status are cash" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing credit/member boundary")
    if not any("10,000 GCA member benefit is self-service claimable" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing member benefit boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_product_page(text: str) -> None:
    label = "/product.html"
    assert_contains(text, "GCA AI Quant Access Product Spec", label)
    assert_contains(text, "Product JSON", label)
    assert_contains(text, "Access Portal", label)
    assert_contains(text, "Access API", label)
    assert_contains(text, "Release Gates", label)
    assert_contains(text, "Credits Catalog", label)
    assert_contains(text, "public product spec only", label)
    assert_contains(text, "not a live trading terminal", label)
    assert_contains(text, "not live market data", label)
    assert_contains(text, "not financial advice", label)
    assert_contains(text, "Public Account UI", label)
    assert_contains(text, "Not live", label)
    assert_contains(text, "China Narrative Radar", label)
    assert_contains(text, "Weekly Go China Radar", label)
    assert_contains(text, "Liquidation Replay", label)
    assert_contains(text, "Risk Warning Credits", label)
    assert_contains(text, "Backtest Lab", label)
    assert_contains(text, "ENTRY_READY Review", label)
    assert_contains(text, "Position Size Calculator", label)
    assert_contains(text, "GCA Member Workspace", label)
    assert_contains(text, "simulation or testnet first", label)
    assert_contains(text, "No custody", label)
    assert_contains(text, "no withdrawal permission", label)
    assert_contains(text, "exchange API secret collection", label)
    assert_contains(text, "10,000 GCA", label)
    assert_contains(text, "100 utility credits", label)
    assert_contains(text, "1,000,000 GCA", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_product_json(text: str) -> None:
    label = "/product.json"
    payload = load_json(text, label)
    positioning = payload.get("positioning", {})
    modules = payload.get("productModules", [])
    module_names = {item.get("name") for item in modules}
    release_gate_ids = {item.get("id") for item in payload.get("releaseGates", [])}
    access = payload.get("gcaAccessRules", {})
    safety = payload.get("safetyArchitecture", {})
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != PRODUCT_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-product-spec-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if positioning.get("productName") != "GCA AI Quant Access":
        raise SiteCheckError(f"{label}: wrong productName")
    if positioning.get("currentStage") != "public-product-spec-only":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if positioning.get("publicAccountUiLive") is not False:
        raise SiteCheckError(f"{label}: publicAccountUiLive must be false")
    if positioning.get("liveTradingEnabled") is not False:
        raise SiteCheckError(f"{label}: liveTradingEnabled must be false")
    for name in (
        "China Narrative Radar",
        "Weekly Go China Radar",
        "Liquidation Replay",
        "Risk Warning Credits",
        "Backtest Lab",
        "ENTRY_READY Review",
        "Position Size Calculator",
        "GCA Member Workspace",
    ):
        if name not in module_names:
            raise SiteCheckError(f"{label}: missing module {name}")
    for gate in ("controlled-https-account-ui", "read-only-wallet-verification", "credit-ledger-activation", "member-ledger-activation", "risk-control-review", "simulation-first"):
        if gate not in release_gate_ids:
            raise SiteCheckError(f"{label}: missing release gate {gate}")
    if "access-portal-blueprint" not in release_gate_ids:
        raise SiteCheckError(f"{label}: missing access portal blueprint gate")
    if "access-api-contract" not in release_gate_ids:
        raise SiteCheckError(f"{label}: missing access API contract gate")
    if "review-queue-contract" not in release_gate_ids:
        raise SiteCheckError(f"{label}: missing review queue contract gate")
    if access.get("holderBonusMinimum") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder bonus minimum")
    if access.get("holderBonusCreditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong holder bonus credit")
    if access.get("gcaMemberMinimum") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member minimum")
    if access.get("gcaMemberMinimumHoldingDays") != 30:
        raise SiteCheckError(f"{label}: wrong member holding days")
    if access.get("gcaMemberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    for key in (
        "custody",
        "withdrawalPermission",
        "privateKeyCollection",
        "seedPhraseCollection",
        "exchangeApiSecretCollection",
        "automaticLiveTradingEnabled",
        "riskControlBypassAllowed",
        "productionExchangeConnection",
    ):
        if safety.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    for key in (
        "simulationFirstRequired",
        "uniqueClientOrderIdRequiredBeforeAnyFutureOrderFlow",
        "riskCheckRequiredBeforeAnyFutureOrderFlow",
    ):
        if safety.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if market.get("liquidityDepth") != "starter-depth-only":
        raise SiteCheckError(f"{label}: wrong liquidityDepth")
    if links.get("productPage") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong productPage")
    if links.get("productJson") != PRODUCT_URL:
        raise SiteCheckError(f"{label}: wrong productJson")
    if links.get("releaseGatesPage") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong releaseGatesPage")
    if links.get("releaseGates") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates")
    if links.get("creditsCatalogPage") != CREDITS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalogPage")
    if links.get("creditsCatalog") != CREDITS_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalog")
    if links.get("accessPortalPage") != ACCESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessPortalPage")
    if links.get("accessPortal") != ACCESS_URL:
        raise SiteCheckError(f"{label}: wrong accessPortal")
    if links.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if links.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if links.get("reviewQueuePage") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueuePage")
    if links.get("reviewQueue") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueue")
    if links.get("utilityJson") != UTILITY_URL:
        raise SiteCheckError(f"{label}: wrong utilityJson")
    if links.get("memberLedger") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedger")
    if "GCA has published a public product specification for GCA AI Quant Access." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing product safe claim")
    if not any("full GCA AI Quant Access product is live" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing product live boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_access_page(text: str) -> None:
    label = "/access.html"
    assert_contains(text, "GCA Access Portal Blueprint", label)
    assert_contains(text, "Access Portal JSON", label)
    assert_contains(text, "Access API", label)
    assert_contains(text, "Review Queue", label)
    assert_contains(text, "blueprint only", label)
    assert_contains(text, "controlled HTTPS account UI is not live", label)
    assert_contains(text, "direct submission is not connected", label)
    assert_contains(text, "credits are not self-service claimable", label)
    assert_contains(text, "GCA Member status is not self-service claimable", label)
    assert_contains(text, "10,000 GCA member benefit is not self-service claimable", label)
    assert_contains(text, "read-only wallet verification", label)
    assert_contains(text, "eth_call", label)
    assert_contains(text, "balanceOf", label)
    assert_contains(text, "10,000 GCA", label)
    assert_contains(text, "100 Web3 Radar utility credits", label)
    assert_contains(text, "1,000,000 GCA", label)
    assert_contains(text, "30 consecutive days", label)
    assert_contains(text, "GCA Member", label)
    assert_contains(text, "credit ledger activation", label)
    assert_contains(text, "member ledger activation", label)
    assert_contains(text, "support review queue", label)
    assert_contains(text, "Review Queue Contract", label)
    assert_contains(text, "Operations JSON", label)
    assert_contains(text, "Liquidation Replay", label)
    assert_contains(text, "Risk Warning Review", label)
    assert_contains(text, "Backtest Lab", label)
    assert_contains(text, "ENTRY_READY Review", label)
    assert_contains(text, "Position Size Calculator", label)
    assert_contains(text, "Risk-Control Training", label)
    assert_contains(text, "Member Research Notes", label)
    assert_contains(text, "Support Review Queue", label)
    assert_contains(text, "No custody", label)
    assert_contains(text, "No withdrawal permission", label)
    assert_contains(text, "No exchange API secret collection", label)
    assert_contains(text, "No private key or seed phrase collection", label)
    assert_contains(text, "gca/member-access/", label)
    assert_contains(text, "review-queue.json", label)
    assert_contains(text, "members.html", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_access_json(text: str) -> None:
    label = "/access.json"
    payload = load_json(text, label)
    state = payload.get("currentState", {})
    routes = payload.get("preparedRoutes", {})
    preview = payload.get("publicPreview", {})
    journey_ids = {item.get("id") for item in payload.get("userJourney", [])}
    thresholds = payload.get("eligibilityThresholds", {})
    controls = payload.get("requiredControls", [])
    security = payload.get("securityBoundaries", {})
    modules = set(payload.get("serviceModules", []))
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != ACCESS_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != ACCESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-access-portal-blueprint-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if state.get("currentStage") != "blueprint-only":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("blueprintOnly") is not True:
        raise SiteCheckError(f"{label}: blueprintOnly must be true")
    if state.get("reviewQueueContract") != "published-manual-review-contract":
        raise SiteCheckError(f"{label}: wrong reviewQueueContract")
    for key in (
        "controlledHttpsAccountUiLive",
        "directSubmissionEndpointConfigured",
        "creditsSelfServiceClaimable",
        "gcaMemberSelfServiceClaimable",
        "liveTradingEnabled",
    ):
        if state.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    for key in ("futureAccountPortal", "preRegistrations", "walletVerifications", "creditLedger", "memberLedger", "supportReview"):
        if key not in routes:
            raise SiteCheckError(f"{label}: missing route {key}")
    if preview.get("memberAccessPreview") != "https://gcagochina.com/gca/member-access/":
        raise SiteCheckError(f"{label}: wrong memberAccessPreview")
    if preview.get("memberPreRegistrationPage") != "https://gcagochina.com/members.html":
        raise SiteCheckError(f"{label}: wrong memberPreRegistrationPage")
    for journey_id in (
        "controlled-account",
        "read-only-wallet-verification",
        "support-review-record",
        "credit-ledger-activation",
        "member-ledger-activation",
        "service-access",
    ):
        if journey_id not in journey_ids:
            raise SiteCheckError(f"{label}: missing journey {journey_id}")
    if thresholds.get("holderBonus", {}).get("minimumHolding") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder minimum")
    if thresholds.get("holderBonus", {}).get("creditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong credit amount")
    if thresholds.get("holderBonus", {}).get("notLive") is not True:
        raise SiteCheckError(f"{label}: holder path must be not live")
    if thresholds.get("gcaMember", {}).get("minimumHolding") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member minimum")
    if thresholds.get("gcaMember", {}).get("minimumHoldingPeriod") != "30 consecutive days":
        raise SiteCheckError(f"{label}: wrong member holding period")
    if thresholds.get("gcaMember", {}).get("memberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    if thresholds.get("gcaMember", {}).get("notLive") is not True:
        raise SiteCheckError(f"{label}: member path must be not live")
    for item in (
        "controlled HTTPS account UI",
        "read-only GCA balance verification",
        "credit ledger activation",
        "member ledger activation",
        "support review queue",
        "review queue contract",
        "privacy notice and participation terms",
        "risk-control review",
        "simulation or testnet first for any future trading workflow",
    ):
        if item not in controls:
            raise SiteCheckError(f"{label}: missing required control {item}")
    for key in ("readOnlyWalletVerification", "usesEthCall", "usesErc20BalanceOf"):
        if security.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    for key in (
        "requiresSignatureForBalanceRead",
        "requiresTransactionForBalanceRead",
        "custody",
        "withdrawalPermission",
        "privateKeyCollection",
        "seedPhraseCollection",
        "exchangeApiSecretCollection",
        "automaticLiveTradingEnabled",
        "riskControlBypassAllowed",
    ):
        if security.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    for module in (
        "Liquidation Replay",
        "Risk Warning Review",
        "Backtest Lab",
        "ENTRY_READY Review",
        "Position Size Calculator",
        "Risk-Control Training",
        "Member Research Notes",
        "Support Review Queue",
    ):
        if module not in modules:
            raise SiteCheckError(f"{label}: missing service module {module}")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if links.get("accessPortalPage") != ACCESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessPortalPage")
    if links.get("accessPortal") != ACCESS_URL:
        raise SiteCheckError(f"{label}: wrong accessPortal")
    if links.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if links.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if links.get("reviewQueuePage") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueuePage")
    if links.get("reviewQueue") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueue")
    if links.get("operationsRunbookPage") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbookPage")
    if links.get("operationsRunbook") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbook")
    if links.get("creditsCatalog") != CREDITS_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalog")
    if links.get("releaseGates") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates")
    if links.get("memberLedger") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedger")
    if links.get("supportJson") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong supportJson")
    if "GCA has published a public access portal blueprint." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing access safe claim")
    if not any("live self-service account UI" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing account UI boundary")
    if not any("cash, income" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing credit value boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_operations_page(text: str) -> None:
    label = "/operations.html"
    assert_social_preview_meta(text, label, OPERATIONS_PAGE_URL)
    assert_contains(text, "GCA Access Operations Runbook", label)
    assert_contains(text, "Operations JSON", label)
    assert_contains(text, "operations runbook only", label)
    assert_contains(text, "not live today", label)
    assert_contains(text, "not a public submission queue", label)
    for step in (
        "Intake Triage",
        "Identity Check",
        "Wallet Balance Check",
        "Holding Period Review",
        "Eligibility Decision",
        "Support Reply",
        "Ledger Handoff",
        "Platform Follow-Up",
        "Review Package Handoff",
        "Closure",
    ):
        assert_contains(text, step, label)
    assert_contains(text, "Required Evidence", label)
    assert_contains(text, "Decision Rules", label)
    assert_contains(text, "eth_call", label)
    assert_contains(text, "balanceOf", label)
    assert_contains(text, "100 Web3 Radar utility credits", label)
    assert_contains(text, "GCA Member", label)
    assert_contains(text, "gca_member_preregistration_v2", label)
    assert_contains(text, "holdingStartDate", label)
    assert_contains(text, "evidenceTxHash", label)
    assert_contains(text, "evidenceTxHashFormatOk", label)
    assert_contains(text, "Member evidence note", label)
    assert_contains(text, "Local Review Package Handoff", label)
    assert_contains(text, "redacted-public", label)
    assert_contains(text, "packageDigestSha256", label)
    assert_contains(text, "tools/export_gca_review_package.py", label)
    assert_contains(text, "tools/verify_gca_review_package.py", label)
    assert_contains(text, "Manual support cannot override on-chain wallet-balance verification", label)
    assert_contains(text, "Private key or seed phrase", label)
    assert_contains(text, "Exchange API secret or withdrawal permission", label)
    assert_contains(text, "Custody request", label)
    assert_contains(text, "GCA/USDT", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_operations_json(text: str) -> None:
    label = "/operations.json"
    payload = load_json(text, label)
    state = payload.get("currentState", {})
    identity = payload.get("identity", {})
    workflow = payload.get("operatorWorkflow", [])
    workflow_ids = {item.get("id") for item in workflow}
    controls = payload.get("operatorControls", {})
    handoff = payload.get("reviewPackageHandoff", {})
    rules = payload.get("decisionRules", {})
    thresholds = payload.get("eligibilityThresholds", {})
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-access-operations-runbook-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if state.get("currentStage") != "public-operations-runbook-only":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("publicRunbookOnly") is not True:
        raise SiteCheckError(f"{label}: publicRunbookOnly must be true")
    for key in (
        "backendLive",
        "publicSubmissionQueueLive",
        "controlledHttpsAccountUiLive",
        "creditsSelfServiceClaimable",
        "gcaMemberSelfServiceClaimable",
        "ledgerWritesLive",
        "liveTradingEnabled",
    ):
        if state.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if identity.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong identity chainId")
    if identity.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong identity contractAddress")
    for workflow_id in (
        "intake-triage",
        "identity-check",
        "wallet-balance-check",
        "holding-period-review",
        "eligibility-decision",
        "support-reply",
        "ledger-handoff",
        "platform-follow-up",
        "review-package-handoff",
        "closure",
    ):
        if workflow_id not in workflow_ids:
            raise SiteCheckError(f"{label}: missing workflow {workflow_id}")
    for field in (
        "reviewId",
        "registrationId",
        "lane",
        "status",
        "walletAddress",
        "checkedAt",
        "holdingStartDate",
        "holdingPeriodDaysVerified",
        "holdingPeriodPreviewEligible",
        "evidenceTxHash",
        "evidenceTxHashFormatOk",
        "memberBenefitReviewEvidenceStatus",
        "reviewerNote",
        "publicEvidenceReference",
        "reviewPackageRedactionMode",
        "reviewPackageDigestSha256",
    ):
        if field not in payload.get("requiredReviewRecord", []):
            raise SiteCheckError(f"{label}: missing review record {field}")
        if field not in controls.get("requiredAuditFields", []):
            raise SiteCheckError(f"{label}: missing audit field {field}")
    for evidence in (
        "official account record",
        "public Base wallet address",
        "read-only GCA balance from eth_call balanceOf",
        "public transaction hash",
        "public purchase or transfer transaction hash used for holding-period review",
        "member holding start date from gca_member_preregistration_v2 packet",
        "0x-format evidence transaction hash check",
        "member evidence note",
        "non-sensitive support note",
        "public review reference",
        "public-redacted local review package digest",
    ):
        if evidence not in payload.get("allowedEvidence", []):
            raise SiteCheckError(f"{label}: missing allowed evidence {evidence}")
    for key in ("walletVerificationReadOnly", "usesEthCall", "usesErc20BalanceOf", "structuredAuditTrailRequired"):
        if controls.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    for key in ("externalReviewPackageMustBeRedacted", "reviewPackageDigestRequiredBeforeSharing"):
        if controls.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    for key in (
        "requiresSignatureForBalanceRead",
        "requiresTransactionForBalanceRead",
        "manualSupportCanOverrideBalanceVerification",
        "manualSupportCanBypassReleaseGates",
        "fullLocalPackageExternalSharingAllowed",
    ):
        if controls.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if controls.get("chainIdMustEqual") != 8453:
        raise SiteCheckError(f"{label}: wrong chain control")
    if controls.get("contractAddressMustEqual") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contract control")
    if payload.get("memberPacketVersion") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong member packet version")
    if handoff.get("externalSharingMode") != "redacted-public":
        raise SiteCheckError(f"{label}: wrong handoff external mode")
    if handoff.get("internalOnlyMode") != "full-local":
        raise SiteCheckError(f"{label}: wrong handoff internal mode")
    if handoff.get("localDataDirectory") != ".gca_access_data/":
        raise SiteCheckError(f"{label}: wrong handoff local data directory")
    if "tools/export_gca_review_package.py" not in handoff.get("exportCommand", ""):
        raise SiteCheckError(f"{label}: missing handoff export command")
    if "tools/verify_gca_review_package.py" not in handoff.get("verifyCommand", ""):
        raise SiteCheckError(f"{label}: missing handoff verify command")
    if handoff.get("replyTemplatePage") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong handoff template page")
    if "confirm package redactionMode is redacted-public" not in handoff.get("requiredBeforeSharing", []):
        raise SiteCheckError(f"{label}: missing handoff pre-share check")
    for field in (
        "memberBenefitReviewEvidence.holdingStartDate",
        "memberBenefitReviewEvidence.daysSinceHoldingStartPreview",
        "memberBenefitReviewEvidence.holdingPeriodPreviewEligible",
        "memberBenefitReviewEvidence.evidenceTxHash",
        "memberBenefitReviewEvidence.evidenceTxHashFormatOk",
        "memberBenefitReviewEvidence.evidenceNote",
    ):
        if field not in payload.get("memberEvidenceFields", []):
            raise SiteCheckError(f"{label}: missing member evidence field {field}")
    if controls.get("memberPacketVersionMustEqual") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong packet version control")
    if rules.get("holderBonusMinimum") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder bonus minimum")
    if rules.get("holderBonusCreditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong holder bonus amount")
    if rules.get("gcaMemberMinimum") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member minimum")
    if rules.get("gcaMemberMinimumHoldingDays") != 30:
        raise SiteCheckError(f"{label}: wrong member holding days")
    if rules.get("gcaMemberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    if rules.get("manualSupportCannotOverrideBalanceVerification") is not True:
        raise SiteCheckError(f"{label}: support override rule must be true")
    if thresholds.get("holderBonusMinimum") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong thresholds holder minimum")
    if thresholds.get("holderBonusCreditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong thresholds credit amount")
    if thresholds.get("gcaMemberMinimum") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong thresholds member minimum")
    if thresholds.get("gcaMemberMinimumHoldingDays") != 30:
        raise SiteCheckError(f"{label}: wrong thresholds member holding days")
    if thresholds.get("gcaMemberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong thresholds member benefit")
    for item in (
        "private key",
        "seed phrase",
        "exchange API secret",
        "withdrawal permission",
        "one-time code",
        "recovery phrase",
        "custody request",
        "fund-transfer request",
        "live trading instruction",
    ):
        if item not in payload.get("doNotCollect", []):
            raise SiteCheckError(f"{label}: missing doNotCollect {item}")
    for item in ("self-service credits claiming", "self-service GCA Member claiming", "live order execution"):
        if item not in payload.get("doNotClaim", []):
            raise SiteCheckError(f"{label}: missing doNotClaim {item}")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    for key, expected in (
        ("operationsRunbookPage", OPERATIONS_PAGE_URL),
        ("operationsRunbook", OPERATIONS_URL),
        ("reviewQueuePage", REVIEW_QUEUE_PAGE_URL),
        ("reviewQueue", REVIEW_QUEUE_URL),
        ("accessApiPage", ACCESS_API_PAGE_URL),
        ("accessApi", ACCESS_API_URL),
        ("memberLedger", MEMBER_LEDGER_URL),
        ("supportJson", SUPPORT_URL),
        ("releaseGates", RELEASE_GATES_URL),
        ("reviewerKitPage", REVIEWER_KIT_PAGE_URL),
        ("reviewerKit", REVIEWER_KIT_URL),
        ("platformRepliesPage", PLATFORM_REPLIES_PAGE_URL),
        ("platformReplies", PLATFORM_REPLIES_URL),
    ):
        if links.get(key) != expected:
            raise SiteCheckError(f"{label}: wrong {key}")
    if "GCA has published a public access operations runbook." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing operations safe claim")
    if "GCA operators can export a redacted-public local review package for reviewer evidence handoff when local ledger records exist." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing review package safe claim")
    if not any("live backend" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing live backend boundary")
    if not any("support can override wallet-balance verification" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing support override boundary")
    if not any("redacted local review package" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing review package boundary")
    assert_current_pool_text(json.dumps(payload), label)
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_access_api_page(text: str) -> None:
    label = "/access-api.html"
    assert_contains(text, "GCA Access API Contract", label)
    assert_contains(text, "Access API JSON", label)
    assert_contains(text, "Review Queue", label)
    assert_contains(text, "Operations Runbook", label)
    assert_contains(text, "contract only", label)
    assert_contains(text, "not live today", label)
    assert_contains(text, "not a public submission endpoint", label)
    assert_contains(text, "tools/gca_member_backend.py", label)
    assert_contains(text, "tools/export_gca_review_package.py", label)
    assert_contains(text, "operator.html", label)
    assert_contains(text, "/gca/operator-summary", label)
    assert_contains(text, "local JSONL ledger records", label)
    assert_contains(text, "POST", label)
    assert_contains(text, "/gca/pre-registrations", label)
    assert_contains(text, "/gca/wallet-verifications", label)
    assert_contains(text, "/gca/credit-ledger", label)
    assert_contains(text, "/gca/member-ledger", label)
    assert_contains(text, "/gca/support-review", label)
    assert_contains(text, "/gca/member-review", label)
    assert_contains(text, "/gca/member-benefit-transfers", label)
    assert_contains(text, "eth_call", label)
    assert_contains(text, "/gca/review-package", label)
    assert_contains(text, "?redact=public", label)
    assert_contains(text, "packageDigestSha256", label)
    assert_contains(text, "recordManifest", label)
    assert_contains(text, "tools/verify_gca_review_package.py", label)
    assert_contains(text, "tools/export_gca_review_package.py", label)
    assert_contains(text, "reviewer evidence", label)
    assert_contains(text, "read-only Base receipt data", label)
    assert_contains(text, "balanceOf", label)
    assert_contains(text, "100 Web3 Radar utility credits", label)
    assert_contains(text, "GCA Member", label)
    assert_contains(text, "gca_member_preregistration_v2", label)
    assert_contains(text, "memberBenefitReviewEvidence", label)
    assert_contains(text, "holdingStartDate", label)
    assert_contains(text, "evidenceTxHash", label)
    assert_contains(text, "evidenceTxHashFormatOk", label)
    assert_contains(text, "controlled HTTPS origin", label)
    assert_contains(text, "authenticated account session", label)
    assert_contains(text, "CSRF protection", label)
    assert_contains(text, "rate limits", label)
    assert_contains(text, "structured audit logs", label)
    assert_contains(text, "Private key or seed phrase", label)
    assert_contains(text, "Exchange API secret", label)
    assert_contains(text, "Withdrawal permission", label)
    assert_contains(text, "Custody request", label)
    assert_contains(text, "review-queue.json", label)
    assert_contains(text, "operations.json", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_access_api_json(text: str) -> None:
    label = "/access-api.json"
    payload = load_json(text, label)
    state = payload.get("currentState", {})
    local_backend = payload.get("localDevelopmentBackend", {})
    security = payload.get("securityModel", {})
    endpoints = payload.get("endpoints", [])
    endpoint_map = {f"{item.get('method')} {item.get('path')}": item for item in endpoints}
    thresholds = payload.get("eligibilityThresholds", {})
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-access-api-contract-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if state.get("currentStage") != "contract-only":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("contractOnly") is not True:
        raise SiteCheckError(f"{label}: contractOnly must be true")
    if state.get("reviewQueueContract") != "published-manual-review-contract":
        raise SiteCheckError(f"{label}: wrong reviewQueueContract")
    if state.get("memberPacketVersion") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong member packet version")
    if state.get("localDevelopmentBackendAvailable") is not True:
        raise SiteCheckError(f"{label}: local development backend should be available")
    for key in (
        "backendLive",
        "publicEndpointLive",
        "controlledHttpsAccountUiLive",
        "directSubmissionEndpointConfigured",
        "creditsSelfServiceClaimable",
        "gcaMemberSelfServiceClaimable",
        "liveTradingEnabled",
    ):
        if state.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if local_backend.get("status") != "local-only-backend-available":
        raise SiteCheckError(f"{label}: wrong local backend status")
    if local_backend.get("script") != "tools/gca_member_backend.py":
        raise SiteCheckError(f"{label}: wrong local backend script")
    if local_backend.get("localUrl") != "http://127.0.0.1:8787/members.html":
        raise SiteCheckError(f"{label}: wrong local backend URL")
    if local_backend.get("operatorConsoleUrl") != "http://127.0.0.1:8787/operator.html":
        raise SiteCheckError(f"{label}: wrong local operator console URL")
    if local_backend.get("dataDirectory") != ".gca_access_data/":
        raise SiteCheckError(f"{label}: wrong local backend data directory")
    if local_backend.get("sameOriginSubmissionOnLocalhost") is not True:
        raise SiteCheckError(f"{label}: local backend should use same-origin localhost submissions")
    if local_backend.get("localOperatorSummaryEndpoint") != "/gca/operator-summary":
        raise SiteCheckError(f"{label}: wrong local operator summary endpoint")
    if local_backend.get("localReviewPackageEndpoint") != "/gca/review-package":
        raise SiteCheckError(f"{label}: wrong local review package endpoint")
    if local_backend.get("localReviewPackageExporter") != "tools/export_gca_review_package.py":
        raise SiteCheckError(f"{label}: wrong local review package exporter")
    if local_backend.get("localReviewPackageVerifier") != "tools/verify_gca_review_package.py":
        raise SiteCheckError(f"{label}: wrong local review package verifier")
    if "redacted-public" not in local_backend.get("localReviewPackageRedactionModes", []):
        raise SiteCheckError(f"{label}: missing local review package redaction mode")
    if local_backend.get("publicProductionEndpointLive") is not False:
        raise SiteCheckError(f"{label}: local backend must not mark production live")
    if local_backend.get("automaticTokenTransfer") is not False:
        raise SiteCheckError(f"{label}: local backend must not automatically transfer tokens")
    for ledger in ("pre_registrations", "wallet_verifications", "credit_ledger", "member_ledger", "member_benefit_transfers", "support_reviews"):
        if ledger not in local_backend.get("writesJsonlLedgers", []):
            raise SiteCheckError(f"{label}: missing local ledger {ledger}")
    for key in (
        "controlledHttpsOriginRequired",
        "authenticatedAccountSessionRequired",
        "csrfProtectionRequiredForStateChangingRoutes",
        "rateLimitsRequired",
        "structuredAuditLogsRequired",
        "serverSideChainValidationRequired",
        "serverSideContractValidationRequired",
        "walletVerificationReadOnly",
        "usesEthCall",
        "usesEthGetTransactionReceipt",
        "usesErc20BalanceOf",
    ):
        if security.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    for key in (
        "requiresSignatureForBalanceRead",
        "requiresTransactionForBalanceRead",
        "custody",
        "withdrawalPermission",
        "privateKeyCollection",
        "seedPhraseCollection",
        "exchangeApiSecretCollection",
        "automaticLiveTradingEnabled",
        "riskControlBypassAllowed",
    ):
        if security.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    for endpoint_key in (
        "POST /gca/pre-registrations",
        "POST /gca/wallet-verifications",
        "GET /gca/credit-ledger",
        "GET /gca/member-ledger",
        "POST /gca/support-review",
        "GET /gca/member-review",
    ):
        endpoint = endpoint_map.get(endpoint_key)
        if endpoint is None:
            raise SiteCheckError(f"{label}: missing endpoint {endpoint_key}")
        if endpoint.get("status") != "planned-not-live":
            raise SiteCheckError(f"{label}: endpoint {endpoint_key} should be planned-not-live")
    operator_summary = endpoint_map.get("GET /gca/operator-summary")
    if operator_summary is None:
        raise SiteCheckError(f"{label}: missing operator summary endpoint")
    if operator_summary.get("status") != "local-only-not-public-production":
        raise SiteCheckError(f"{label}: wrong operator summary endpoint status")
    if "publicSelfServiceClaim" not in operator_summary.get("responseFields", []):
        raise SiteCheckError(f"{label}: missing operator summary claim boundary")
    review_package = endpoint_map.get("GET /gca/review-package")
    if review_package is None:
        raise SiteCheckError(f"{label}: missing review package endpoint")
    if review_package.get("status") != "local-only-not-public-production":
        raise SiteCheckError(f"{label}: wrong review package endpoint status")
    if review_package.get("verificationTool") != "tools/verify_gca_review_package.py":
        raise SiteCheckError(f"{label}: wrong review package verification tool")
    if review_package.get("exportTool") != "tools/export_gca_review_package.py":
        raise SiteCheckError(f"{label}: wrong review package export tool")
    for expected_field in (
        "packageDigestAlgorithm",
        "packageDigestSha256",
        "recordManifest",
        "operatorSummary",
        "exportBoundaries",
        "publicReferences",
        "reviewChecklist",
    ):
        if expected_field not in review_package.get("responseFields", []):
            raise SiteCheckError(f"{label}: missing review package field {expected_field}")
    for expected_field in ("redactedForExternalSharing", "redactionPolicy"):
        if expected_field not in review_package.get("responseFields", []):
            raise SiteCheckError(f"{label}: missing review package redaction field {expected_field}")
    if "redact=public" not in review_package.get("optionalRequestFields", []):
        raise SiteCheckError(f"{label}: missing review package redaction option")
    redaction_policy = review_package.get("redactionPolicy", {})
    if redaction_policy.get("publicMode") != "redact=public":
        raise SiteCheckError(f"{label}: wrong review package redaction public mode")
    for expected_field in ("email", "telegram", "reviewerNote", "supportNote", "evidenceNote"):
        if expected_field not in redaction_policy.get("redactedFields", []):
            raise SiteCheckError(f"{label}: missing redacted field {expected_field}")
    for endpoint_key in ("GET /gca/member-benefit-transfers", "POST /gca/member-benefit-transfers"):
        endpoint = endpoint_map.get(endpoint_key)
        if endpoint is None:
            raise SiteCheckError(f"{label}: missing endpoint {endpoint_key}")
        if endpoint.get("status") != "local-only-not-public-production":
            raise SiteCheckError(f"{label}: endpoint {endpoint_key} should be local-only")
    transfer_create = endpoint_map["POST /gca/member-benefit-transfers"]
    if "memberBenefitTransferTx" not in transfer_create.get("requiredRequestFields", []):
        raise SiteCheckError(f"{label}: missing transfer tx field")
    for expected_check in (
        "eth_getTransactionReceipt is read-only",
        "receipt must contain a successful GCA Transfer log to recipientWallet",
        "matched transfer amount must be at least 10000 GCA",
    ):
        if expected_check not in transfer_create.get("serverChecks", []):
            raise SiteCheckError(f"{label}: missing transfer receipt check {expected_check}")
    if "alreadyRecorded" not in transfer_create.get("responseFields", []):
        raise SiteCheckError(f"{label}: missing transfer idempotency field")
    transfer_read = endpoint_map["GET /gca/member-benefit-transfers"]
    if "transferVerificationStatus" not in transfer_read.get("responseFields", []):
        raise SiteCheckError(f"{label}: missing transfer verification status field")
    if "transferVerification" not in transfer_read.get("responseFields", []):
        raise SiteCheckError(f"{label}: missing transfer verification evidence field")
    wallet = endpoint_map["POST /gca/wallet-verifications"]
    if "chainId must be 8453" not in wallet.get("serverChecks", []):
        raise SiteCheckError(f"{label}: missing chain check")
    if not any(MAINNET_ADDRESS in item for item in wallet.get("serverChecks", [])):
        raise SiteCheckError(f"{label}: missing contract check")
    if "balance source must be read-only eth_call balanceOf" not in wallet.get("serverChecks", []):
        raise SiteCheckError(f"{label}: missing balance source check")
    if payload.get("memberPacketVersion") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong top-level member packet version")
    for field in (
        "memberBenefitReviewEvidence.holdingStartDate",
        "memberBenefitReviewEvidence.daysSinceHoldingStartPreview",
        "memberBenefitReviewEvidence.holdingPeriodPreviewEligible",
        "memberBenefitReviewEvidence.evidenceTxHash",
        "memberBenefitReviewEvidence.evidenceTxHashFormatOk",
        "memberBenefitReviewEvidence.evidenceNote",
    ):
        if field not in payload.get("memberEvidenceFields", []):
            raise SiteCheckError(f"{label}: missing member evidence field {field}")
    prereg = endpoint_map["POST /gca/pre-registrations"]
    for field in (
        "memberBenefitReviewEvidence",
        "memberBenefitReviewEvidence.holdingStartDate",
        "memberBenefitReviewEvidence.evidenceTxHash",
        "memberBenefitReviewEvidence.evidenceTxHashFormatOk",
    ):
        if field not in prereg.get("optionalRequestFields", []):
            raise SiteCheckError(f"{label}: missing pre-registration optional field {field}")
    member_ledger = endpoint_map["GET /gca/member-ledger"]
    for field in (
        "holdingStartDate",
        "evidenceTxHash",
        "evidenceTxHashFormatOk",
        "memberBenefitReviewEvidenceStatus",
        "memberBenefitTransferTx",
    ):
        if field not in member_ledger.get("responseFields", []):
            raise SiteCheckError(f"{label}: missing member ledger response field {field}")
    member_review = endpoint_map["GET /gca/member-review"]
    for field in ("holdingStartDate", "evidenceTxHashFormatOk", "memberBenefitClaimStatus"):
        if field not in member_review.get("responseFields", []):
            raise SiteCheckError(f"{label}: missing member review response field {field}")
    support_review = endpoint_map["POST /gca/support-review"]
    for field in ("publicEvidenceReference", "memberBenefitReviewEvidence"):
        if field not in support_review.get("requiredRequestFields", []):
            raise SiteCheckError(f"{label}: missing support review request field {field}")
    if thresholds.get("holderBonusMinimum") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holderBonusMinimum")
    if thresholds.get("holderBonusCreditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong holderBonusCreditAmount")
    if thresholds.get("gcaMemberMinimum") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong gcaMemberMinimum")
    if thresholds.get("gcaMemberMinimumHoldingDays") != 30:
        raise SiteCheckError(f"{label}: wrong gcaMemberMinimumHoldingDays")
    if thresholds.get("gcaMemberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong gcaMemberBenefitAmount")
    for forbidden in ("private key", "seed phrase", "exchange API secret", "withdrawal permission", "custody request", "one-time code"):
        if forbidden not in payload.get("doNotCollect", []):
            raise SiteCheckError(f"{label}: missing doNotCollect {forbidden}")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if links.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if links.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if links.get("accessPortal") != ACCESS_URL:
        raise SiteCheckError(f"{label}: wrong accessPortal")
    if links.get("memberLedger") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedger")
    if links.get("supportJson") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong supportJson")
    if links.get("reviewQueuePage") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueuePage")
    if links.get("reviewQueue") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueue")
    if links.get("operationsRunbookPage") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbookPage")
    if links.get("operationsRunbook") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbook")
    if "GCA has published a public access API contract." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing API safe claim")
    if not any("live public submission infrastructure" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing live API boundary")
    if not any("private keys, seed phrases" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing sensitive data boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_review_queue_page(text: str) -> None:
    label = "/review-queue.html"
    assert_contains(text, "GCA Review Queue Contract", label)
    assert_contains(text, "Review Queue JSON", label)
    assert_contains(text, "Operations Runbook", label)
    assert_contains(text, "manual review contract", label)
    assert_contains(text, "not live today", label)
    assert_contains(text, "not a public submission queue", label)
    for lane in (
        "Pre-Registration Intake",
        "Wallet Balance Review",
        "Holder Credit Review",
        "GCA Member Review",
        "Support Case Review",
        "Platform Profile Follow-Up",
    ):
        assert_contains(text, lane, label)
    for status in (
        "Received",
        "Wallet pending",
        "Eligible",
        "Below threshold",
        "Needs more information",
        "Ledger recorded",
        "Closed",
    ):
        assert_contains(text, status, label)
    assert_contains(text, "eth_call", label)
    assert_contains(text, "balanceOf", label)
    assert_contains(text, "100 Web3 Radar utility credits", label)
    assert_contains(text, "GCA Member", label)
    assert_contains(text, "gca_member_preregistration_v2", label)
    assert_contains(text, "holdingStartDate", label)
    assert_contains(text, "evidenceTxHash", label)
    assert_contains(text, "evidenceTxHashFormatOk", label)
    assert_contains(text, "Member evidence note", label)
    assert_contains(text, "Manual support cannot override on-chain wallet-balance verification", label)
    assert_contains(text, "Private key or seed phrase", label)
    assert_contains(text, "Exchange API secret", label)
    assert_contains(text, "withdrawal permission", label)
    assert_contains(text, "Custody request", label)
    assert_contains(text, "operations.json", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_review_queue_json(text: str) -> None:
    label = "/review-queue.json"
    payload = load_json(text, label)
    state = payload.get("currentState", {})
    identity = payload.get("identity", {})
    lanes = payload.get("reviewLanes", [])
    lane_ids = {item.get("id") for item in lanes}
    controls = payload.get("operatorControls", {})
    thresholds = payload.get("eligibilityThresholds", {})
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-review-queue-contract-published":
        raise SiteCheckError(f"{label}: wrong status")
    if state.get("currentStage") != "manual-review-contract":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("memberPacketVersion") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong member packet version")
    if state.get("contractOnly") is not True:
        raise SiteCheckError(f"{label}: contractOnly must be true")
    for key in (
        "publicQueueLive",
        "publicSubmissionQueueLive",
        "controlledHttpsAccountUiLive",
        "creditsSelfServiceClaimable",
        "gcaMemberSelfServiceClaimable",
        "ledgerWritesLive",
        "liveTradingEnabled",
    ):
        if state.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if identity.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if identity.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    for lane_id in (
        "pre-registration-intake",
        "wallet-balance-review",
        "holder-credit-review",
        "gca-member-review",
        "support-case-review",
        "platform-profile-follow-up",
    ):
        if lane_id not in lane_ids:
            raise SiteCheckError(f"{label}: missing lane {lane_id}")
    if controls.get("chainIdMustEqual") != 8453:
        raise SiteCheckError(f"{label}: wrong chain control")
    if controls.get("contractAddressMustEqual") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contract control")
    for key in ("walletVerificationReadOnly", "usesEthCall", "usesErc20BalanceOf", "structuredAuditTrailRequired"):
        if controls.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    for key in (
        "requiresSignatureForBalanceRead",
        "requiresTransactionForBalanceRead",
        "manualSupportCanOverrideBalanceVerification",
    ):
        if controls.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    for field in (
        "reviewId",
        "registrationId",
        "lane",
        "status",
        "updatedAt",
        "holdingStartDate",
        "holdingPeriodDaysVerified",
        "evidenceTxHash",
        "evidenceTxHashFormatOk",
        "memberBenefitReviewEvidenceStatus",
        "reviewerNote",
        "publicEvidenceReference",
    ):
        if field not in controls.get("requiredAuditFields", []):
            raise SiteCheckError(f"{label}: missing audit field {field}")
    if controls.get("memberPacketVersionMustEqual") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong packet version control")
    for evidence in (
        "public purchase or transfer transaction hash used for 30-day holding-period review",
        "member holding start date from gca_member_preregistration_v2 packet",
        "0x-format evidence transaction hash check",
        "member evidence note",
    ):
        if evidence not in payload.get("allowedEvidence", []):
            raise SiteCheckError(f"{label}: missing allowed evidence {evidence}")
    if thresholds.get("holderBonusMinimum") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder threshold")
    if thresholds.get("holderBonusCreditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong credit amount")
    if thresholds.get("gcaMemberMinimum") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member threshold")
    if thresholds.get("gcaMemberMinimumHoldingDays") != 30:
        raise SiteCheckError(f"{label}: wrong member holding days")
    if thresholds.get("gcaMemberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    member_evidence = payload.get("memberBenefitReviewEvidence", {})
    if member_evidence.get("packetVersion") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong member evidence packet version")
    if member_evidence.get("status") != "user_supplied_pending_review":
        raise SiteCheckError(f"{label}: wrong member evidence status")
    for field in (
        "holdingStartDate",
        "daysSinceHoldingStartPreview",
        "holdingPeriodPreviewEligible",
        "evidenceTxHash",
        "evidenceTxHashFormatOk",
        "evidenceNote",
    ):
        if field not in member_evidence.get("requiredFields", []):
            raise SiteCheckError(f"{label}: missing required member evidence field {field}")
    if member_evidence.get("finalEligibilityStillRequiresSupportAndLedgerReview") is not True:
        raise SiteCheckError(f"{label}: member evidence must require final review")
    if member_evidence.get("doesNotCreateLedgerRecord") is not True:
        raise SiteCheckError(f"{label}: member evidence must not create ledger")
    for item in ("private key", "seed phrase", "exchange API secret", "withdrawal permission", "custody request"):
        if item not in payload.get("doNotCollect", []):
            raise SiteCheckError(f"{label}: missing doNotCollect {item}")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    for key, expected in (
        ("reviewQueuePage", REVIEW_QUEUE_PAGE_URL),
        ("reviewQueue", REVIEW_QUEUE_URL),
        ("accessApiPage", ACCESS_API_PAGE_URL),
        ("accessApi", ACCESS_API_URL),
        ("memberLedger", MEMBER_LEDGER_URL),
        ("supportJson", SUPPORT_URL),
        ("releaseGates", RELEASE_GATES_URL),
        ("operationsRunbookPage", OPERATIONS_PAGE_URL),
        ("operationsRunbook", OPERATIONS_URL),
    ):
        if links.get(key) != expected:
            raise SiteCheckError(f"{label}: wrong {key}")
    if "GCA has published a public review queue contract." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing safe claim")
    if not any("support can override wallet-balance verification" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing override boundary")
    assert_current_pool_text(json.dumps(payload), label)
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_credits_page(text: str) -> None:
    label = "/credits.html"
    assert_contains(text, "GCA Utility Credits Catalog", label)
    assert_contains(text, "Credits Catalog JSON", label)
    assert_contains(text, "Access Portal", label)
    assert_contains(text, "Access API", label)
    assert_contains(text, "draft service catalog", label)
    assert_contains(text, "not self-service claimable", label)
    assert_contains(text, "100 Web3 Radar utility credits", label)
    assert_contains(text, "10,000 GCA", label)
    assert_contains(text, "1,000,000 GCA", label)
    assert_contains(text, "Liquidation Replay", label)
    assert_contains(text, "Risk Warning Review", label)
    assert_contains(text, "Backtest Lab", label)
    assert_contains(text, "ENTRY_READY Review", label)
    assert_contains(text, "Position Size Calculator", label)
    assert_contains(text, "Risk-Control Training", label)
    assert_contains(text, "Member Research Notes", label)
    assert_contains(text, "Support Review Queue", label)
    assert_contains(text, "controlled HTTPS account UI", label)
    assert_contains(text, "read-only GCA balance verification", label)
    assert_contains(text, "credit ledger activation", label)
    assert_contains(text, "member ledger activation", label)
    assert_contains(text, "support review queue", label)
    assert_contains(text, "No custody", label)
    assert_contains(text, "No withdrawal permission", label)
    assert_contains(text, "No exchange API secret collection", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_credits_json(text: str) -> None:
    label = "/credits.json"
    payload = load_json(text, label)
    state = payload.get("currentState", {})
    holder_bonus = payload.get("holderBonus", {})
    member = payload.get("gcaMember", {})
    service_ids = {item.get("id") for item in payload.get("serviceCatalog", [])}
    service_names = {item.get("name") for item in payload.get("serviceCatalog", [])}
    redemption = payload.get("redemptionBoundaries", {})
    safety = payload.get("safetyArchitecture", {})
    release_gates = payload.get("releaseGates", {})
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != CREDITS_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != CREDITS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-credits-catalog-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if state.get("currentStage") != "draft-service-catalog-only":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("draftServiceCatalogOnly") is not True:
        raise SiteCheckError(f"{label}: draftServiceCatalogOnly must be true")
    for key in ("publicAccountUiLive", "creditsSelfServiceClaimable", "gcaMemberSelfServiceClaimable", "liveTradingEnabled"):
        if state.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if holder_bonus.get("minimumHolding") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder bonus minimum")
    if holder_bonus.get("creditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong holder bonus credit")
    if holder_bonus.get("notLive") is not True:
        raise SiteCheckError(f"{label}: holder bonus must be not live")
    if member.get("minimumHolding") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member minimum")
    if member.get("minimumHoldingPeriod") != "30 consecutive days":
        raise SiteCheckError(f"{label}: wrong member holding period")
    if member.get("memberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    if member.get("notLive") is not True:
        raise SiteCheckError(f"{label}: member must be not live")
    for service_id in (
        "liquidation-replay-report",
        "risk-warning-review",
        "backtest-lab-run",
        "entry-ready-review",
        "position-size-calculator",
        "risk-control-training",
        "member-research-notes",
        "support-review-queue",
    ):
        if service_id not in service_ids:
            raise SiteCheckError(f"{label}: missing service {service_id}")
    for service_name in (
        "Liquidation Replay",
        "Risk Warning Review",
        "Backtest Lab",
        "ENTRY_READY Review",
        "Position Size Calculator",
        "Risk-Control Training",
        "Member Research Notes",
        "Support Review Queue",
    ):
        if service_name not in service_names:
            raise SiteCheckError(f"{label}: missing service name {service_name}")
    for item in payload.get("serviceCatalog", []):
        if item.get("status") not in {"planned-controlled-account-ui-required", "planned-member-ledger-required"}:
            raise SiteCheckError(f"{label}: wrong service status for {item.get('id')}")
        if item.get("unitType") not in {"draft service credit unit", "draft member credit unit", "member workflow priority"}:
            raise SiteCheckError(f"{label}: wrong unitType for {item.get('id')}")
    for key in (
        "accountLevelOnly",
        "requiresControlledAccountUi",
        "requiresLedgerActivation",
        "requiresSupportReview",
    ):
        if redemption.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    for key in (
        "transferable",
        "cashEquivalent",
        "tokenRebate",
        "incomeOrReimbursement",
        "tradingPermission",
        "riskControlBypass",
    ):
        if redemption.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    for key in (
        "custody",
        "withdrawalPermission",
        "privateKeyCollection",
        "seedPhraseCollection",
        "exchangeApiSecretCollection",
        "automaticLiveTradingEnabled",
        "riskControlBypassAllowed",
    ):
        if safety.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if safety.get("simulationFirstRequiredBeforeFutureExecution") is not True:
        raise SiteCheckError(f"{label}: simulation-first requirement must be true")
    if release_gates.get("releaseGatesPage") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong releaseGatesPage")
    if release_gates.get("releaseGates") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates")
    for item in ("controlled HTTPS account UI", "read-only GCA balance verification", "credit ledger activation", "support review queue"):
        if item not in release_gates.get("requiredBeforeCreditUse", []):
            raise SiteCheckError(f"{label}: missing credit gate {item}")
    for item in ("controlled HTTPS account UI", "read-only GCA balance verification", "member ledger activation", "support review queue"):
        if item not in release_gates.get("requiredBeforeMemberUse", []):
            raise SiteCheckError(f"{label}: missing member gate {item}")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if market.get("liquidityDepth") != "starter-depth-only":
        raise SiteCheckError(f"{label}: wrong liquidityDepth")
    if links.get("creditsCatalogPage") != CREDITS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalogPage")
    if links.get("creditsCatalog") != CREDITS_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalog")
    if links.get("accessPortalPage") != ACCESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessPortalPage")
    if links.get("accessPortal") != ACCESS_URL:
        raise SiteCheckError(f"{label}: wrong accessPortal")
    if links.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if links.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if links.get("utilityJson") != UTILITY_URL:
        raise SiteCheckError(f"{label}: wrong utilityJson")
    if links.get("productJson") != PRODUCT_URL:
        raise SiteCheckError(f"{label}: wrong productJson")
    if links.get("releaseGates") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates")
    if links.get("reviewQueuePage") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueuePage")
    if links.get("reviewQueue") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueue")
    if links.get("memberLedger") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedger")
    if "GCA has published a draft service catalog for planned Web3 Radar utility credits." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing credits safe claim")
    if not any("live self-service claimable" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing self-service boundary")
    if not any("cash, income" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing credit value boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_release_gates_page(text: str) -> None:
    label = "/release-gates.html"
    assert_contains(text, "GCA Product Release Gates", label)
    assert_contains(text, "Release Gates JSON", label)
    assert_contains(text, "Credits Catalog", label)
    assert_contains(text, "Access Portal", label)
    assert_contains(text, "Operations Runbook", label)
    assert_contains(text, "Access API", label)
    assert_contains(text, "public product spec only", label)
    assert_contains(text, "Public Account UI is not live", label)
    assert_contains(text, "Credits are not self-service claimable", label)
    assert_contains(text, "GCA Member status is not self-service claimable", label)
    assert_contains(text, "controlled HTTPS account UI", label)
    assert_contains(text, "read-only GCA balance verification", label)
    assert_contains(text, "credit ledger activation", label)
    assert_contains(text, "member ledger activation", label)
    assert_contains(text, "risk-control review", label)
    assert_contains(text, "support review queue", label)
    assert_contains(text, "simulation or testnet first", label)
    assert_contains(text, "BaseScan token profile awaiting review", label)
    assert_contains(text, "no third-party audit", label)
    assert_contains(text, "No custody", label)
    assert_contains(text, "no withdrawal permission", label)
    assert_contains(text, "no exchange API secret collection", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_release_gates_json(text: str) -> None:
    label = "/release-gates.json"
    payload = load_json(text, label)
    state = payload.get("currentState", {})
    gate_ids = {item.get("id") for item in payload.get("releaseGates", [])}
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})

    if payload.get("schema") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-release-gates-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if state.get("currentStage") != "public-product-spec-only":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("publicProductSpecOnly") is not True:
        raise SiteCheckError(f"{label}: publicProductSpecOnly must be true")
    for key in ("publicAccountUiLive", "creditsSelfServiceClaimable", "gcaMemberSelfServiceClaimable", "liveTradingEnabled"):
        if state.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if state.get("baseScanTokenProfile") != "resubmitted-awaiting-review":
        raise SiteCheckError(f"{label}: wrong BaseScan state")
    if state.get("thirdPartyAudit") != "not-completed":
        raise SiteCheckError(f"{label}: wrong audit state")
    for gate in (
        "access-portal-blueprint",
        "access-api-contract",
        "operations-runbook",
        "review-queue-contract",
        "controlled-https-account-ui",
        "read-only-wallet-verification",
        "credit-ledger-activation",
        "member-ledger-activation",
        "support-review-queue",
        "risk-control-review",
        "simulation-first",
    ):
        if gate not in gate_ids:
            raise SiteCheckError(f"{label}: missing gate {gate}")
    for item in (
        "access portal blueprint",
        "access API contract",
        "public access operations runbook",
        "review queue contract",
        "controlled HTTPS account UI",
        "read-only GCA balance verification",
        "credit ledger activation",
        "member ledger activation",
        "support review queue",
        "risk-control review",
        "simulation or testnet first",
        "no custody",
        "no withdrawal permission",
        "no exchange API secret collection",
    ):
        if item not in payload.get("noGoLiveWithout", []):
            raise SiteCheckError(f"{label}: missing no-go-live item {item}")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if links.get("releaseGatesPage") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong releaseGatesPage")
    if links.get("releaseGates") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates")
    if links.get("productPage") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong productPage")
    if links.get("productJson") != PRODUCT_URL:
        raise SiteCheckError(f"{label}: wrong productJson")
    if links.get("creditsCatalogPage") != CREDITS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalogPage")
    if links.get("creditsCatalog") != CREDITS_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalog")
    if links.get("accessPortalPage") != ACCESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessPortalPage")
    if links.get("accessPortal") != ACCESS_URL:
        raise SiteCheckError(f"{label}: wrong accessPortal")
    if links.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if links.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if links.get("operationsRunbookPage") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbookPage")
    if links.get("operationsRunbook") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbook")
    if links.get("reviewQueuePage") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueuePage")
    if links.get("reviewQueue") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueue")
    if links.get("utilityJson") != UTILITY_URL:
        raise SiteCheckError(f"{label}: wrong utilityJson")
    if links.get("memberLedger") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedger")
    if not any("public release gates" in item for item in payload.get("publicClaimBoundaries", {}).get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing release-gates safe claim")
    if not any("credit claiming is live" in item for item in payload.get("publicClaimBoundaries", {}).get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing credit boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_privacy_page(text: str) -> None:
    label = "/privacy.html"
    assert_contains(text, "GCA Privacy Notice", label)
    assert_contains(text, "Privacy JSON", label)
    assert_contains(text, "local pre-registration packet", label)
    assert_contains(text, "directSubmissionEndpointConfigured", label)
    assert_contains(text, "No private key, seed phrase, exchange API secret, withdrawal permission, or custody request", label)
    assert_contains(text, "read-only ERC-20", label)
    assert_contains(text, "GCAgochina@outlook.com", label)
    assert_contains(text, "Participation Terms", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def validate_privacy_json(text: str) -> None:
    label = "/privacy.json"
    payload = load_json(text, label)
    static = payload.get("currentStaticSiteBehavior", {})
    verification = payload.get("walletVerification", {})
    future = payload.get("futureControlledIntake", {})
    boundary = payload.get("securityBoundary", {})
    links = payload.get("publicLinks", {})

    if payload.get("schema") != PRIVACY_NOTICE_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != PRIVACY_NOTICE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-privacy-notice-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("contactEmail") != "GCAgochina@outlook.com":
        raise SiteCheckError(f"{label}: wrong contact email")
    if static.get("automaticServerStorage") is not False:
        raise SiteCheckError(f"{label}: static site must not claim server storage")
    if static.get("directSubmissionEndpointConfigured") is not False:
        raise SiteCheckError(f"{label}: direct submission must remain false")
    if verification.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if verification.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if verification.get("requiresPrivateKey") is not False:
        raise SiteCheckError(f"{label}: wallet verification must not require private key")
    if verification.get("requiresSeedPhrase") is not False:
        raise SiteCheckError(f"{label}: wallet verification must not require seed phrase")
    if verification.get("requiresWithdrawalPermission") is not False:
        raise SiteCheckError(f"{label}: wallet verification must not require withdrawal permission")
    if future.get("preparedIntakeEndpoint") != "/gca/pre-registrations":
        raise SiteCheckError(f"{label}: wrong prepared intake endpoint")
    if "private key" not in boundary.get("neverAskFor", []):
        raise SiteCheckError(f"{label}: missing private key boundary")
    if links.get("support") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong support link")
    if links.get("supportJson") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong support JSON link")
    if links.get("participationTerms") != PARTICIPATION_TERMS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong terms link")
    if links.get("memberLedgerSchema") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong ledger schema link")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_terms_page(text: str) -> None:
    label = "/terms.html"
    assert_contains(text, "GCA Participation Terms", label)
    assert_contains(text, "Terms JSON", label)
    assert_contains(text, "Pre-Registration Only", label)
    assert_contains(text, "Account-Level Service Access", label)
    assert_contains(text, "No Custody Or Withdrawal Permission", label)
    assert_contains(text, "No Outcome Promise", label)
    assert_contains(text, "Resubmitted: awaiting review", label)
    assert_contains(text, "GCA/USDT on Base Mainnet", label)
    assert_contains(text, "Privacy Notice", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def validate_terms_json(text: str) -> None:
    label = "/terms.json"
    payload = load_json(text, label)
    boundaries = payload.get("participationBoundaries", {})
    programs = payload.get("programTerms", {})
    status = payload.get("externalStatus", {})
    no_promise = payload.get("noPromiseBoundary", {})
    links = payload.get("publicLinks", {})

    if payload.get("schema") != PARTICIPATION_TERMS_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != PARTICIPATION_TERMS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-participation-terms-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if boundaries.get("publicSelfServiceClaimConnected") is not False:
        raise SiteCheckError(f"{label}: self-service claim must remain false")
    if boundaries.get("requiresCustody") is not False:
        raise SiteCheckError(f"{label}: custody must remain false")
    if programs.get("holderBonus", {}).get("minimumHolding") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder threshold")
    if programs.get("gcaMember", {}).get("minimumHolding") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member threshold")
    if programs.get("gcaMember", {}).get("minimumHoldingPeriod") != "30 consecutive days":
        raise SiteCheckError(f"{label}: wrong member holding period")
    if programs.get("gcaMember", {}).get("memberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    if status.get("baseScanTokenProfile") != "resubmitted-awaiting-review":
        raise SiteCheckError(f"{label}: wrong BaseScan status")
    if status.get("geckoTerminalTokenInfo") != "approved-2026-05-11":
        raise SiteCheckError(f"{label}: wrong GeckoTerminal status")
    if status.get("thirdPartyAudit") != "not-completed":
        raise SiteCheckError(f"{label}: wrong audit status")
    if no_promise.get("notFinancialAdvice") is not True:
        raise SiteCheckError(f"{label}: missing no-advice boundary")
    if "risk-control bypass" not in no_promise.get("doesNotPromise", []):
        raise SiteCheckError(f"{label}: missing risk-control boundary")
    if links.get("support") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong support link")
    if links.get("supportJson") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong support JSON link")
    if links.get("privacyNotice") != PRIVACY_NOTICE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong privacy link")
    if links.get("memberLedgerSchema") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong ledger schema link")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


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
    assert_contains(text, X_URL, label)
    assert_contains(text, "Do not use this logo to imply third-party audit completion", label)
    assert_contains(text, "Submit only the official X profile", label)
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
    if payload.get("memberBenefitPageUrl") != MEMBER_BENEFIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitPageUrl")
    if payload.get("memberBenefitJsonUrl") != MEMBER_BENEFIT_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitJsonUrl")
    if payload.get("memberBenefitTransferPageUrl") != MEMBER_BENEFIT_TRANSFER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitTransferPageUrl")
    if payload.get("memberBenefitTransferJsonUrl") != MEMBER_BENEFIT_TRANSFER_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitTransferJsonUrl")
    if payload.get("supportPageUrl") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong supportPageUrl")
    if payload.get("supportJsonUrl") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong supportJsonUrl")
    if payload.get("roadmapPageUrl") != ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong roadmapPageUrl")
    if payload.get("roadmapUrl") != ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong roadmapUrl")
    if payload.get("communityPageUrl") != COMMUNITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong communityPageUrl")
    if payload.get("communityUrl") != COMMUNITY_URL:
        raise SiteCheckError(f"{label}: wrong communityUrl")
    if payload.get("narrativePageUrl") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong narrativePageUrl")
    if payload.get("narrativeUrl") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong narrativeUrl")
    if payload.get("weeklyRadarPageUrl") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarPageUrl")
    if payload.get("weeklyRadarUrl") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarUrl")
    if payload.get("privacyNoticePageUrl") != PRIVACY_NOTICE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong privacyNoticePageUrl")
    if payload.get("privacyNoticeUrl") != PRIVACY_NOTICE_URL:
        raise SiteCheckError(f"{label}: wrong privacyNoticeUrl")
    if payload.get("participationTermsPageUrl") != PARTICIPATION_TERMS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong participationTermsPageUrl")
    if payload.get("participationTermsUrl") != PARTICIPATION_TERMS_URL:
        raise SiteCheckError(f"{label}: wrong participationTermsUrl")
    if payload.get("utilityThesisUrl") != UTILITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong utilityThesisUrl")
    if payload.get("utilityThesisJsonUrl") != UTILITY_URL:
        raise SiteCheckError(f"{label}: wrong utilityThesisJsonUrl")
    if payload.get("productSpecPageUrl") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong productSpecPageUrl")
    if payload.get("productSpecUrl") != PRODUCT_URL:
        raise SiteCheckError(f"{label}: wrong productSpecUrl")
    if payload.get("creditsCatalogPageUrl") != CREDITS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalogPageUrl")
    if payload.get("creditsCatalogUrl") != CREDITS_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalogUrl")
    if payload.get("accessPortalPageUrl") != ACCESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessPortalPageUrl")
    if payload.get("accessPortalUrl") != ACCESS_URL:
        raise SiteCheckError(f"{label}: wrong accessPortalUrl")
    if payload.get("accessApiPageUrl") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPageUrl")
    if payload.get("accessApiUrl") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApiUrl")
    if payload.get("reviewQueuePageUrl") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueuePageUrl")
    if payload.get("reviewQueueUrl") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueueUrl")
    if payload.get("operationsRunbookPageUrl") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbookPageUrl")
    if payload.get("operationsRunbookUrl") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbookUrl")
    if payload.get("releaseGatesPageUrl") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong releaseGatesPageUrl")
    if payload.get("releaseGatesUrl") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong releaseGatesUrl")
    if payload.get("walletWarningEvidencePageUrl") != WALLET_WARNING_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidencePageUrl")
    if payload.get("walletWarningEvidenceUrl") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidenceUrl")
    if payload.get("walletSecurityProfileUrl") != WALLET_SECURITY_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong walletSecurityProfileUrl")
    if payload.get("tokenSafetyPageUrl") != TOKEN_SAFETY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafetyPageUrl")
    if payload.get("tokenSafetyUrl") != TOKEN_SAFETY_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafetyUrl")
    if payload.get("technicalReportPageUrl") != TECHNICAL_REPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong technicalReportPageUrl")
    if payload.get("technicalReportUrl") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technicalReportUrl")
    if payload.get("blockaidFollowupPageUrl") != BLOCKAID_FOLLOWUP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowupPageUrl")
    if payload.get("blockaidFollowupUrl") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowupUrl")
    if payload.get("reserveStatementPageUrl") != RESERVE_STATEMENT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatementPageUrl")
    if payload.get("reserveStatementUrl") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatementUrl")
    if payload.get("externalReviewStatusPageUrl") != EXTERNAL_REVIEW_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatusPageUrl")
    if payload.get("externalReviewStatusUrl") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatusUrl")
    if payload.get("reviewerKitPageUrl") != REVIEWER_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKitPageUrl")
    if payload.get("reviewerKitUrl") != REVIEWER_KIT_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKitUrl")
    if payload.get("platformRepliesPageUrl") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesPageUrl")
    if payload.get("platformRepliesUrl") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesUrl")
    if payload.get("trustCenterPageUrl") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterPageUrl")
    if payload.get("trustCenterUrl") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterUrl")
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
    social_links = payload.get("officialSocialLinks", [])
    if not any(link.get("platform") == "X" and link.get("url") == X_URL for link in social_links):
        raise SiteCheckError(f"{label}: missing official X social link")
    if market.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialPair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if status.get("baseScanTokenProfile") != "resubmitted-awaiting-review":
        raise SiteCheckError(f"{label}: unexpected BaseScan status")
    if status.get("geckoTerminalTokenInfo") != "approved-2026-05-11":
        raise SiteCheckError(f"{label}: unexpected GeckoTerminal status")
    if status.get("narrativeSystem") != "public-narrative-system-published":
        raise SiteCheckError(f"{label}: unexpected narrative system status")
    if status.get("weeklyGoChinaRadar") != "weekly-go-china-radar-issue-002-published":
        raise SiteCheckError(f"{label}: unexpected weekly radar status")
    if status.get("accessPortal") != "public-access-portal-blueprint-published":
        raise SiteCheckError(f"{label}: unexpected access portal status")
    if status.get("accessApiContract") != "public-access-api-contract-published":
        raise SiteCheckError(f"{label}: unexpected access API status")
    if status.get("reviewQueueContract") != "public-review-queue-contract-published":
        raise SiteCheckError(f"{label}: unexpected review queue status")
    if status.get("accessOperationsRunbook") != "public-access-operations-runbook-published":
        raise SiteCheckError(f"{label}: unexpected operations runbook status")
    if status.get("blockaidFollowup") != "public-blockaid-followup-package-published":
        raise SiteCheckError(f"{label}: unexpected Blockaid follow-up status")
    if status.get("technicalReport") != "public-internal-technical-report-published":
        raise SiteCheckError(f"{label}: unexpected technical report status")
    if status.get("reserveStatement") != "public-reserve-address-statement-published":
        raise SiteCheckError(f"{label}: unexpected reserve statement status")
    if member_program.get("status") != "rules-published-public-claim-not-connected":
        raise SiteCheckError(f"{label}: unexpected member program status")
    if member_program.get("supportIntake", {}).get("status") != "public-support-intake-published":
        raise SiteCheckError(f"{label}: unexpected support intake status")
    if member_program.get("ledgerSchema", {}).get("status") != "public-member-ledger-schema-published":
        raise SiteCheckError(f"{label}: unexpected member ledger schema status")
    if member_program.get("privacyAndTerms", {}).get("status") != "public-privacy-and-terms-published":
        raise SiteCheckError(f"{label}: unexpected privacy and terms status")
    if payload.get("roadmap", {}).get("status") != "public-roadmap-published":
        raise SiteCheckError(f"{label}: unexpected roadmap status")
    if payload.get("roadmap", {}).get("publicSelfServiceClaimsLive") is not False:
        raise SiteCheckError(f"{label}: roadmap must keep self-service claims false")
    if payload.get("utilityBridge", {}).get("status") != "public-utility-bridge-spec-published":
        raise SiteCheckError(f"{label}: unexpected utility bridge status")
    if payload.get("utilityBridge", {}).get("url") != UTILITY_URL:
        raise SiteCheckError(f"{label}: wrong utility bridge url")
    if payload.get("utilityBridge", {}).get("publicSelfServiceClaimsLive") is not False:
        raise SiteCheckError(f"{label}: utility bridge must keep self-service claims false")
    if payload.get("utilityBridge", {}).get("requiresControlledWalletVerification") is not True:
        raise SiteCheckError(f"{label}: utility bridge must require controlled wallet verification")
    if status.get("productSpec") != "public-product-spec-published":
        raise SiteCheckError(f"{label}: unexpected product spec status")
    if status.get("releaseGates") != "public-release-gates-published":
        raise SiteCheckError(f"{label}: unexpected release gates status")
    if status.get("creditsCatalog") != "public-credits-catalog-published":
        raise SiteCheckError(f"{label}: unexpected credits catalog status")
    if payload.get("productSpec", {}).get("status") != "public-product-spec-published":
        raise SiteCheckError(f"{label}: unexpected product spec object status")
    if payload.get("productSpec", {}).get("pageUrl") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong product spec page")
    if payload.get("productSpec", {}).get("url") != PRODUCT_URL:
        raise SiteCheckError(f"{label}: wrong product spec url")
    if payload.get("productSpec", {}).get("publicAccountUiLive") is not False:
        raise SiteCheckError(f"{label}: product account UI must be false")
    if payload.get("productSpec", {}).get("liveTradingEnabled") is not False:
        raise SiteCheckError(f"{label}: product live trading must be false")
    if "ENTRY_READY Review" not in payload.get("productSpec", {}).get("moduleNames", []):
        raise SiteCheckError(f"{label}: missing product module")
    credits = payload.get("creditsCatalog", {})
    if credits.get("status") != "public-credits-catalog-published":
        raise SiteCheckError(f"{label}: unexpected credits catalog object status")
    if credits.get("pageUrl") != CREDITS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong credits catalog page")
    if credits.get("url") != CREDITS_URL:
        raise SiteCheckError(f"{label}: wrong credits catalog url")
    if credits.get("currentStage") != "draft-service-catalog-only":
        raise SiteCheckError(f"{label}: wrong credits catalog stage")
    if credits.get("publicAccountUiLive") is not False:
        raise SiteCheckError(f"{label}: credits account UI must be false")
    if credits.get("creditsSelfServiceClaimable") is not False:
        raise SiteCheckError(f"{label}: credits self-service must be false")
    if credits.get("gcaMemberSelfServiceClaimable") is not False:
        raise SiteCheckError(f"{label}: member self-service must be false")
    if credits.get("holderBonusCreditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong credits holder bonus")
    if "Support Review Queue" not in credits.get("serviceNames", []):
        raise SiteCheckError(f"{label}: missing credits service")
    review_queue = payload.get("reviewQueueContract", {})
    if review_queue.get("status") != "public-review-queue-contract-published":
        raise SiteCheckError(f"{label}: unexpected review queue object status")
    if review_queue.get("pageUrl") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong review queue page")
    if review_queue.get("url") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong review queue url")
    if review_queue.get("publicQueueLive") is not False:
        raise SiteCheckError(f"{label}: review queue publicQueueLive must be false")
    if review_queue.get("creditsSelfServiceClaimable") is not False:
        raise SiteCheckError(f"{label}: review queue credits must be false")
    if "wallet-balance-review" not in review_queue.get("lanes", []):
        raise SiteCheckError(f"{label}: missing review queue lane")
    operations = payload.get("accessOperationsRunbook", {})
    if operations.get("status") != "public-access-operations-runbook-published":
        raise SiteCheckError(f"{label}: unexpected operations object status")
    if operations.get("pageUrl") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong operations page")
    if operations.get("url") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong operations url")
    if operations.get("publicRunbookOnly") is not True:
        raise SiteCheckError(f"{label}: operations must remain runbook only")
    if operations.get("ledgerWritesLive") is not False:
        raise SiteCheckError(f"{label}: operations ledger writes must be false")
    if payload.get("releaseGates", {}).get("status") != "public-release-gates-published":
        raise SiteCheckError(f"{label}: unexpected release gates object status")
    if payload.get("releaseGates", {}).get("pageUrl") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong release gates page")
    if payload.get("releaseGates", {}).get("url") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong release gates url")
    if payload.get("releaseGates", {}).get("publicAccountUiLive") is not False:
        raise SiteCheckError(f"{label}: release gates account UI must be false")
    if payload.get("releaseGates", {}).get("creditsSelfServiceClaimable") is not False:
        raise SiteCheckError(f"{label}: release gates credits must be false")
    if payload.get("releaseGates", {}).get("gcaMemberSelfServiceClaimable") is not False:
        raise SiteCheckError(f"{label}: release gates member status must be false")
    if "risk-control review" not in payload.get("releaseGates", {}).get("requiredBeforePublicClaims", []):
        raise SiteCheckError(f"{label}: missing release gates risk-control gate")
    if payload.get("communityKit", {}).get("status") != "public-community-kit-published":
        raise SiteCheckError(f"{label}: unexpected community kit status")
    if payload.get("communityKit", {}).get("officialTelegram") != "https://t.me/gcagochinaofficial":
        raise SiteCheckError(f"{label}: wrong community Telegram")
    if payload.get("communityKit", {}).get("officialX") != X_URL:
        raise SiteCheckError(f"{label}: wrong community X")
    if payload.get("narrativeSystem", {}).get("status") != "public-narrative-system-published":
        raise SiteCheckError(f"{label}: unexpected narrative system status")
    if payload.get("narrativeSystem", {}).get("tagline") != "Narrative meets risk control.":
        raise SiteCheckError(f"{label}: wrong narrative tagline")
    if payload.get("weeklyGoChinaRadar", {}).get("status") != "weekly-go-china-radar-issue-002-published":
        raise SiteCheckError(f"{label}: unexpected weekly radar object status")
    if payload.get("weeklyGoChinaRadar", {}).get("pageUrl") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weekly radar object page")
    if payload.get("weeklyGoChinaRadar", {}).get("url") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weekly radar object url")
    if payload.get("weeklyGoChinaRadar", {}).get("issue") != "issue-002":
        raise SiteCheckError(f"{label}: wrong weekly radar issue")
    if payload.get("weeklyGoChinaRadar", {}).get("issueDate") != "2026-05-14":
        raise SiteCheckError(f"{label}: wrong weekly radar issueDate")
    if payload.get("weeklyGoChinaRadar", {}).get("notFinancialAdvice") is not True:
        raise SiteCheckError(f"{label}: weekly radar must keep notFinancialAdvice true")
    if payload.get("listingReadiness", {}).get("status") != "not-ready":
        raise SiteCheckError(f"{label}: unexpected listing readiness status")
    if payload.get("marketQuality", {}).get("status") != "early-stage-market-quality-plan":
        raise SiteCheckError(f"{label}: unexpected market quality status")
    if payload.get("externalReviewStatus", {}).get("status") != "external-review-status-active":
        raise SiteCheckError(f"{label}: unexpected external review status")
    if payload.get("reviewerKit", {}).get("status") != "public-reviewer-kit-published":
        raise SiteCheckError(f"{label}: unexpected reviewer kit status")
    if payload.get("platformReplies", {}).get("status") != "public-platform-reply-kit-published":
        raise SiteCheckError(f"{label}: unexpected platform replies status")
    if payload.get("trustCenter", {}).get("status") != "public-trust-center-published":
        raise SiteCheckError(f"{label}: unexpected trust center status")
    if payload.get("tokenSafety", {}).get("status") != "public-token-safety-checklist-published":
        raise SiteCheckError(f"{label}: unexpected token safety status")
    if payload.get("blockaidFollowup", {}).get("status") != "public-blockaid-followup-package-published":
        raise SiteCheckError(f"{label}: unexpected Blockaid follow-up object status")
    if payload.get("blockaidFollowup", {}).get("pageUrl") != BLOCKAID_FOLLOWUP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up page")
    if payload.get("blockaidFollowup", {}).get("url") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up url")
    if payload.get("technicalReport", {}).get("status") != "public-internal-technical-report-published":
        raise SiteCheckError(f"{label}: unexpected technical report object status")
    if payload.get("technicalReport", {}).get("pageUrl") != TECHNICAL_REPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong technical report page")
    if payload.get("technicalReport", {}).get("url") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technical report url")
    if payload.get("reserveStatement", {}).get("status") != "public-reserve-address-statement-published":
        raise SiteCheckError(f"{label}: unexpected reserve statement object status")
    if payload.get("reserveStatement", {}).get("pageUrl") != RESERVE_STATEMENT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reserve statement page")
    if payload.get("reserveStatement", {}).get("url") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserve statement url")
    if payload.get("walletWarningEvidence", {}).get("status") != "warning-report-submitted-owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: unexpected wallet warning status")
    if payload.get("walletWarningEvidence", {}).get("walletSecurityProfileUrl") != WALLET_SECURITY_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong wallet security profile URL")
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
    if extensions.get("memberBenefitPage") != MEMBER_BENEFIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitPage")
    if extensions.get("memberBenefitJson") != MEMBER_BENEFIT_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitJson")
    if extensions.get("memberBenefitTransferPage") != MEMBER_BENEFIT_TRANSFER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitTransferPage")
    if extensions.get("memberBenefitTransferJson") != MEMBER_BENEFIT_TRANSFER_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitTransferJson")
    if extensions.get("supportPage") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong supportPage")
    if extensions.get("supportJson") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong supportJson")
    if extensions.get("roadmapPage") != ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong roadmapPage")
    if extensions.get("roadmap") != ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong roadmap")
    if extensions.get("communityPage") != COMMUNITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong communityPage")
    if extensions.get("community") != COMMUNITY_URL:
        raise SiteCheckError(f"{label}: wrong community")
    if extensions.get("narrativePage") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong narrativePage")
    if extensions.get("narrative") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong narrative")
    if extensions.get("weeklyRadarPage") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarPage")
    if extensions.get("weeklyRadar") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadar")
    if extensions.get("privacyNoticePage") != PRIVACY_NOTICE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong privacyNoticePage")
    if extensions.get("privacyNotice") != PRIVACY_NOTICE_URL:
        raise SiteCheckError(f"{label}: wrong privacyNotice")
    if extensions.get("participationTermsPage") != PARTICIPATION_TERMS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong participationTermsPage")
    if extensions.get("participationTerms") != PARTICIPATION_TERMS_URL:
        raise SiteCheckError(f"{label}: wrong participationTerms")
    if extensions.get("utilityThesis") != UTILITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong utilityThesis")
    if extensions.get("utilityThesisJson") != UTILITY_URL:
        raise SiteCheckError(f"{label}: wrong utilityThesisJson")
    if extensions.get("productSpecPage") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong productSpecPage")
    if extensions.get("productSpec") != PRODUCT_URL:
        raise SiteCheckError(f"{label}: wrong productSpec")
    if extensions.get("productSpecStatus") != "public-product-spec-published":
        raise SiteCheckError(f"{label}: wrong productSpecStatus")
    if extensions.get("releaseGatesPage") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong releaseGatesPage")
    if extensions.get("releaseGates") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates")
    if extensions.get("releaseGatesStatus") != "public-release-gates-published":
        raise SiteCheckError(f"{label}: wrong releaseGatesStatus")
    if extensions.get("creditsCatalogPage") != CREDITS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalogPage")
    if extensions.get("creditsCatalog") != CREDITS_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalog")
    if extensions.get("creditsCatalogStatus") != "public-credits-catalog-published":
        raise SiteCheckError(f"{label}: wrong creditsCatalogStatus")
    if extensions.get("accessPortalPage") != ACCESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessPortalPage")
    if extensions.get("accessPortal") != ACCESS_URL:
        raise SiteCheckError(f"{label}: wrong accessPortal")
    if extensions.get("accessPortalStatus") != "public-access-portal-blueprint-published":
        raise SiteCheckError(f"{label}: wrong accessPortalStatus")
    if extensions.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if extensions.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if extensions.get("accessApiStatus") != "public-access-api-contract-published":
        raise SiteCheckError(f"{label}: wrong accessApiStatus")
    if extensions.get("reviewQueuePage") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueuePage")
    if extensions.get("reviewQueue") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueue")
    if extensions.get("reviewQueueStatus") != "public-review-queue-contract-published":
        raise SiteCheckError(f"{label}: wrong reviewQueueStatus")
    if extensions.get("operationsRunbookPage") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbookPage")
    if extensions.get("operationsRunbook") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbook")
    if extensions.get("operationsRunbookStatus") != "public-access-operations-runbook-published":
        raise SiteCheckError(f"{label}: wrong operationsRunbookStatus")
    if extensions.get("walletWarningEvidencePage") != WALLET_WARNING_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidencePage")
    if extensions.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidence")
    if extensions.get("walletSecurityProfile") != WALLET_SECURITY_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong walletSecurityProfile")
    if extensions.get("tokenSafetyPage") != TOKEN_SAFETY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafetyPage")
    if extensions.get("tokenSafety") != TOKEN_SAFETY_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafety")
    if extensions.get("blockaidFollowupPage") != BLOCKAID_FOLLOWUP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowupPage")
    if extensions.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup")
    if extensions.get("technicalReportPage") != TECHNICAL_REPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong technicalReportPage")
    if extensions.get("technicalReport") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technicalReport")
    if extensions.get("reserveStatementPage") != RESERVE_STATEMENT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatementPage")
    if extensions.get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatement")
    if extensions.get("externalReviewStatusPage") != EXTERNAL_REVIEW_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatusPage")
    if extensions.get("externalReviewStatus") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatus")
    if extensions.get("reviewerKitPage") != REVIEWER_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKitPage")
    if extensions.get("reviewerKit") != REVIEWER_KIT_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKit")
    if extensions.get("platformRepliesPage") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesPage")
    if extensions.get("platformReplies") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong platformReplies")
    if extensions.get("trustCenterPage") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterPage")
    if extensions.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trustCenter")
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
    if extensions.get("reviewerKitStatus") != "public-reviewer-kit-published":
        raise SiteCheckError(f"{label}: wrong reviewerKitStatus")
    if extensions.get("platformRepliesStatus") != "public-platform-reply-kit-published":
        raise SiteCheckError(f"{label}: wrong platformRepliesStatus")
    if extensions.get("trustCenterStatus") != "public-trust-center-published":
        raise SiteCheckError(f"{label}: wrong trustCenterStatus")
    if extensions.get("narrativeSystemStatus") != "public-narrative-system-published":
        raise SiteCheckError(f"{label}: wrong narrativeSystemStatus")
    if extensions.get("weeklyRadarStatus") != "weekly-go-china-radar-issue-002-published":
        raise SiteCheckError(f"{label}: wrong weeklyRadarStatus")
    if extensions.get("utilityBridgeStatus") != "public-utility-bridge-spec-published":
        raise SiteCheckError(f"{label}: wrong utilityBridgeStatus")
    if extensions.get("walletSecurityProfileStatus") != "public-wallet-security-profile-published":
        raise SiteCheckError(f"{label}: wrong walletSecurityProfileStatus")
    if extensions.get("tokenSafetyStatus") != "public-token-safety-checklist-published":
        raise SiteCheckError(f"{label}: wrong tokenSafetyStatus")
    if extensions.get("blockaidFollowupStatus") != "public-blockaid-followup-package-published":
        raise SiteCheckError(f"{label}: wrong blockaidFollowupStatus")
    if extensions.get("technicalReportStatus") != "public-internal-technical-report-published":
        raise SiteCheckError(f"{label}: wrong technicalReportStatus")
    if extensions.get("reserveStatementStatus") != "public-reserve-address-statement-published":
        raise SiteCheckError(f"{label}: wrong reserveStatementStatus")
    if extensions.get("memberLedgerStatus") != "public-member-ledger-schema-published":
        raise SiteCheckError(f"{label}: wrong memberLedgerStatus")
    if extensions.get("supportIntakeStatus") != "public-support-intake-published":
        raise SiteCheckError(f"{label}: wrong supportIntakeStatus")
    if extensions.get("roadmapStatus") != "public-roadmap-published":
        raise SiteCheckError(f"{label}: wrong roadmapStatus")
    if extensions.get("communityKitStatus") != "public-community-kit-published":
        raise SiteCheckError(f"{label}: wrong communityKitStatus")
    if extensions.get("privacyNoticeStatus") != "public-privacy-notice-published":
        raise SiteCheckError(f"{label}: wrong privacyNoticeStatus")
    if extensions.get("participationTermsStatus") != "public-participation-terms-published":
        raise SiteCheckError(f"{label}: wrong participationTermsStatus")
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
    if urls.get("memberBenefitPage") != MEMBER_BENEFIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitPage")
    if urls.get("memberBenefitJson") != MEMBER_BENEFIT_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitJson")
    if urls.get("memberBenefitTransferPage") != MEMBER_BENEFIT_TRANSFER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitTransferPage")
    if urls.get("memberBenefitTransferJson") != MEMBER_BENEFIT_TRANSFER_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitTransferJson")
    if urls.get("supportPage") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong supportPage")
    if urls.get("supportJson") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong supportJson")
    if urls.get("roadmapPage") != ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong roadmapPage")
    if urls.get("roadmap") != ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong roadmap")
    if urls.get("communityPage") != COMMUNITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong communityPage")
    if urls.get("community") != COMMUNITY_URL:
        raise SiteCheckError(f"{label}: wrong community")
    if urls.get("narrativePage") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong narrativePage")
    if urls.get("narrative") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong narrative")
    if urls.get("weeklyRadarPage") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarPage")
    if urls.get("weeklyRadar") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadar")
    if urls.get("privacyNoticePage") != PRIVACY_NOTICE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong privacyNoticePage")
    if urls.get("privacyNotice") != PRIVACY_NOTICE_URL:
        raise SiteCheckError(f"{label}: wrong privacyNotice")
    if urls.get("participationTermsPage") != PARTICIPATION_TERMS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong participationTermsPage")
    if urls.get("participationTerms") != PARTICIPATION_TERMS_URL:
        raise SiteCheckError(f"{label}: wrong participationTerms")
    if urls.get("utilityThesis") != UTILITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong utilityThesis")
    if urls.get("utilityThesisJson") != UTILITY_URL:
        raise SiteCheckError(f"{label}: wrong utilityThesisJson")
    if urls.get("productSpecPage") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong productSpecPage")
    if urls.get("productSpec") != PRODUCT_URL:
        raise SiteCheckError(f"{label}: wrong productSpec")
    if urls.get("releaseGatesPage") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong releaseGatesPage")
    if urls.get("releaseGates") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates")
    if urls.get("creditsCatalogPage") != CREDITS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalogPage")
    if urls.get("creditsCatalog") != CREDITS_URL:
        raise SiteCheckError(f"{label}: wrong creditsCatalog")
    if urls.get("accessPortalPage") != ACCESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessPortalPage")
    if urls.get("accessPortal") != ACCESS_URL:
        raise SiteCheckError(f"{label}: wrong accessPortal")
    if urls.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if urls.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if urls.get("reviewQueuePage") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueuePage")
    if urls.get("reviewQueue") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueue")
    if urls.get("operationsRunbookPage") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbookPage")
    if urls.get("operationsRunbook") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong operationsRunbook")
    if urls.get("walletWarningEvidencePage") != WALLET_WARNING_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidencePage")
    if urls.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidence")
    if urls.get("walletSecurityProfile") != WALLET_SECURITY_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong walletSecurityProfile")
    if urls.get("tokenSafetyPage") != TOKEN_SAFETY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafetyPage")
    if urls.get("tokenSafety") != TOKEN_SAFETY_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafety")
    if urls.get("blockaidFollowupPage") != BLOCKAID_FOLLOWUP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowupPage")
    if urls.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup")
    if urls.get("technicalReportPage") != TECHNICAL_REPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong technicalReportPage")
    if urls.get("technicalReport") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technicalReport")
    if urls.get("reserveStatementPage") != RESERVE_STATEMENT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatementPage")
    if urls.get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatement")
    if urls.get("externalReviewStatusPage") != EXTERNAL_REVIEW_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatusPage")
    if urls.get("externalReviewStatus") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatus")
    if urls.get("reviewerKitPage") != REVIEWER_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKitPage")
    if urls.get("reviewerKit") != REVIEWER_KIT_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKit")
    if urls.get("platformRepliesPage") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesPage")
    if urls.get("platformReplies") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong platformReplies")
    if urls.get("trustCenterPage") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterPage")
    if urls.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trustCenter")
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
    if urls.get("x") != X_URL:
        raise SiteCheckError(f"{label}: wrong x")
    if market.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialPair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if security.get("thirdPartyAuditCompleted") is not False:
        raise SiteCheckError(f"{label}: third-party audit status must remain false")
    if payload.get("platformStatus", {}).get("platformReplies") != "public-platform-reply-kit-published":
        raise SiteCheckError(f"{label}: wrong platformReplies status")
    if payload.get("platformStatus", {}).get("trustCenter") != "public-trust-center-published":
        raise SiteCheckError(f"{label}: wrong trustCenter status")
    if payload.get("platformStatus", {}).get("narrativeSystem") != "public-narrative-system-published":
        raise SiteCheckError(f"{label}: wrong narrativeSystem status")
    if payload.get("platformStatus", {}).get("weeklyGoChinaRadar") != "weekly-go-china-radar-issue-002-published":
        raise SiteCheckError(f"{label}: wrong weeklyGoChinaRadar status")
    if payload.get("platformStatus", {}).get("accessPortal") != "public-access-portal-blueprint-published":
        raise SiteCheckError(f"{label}: wrong accessPortal status")
    if payload.get("platformStatus", {}).get("accessApiContract") != "public-access-api-contract-published":
        raise SiteCheckError(f"{label}: wrong accessApiContract status")
    if payload.get("platformStatus", {}).get("reviewQueueContract") != "public-review-queue-contract-published":
        raise SiteCheckError(f"{label}: wrong reviewQueueContract status")
    if payload.get("platformStatus", {}).get("accessOperationsRunbook") != "public-access-operations-runbook-published":
        raise SiteCheckError(f"{label}: wrong operations runbook status")
    if payload.get("platformStatus", {}).get("utilityBridge") != "public-utility-bridge-spec-published":
        raise SiteCheckError(f"{label}: wrong utilityBridge status")
    if payload.get("platformStatus", {}).get("productSpec") != "public-product-spec-published":
        raise SiteCheckError(f"{label}: wrong productSpec status")
    if payload.get("platformStatus", {}).get("releaseGates") != "public-release-gates-published":
        raise SiteCheckError(f"{label}: wrong releaseGates status")
    if payload.get("productSpec", {}).get("pageUrl") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong productSpec page")
    if payload.get("productSpec", {}).get("url") != PRODUCT_URL:
        raise SiteCheckError(f"{label}: wrong productSpec url")
    if payload.get("productSpec", {}).get("publicAccountUiLive") is not False:
        raise SiteCheckError(f"{label}: product account UI must be false")
    if payload.get("productSpec", {}).get("liveTradingEnabled") is not False:
        raise SiteCheckError(f"{label}: product live trading must be false")
    if payload.get("releaseGates", {}).get("pageUrl") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates page")
    if payload.get("releaseGates", {}).get("url") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates url")
    if payload.get("releaseGates", {}).get("creditsSelfServiceClaimable") is not False:
        raise SiteCheckError(f"{label}: release gates credits must be false")
    if payload.get("releaseGates", {}).get("gcaMemberSelfServiceClaimable") is not False:
        raise SiteCheckError(f"{label}: release gates member must be false")
    if payload.get("reviewQueueContract", {}).get("pageUrl") != REVIEW_QUEUE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueueContract page")
    if payload.get("reviewQueueContract", {}).get("url") != REVIEW_QUEUE_URL:
        raise SiteCheckError(f"{label}: wrong reviewQueueContract url")
    if payload.get("reviewQueueContract", {}).get("publicQueueLive") is not False:
        raise SiteCheckError(f"{label}: review queue must not be live")
    if payload.get("accessOperationsRunbook", {}).get("pageUrl") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong operations page")
    if payload.get("accessOperationsRunbook", {}).get("url") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong operations url")
    if payload.get("accessOperationsRunbook", {}).get("publicRunbookOnly") is not True:
        raise SiteCheckError(f"{label}: operations must remain runbook only")
    if payload.get("platformStatus", {}).get("walletSecurityProfile") != "public-wallet-security-profile-published":
        raise SiteCheckError(f"{label}: wrong walletSecurityProfile status")
    if payload.get("platformStatus", {}).get("tokenSafety") != "public-token-safety-checklist-published":
        raise SiteCheckError(f"{label}: wrong tokenSafety status")
    if payload.get("platformStatus", {}).get("blockaidFollowup") != "public-blockaid-followup-package-published":
        raise SiteCheckError(f"{label}: wrong blockaidFollowup status")
    if payload.get("platformStatus", {}).get("technicalReport") != "public-internal-technical-report-published":
        raise SiteCheckError(f"{label}: wrong technicalReport status")
    if payload.get("platformStatus", {}).get("reserveStatement") != "public-reserve-address-statement-published":
        raise SiteCheckError(f"{label}: wrong reserveStatement status")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_wallet_security_json(text: str) -> None:
    label = "/.well-known/wallet-security.json"
    payload = load_json(text, label)
    network = payload.get("network", {})
    token = payload.get("token", {})
    facts = payload.get("securityFacts", {})
    review = payload.get("walletReviewStatus", {})
    basescan = payload.get("baseScanStatus", {})
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})

    if payload.get("schema") != WALLET_SECURITY_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("status") != "public-wallet-security-profile-published":
        raise SiteCheckError(f"{label}: wrong status")
    if network.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if token.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if facts.get("sourceVerifiedOnBaseScan") is not True:
        raise SiteCheckError(f"{label}: source verification must be true")
    for key in (
        "postDeploymentMintFunction",
        "ownerOrAdminRole",
        "proxyOrUpgradePath",
        "blacklistFunction",
        "pauseFunction",
        "transferTaxOrHiddenFee",
        "custodyOrWithdrawalPath",
        "thirdPartyAuditCompleted",
    ):
        if facts.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if review.get("blockaidMetaMaskWarning") != "owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong wallet warning status")
    if review.get("warningRemovalConfirmed") is not True:
        raise SiteCheckError(f"{label}: owner-visible warning state must be true")
    if basescan.get("sourceVerification") != "verified":
        raise SiteCheckError(f"{label}: wrong BaseScan source status")
    if basescan.get("tokenProfile") != "resubmitted-awaiting-review":
        raise SiteCheckError(f"{label}: wrong BaseScan token profile status")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong official market pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong official pool")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quote asset")
    if links.get("walletSecurityProfile") != WALLET_SECURITY_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong walletSecurityProfile link")
    if links.get("tokenSafetyPage") != TOKEN_SAFETY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafetyPage")
    if links.get("tokenSafety") != TOKEN_SAFETY_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafety")
    if links.get("blockaidFollowupPage") != BLOCKAID_FOLLOWUP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowupPage")
    if links.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup")
    if links.get("technicalReportPage") != TECHNICAL_REPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong technicalReportPage")
    if links.get("technicalReport") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technicalReport")
    if links.get("reserveStatementPage") != RESERVE_STATEMENT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatementPage")
    if links.get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatement")
    if links.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong wallet warning evidence link")
    if links.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trust center link")
    if "No third-party audit has been completed." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "security-vendor approval, permanent warning-free status, or cross-wallet warning removal before vendor/current wallet UI confirms it" not in payload.get("publicClaimBoundaries", {}).get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing warning-removal boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_member_program_json(text: str) -> None:
    label = "/member-program.json"
    payload = load_json(text, label)
    public_pages = payload.get("publicPages", {})
    token = payload.get("token", {})
    holder_bonus = payload.get("holderBonus", {})
    member_tier = payload.get("memberTier", {})
    verification = payload.get("verification", {})
    privacy_terms = payload.get("privacyAndTerms", {})
    support_intake = payload.get("supportIntake", {})
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
    if public_pages.get("memberAccessPreview") != "https://gcagochina.com/gca/member-access/":
        raise SiteCheckError(f"{label}: wrong memberAccessPreview page")
    if public_pages.get("memberLedgerSchema") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong memberLedger schema")
    if public_pages.get("memberBenefit") != MEMBER_BENEFIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong member benefit page")
    if public_pages.get("memberBenefitJson") != MEMBER_BENEFIT_URL:
        raise SiteCheckError(f"{label}: wrong member benefit JSON")
    if public_pages.get("memberBenefitTransfer") != MEMBER_BENEFIT_TRANSFER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong member benefit transfer page")
    if public_pages.get("memberBenefitTransferJson") != MEMBER_BENEFIT_TRANSFER_URL:
        raise SiteCheckError(f"{label}: wrong member benefit transfer JSON")
    if public_pages.get("support") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong support page")
    if public_pages.get("supportJson") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong support JSON")
    if public_pages.get("privacyNotice") != PRIVACY_NOTICE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong privacy notice page")
    if public_pages.get("participationTerms") != PARTICIPATION_TERMS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong participation terms page")
    if holder_bonus.get("minimumHolding") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder bonus threshold")
    if holder_bonus.get("creditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong credit amount")
    if holder_bonus.get("creditExpiry") != "180 days after ledger activation unless a later published policy extends it":
        raise SiteCheckError(f"{label}: wrong credit expiry")
    if member_tier.get("minimumHolding") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member threshold")
    if member_tier.get("minimumHoldingPeriod") != "30 consecutive days":
        raise SiteCheckError(f"{label}: wrong member holding period")
    if member_tier.get("memberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    if member_tier.get("refreshCadence") != "30 days after activation, or earlier if the user requests a manual recheck":
        raise SiteCheckError(f"{label}: wrong member refresh cadence")
    if verification.get("directSubmissionEndpointConfigured") is not False:
        raise SiteCheckError(f"{label}: direct submission must remain false")
    preview = verification.get("browserPreview", {})
    local_backend = verification.get("localOperatorBackend", {})
    if local_backend.get("status") != "local-only-backend-available":
        raise SiteCheckError(f"{label}: wrong local backend status")
    if local_backend.get("script") != "tools/gca_member_backend.py":
        raise SiteCheckError(f"{label}: wrong local backend script")
    if local_backend.get("localUrl") != "http://127.0.0.1:8787/members.html":
        raise SiteCheckError(f"{label}: wrong local backend URL")
    if local_backend.get("operatorConsoleUrl") != "http://127.0.0.1:8787/operator.html":
        raise SiteCheckError(f"{label}: wrong local operator console URL")
    if local_backend.get("dataDirectory") != ".gca_access_data/":
        raise SiteCheckError(f"{label}: wrong local backend data directory")
    if local_backend.get("sameOriginSubmissionOnLocalhost") is not True:
        raise SiteCheckError(f"{label}: local backend should use same-origin localhost submissions")
    if local_backend.get("localOperatorSummaryEndpoint") != "/gca/operator-summary":
        raise SiteCheckError(f"{label}: wrong local operator summary endpoint")
    if local_backend.get("localReviewPackageEndpoint") != "/gca/review-package":
        raise SiteCheckError(f"{label}: wrong local review package endpoint")
    if local_backend.get("localReviewPackageExporter") != "tools/export_gca_review_package.py":
        raise SiteCheckError(f"{label}: wrong local review package exporter")
    if local_backend.get("localReviewPackageVerifier") != "tools/verify_gca_review_package.py":
        raise SiteCheckError(f"{label}: wrong local review package verifier")
    if "redacted-public" not in local_backend.get("localReviewPackageRedactionModes", []):
        raise SiteCheckError(f"{label}: missing local review package redaction mode")
    if local_backend.get("publicProductionEndpointLive") is not False:
        raise SiteCheckError(f"{label}: local backend must not mark production live")
    if "credit_ledger" not in local_backend.get("writesJsonlLedgers", []):
        raise SiteCheckError(f"{label}: missing local credit ledger")
    if "member_benefit_transfers" not in local_backend.get("writesJsonlLedgers", []):
        raise SiteCheckError(f"{label}: missing local transfer ledger")
    if local_backend.get("transferReceiptVerificationMethod") != "Base Mainnet public RPC eth_getTransactionReceipt ERC-20 Transfer log":
        raise SiteCheckError(f"{label}: wrong transfer receipt verification method")
    if preview.get("status") != "browser-read-only-preview-live":
        raise SiteCheckError(f"{label}: wrong browser preview status")
    if preview.get("ledgerEffect") != "none":
        raise SiteCheckError(f"{label}: browser preview must not write ledger")
    if preview.get("requiresSignature") is not False:
        raise SiteCheckError(f"{label}: browser preview must not require signature")
    if preview.get("requiresTransaction") is not False:
        raise SiteCheckError(f"{label}: browser preview must not require transaction")
    if preview.get("finalEligibilityStillRequiresControlledAccountUi") is not True:
        raise SiteCheckError(f"{label}: browser preview must require controlled UI for final eligibility")
    if verification.get("publicLedgerSchemaUrl") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong public ledger schema URL")
    if verification.get("preparedMemberBenefitTransferEndpoint") != "/gca/member-benefit-transfers":
        raise SiteCheckError(f"{label}: wrong member benefit transfer endpoint")
    if privacy_terms.get("status") != "public-privacy-and-terms-published":
        raise SiteCheckError(f"{label}: wrong privacy and terms status")
    if privacy_terms.get("privacyNoticeUrl") != PRIVACY_NOTICE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong privacy notice URL")
    if privacy_terms.get("privacyNoticeJsonUrl") != PRIVACY_NOTICE_URL:
        raise SiteCheckError(f"{label}: wrong privacy JSON URL")
    if privacy_terms.get("participationTermsUrl") != PARTICIPATION_TERMS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong participation terms URL")
    if privacy_terms.get("participationTermsJsonUrl") != PARTICIPATION_TERMS_URL:
        raise SiteCheckError(f"{label}: wrong terms JSON URL")
    if support_intake.get("status") != "public-support-intake-published":
        raise SiteCheckError(f"{label}: wrong support intake status")
    if support_intake.get("pageUrl") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong support page URL")
    if support_intake.get("url") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong support JSON URL")
    if support_intake.get("directSubmissionEndpointConfigured") is not False:
        raise SiteCheckError(f"{label}: support direct submission must remain false")
    if support.get("contactEmail") != "GCAgochina@outlook.com":
        raise SiteCheckError(f"{label}: wrong support contact")
    if "ledger_recorded" not in support.get("reviewStatuses", []):
        raise SiteCheckError(f"{label}: missing ledger_recorded status")
    if not any("public self-service claiming is not connected" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing not-connected safe claim")
    if not any("browser-only read-only GCA balance preview" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing browser preview safe claim")
    if not any("manual transfer runbook" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing transfer runbook safe claim")
    if not any("credits or membership are cash" in claim for claim in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing cash/token do-not-claim boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_member_benefit_json(text: str) -> None:
    label = "/member-benefit.json"
    payload = load_json(text, label)
    token = payload.get("token", {})
    program = payload.get("program", {})
    boundaries = payload.get("publicClaimBoundaries", {})
    links = payload.get("publicLinks", {})

    if payload.get("schema") != MEMBER_BENEFIT_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != MEMBER_BENEFIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-review-rules-published-benefit-not-self-service":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if token.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if program.get("minimumHolding") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong minimum holding")
    if program.get("minimumHoldingPeriodDays") != 30:
        raise SiteCheckError(f"{label}: wrong holding period")
    if program.get("memberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit amount")
    if "no new minting" not in program.get("memberBenefitSource", ""):
        raise SiteCheckError(f"{label}: missing no-minting source boundary")
    if not any("1,000,000 GCA for 30 consecutive days" in item for item in payload.get("eligibilityRules", [])):
        raise SiteCheckError(f"{label}: missing 30-day eligibility rule")
    if "reserve-transfer" not in [step.get("id") for step in payload.get("reviewFlow", [])]:
        raise SiteCheckError(f"{label}: missing reserve transfer step")
    if "transferred" not in payload.get("allowedStatuses", []):
        raise SiteCheckError(f"{label}: missing transferred status")
    packet = payload.get("memberPacketEvidence", {})
    if packet.get("packetVersion") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong packet evidence version")
    if packet.get("packetObject") != "memberBenefitReviewEvidence":
        raise SiteCheckError(f"{label}: wrong packet evidence object")
    for field in ("holdingStartDate", "evidenceTxHash", "evidenceTxHashFormatOk"):
        if field not in packet.get("requiredFields", []):
            raise SiteCheckError(f"{label}: missing packet evidence field {field}")
    if packet.get("finalEligibilityStillRequiresSupportAndLedgerReview") is not True:
        raise SiteCheckError(f"{label}: packet evidence must require final review")
    if packet.get("doesNotCreateLedgerRecord") is not True:
        raise SiteCheckError(f"{label}: packet evidence must not create ledger")
    if not any("10,000 GCA member benefit is self-service claimable today" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing self-service boundary")
    if links.get("memberBenefitPage") != MEMBER_BENEFIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitPage")
    if links.get("memberBenefitJson") != MEMBER_BENEFIT_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitJson")
    if links.get("memberBenefitTransferPage") != MEMBER_BENEFIT_TRANSFER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitTransferPage")
    if links.get("memberBenefitTransferJson") != MEMBER_BENEFIT_TRANSFER_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitTransferJson")
    if links.get("memberProgram") != MEMBER_PROGRAM_URL:
        raise SiteCheckError(f"{label}: wrong memberProgram")
    if links.get("memberLedger") != MEMBER_LEDGER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberLedger")
    if links.get("support") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong support")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_member_benefit_page(text: str) -> None:
    label = "/member-benefit.html"
    assert_contains(text, "GCA Member Benefit Review", label)
    assert_contains(text, "Member Benefit JSON", label)
    assert_contains(text, "Transfer Runbook", label)
    assert_contains(text, "1,000,000 GCA", label)
    assert_contains(text, "30 consecutive days", label)
    assert_contains(text, "10,000 GCA", label)
    assert_contains(text, "Reserve transfer", label)
    assert_contains(text, "No minting and no automatic transfer", label)
    assert_contains(text, "holdingStartDate", label)
    assert_contains(text, "evidenceTxHash", label)
    assert_contains(text, "evidenceTxHashFormatOk", label)
    assert_contains(text, "Public Claim Boundaries", label)
    assert_contains(text, "self-service claimable today", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_no_forbidden_public_claims(text, label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def validate_member_benefit_transfer_json(text: str) -> None:
    label = "/member-benefit-transfer.json"
    payload = load_json(text, label)
    token = payload.get("token", {})
    policy = payload.get("transferPolicy", {})
    links = payload.get("publicLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != MEMBER_BENEFIT_TRANSFER_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != MEMBER_BENEFIT_TRANSFER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-member-benefit-transfer-runbook-published-transfer-not-automatic":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if token.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if token.get("mintingSupportedAfterDeployment") is not False:
        raise SiteCheckError(f"{label}: minting must remain false")
    if policy.get("memberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong benefit amount")
    if policy.get("sourceWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong source wallet")
    for key in ("mintingAllowed", "automaticTransferAllowed", "selfServiceClaimable"):
        if policy.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if policy.get("recipientMustEqualVerifiedMemberWallet") is not True:
        raise SiteCheckError(f"{label}: recipient rule must be true")
    for prerequisite in (
        "memberBenefitReviewEvidence packet version is gca_member_preregistration_v2",
        "evidenceTxHashFormatOk is true",
        "memberBenefitReviewEvidenceStatus is eligible",
        "no prior memberBenefitTransferTx exists for the same registered user",
    ):
        if prerequisite not in payload.get("approvalPrerequisites", []):
            raise SiteCheckError(f"{label}: missing prerequisite {prerequisite}")
    for step in (
        "confirm-review-record",
        "verify-current-balance",
        "prepare-wallet",
        "send-member-benefit",
        "record-transfer",
        "close-review",
    ):
        if step not in [item.get("id") for item in payload.get("manualTransferSteps", [])]:
            raise SiteCheckError(f"{label}: missing transfer step {step}")
    for field in (
        "memberLedgerId",
        "registrationId",
        "walletAddress",
        "memberBenefitAmount",
        "memberBenefitTransferTx",
        "sourceWallet",
        "recipientWallet",
        "reviewerNote",
    ):
        if field not in payload.get("requiredLedgerFieldsAfterTransfer", []):
            raise SiteCheckError(f"{label}: missing ledger field {field}")
    for forbidden in ("private key", "seed phrase", "exchange API secret", "withdrawal permission", "custody request"):
        if forbidden not in payload.get("doNotCollect", []):
            raise SiteCheckError(f"{label}: missing doNotCollect {forbidden}")
    if not any("manual transfer runbook" in item for item in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing runbook safe claim")
    if not any("self-service claimable today" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing self-service boundary")
    if links.get("memberBenefitTransferPage") != MEMBER_BENEFIT_TRANSFER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong transfer page")
    if links.get("memberBenefitTransferJson") != MEMBER_BENEFIT_TRANSFER_URL:
        raise SiteCheckError(f"{label}: wrong transfer json")
    if links.get("memberBenefitPage") != MEMBER_BENEFIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong member benefit page")
    if links.get("memberLedgerJson") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong member ledger json")
    if links.get("support") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong support")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_member_benefit_transfer_page(text: str) -> None:
    label = "/member-benefit-transfer.html"
    assert_contains(text, "GCA Member Benefit Transfer Runbook", label)
    assert_contains(text, "Transfer Runbook JSON", label)
    assert_contains(text, "10,000 GCA", label)
    assert_contains(text, "Owner reserve", label)
    assert_contains(text, "Manual only", label)
    assert_contains(text, "memberBenefitTransferTx", label)
    assert_contains(text, "gca_member_preregistration_v2", label)
    assert_contains(text, "memberBenefitReviewEvidenceStatus", label)
    assert_contains(text, "evidenceTxHashFormatOk", label)
    assert_contains(text, "Base Mainnet / chainId 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_contains(text, "Private key or seed phrase", label)
    assert_contains(text, "not self-service claimable", label)
    assert_contains(text, "Do not say holding 1,000,000 GCA automatically triggers a transfer", label)
    assert_no_forbidden_public_claims(text, label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def validate_member_ledger_json(text: str) -> None:
    label = "/member-ledger.json"
    payload = load_json(text, label)
    token = payload.get("token", {})
    urls = payload.get("publicUrls", {})
    paths = payload.get("preparedPaths", {})
    preview = payload.get("browserBalancePreview", {})
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
    if urls.get("memberAccessPreview") != "https://gcagochina.com/gca/member-access/":
        raise SiteCheckError(f"{label}: wrong memberAccessPreview")
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
    if preview.get("status") != "browser-read-only-preview-live":
        raise SiteCheckError(f"{label}: wrong browser balance preview status")
    if preview.get("ledgerEffect") != "none":
        raise SiteCheckError(f"{label}: browser balance preview must not write ledger")
    if preview.get("requiresSignature") is not False:
        raise SiteCheckError(f"{label}: browser balance preview must not require signature")
    if preview.get("requiresTransaction") is not False:
        raise SiteCheckError(f"{label}: browser balance preview must not require transaction")
    if preview.get("finalEligibilityStillRequiresControlledAccountUi") is not True:
        raise SiteCheckError(f"{label}: browser balance preview must require controlled UI for final eligibility")
    if thresholds.get("holderBonusMinimum") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder threshold")
    if thresholds.get("holderBonusCreditAmount") != "100 Web3 Radar utility credits":
        raise SiteCheckError(f"{label}: wrong credit amount")
    if thresholds.get("creditExpiryDaysAfterLedgerActivation") != 180:
        raise SiteCheckError(f"{label}: wrong credit expiry")
    if thresholds.get("gcaMemberMinimum") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member threshold")
    if thresholds.get("gcaMemberMinimumHoldingDays") != 30:
        raise SiteCheckError(f"{label}: wrong member holding days")
    if thresholds.get("gcaMemberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    if thresholds.get("memberRefreshDays") != 30:
        raise SiteCheckError(f"{label}: wrong member refresh")
    if "walletVerificationRecord" not in schemas:
        raise SiteCheckError(f"{label}: missing wallet verification schema")
    if "creditLedgerRecord" not in schemas:
        raise SiteCheckError(f"{label}: missing credit ledger schema")
    if "memberLedgerRecord" not in schemas:
        raise SiteCheckError(f"{label}: missing member ledger schema")
    if "memberBenefitReviewEvidenceRecord" not in schemas:
        raise SiteCheckError(f"{label}: missing member benefit evidence schema")
    if "supportReviewRecord" not in schemas:
        raise SiteCheckError(f"{label}: missing support review schema")
    prereg_fields = schemas.get("preRegistrationRecord", {}).get("requiredFields", [])
    if "memberBenefitReviewEvidence" not in prereg_fields:
        raise SiteCheckError(f"{label}: missing pre-registration evidence field")
    member_fields = schemas.get("memberLedgerRecord", {}).get("requiredFields", [])
    for field in (
        "holdingStartDate",
        "holdingPeriodPreviewEligible",
        "evidenceTxHash",
        "evidenceTxHashFormatOk",
        "memberBenefitReviewEvidenceStatus",
        "memberBenefitTransferTx",
    ):
        if field not in member_fields:
            raise SiteCheckError(f"{label}: missing member ledger field {field}")
    evidence = schemas.get("memberBenefitReviewEvidenceRecord", {})
    if evidence.get("packetVersion") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong evidence packet version")
    for field in (
        "holdingStartDate",
        "daysSinceHoldingStartPreview",
        "holdingPeriodPreviewEligible",
        "evidenceTxHash",
        "evidenceTxHashFormatOk",
        "evidenceNote",
        "doesNotCreateLedgerRecord",
    ):
        if field not in evidence.get("requiredFields", []):
            raise SiteCheckError(f"{label}: missing evidence field {field}")
    if "publicEvidenceReference" not in schemas.get("supportReviewRecord", {}).get("requiredFields", []):
        raise SiteCheckError(f"{label}: missing support evidence reference")
    if "ledger_recorded" not in schemas.get("supportReviewRecord", {}).get("allowedStatuses", []):
        raise SiteCheckError(f"{label}: missing ledger_recorded status")
    if not any("Public self-service claiming is not connected yet" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing not-connected safe claim")
    if not any("browser-only read-only GCA balance preview" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing browser preview safe claim")
    if not any("self-service claimable before controlled HTTPS account UI is live" in claim for claim in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing self-service boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_member_ledger_page(text: str) -> None:
    label = "/member-ledger.html"
    assert_contains(text, "GCA Member Ledger Schema", label)
    assert_contains(text, "Member Ledger JSON", label)
    assert_contains(text, "member-benefit.html", label)
    assert_contains(text, "Wallet Verification Record", label)
    assert_contains(text, "100 Credit Ledger", label)
    assert_contains(text, "GCA Member Ledger", label)
    assert_contains(text, "Support Review Record", label)
    assert_contains(text, "Member Benefit Evidence Record", label)
    assert_contains(text, "gca_member_preregistration_v2", label)
    assert_contains(text, "memberBenefitReviewEvidence", label)
    assert_contains(text, "holdingStartDate", label)
    assert_contains(text, "evidenceTxHash", label)
    assert_contains(text, "evidenceTxHashFormatOk", label)
    assert_contains(text, "memberBenefitReviewEvidenceStatus", label)
    assert_contains(text, "memberBenefitTransferTx", label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "/gca/member-access", label)
    assert_contains(text, "/gca/wallet-verifications", label)
    assert_contains(text, "/gca/credit-ledger", label)
    assert_contains(text, "/gca/member-ledger", label)
    assert_contains(text, "10,000 GCA", label)
    assert_contains(text, "1,000,000 GCA", label)
    assert_contains(text, "10,000 GCA after approval", label)
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
    if reserve.get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatement")
    if reserve.get("lpLockClaimed") is not False:
        raise SiteCheckError(f"{label}: LP lock must not be claimed")
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
    if payload.get("officialLinks", {}).get("technicalReport") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technicalReport")
    if payload.get("officialLinks", {}).get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatement link")
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
    assert_contains(text, "Reserve statement", label)
    assert_contains(text, "Technical Report", label)
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


def validate_reviewer_kit_json(text: str) -> None:
    label = "/reviewer-kit.json"
    payload = load_json(text, label)
    links = payload.get("officialLinks", {})
    market = payload.get("officialMarket", {})
    facts = payload.get("contractFacts", {})
    reviews = payload.get("externalReviewStatus", {})
    boundaries = payload.get("publicClaimBoundaries", {})
    evidence = payload.get("historicalFunctionalSwapEvidence", {})
    local_package = payload.get("localReviewPackage", {})

    if payload.get("schema") != REVIEWER_KIT_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != REVIEWER_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-reviewer-kit-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if links.get("verify") != "https://gcagochina.com/verify.html":
        raise SiteCheckError(f"{label}: wrong verify link")
    if links.get("reviewerKitPage") != REVIEWER_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKitPage")
    if links.get("reviewerKit") != REVIEWER_KIT_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKit")
    if links.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if links.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if links.get("platformRepliesPage") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesPage")
    if links.get("platformReplies") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong platformReplies")
    if links.get("trustCenterPage") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterPage")
    if links.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trustCenter")
    if links.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidence")
    if links.get("walletSecurityProfile") != WALLET_SECURITY_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong walletSecurityProfile")
    if links.get("tokenSafetyPage") != TOKEN_SAFETY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafetyPage")
    if links.get("tokenSafety") != TOKEN_SAFETY_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafety")
    if links.get("blockaidFollowupPage") != BLOCKAID_FOLLOWUP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowupPage")
    if links.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup")
    if links.get("externalReviewStatus") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatus")
    if links.get("onchainProofs") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofs")
    if links.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if links.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if links.get("trustCenterPage") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterPage")
    if links.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trustCenter")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if facts.get("sourceVerifiedOnBaseScan") is not True:
        raise SiteCheckError(f"{label}: source verification must be true")
    if facts.get("postDeploymentMintFunction") is not False:
        raise SiteCheckError(f"{label}: post-deployment mint must be false")
    if facts.get("ownerOrAdminRole") is not False:
        raise SiteCheckError(f"{label}: owner/admin role must be false")
    if facts.get("transferTaxOrHiddenFee") is not False:
        raise SiteCheckError(f"{label}: transfer tax must be false")
    if facts.get("thirdPartyAuditCompleted") is not False:
        raise SiteCheckError(f"{label}: third-party audit must be false")
    if reviews.get("baseScanTokenProfile") != "resubmitted-awaiting-review":
        raise SiteCheckError(f"{label}: wrong BaseScan profile status")
    if reviews.get("blockaidMetaMask") != "owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong Blockaid status")
    if reviews.get("blockaidFollowUpSubmissionDate") != "2026-05-13":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up date")
    if reviews.get("geckoTerminal") != "approved-2026-05-11":
        raise SiteCheckError(f"{label}: wrong GeckoTerminal status")
    if reviews.get("coinGecko") != "deferred":
        raise SiteCheckError(f"{label}: wrong CoinGecko status")
    if evidence.get("status") != "observed-historical-functional-evidence-only":
        raise SiteCheckError(f"{label}: wrong functional evidence status")
    if local_package.get("status") != "local-export-tool-ready":
        raise SiteCheckError(f"{label}: wrong local review package status")
    if local_package.get("offlineExportTool") != "tools/export_gca_review_package.py":
        raise SiteCheckError(f"{label}: wrong local package export tool")
    if local_package.get("verificationTool") != "tools/verify_gca_review_package.py":
        raise SiteCheckError(f"{label}: wrong local package verification tool")
    if local_package.get("recommendedExternalMode") != "redacted-public":
        raise SiteCheckError(f"{label}: wrong local package external mode")
    if "redacted-public" not in local_package.get("redactionModes", []):
        raise SiteCheckError(f"{label}: missing local package redaction mode")
    for key in ("requiresPrivateKey", "requiresSeedPhrase", "requiresWalletSignature", "sendsTransaction", "automaticTokenTransfer"):
        if local_package.get("boundaries", {}).get(key) is not False:
            raise SiteCheckError(f"{label}: local package boundary {key} must be false")
    if SWAP_TEST_BUY_TX not in evidence.get("buyTestTransactions", []):
        raise SiteCheckError(f"{label}: missing buy test transaction")
    if SWAP_TEST_SELL_TX not in evidence.get("sellTestTransactions", []):
        raise SiteCheckError(f"{label}: missing sell test transaction")
    if "No third-party audit has been completed." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "security-vendor approval, permanent warning-free status, or cross-wallet warning removal before vendor/current wallet UI confirms it" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing warning boundary")
    assert_current_pool_text(json.dumps(payload), label)


def validate_reviewer_kit_page(text: str) -> None:
    label = "/reviewer-kit.html"
    assert_contains(text, "GCA Reviewer Kit", label)
    assert_contains(text, "Reviewer Kit JSON", label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "GCA/USDT", label)
    assert_contains(text, "Contract Facts", label)
    assert_contains(text, "Blockaid / MetaMask", label)
    assert_contains(text, "Blockaid Follow-up", label)
    assert_contains(text, "Follow-up submitted on 2026-05-13", label)
    assert_contains(text, "BaseScan Profile", label)
    assert_contains(text, "On-chain Proofs", label)
    assert_contains(text, "Local Review Package", label)
    assert_contains(text, "tools/export_gca_review_package.py", label)
    assert_contains(text, "redacted-public", label)
    assert_contains(text, "packageDigestSha256", label)
    assert_contains(text, "tools/verify_gca_review_package.py", label)
    assert_contains(text, "External Review Status", label)
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "Public Claim Boundaries", label)
    assert_contains(text, "No third-party audit has been completed", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)


def validate_platform_replies_json(text: str) -> None:
    label = "/platform-replies.json"
    payload = load_json(text, label)
    links = payload.get("officialLinks", {})
    market = payload.get("officialMarket", {})
    rules = payload.get("replyRules", {})
    templates = payload.get("replyTemplates", {})

    if payload.get("schema") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-platform-reply-kit-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("officialEmail") != "GCAgochina@outlook.com":
        raise SiteCheckError(f"{label}: wrong officialEmail")
    if links.get("platformRepliesPage") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesPage")
    if links.get("platformReplies") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong platformReplies")
    if links.get("trustCenterPage") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterPage")
    if links.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trustCenter")
    if links.get("reviewerKitPage") != REVIEWER_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKitPage")
    if links.get("reviewerKit") != REVIEWER_KIT_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKit")
    if links.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if links.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if links.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidence")
    if links.get("externalReviewStatus") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatus")
    if links.get("onchainProofs") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofs")
    if links.get("brandKit") != BRAND_KIT_URL:
        raise SiteCheckError(f"{label}: wrong brandKit")
    if links.get("marketQuality") != MARKET_QUALITY_URL:
        raise SiteCheckError(f"{label}: wrong marketQuality")
    if links.get("listingReadiness") != LISTING_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong listingReadiness")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if market.get("geckoTerminal") != OFFICIAL_GECKOTERMINAL_URL:
        raise SiteCheckError(f"{label}: wrong geckoTerminal")
    if market.get("dexScreener") != OFFICIAL_DEXSCREENER_URL:
        raise SiteCheckError(f"{label}: wrong dexScreener")
    for key in (
        "walletWarningReviewer",
        "baseScanProfile",
        "metadataCorrection",
        "localReviewPackageHandoff",
        "communityModerator",
        "trackedListingNotReady",
    ):
        if key not in templates:
            raise SiteCheckError(f"{label}: missing {key} template")
    wallet_body = "\n".join(templates.get("walletWarningReviewer", {}).get("body", []))
    if "Blockaid false-positive report was submitted on 2026-05-10" not in wallet_body:
        raise SiteCheckError(f"{label}: missing Blockaid report date")
    if "follow-up was submitted on 2026-05-13" not in wallet_body:
        raise SiteCheckError(f"{label}: missing Blockaid follow-up date")
    if "The owner observed no wallet risk warning visible on 2026-05-14; no security-vendor approval is claimed." not in wallet_body:
        raise SiteCheckError(f"{label}: missing warning boundary")
    local_package_body = "\n".join(templates.get("localReviewPackageHandoff", {}).get("body", []))
    for expected in (
        "redacted-public",
        "tools/export_gca_review_package.py",
        "packageDigestSha256",
        "tools/verify_gca_review_package.py",
        "support evidence only",
    ):
        if expected not in local_package_body:
            raise SiteCheckError(f"{label}: local review package template missing {expected}")
    if not any("wallet-security reviewer asks for more evidence" in item for item in rules.get("useWhen", [])):
        raise SiteCheckError(f"{label}: missing wallet-security use rule")
    if not any("redacted local member-ledger review package" in item for item in rules.get("useWhen", [])):
        raise SiteCheckError(f"{label}: missing local package use rule")
    if "the reply would claim security-vendor approval or permanent warning-free status before confirmation" not in rules.get("doNotUseWhen", []):
        raise SiteCheckError(f"{label}: missing warning do-not-use rule")
    if "No third-party audit has been completed." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "security-vendor approval, permanent warning-free status, or cross-wallet warning removal before vendor/current wallet UI confirms it" not in payload.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing warning do-not-claim")
    assert_current_pool_text(json.dumps(payload), label)


def validate_platform_replies_page(text: str) -> None:
    label = "/platform-replies.html"
    assert_contains(text, "GCA Platform Replies", label)
    assert_contains(text, "Platform Replies JSON", label)
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "Wallet Warning Reviewer", label)
    assert_contains(text, "BaseScan Token Profile", label)
    assert_contains(text, "Metadata Correction", label)
    assert_contains(text, "Local Review Package Handoff", label)
    assert_contains(text, "Community Moderator", label)
    assert_contains(text, "Tracked Listing Not Ready", label)
    assert_contains(text, "Blockaid false-positive report was submitted on 2026-05-10", label)
    assert_contains(text, "follow-up was submitted on 2026-05-13", label)
    assert_contains(text, "Owner observed no wallet risk warning visible on 2026-05-14; no security-vendor approval is claimed", label)
    assert_contains(text, "redacted-public", label)
    assert_contains(text, "tools/export_gca_review_package.py", label)
    assert_contains(text, "packageDigestSha256", label)
    assert_contains(text, "tools/verify_gca_review_package.py", label)
    assert_contains(text, "support evidence only", label)
    assert_contains(text, "External audit completion before an independent report is published", label)
    assert_contains(text, "no completed third-party audit", label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)


def validate_trust_json(text: str) -> None:
    label = "/trust.json"
    payload = load_json(text, label)
    links = payload.get("officialLinks", {})
    snapshot = payload.get("verificationSnapshot", {})
    facts = payload.get("contractFacts", {})
    market = payload.get("officialMarket", {})
    supply = payload.get("supplyDisclosure", {})
    reviews = payload.get("externalReviewStatus", {})

    if payload.get("schema") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-trust-center-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("officialEmail") != "GCAgochina@outlook.com":
        raise SiteCheckError(f"{label}: wrong officialEmail")
    if links.get("trustCenterPage") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterPage")
    if links.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trustCenter")
    for key, expected in {
        "verify": "https://gcagochina.com/verify.html",
        "reviewerKit": REVIEWER_KIT_URL,
        "platformReplies": PLATFORM_REPLIES_URL,
        "walletWarningEvidence": WALLET_WARNING_URL,
        "blockaidFollowup": BLOCKAID_FOLLOWUP_URL,
        "walletSecurityProfile": WALLET_SECURITY_PROFILE_URL,
        "tokenSafetyPage": TOKEN_SAFETY_PAGE_URL,
        "tokenSafety": TOKEN_SAFETY_URL,
        "externalReviewStatus": EXTERNAL_REVIEW_URL,
        "onchainProofs": ONCHAIN_PROOFS_URL,
        "brandKit": BRAND_KIT_URL,
        "marketQuality": MARKET_QUALITY_URL,
        "listingReadiness": LISTING_READINESS_URL,
        "supplyDisclosure": SUPPLY_DISCLOSURE_URL,
        "projectJson": "https://gcagochina.com/project.json",
        "tokenList": "https://gcagochina.com/tokenlist.json",
    }.items():
        if links.get(key) != expected:
            raise SiteCheckError(f"{label}: wrong {key} link")
    if snapshot.get("baseScanSource") != "verified":
        raise SiteCheckError(f"{label}: wrong BaseScan source status")
    if snapshot.get("baseScanOwnership") != "verified":
        raise SiteCheckError(f"{label}: wrong BaseScan ownership status")
    if snapshot.get("baseScanTokenProfile") != "resubmitted-awaiting-review":
        raise SiteCheckError(f"{label}: wrong BaseScan token profile status")
    if snapshot.get("geckoTerminalTokenInfo") != "approved-2026-05-11":
        raise SiteCheckError(f"{label}: wrong GeckoTerminal status")
    if snapshot.get("walletWarning") != "owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong wallet warning status")
    if snapshot.get("blockaidFollowUpDate") != "2026-05-13":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up date")
    if facts.get("sourceVerifiedOnBaseScan") is not True:
        raise SiteCheckError(f"{label}: source verification must be true")
    if facts.get("fixedSupply") is not True:
        raise SiteCheckError(f"{label}: fixed supply must be true")
    if facts.get("totalSupply") != "1000000000":
        raise SiteCheckError(f"{label}: wrong totalSupply")
    for key in (
        "postDeploymentMintFunction",
        "ownerOrAdminRole",
        "proxyOrUpgradePath",
        "blacklistFunction",
        "pauseFunction",
        "transferTaxOrHiddenFee",
        "custodyOrWithdrawalPath",
        "thirdPartyAuditCompleted",
    ):
        if facts.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if market.get("geckoTerminal") != OFFICIAL_GECKOTERMINAL_URL:
        raise SiteCheckError(f"{label}: wrong geckoTerminal")
    if market.get("dexScreener") != OFFICIAL_DEXSCREENER_URL:
        raise SiteCheckError(f"{label}: wrong dexScreener")
    if supply.get("ownerReserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong ownerReserveWallet")
    if supply.get("ownerReserveTransferTxs") != [RESERVE_TX_1, RESERVE_TX_2]:
        raise SiteCheckError(f"{label}: wrong reserve transfer txs")
    if payload.get("blockaidFollowup", {}).get("status") != "public-blockaid-followup-package-published":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up status")
    if payload.get("blockaidFollowup", {}).get("url") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up URL")
    if reviews.get("thirdPartyAudit") != "not-completed-deferred":
        raise SiteCheckError(f"{label}: wrong third-party audit status")
    if "No third-party audit has been completed." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "security-vendor approval, permanent warning-free status, or cross-wallet warning removal before vendor/current wallet UI confirms it" not in payload.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing warning do-not-claim")
    assert_current_pool_text(json.dumps(payload), label)


def validate_trust_page(text: str) -> None:
    label = "/trust.html"
    assert_contains(text, "GCA Trust Center", label)
    assert_contains(text, "Trust Center JSON", label)
    assert_contains(text, "Verification Snapshot", label)
    assert_contains(text, "Contract Facts", label)
    assert_contains(text, "Market And Liquidity", label)
    assert_contains(text, "Supply And Reserve", label)
    assert_contains(text, "Evidence Links", label)
    assert_contains(text, "Blockaid Follow-up", label)
    assert_contains(text, "Public Claim Boundaries", label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "BaseScan source code", label)
    assert_contains(text, "Resubmitted: awaiting review", label)
    assert_contains(text, "Approved 2026-05-11", label)
    assert_contains(text, "Owner observed no warning visible", label)
    assert_contains(text, "No completed third-party audit", label)
    assert_contains(text, "Post-deployment mint function", label)
    assert_contains(text, "Transfer tax or hidden fee", label)
    assert_contains(text, "not a lock, vesting contract, or multisig", label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_contains(text, "Do not claim security-vendor approval, permanent warning-free status, or cross-wallet warning removal before vendor/current wallet UI confirms it", label)
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
    if links.get("blockaidFollowupPage") != BLOCKAID_FOLLOWUP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowupPage")
    if links.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup")
    if links.get("trustCenterPage") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterPage")
    if links.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trustCenter")
    if links.get("marketQualityPage") != MARKET_QUALITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong marketQualityPage")
    if links.get("onchainProofsPage") != ONCHAIN_PROOFS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsPage")
    if links.get("onchainProofs") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofs")
    if links.get("walletSecurityProfile") != WALLET_SECURITY_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong walletSecurityProfile")
    if links.get("tokenSafetyPage") != TOKEN_SAFETY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafetyPage")
    if links.get("tokenSafety") != TOKEN_SAFETY_URL:
        raise SiteCheckError(f"{label}: wrong tokenSafety")
    if market.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialPair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if reviews.get("baseScanSource", {}).get("status") != "verified":
        raise SiteCheckError(f"{label}: wrong BaseScan source status")
    if reviews.get("baseScanTokenProfile", {}).get("status") != "resubmitted-awaiting-review":
        raise SiteCheckError(f"{label}: wrong BaseScan profile status")
    blockaid = reviews.get("blockaidMetaMask", {})
    if blockaid.get("status") != "owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong Blockaid status")
    if blockaid.get("submissionDate") != "2026-05-10":
        raise SiteCheckError(f"{label}: wrong Blockaid submission date")
    if blockaid.get("followUpSubmissionDate") != "2026-05-13":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up date")
    if blockaid.get("riskFactorFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong Blockaid risk-factor follow-up URL")
    if blockaid.get("followUpSubmissionResult") != "Blockaid support portal returned HTTP 200 OK":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up result")
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
    assert_contains(text, "Blockaid Follow-up", label)
    assert_contains(text, "External Reviews JSON", label)
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "Resubmitted: awaiting review", label)
    assert_contains(text, "Owner observed no warning visible 2026-05-14", label)
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
    if payload.get("status") != "warning-report-submitted-owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if links.get("onchainProofsPage") != ONCHAIN_PROOFS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsPage")
    if links.get("onchainProofs") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofs")
    if links.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if report.get("status") != "owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong Blockaid report status")
    if report.get("submissionDate") != "2026-05-10":
        raise SiteCheckError(f"{label}: wrong Blockaid submission date")
    if report.get("followUpSubmissionDate") != "2026-05-13":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up date")
    if report.get("followUpSubmissionResult") != "Blockaid support portal returned HTTP 200 OK":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up result")
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
    assert_contains(text, "Wallet Security JSON", label)
    assert_contains(text, "Blockaid Follow-up", label)
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "Follow-up submitted 2026-05-13", label)
    assert_contains(text, "Owner observed no warning visible 2026-05-14", label)
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
        "https://gcagochina.com/status.html",
        "https://gcagochina.com/listing-kit.html",
        "https://gcagochina.com/whitepaper.html",
        "https://gcagochina.com/buy.html",
        "https://gcagochina.com/markets.html",
        "https://gcagochina.com/security.html",
        "https://gcagochina.com/risk.html",
        "https://gcagochina.com/faq.html",
        "https://gcagochina.com/wallet-warning.html",
        "https://gcagochina.com/wallet-warning.json",
        "https://gcagochina.com/reviewer-kit.html",
        "https://gcagochina.com/reviewer-kit.json",
        "https://gcagochina.com/platform-replies.html",
        "https://gcagochina.com/platform-replies.json",
        "https://gcagochina.com/trust.html",
        "https://gcagochina.com/trust.json",
        "https://gcagochina.com/market-quality.html",
        "https://gcagochina.com/market-quality.json",
        "https://gcagochina.com/token-safety.html",
        "https://gcagochina.com/token-safety.json",
        "https://gcagochina.com/blockaid-followup.html",
        "https://gcagochina.com/blockaid-followup.json",
        "https://gcagochina.com/technical-report.html",
        "https://gcagochina.com/technical-report.json",
        "https://gcagochina.com/reserve-statement.html",
        "https://gcagochina.com/reserve-statement.json",
        "https://gcagochina.com/brand-kit.html",
        "https://gcagochina.com/brand-kit.json",
        "https://gcagochina.com/onchain-proofs.html",
        "https://gcagochina.com/onchain-proofs.json",
        "https://gcagochina.com/external-reviews.html",
        "https://gcagochina.com/external-reviews.json",
        "https://gcagochina.com/roadmap.html",
        "https://gcagochina.com/roadmap.json",
        "https://gcagochina.com/community.html",
        "https://gcagochina.com/community.json",
        "https://gcagochina.com/narrative.html",
        "https://gcagochina.com/narrative.json",
        "https://gcagochina.com/radar.html",
        "https://gcagochina.com/radar.json",
        "https://gcagochina.com/gca/member-access/",
        "https://gcagochina.com/member-program.json",
        "https://gcagochina.com/member-ledger.html",
        "https://gcagochina.com/member-ledger.json",
        "https://gcagochina.com/member-benefit.html",
        "https://gcagochina.com/member-benefit.json",
        "https://gcagochina.com/member-benefit-transfer.html",
        "https://gcagochina.com/member-benefit-transfer.json",
        "https://gcagochina.com/operator.html",
        "https://gcagochina.com/support.html",
        "https://gcagochina.com/support.json",
        "https://gcagochina.com/privacy.html",
        "https://gcagochina.com/privacy.json",
        "https://gcagochina.com/terms.html",
        "https://gcagochina.com/terms.json",
        "https://gcagochina.com/utility.html",
        "https://gcagochina.com/utility.json",
        "https://gcagochina.com/product.html",
        "https://gcagochina.com/product.json",
        "https://gcagochina.com/access.html",
        "https://gcagochina.com/access.json",
        "https://gcagochina.com/operations.html",
        "https://gcagochina.com/operations.json",
        "https://gcagochina.com/access-api.html",
        "https://gcagochina.com/access-api.json",
        "https://gcagochina.com/review-queue.html",
        "https://gcagochina.com/review-queue.json",
        "https://gcagochina.com/credits.html",
        "https://gcagochina.com/credits.json",
        "https://gcagochina.com/release-gates.html",
        "https://gcagochina.com/release-gates.json",
        "https://gcagochina.com/supply.json",
        "https://gcagochina.com/listing-readiness.html",
        "https://gcagochina.com/listing-readiness.json",
        "https://gcagochina.com/project.json",
        "https://gcagochina.com/tokenlist.json",
        "https://gcagochina.com/.well-known/gca-token.json",
        "https://gcagochina.com/.well-known/wallet-security.json",
        "https://gcagochina.com/.well-known/security.txt",
    ):
        assert_contains(text, expected, label)


def validate_robots(text: str) -> None:
    label = "/robots.txt"
    assert_contains(text, "Allow: /status.html", label)
    assert_contains(text, "Allow: /listing-kit.html", label)
    assert_contains(text, "Allow: /whitepaper.html", label)
    assert_contains(text, "Allow: /buy.html", label)
    assert_contains(text, "Allow: /security.html", label)
    assert_contains(text, "Allow: /risk.html", label)
    assert_contains(text, "Allow: /faq.html", label)
    assert_contains(text, "Allow: /wallet-warning.html", label)
    assert_contains(text, "Allow: /brand-kit.html", label)
    assert_contains(text, "Allow: /brand-kit.json", label)
    assert_contains(text, "Allow: /reviewer-kit.html", label)
    assert_contains(text, "Allow: /reviewer-kit.json", label)
    assert_contains(text, "Allow: /platform-replies.html", label)
    assert_contains(text, "Allow: /platform-replies.json", label)
    assert_contains(text, "Allow: /trust.html", label)
    assert_contains(text, "Allow: /trust.json", label)
    assert_contains(text, "Allow: /wallet-warning.json", label)
    assert_contains(text, "Allow: /listing-readiness.html", label)
    assert_contains(text, "Allow: /listing-readiness.json", label)
    assert_contains(text, "Allow: /external-reviews.html", label)
    assert_contains(text, "Allow: /external-reviews.json", label)
    assert_contains(text, "Allow: /roadmap.html", label)
    assert_contains(text, "Allow: /roadmap.json", label)
    assert_contains(text, "Allow: /community.html", label)
    assert_contains(text, "Allow: /community.json", label)
    assert_contains(text, "Allow: /narrative.html", label)
    assert_contains(text, "Allow: /narrative.json", label)
    assert_contains(text, "Allow: /radar.html", label)
    assert_contains(text, "Allow: /radar.json", label)
    assert_contains(text, "Allow: /market-quality.html", label)
    assert_contains(text, "Allow: /market-quality.json", label)
    assert_contains(text, "Allow: /token-safety.html", label)
    assert_contains(text, "Allow: /token-safety.json", label)
    assert_contains(text, "Allow: /blockaid-followup.html", label)
    assert_contains(text, "Allow: /blockaid-followup.json", label)
    assert_contains(text, "Allow: /technical-report.html", label)
    assert_contains(text, "Allow: /technical-report.json", label)
    assert_contains(text, "Allow: /reserve-statement.html", label)
    assert_contains(text, "Allow: /reserve-statement.json", label)
    assert_contains(text, "Allow: /supply.json", label)
    assert_contains(text, "Allow: /onchain-proofs.html", label)
    assert_contains(text, "Allow: /onchain-proofs.json", label)
    assert_contains(text, "Allow: /member-ledger.html", label)
    assert_contains(text, "Allow: /member-ledger.json", label)
    assert_contains(text, "Allow: /member-benefit.html", label)
    assert_contains(text, "Allow: /member-benefit.json", label)
    assert_contains(text, "Allow: /member-benefit-transfer.html", label)
    assert_contains(text, "Allow: /member-benefit-transfer.json", label)
    assert_contains(text, "Allow: /operator.html", label)
    assert_contains(text, "Allow: /member-program.json", label)
    assert_contains(text, "Allow: /gca/member-access/", label)
    assert_contains(text, "Allow: /support.html", label)
    assert_contains(text, "Allow: /support.json", label)
    assert_contains(text, "Allow: /privacy.html", label)
    assert_contains(text, "Allow: /privacy.json", label)
    assert_contains(text, "Allow: /terms.html", label)
    assert_contains(text, "Allow: /terms.json", label)
    assert_contains(text, "Allow: /utility.html", label)
    assert_contains(text, "Allow: /utility.json", label)
    assert_contains(text, "Allow: /product.html", label)
    assert_contains(text, "Allow: /product.json", label)
    assert_contains(text, "Allow: /access.html", label)
    assert_contains(text, "Allow: /access.json", label)
    assert_contains(text, "Allow: /operations.html", label)
    assert_contains(text, "Allow: /operations.json", label)
    assert_contains(text, "Allow: /access-api.html", label)
    assert_contains(text, "Allow: /access-api.json", label)
    assert_contains(text, "Allow: /review-queue.html", label)
    assert_contains(text, "Allow: /review-queue.json", label)
    assert_contains(text, "Allow: /credits.html", label)
    assert_contains(text, "Allow: /credits.json", label)
    assert_contains(text, "Allow: /release-gates.html", label)
    assert_contains(text, "Allow: /release-gates.json", label)
    assert_contains(text, "Allow: /.well-known/gca-token.json", label)
    assert_contains(text, "Allow: /.well-known/wallet-security.json", label)
    assert_contains(text, "Allow: /.well-known/security.txt", label)
    assert_contains(text, "Sitemap: https://gcagochina.com/sitemap.xml", label)


CHECKS: list[EndpointCheck] = [
    ("/", validate_root),
    ("/verify.html", validate_verify),
    ("/status.html", validate_status_page),
    ("/listing-kit.html", validate_listing_kit_page),
    ("/whitepaper.html", validate_whitepaper_page),
    ("/buy.html", validate_buy_page),
    ("/markets.html", validate_markets),
    ("/security.html", validate_security_page),
    ("/risk.html", validate_risk_page),
    ("/faq.html", validate_faq_page),
    ("/wallet-warning.html", validate_wallet_warning_page),
    ("/wallet-warning.json", validate_wallet_warning_json),
    ("/reviewer-kit.html", validate_reviewer_kit_page),
    ("/reviewer-kit.json", validate_reviewer_kit_json),
    ("/platform-replies.html", validate_platform_replies_page),
    ("/platform-replies.json", validate_platform_replies_json),
    ("/trust.html", validate_trust_page),
    ("/trust.json", validate_trust_json),
    ("/external-reviews.html", validate_external_reviews_page),
    ("/external-reviews.json", validate_external_reviews_json),
    ("/market-quality.html", validate_market_quality_page),
    ("/market-quality.json", validate_market_quality_json),
    ("/token-safety.html", validate_token_safety_page),
    ("/token-safety.json", validate_token_safety_json),
    ("/blockaid-followup.html", validate_blockaid_followup_page),
    ("/blockaid-followup.json", validate_blockaid_followup_json),
    ("/technical-report.html", validate_technical_report_page),
    ("/technical-report.json", validate_technical_report_json),
    ("/reserve-statement.html", validate_reserve_statement_page),
    ("/reserve-statement.json", validate_reserve_statement_json),
    ("/brand-kit.html", validate_brand_kit_page),
    ("/brand-kit.json", validate_brand_kit_json),
    ("/onchain-proofs.html", validate_onchain_proofs_page),
    ("/onchain-proofs.json", validate_onchain_proofs_json),
    ("/supply.html", validate_supply_page),
    ("/supply.json", validate_supply_json),
    ("/members.html", validate_members),
    ("/gca/member-access/", validate_member_access_page),
    ("/member-program.json", validate_member_program_json),
    ("/member-ledger.html", validate_member_ledger_page),
    ("/member-ledger.json", validate_member_ledger_json),
    ("/member-benefit.html", validate_member_benefit_page),
    ("/member-benefit.json", validate_member_benefit_json),
    ("/member-benefit-transfer.html", validate_member_benefit_transfer_page),
    ("/member-benefit-transfer.json", validate_member_benefit_transfer_json),
    ("/operator.html", validate_operator_page),
    ("/support.html", validate_support_page),
    ("/support.json", validate_support_json),
    ("/roadmap.html", validate_roadmap_page),
    ("/roadmap.json", validate_roadmap_json),
    ("/community.html", validate_community_page),
    ("/community.json", validate_community_json),
    ("/narrative.html", validate_narrative_page),
    ("/narrative.json", validate_narrative_json),
    ("/radar.html", validate_radar_page),
    ("/radar.json", validate_radar_json),
    ("/utility.html", validate_utility_page),
    ("/utility.json", validate_utility_json),
    ("/product.html", validate_product_page),
    ("/product.json", validate_product_json),
    ("/access.html", validate_access_page),
    ("/access.json", validate_access_json),
    ("/operations.html", validate_operations_page),
    ("/operations.json", validate_operations_json),
    ("/access-api.html", validate_access_api_page),
    ("/access-api.json", validate_access_api_json),
    ("/review-queue.html", validate_review_queue_page),
    ("/review-queue.json", validate_review_queue_json),
    ("/credits.html", validate_credits_page),
    ("/credits.json", validate_credits_json),
    ("/release-gates.html", validate_release_gates_page),
    ("/release-gates.json", validate_release_gates_json),
    ("/privacy.html", validate_privacy_page),
    ("/privacy.json", validate_privacy_json),
    ("/terms.html", validate_terms_page),
    ("/terms.json", validate_terms_json),
    ("/listing-readiness.html", validate_listing_readiness_page),
    ("/listing-readiness.json", validate_listing_readiness_json),
    ("/project.json", validate_project_json),
    ("/tokenlist.json", validate_tokenlist_json),
    ("/.well-known/gca-token.json", validate_well_known_json),
    ("/.well-known/wallet-security.json", validate_wallet_security_json),
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
