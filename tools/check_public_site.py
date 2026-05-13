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
X_URL = "https://x.com/XXYRadar"
OFFICIAL_POOL_ADDRESS = "0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0"
BASE_USDT_ADDRESS = "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"
OLD_WETH_POOL_ADDRESS = "0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff"
OFFICIAL_GECKOTERMINAL_URL = f"https://www.geckoterminal.com/base/pools/{OFFICIAL_POOL_ADDRESS}"
OFFICIAL_DEXSCREENER_URL = f"https://dexscreener.com/base/{OFFICIAL_POOL_ADDRESS}"
MEMBER_PROGRAM_URL = "https://gcagochina.com/member-program.json"
MEMBER_LEDGER_PAGE_URL = "https://gcagochina.com/member-ledger.html"
MEMBER_LEDGER_URL = "https://gcagochina.com/member-ledger.json"
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
PRIVACY_NOTICE_PAGE_URL = "https://gcagochina.com/privacy.html"
PRIVACY_NOTICE_URL = "https://gcagochina.com/privacy.json"
PARTICIPATION_TERMS_PAGE_URL = "https://gcagochina.com/terms.html"
PARTICIPATION_TERMS_URL = "https://gcagochina.com/terms.json"
WALLET_WARNING_PAGE_URL = "https://gcagochina.com/wallet-warning.html"
WALLET_WARNING_URL = "https://gcagochina.com/wallet-warning.json"
WALLET_SECURITY_PROFILE_URL = "https://gcagochina.com/.well-known/wallet-security.json"
TOKEN_SAFETY_PAGE_URL = "https://gcagochina.com/token-safety.html"
TOKEN_SAFETY_URL = "https://gcagochina.com/token-safety.json"
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
    assert_contains(text, "Platform Replies", label)
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "Token Safety", label)
    assert_contains(text, "Listing Readiness", label)
    assert_contains(text, "On-chain Proofs", label)
    assert_contains(text, "Brand Kit", label)
    assert_contains(text, "Member Ledger", label)
    assert_contains(text, "Support & Intake", label)
    assert_contains(text, "Roadmap", label)
    assert_contains(text, "Community Kit", label)
    assert_contains(text, "Narrative System", label)
    assert_contains(text, "Weekly Radar", label)
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


def validate_token_safety_page(text: str) -> None:
    label = "/token-safety.html"
    assert_contains(text, "GCA Token Safety Checklist", label)
    assert_contains(text, "Token Safety JSON", label)
    assert_contains(text, "Wallet Security JSON", label)
    assert_contains(text, "Verified Positive Controls", label)
    assert_contains(text, "Pending Or Not Claimed", label)
    assert_contains(text, "No mint function", label)
    assert_contains(text, "No third-party audit", label)
    assert_contains(text, "warning removal before visible confirmation", label)
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
    if pending.get("blockaidMetaMaskWarning") != "submitted-warning-removal-not-confirmed":
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
    if links.get("walletSecurityProfile") != WALLET_SECURITY_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong walletSecurityProfile")
    if links.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong walletWarningEvidence")
    if "No third-party audit has been completed." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "Blockaid or MetaMask warning removal before visible confirmation" not in payload.get("publicClaimBoundaries", {}).get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing warning-removal boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_members(text: str) -> None:
    label = "/members.html"
    assert_contains(text, "GCA Member Pre-Registration", label)
    assert_contains(text, "member access preview", label)
    assert_contains(text, "gca/member-access/", label)
    assert_contains(text, "100 Credit Rules", label)
    assert_contains(text, "Member Rules", label)
    assert_contains(text, "Support Workflow", label)
    assert_contains(text, "Check On-chain Balance", label)
    assert_contains(text, "browser-only preview reads GCA balance", label)
    assert_contains(text, "eth_call", label)
    assert_contains(text, "wallet_switchEthereumChain", label)
    assert_contains(text, "doesNotCreateLedgerRecord", label)
    assert_contains(text, "member-program.json", label)
    assert_contains(text, "member-ledger.html", label)
    assert_contains(text, "member-ledger.json", label)
    assert_contains(text, "support.html", label)
    assert_contains(text, "privacy.html", label)
    assert_contains(text, "terms.html", label)
    assert_contains(text, "180 days", label)
    assert_contains(text, "30 days", label)
    assert_contains(text, "5-10 business days", label)
    assert_contains(text, "Direct submission is not connected", label)
    assert_contains(text, "No cash, token rebate, income, reimbursement, trading permission, or risk-control bypass", label)
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


def validate_support_page(text: str) -> None:
    label = "/support.html"
    assert_contains(text, "GCA Support & Intake", label)
    assert_contains(text, "Support JSON", label)
    assert_contains(text, "GCAgochina@outlook.com", label)
    assert_contains(text, "Direct Submit", label)
    assert_contains(text, "Not connected", label)
    assert_contains(text, "Private key or seed phrase", label)
    assert_contains(text, "Exchange API secret or withdrawal permission", label)
    assert_contains(text, "Support Workflow", label)
    assert_contains(text, "Support Cannot Do", label)
    assert_contains(text, "Base Mainnet / chainId 8453", label)
    assert_contains(text, "GCA/USDT", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def validate_support_json(text: str) -> None:
    label = "/support.json"
    payload = load_json(text, label)
    submission = payload.get("currentSubmissionMode", {})
    workflow = payload.get("supportWorkflow", {})
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
    if identity.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong official pair")
    if identity.get("officialPool") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong official pool")
    if links.get("supportPage") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong support page link")
    if links.get("supportJson") != SUPPORT_URL:
        raise SiteCheckError(f"{label}: wrong support json link")
    if links.get("privacyNotice") != PRIVACY_NOTICE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong privacy link")
    if links.get("participationTerms") != PARTICIPATION_TERMS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong terms link")
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
    assert_contains(text, "Removal not confirmed", label)
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
    if dependencies.get("blockaidMetaMaskWarning") != "submitted-warning-removal-not-confirmed":
        raise SiteCheckError(f"{label}: wrong wallet warning status")
    if dependencies.get("thirdPartyAudit") != "not-completed-deferred":
        raise SiteCheckError(f"{label}: wrong audit status")
    if not any(priority.get("id") == "controlled-account-ui" for priority in payload.get("nextBuildPriorities", [])):
        raise SiteCheckError(f"{label}: missing controlled account UI priority")
    if not any(priority.get("id") == "utility-credit-ledger" for priority in payload.get("nextBuildPriorities", [])):
        raise SiteCheckError(f"{label}: missing utility credit ledger priority")
    if "GCA is concept-stage and is building public identity, safer support intake, and planned non-custodial quant research access." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing concept-stage safe claim")
    if "public self-service member claiming is live before controlled HTTPS UI is connected" not in payload.get("publicClaimBoundaries", {}).get("doNotClaim", []):
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
        raise SiteCheckError(f"{label}: weekly radar pilot should not remain a next priority")
    if not any(milestone.get("id") == "weekly-go-china-radar-pilot" for milestone in payload.get("completedMilestones", [])):
        raise SiteCheckError(f"{label}: missing weekly radar completed milestone")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_community_page(text: str) -> None:
    label = "/community.html"
    assert_contains(text, "GCA Community Kit", label)
    assert_contains(text, "Community JSON", label)
    assert_contains(text, "Official Telegram", label)
    assert_contains(text, "Safe Announcement Copy", label)
    assert_contains(text, "Moderator replies", label)
    assert_contains(text, "Wallet Warning Reply", label)
    assert_contains(text, "Price Display Reply", label)
    assert_contains(text, "Member Access Reply", label)
    assert_contains(text, "Do Not Post", label)
    assert_contains(text, "private keys, seed phrases, exchange API secrets", label)
    assert_contains(text, "Base Mainnet / chainId 8453", label)
    assert_contains(text, "https://t.me/gcagochinaofficial", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_current_pool_text(text, label)


def validate_community_json(text: str) -> None:
    label = "/community.json"
    payload = load_json(text, label)
    market = payload.get("officialMarket", {})
    links = payload.get("publicLinks", {})
    templates = payload.get("moderatorReplyTemplates", {})

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
    if payload.get("weeklyRadar", {}).get("status") != "weekly-go-china-radar-pilot-published":
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
    assert_contains(text, "Pilot 001 / 2026-05-14", label)
    assert_contains(text, "not live market data", label)
    assert_contains(text, "not financial advice", label)
    assert_contains(text, "Narrative Radar Board", label)
    assert_contains(text, "China-facing Web3 attention", label)
    assert_contains(text, "Base ecosystem access", label)
    assert_contains(text, "Risk-control education", label)
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
    if payload.get("status") != "weekly-go-china-radar-pilot-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("issue") != "pilot-001":
        raise SiteCheckError(f"{label}: wrong issue")
    if payload.get("issueDate") != "2026-05-14":
        raise SiteCheckError(f"{label}: wrong issueDate")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if "not live market data" not in payload.get("scope", ""):
        raise SiteCheckError(f"{label}: missing market-data boundary")
    for theme in ("China-facing Web3 attention", "Base ecosystem access", "Risk-control education"):
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
    if status.get("weeklyGoChinaRadar") != "weekly-go-china-radar-pilot-published":
        raise SiteCheckError(f"{label}: unexpected weekly radar status")
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
    if payload.get("weeklyGoChinaRadar", {}).get("status") != "weekly-go-china-radar-pilot-published":
        raise SiteCheckError(f"{label}: unexpected weekly radar object status")
    if payload.get("weeklyGoChinaRadar", {}).get("pageUrl") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weekly radar object page")
    if payload.get("weeklyGoChinaRadar", {}).get("url") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weekly radar object url")
    if payload.get("weeklyGoChinaRadar", {}).get("issue") != "pilot-001":
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
    if payload.get("walletWarningEvidence", {}).get("status") != "warning-report-submitted-removal-not-confirmed":
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
    if extensions.get("weeklyRadarStatus") != "weekly-go-china-radar-pilot-published":
        raise SiteCheckError(f"{label}: wrong weeklyRadarStatus")
    if extensions.get("walletSecurityProfileStatus") != "public-wallet-security-profile-published":
        raise SiteCheckError(f"{label}: wrong walletSecurityProfileStatus")
    if extensions.get("tokenSafetyStatus") != "public-token-safety-checklist-published":
        raise SiteCheckError(f"{label}: wrong tokenSafetyStatus")
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
    if payload.get("platformStatus", {}).get("weeklyGoChinaRadar") != "weekly-go-china-radar-pilot-published":
        raise SiteCheckError(f"{label}: wrong weeklyGoChinaRadar status")
    if payload.get("platformStatus", {}).get("walletSecurityProfile") != "public-wallet-security-profile-published":
        raise SiteCheckError(f"{label}: wrong walletSecurityProfile status")
    if payload.get("platformStatus", {}).get("tokenSafety") != "public-token-safety-checklist-published":
        raise SiteCheckError(f"{label}: wrong tokenSafety status")
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
    if review.get("blockaidMetaMaskWarning") != "submitted-warning-removal-not-confirmed":
        raise SiteCheckError(f"{label}: wrong wallet warning status")
    if review.get("warningRemovalConfirmed") is not False:
        raise SiteCheckError(f"{label}: warning removal must remain false")
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
    if links.get("walletWarningEvidence") != WALLET_WARNING_URL:
        raise SiteCheckError(f"{label}: wrong wallet warning evidence link")
    if links.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trust center link")
    if "No third-party audit has been completed." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "Blockaid or MetaMask warning removal before visible confirmation" not in payload.get("publicClaimBoundaries", {}).get("doNotClaim", []):
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
    if member_tier.get("refreshCadence") != "30 days after activation, or earlier if the user requests a manual recheck":
        raise SiteCheckError(f"{label}: wrong member refresh cadence")
    if verification.get("directSubmissionEndpointConfigured") is not False:
        raise SiteCheckError(f"{label}: direct submission must remain false")
    preview = verification.get("browserPreview", {})
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
    if not any("credits or membership are cash" in claim for claim in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing cash/token do-not-claim boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


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


def validate_reviewer_kit_json(text: str) -> None:
    label = "/reviewer-kit.json"
    payload = load_json(text, label)
    links = payload.get("officialLinks", {})
    market = payload.get("officialMarket", {})
    facts = payload.get("contractFacts", {})
    reviews = payload.get("externalReviewStatus", {})
    boundaries = payload.get("publicClaimBoundaries", {})
    evidence = payload.get("historicalFunctionalSwapEvidence", {})

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
    if links.get("externalReviewStatus") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong externalReviewStatus")
    if links.get("onchainProofs") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofs")
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
    if reviews.get("blockaidMetaMask") != "submitted-warning-removal-not-confirmed":
        raise SiteCheckError(f"{label}: wrong Blockaid status")
    if reviews.get("blockaidFollowUpSubmissionDate") != "2026-05-13":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up date")
    if reviews.get("geckoTerminal") != "approved-2026-05-11":
        raise SiteCheckError(f"{label}: wrong GeckoTerminal status")
    if reviews.get("coinGecko") != "deferred":
        raise SiteCheckError(f"{label}: wrong CoinGecko status")
    if evidence.get("status") != "observed-historical-functional-evidence-only":
        raise SiteCheckError(f"{label}: wrong functional evidence status")
    if SWAP_TEST_BUY_TX not in evidence.get("buyTestTransactions", []):
        raise SiteCheckError(f"{label}: missing buy test transaction")
    if SWAP_TEST_SELL_TX not in evidence.get("sellTestTransactions", []):
        raise SiteCheckError(f"{label}: missing sell test transaction")
    if "No third-party audit has been completed." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "Blockaid or MetaMask warning removal before visible confirmation" not in boundaries.get("doNotClaim", []):
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
    assert_contains(text, "Follow-up submitted on 2026-05-13", label)
    assert_contains(text, "BaseScan Profile", label)
    assert_contains(text, "On-chain Proofs", label)
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
    if "Warning removal is not confirmed." not in wallet_body:
        raise SiteCheckError(f"{label}: missing warning boundary")
    if not any("wallet-security reviewer asks for more evidence" in item for item in rules.get("useWhen", [])):
        raise SiteCheckError(f"{label}: missing wallet-security use rule")
    if "the reply would claim warning removal before visible confirmation" not in rules.get("doNotUseWhen", []):
        raise SiteCheckError(f"{label}: missing warning do-not-use rule")
    if "No third-party audit has been completed." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "Blockaid or MetaMask warning removal before visible confirmation" not in payload.get("doNotClaim", []):
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
    assert_contains(text, "Community Moderator", label)
    assert_contains(text, "Tracked Listing Not Ready", label)
    assert_contains(text, "Blockaid false-positive report was submitted on 2026-05-10", label)
    assert_contains(text, "follow-up was submitted on 2026-05-13", label)
    assert_contains(text, "Warning removal is not confirmed", label)
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
    if snapshot.get("walletWarning") != "submitted-warning-removal-not-confirmed":
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
    if reviews.get("thirdPartyAudit") != "not-completed-deferred":
        raise SiteCheckError(f"{label}: wrong third-party audit status")
    if "No third-party audit has been completed." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "Blockaid or MetaMask warning removal before visible confirmation" not in payload.get("doNotClaim", []):
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
    assert_contains(text, "Public Claim Boundaries", label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "BaseScan source code", label)
    assert_contains(text, "Resubmitted: awaiting review", label)
    assert_contains(text, "Approved 2026-05-11", label)
    assert_contains(text, "Submitted, removal not confirmed", label)
    assert_contains(text, "No completed third-party audit", label)
    assert_contains(text, "Post-deployment mint function", label)
    assert_contains(text, "Transfer tax or hidden fee", label)
    assert_contains(text, "not a lock, vesting contract, or multisig", label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_contains(text, "Do not claim Blockaid or MetaMask warning removal before visible confirmation", label)
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
    if blockaid.get("status") != "submitted-warning-removal-not-confirmed":
        raise SiteCheckError(f"{label}: wrong Blockaid status")
    if blockaid.get("submissionDate") != "2026-05-10":
        raise SiteCheckError(f"{label}: wrong Blockaid submission date")
    if blockaid.get("followUpSubmissionDate") != "2026-05-13":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up date")
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
    assert_contains(text, "External Reviews JSON", label)
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "Resubmitted: awaiting review", label)
    assert_contains(text, "Follow-up submitted 2026-05-13; removal not confirmed", label)
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
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "Follow-up submitted 2026-05-13", label)
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
        "https://gcagochina.com/support.html",
        "https://gcagochina.com/support.json",
        "https://gcagochina.com/privacy.html",
        "https://gcagochina.com/privacy.json",
        "https://gcagochina.com/terms.html",
        "https://gcagochina.com/terms.json",
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
    assert_contains(text, "Allow: /supply.json", label)
    assert_contains(text, "Allow: /onchain-proofs.html", label)
    assert_contains(text, "Allow: /onchain-proofs.json", label)
    assert_contains(text, "Allow: /member-ledger.html", label)
    assert_contains(text, "Allow: /member-ledger.json", label)
    assert_contains(text, "Allow: /member-program.json", label)
    assert_contains(text, "Allow: /gca/member-access/", label)
    assert_contains(text, "Allow: /support.html", label)
    assert_contains(text, "Allow: /support.json", label)
    assert_contains(text, "Allow: /privacy.html", label)
    assert_contains(text, "Allow: /privacy.json", label)
    assert_contains(text, "Allow: /terms.html", label)
    assert_contains(text, "Allow: /terms.json", label)
    assert_contains(text, "Allow: /.well-known/gca-token.json", label)
    assert_contains(text, "Allow: /.well-known/wallet-security.json", label)
    assert_contains(text, "Allow: /.well-known/security.txt", label)
    assert_contains(text, "Sitemap: https://gcagochina.com/sitemap.xml", label)


CHECKS: list[EndpointCheck] = [
    ("/", validate_root),
    ("/verify.html", validate_verify),
    ("/markets.html", validate_markets),
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
