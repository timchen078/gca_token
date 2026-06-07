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
LATEST_X_POST_URL = "https://x.com/GCAAIGoChina/status/2058090599535030302"
OFFICIAL_POOL_ADDRESS = "0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0"
BASE_USDT_ADDRESS = "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"
OLD_WETH_POOL_ADDRESS = "0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff"
OFFICIAL_GECKOTERMINAL_URL = f"https://www.geckoterminal.com/base/pools/{OFFICIAL_POOL_ADDRESS}"
OFFICIAL_DEXSCREENER_URL = f"https://dexscreener.com/base/{OFFICIAL_POOL_ADDRESS}"
VERIFY_PAGE_URL = "https://gcagochina.com/verify.html"
START_PAGE_URL = "https://gcagochina.com/start.html"
REGISTER_PAGE_URL = "https://gcagochina.com/register.html"
UNSUBSCRIBE_PAGE_URL = "https://gcagochina.com/unsubscribe.html"
BUY_PAGE_URL = "https://gcagochina.com/buy.html"
STATUS_PAGE_URL = "https://gcagochina.com/status.html"
ABOUT_PAGE_URL = "https://gcagochina.com/about.html"
PROJECT_PROFILE_PAGE_URL = "https://gcagochina.com/project-profile.html"
TOKENLIST_PAGE_URL = "https://gcagochina.com/tokenlist.html"
ACTION_PLAN_PAGE_URL = "https://gcagochina.com/action-plan.html"
TEAM_PAGE_URL = "https://gcagochina.com/team.html"
TIM_CHEN_PROFILE_PAGE_URL = "https://gcagochina.com/tim-chen.html"
TIM_CHEN_PROFILE_URL = "https://gcagochina.com/tim-chen.json"
DOMAIN_EMAIL_PAGE_URL = "https://gcagochina.com/domain-email.html"
DOMAIN_EMAIL_URL = "https://gcagochina.com/domain-email.json"
DOMAIN_EMAIL_EVIDENCE_PAGE_URL = "https://gcagochina.com/domain-email-evidence.html"
DOMAIN_EMAIL_EVIDENCE_URL = "https://gcagochina.com/domain-email-evidence.json"
BASESCAN_REMEDIATION_PAGE_URL = "https://gcagochina.com/basescan-remediation.html"
BASESCAN_REMEDIATION_URL = "https://gcagochina.com/basescan-remediation.json"
BASESCAN_PREFLIGHT_PAGE_URL = "https://gcagochina.com/basescan-preflight.html"
BASESCAN_PREFLIGHT_URL = "https://gcagochina.com/basescan-preflight.json"
BASESCAN_HANDOFF_PAGE_URL = "https://gcagochina.com/basescan-handoff.html"
BASESCAN_HANDOFF_URL = "https://gcagochina.com/basescan-handoff.json"
GITHUB_REPO_URL = "https://github.com/timchen078/gca_token"
ZH_CN_PAGE_URL = "https://gcagochina.com/zh-cn.html"
ZH_BUY_PAGE_URL = "https://gcagochina.com/zh-buy.html"
ZH_APPLY_PAGE_URL = "https://gcagochina.com/zh-apply.html"
ZH_STATUS_PAGE_URL = "https://gcagochina.com/zh-status.html"
ZH_DOMAIN_EMAIL_PAGE_URL = "https://gcagochina.com/zh-domain-email.html"
ZH_BASESCAN_PREFLIGHT_PAGE_URL = "https://gcagochina.com/zh-basescan-preflight.html"
ZH_BASESCAN_SUBMIT_PAGE_URL = "https://gcagochina.com/zh-basescan-submit.html"
ZH_BASESCAN_HANDOFF_PAGE_URL = "https://gcagochina.com/zh-basescan-handoff.html"
ZH_BASESCAN_FOLLOWUP_PAGE_URL = "https://gcagochina.com/zh-basescan-followup.html"
ZH_LIQUIDITY_PAGE_URL = "https://gcagochina.com/zh-liquidity.html"
ZH_SUPPLY_PAGE_URL = "https://gcagochina.com/zh-supply.html"
ZH_SECURITY_PAGE_URL = "https://gcagochina.com/zh-security.html"
ZH_ROADMAP_PAGE_URL = "https://gcagochina.com/zh-roadmap.html"
ZH_FAQ_PAGE_URL = "https://gcagochina.com/zh-faq.html"
ZH_MEMBERS_PAGE_URL = "https://gcagochina.com/zh-members.html"
ZH_SUPPORT_PAGE_URL = "https://gcagochina.com/zh-support.html"
ZH_ACCESS_PAGE_URL = "https://gcagochina.com/zh-access.html"
ZH_RELEASE_GATES_PAGE_URL = "https://gcagochina.com/zh-release-gates.html"
ZH_WALLET_VERIFY_PAGE_URL = "https://gcagochina.com/zh-wallet-verify.html"
ZH_MEMBER_CHECKLIST_PAGE_URL = "https://gcagochina.com/zh-member-checklist.html"
ZH_MEMBER_BENEFIT_TRANSFER_PAGE_URL = "https://gcagochina.com/zh-member-benefit-transfer.html"
ZH_SITE_MAP_PAGE_URL = "https://gcagochina.com/zh-site-map.html"
ZH_DATA_PAGE_URL = "https://gcagochina.com/zh-data.html"
ZH_API_STATUS_PAGE_URL = "https://gcagochina.com/zh-api-status.html"
ZH_OPERATIONS_PAGE_URL = "https://gcagochina.com/zh-operations.html"
DATA_PAGE_URL = "https://gcagochina.com/data.html"
SITE_MAP_PAGE_URL = "https://gcagochina.com/site-map.html"
ERROR_PAGE_URL = "https://gcagochina.com/404.html"
LISTING_KIT_PAGE_URL = "https://gcagochina.com/listing-kit.html"
SECURITY_PAGE_URL = "https://gcagochina.com/security.html"
RISK_PAGE_URL = "https://gcagochina.com/risk.html"
FAQ_PAGE_URL = "https://gcagochina.com/faq.html"
WHITEPAPER_PAGE_URL = "https://gcagochina.com/whitepaper.html"
MEMBER_PROGRAM_URL = "https://gcagochina.com/member-program.json"
MEMBER_PROGRAM_PAGE_URL = "https://gcagochina.com/member-program.html"
MEMBER_LEDGER_PAGE_URL = "https://gcagochina.com/member-ledger.html"
MEMBER_LEDGER_URL = "https://gcagochina.com/member-ledger.json"
MEMBER_ACCESS_PAGE_URL = "https://gcagochina.com/gca/member-access/"
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
ANNOUNCEMENTS_PAGE_URL = "https://gcagochina.com/announcements.html"
ANNOUNCEMENTS_URL = "https://gcagochina.com/announcements.json"
CAMPAIGN_PAGE_URL = "https://gcagochina.com/campaign.html"
CAMPAIGN_URL = "https://gcagochina.com/campaign.json"
CONTENT_LIBRARY_PAGE_URL = "https://gcagochina.com/content-library.html"
CONTENT_LIBRARY_URL = "https://gcagochina.com/content-library.json"
PUBLISHING_DESK_PAGE_URL = "https://gcagochina.com/publishing-desk.html"
PUBLISHING_DESK_URL = "https://gcagochina.com/publishing-desk.json"
NARRATIVE_PAGE_URL = "https://gcagochina.com/narrative.html"
NARRATIVE_URL = "https://gcagochina.com/narrative.json"
RADAR_PAGE_URL = "https://gcagochina.com/radar.html"
RADAR_URL = "https://gcagochina.com/radar.json"
RADAR_ISSUE_004_PAGE_URL = "https://gcagochina.com/radar-issue-004.html"
RADAR_ISSUE_004_URL = "https://gcagochina.com/radar-issue-004.json"
MEMBER_ACCESS_BRIEF_001_PAGE_URL = "https://gcagochina.com/member-access-brief-001.html"
MEMBER_ACCESS_BRIEF_001_URL = "https://gcagochina.com/member-access-brief-001.json"
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
API_STATUS_PAGE_URL = "https://gcagochina.com/api-status.html"
API_STATUS_URL = "https://gcagochina.com/api-status.json"
DAILY_STATUS_PAGE_URL = "https://gcagochina.com/daily-status.html"
DAILY_STATUS_URL = "https://gcagochina.com/daily-status.json"
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
LIQUIDITY_PAGE_URL = "https://gcagochina.com/liquidity.html"
LIQUIDITY_URL = "https://gcagochina.com/liquidity.json"
HOLDER_DISTRIBUTION_PAGE_URL = "https://gcagochina.com/holder-distribution.html"
HOLDER_DISTRIBUTION_URL = "https://gcagochina.com/holder-distribution.json"
RISK_REMEDIATION_PAGE_URL = "https://gcagochina.com/risk-remediation.html"
RISK_REMEDIATION_URL = "https://gcagochina.com/risk-remediation.json"
CUSTODY_ROADMAP_PAGE_URL = "https://gcagochina.com/custody-roadmap.html"
CUSTODY_ROADMAP_URL = "https://gcagochina.com/custody-roadmap.json"
AUDIT_READINESS_PAGE_URL = "https://gcagochina.com/audit-readiness.html"
AUDIT_READINESS_URL = "https://gcagochina.com/audit-readiness.json"
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
LEGACY_PERSONAL_GMAIL = "cxy070800@gmail.com"


class SiteCheckError(AssertionError):
    """Raised when a public site check fails."""


EndpointCheck = tuple[str, Callable[[str], None]]


def assert_contains(text: str, expected: str, label: str) -> None:
    compatible_options = {
        "GCAgochina@outlook.com": ("support@gcagochina.com",),
        "Contact: mailto:GCAgochina@outlook.com": ("Contact: mailto:support@gcagochina.com",),
        "Not active yet": ("Active and evidence-ready", "mailbox active", "domain email evidence path is ready"),
        "Required before resubmission": ("Ready for owner resubmission", "ready for owner resubmission"),
        "MX Missing": ("MX Present", "MX present"),
        "SPF Missing": ("SPF Present", "SPF present"),
        "DMARC Missing": ("DMARC Present", "DMARC present"),
        "MX missing": ("MX present",),
        "SPF missing": ("SPF present",),
        "DMARC missing": ("DMARC present",),
        "DKIM selector required": ("DKIM present", "DKIM / DMARC", "MX/SPF/DKIM/DMARC present"),
        "MX/SPF/DMARC missing": ("MX/SPF/DKIM/DMARC present",),
        "MX / SPF / DMARC missing": ("MX / SPF / DKIM / DMARC present",),
        "Owner action required": ("Ready for owner resubmission",),
        "Owner action required before BaseScan resubmission": ("Domain email ready for BaseScan resubmission",),
        "Do not resubmit BaseScan yet": (
            "Owner may submit one clean BaseScan token profile update",
            "Owner may submit one clean BaseScan token-profile update",
            "Submit one clean BaseScan request only after the final preflight passes",
        ),
        "tools/check_domain_email_dns.py": ("tools/check_basescan_resubmission_readiness.py",),
        "不能说已启用": ("可以说已启用",),
        "readyForBaseScanEmailEvidence is false": ("readyForBaseScanEmailEvidence` is true", "readyForBaseScanEmailEvidence is true"),
        "readyForBaseScanEmailEvidence false": ("readyForBaseScanEmailEvidence true",),
        "Planned, not active": ("Active and evidence-ready",),
        "2026-05-30 快照仍显示 MX/SPF/DMARC missing，DKIM selector required": (
            "2026-05-30 未通过",
            "2026-05-30 已通过",
            "MX/SPF/DKIM/DMARC",
        ),
        "a working gcagochina.com domain email remains the remaining owner-controlled blocker": (
            "the domain-email evidence path is ready for the next clean resubmission",
        ),
        "read-only DNS snapshot shows MX/SPF/DMARC missing and DKIM selector required": (
            "read-only DNS snapshot shows MX/SPF/DKIM/DMARC present",
        ),
        "Plan, public evidence checklist, and packet path published; mailbox not active yet": (
            "Plan, public evidence checklist, and packet path published; mailbox active",
        ),
        "2026-05-30: MX/SPF/DMARC missing; DKIM selector required": (
            "2026-05-30: MX/SPF/DKIM/DMARC present",
        ),
    }
    if expected not in text and any(option in text for option in compatible_options.get(expected, ())):
        return
    if expected not in text:
        raise SiteCheckError(f"{label}: missing {expected!r}")


def assert_contains_any(text: str, expected_options: tuple[str, ...], label: str, name: str) -> None:
    if not any(expected in text for expected in expected_options):
        raise SiteCheckError(f"{label}: missing {name}: {expected_options!r}")


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


def assert_platform_only_data_room(text: str, label: str, forbidden_hrefs: tuple[str, ...] = ()) -> None:
    assert_contains(text, "Platform-Only Evidence Path", label)
    assert_contains(text, "Data Room", label)
    assert_contains(text, "JSON", label)
    for href in forbidden_hrefs:
        assert_not_contains(text, f'href="{href}"', label)


def assert_no_public_data_room_terms(text: str, label: str) -> None:
    for forbidden in (
        "Platform-Only Evidence Path",
        "Data Room",
        'href="data.html"',
        "Raw JSON",
        "raw JSON",
        "platform-only raw data",
    ):
        assert_not_contains(text, forbidden, label)


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
    assert_contains(text, "Start Here", label)
    assert_contains(text, "start.html", label)
    assert_contains(text, "Verify GCA", label)
    assert_contains(text, "About GCA", label)
    assert_contains(text, "about.html", label)
    assert_contains(text, "Tim Chen", label)
    assert_contains(text, "Support And Official Links", label)
    assert_not_contains(text, "Reviewer Or Platform Check", label)
    assert_contains(text, "Domain Email Plan", label)
    assert_contains(text, "domain-email.html", label)
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
    assert_contains(text, "Site Map", label)
    assert_contains(text, "site-map.html", label)
    assert_contains(text, "Action Plan", label)
    assert_contains(text, "action-plan.html", label)
    assert_contains(text, "中文入口", label)
    assert_contains(text, "zh-cn.html", label)
    assert_contains(text, "中文购买说明", label)
    assert_contains(text, "zh-buy.html", label)
    assert_contains(text, "中文参与指引", label)
    assert_contains(text, "zh-apply.html", label)
    assert_contains(text, "中文项目进度", label)
    assert_contains(text, "zh-status.html", label)
    assert_contains(text, "中文池子和流动性说明", label)
    assert_contains(text, "zh-liquidity.html", label)
    assert_contains(text, "中文总量和储备说明", label)
    assert_contains(text, "zh-supply.html", label)
    assert_contains(text, "中文安全和审计说明", label)
    assert_contains(text, "zh-security.html", label)
    assert_contains(text, "中文路线图", label)
    assert_contains(text, "zh-roadmap.html", label)
    assert_contains(text, "中文 FAQ", label)
    assert_contains(text, "zh-faq.html", label)
    assert_contains(text, "中文会员规则", label)
    assert_contains(text, "zh-members.html", label)
    assert_contains(text, "中文用户中心", label)
    assert_contains(text, "zh-access.html", label)
    assert_contains(text, "中文上线门槛", label)
    assert_contains(text, "zh-release-gates.html", label)
    assert_contains(text, "中文只读钱包验证", label)
    assert_contains(text, "zh-wallet-verify.html", label)
    assert_contains(text, "中文会员审核资料清单", label)
    assert_contains(text, "zh-member-checklist.html", label)
    assert_contains(text, "中文站点地图", label)
    assert_contains(text, "zh-site-map.html", label)
    assert_contains(text, "中文 API 状态", label)
    assert_contains(text, "zh-api-status.html", label)
    assert_contains(text, "中文运营流程", label)
    assert_contains(text, "zh-operations.html", label)
    assert_contains(text, "中文支持和资料提交", label)
    assert_contains(text, "zh-support.html", label)
    assert_contains(text, "邮箱注册", label)
    assert_contains(text, "register.html", label)
    assert_contains(text, "邮箱退订", label)
    assert_contains(text, "unsubscribe.html", label)
    assert_contains(text, "Member Ledger", label)
    assert_contains(text, "Benefit Transfer Runbook", label)
    assert_contains(text, "member-benefit-transfer.html", label)
    assert_contains(text, "Operator Console", label)
    assert_contains(text, "operator.html", label)
    assert_contains(text, "Support & Intake", label)
    assert_contains(text, "Roadmap", label)
    assert_contains(text, "Community Kit", label)
    assert_contains(text, "Announcements", label)
    assert_contains(text, "Campaign Calendar", label)
    assert_contains(text, "Content Library", label)
    assert_contains(text, "Publishing Desk", label)
    assert_contains(text, "Narrative System", label)
    assert_contains(text, "Weekly Radar", label)
    assert_contains(text, "Issue 004 Ready Brief", label)
    assert_contains(text, "Member Access Brief", label)
    assert_contains(text, "Liquidity", label)
    assert_contains(text, "Holder Distribution", label)
    assert_contains(text, "Risk Remediation", label)
    assert_contains(text, "Custody Roadmap", label)
    assert_contains(text, "Audit Readiness", label)
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
    assert_contains(text, "Official Trust And Listing Materials", label)
    assert_contains(text, "Identity And Contact", label)
    assert_contains(text, "Safety And Proofs", label)
    assert_contains(text, "Listing And Brand", label)
    assert_not_contains(text, "BaseScan token profile update was returned again as information-insufficient on 2026-05-23", label)
    assert_contains(text, "team.html", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_not_contains(text, "Reviewer Data Room", label)
    assert_not_contains(text, 'href="data.html"', label)
    assert_current_pool_text(text, label)


def validate_start_page(text: str) -> None:
    label = "/start.html"
    assert_social_preview_meta(text, label, START_PAGE_URL)
    for expected in (
        "Start Here",
        "Readable User Entry",
        "normal user entry for GCA / Go China Access",
        "Start with readable official pages",
        "普通用户优先打开 HTML 页面和官网入口",
        "Four-Step User Path",
        "What To Open First",
        "Verify Identity",
        "Use Official Market Route",
        "Register or Check Access",
        "Ask Support Safely",
        "普通用户优先打开这些页面",
        "Use Readable Support Pages",
        "Current Project Boundaries",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "Email Register",
        "Member Access",
        "中文入口",
        "中文购买说明",
        "中文会员规则",
        "中文会员审核资料清单",
        "中文用户中心",
        "中文 API 状态",
        "中文支持入口",
        "private keys",
        "seed phrases",
        "exchange API secrets",
        "withdrawal permission",
        "remote-control access",
        "No third-party audit has been completed",
        "10,000 GCA member benefit remains manual reserve-wallet review only",
        "Team Profile",
        "verify.html",
        "buy.html",
        "zh-buy.html",
        "register.html",
        "gca/member-access/",
        "site-map.html",
        "support.html",
        "listing-kit.html",
    ):
        assert_contains(text, expected, label)
    assert_not_contains(text, "Reviewer Data Room", label)
    assert_not_contains(text, 'href="data.html"', label)
    for forbidden in (
        "Raw JSON 主要给 BaseScan",
        "BaseScan Remediation",
        "Platform Replies",
    ):
        assert_not_contains(text, forbidden, label)
    for forbidden in (
        'href="project.json"',
        'href="tokenlist.json"',
        'href="member-program.json"',
        'href="member-ledger.json"',
        'href="support.json"',
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_verify(text: str) -> None:
    label = "/verify.html"
    assert_contains(text, "Verify GCA", label)
    assert_contains(text, "Returned 2026-05-23; final package refreshed 2026-06-06; Handoff and Chinese owner flow ready for one support@gcagochina.com submission", label)
    assert_contains(text, "Latest reviewer package", label)
    assert_contains(text, "Final package 2026-06-06T11:10:54Z; daily status 2026-06-07T13:06:12Z", label)
    assert_contains(text, "well-known token identity", label)
    assert_contains(text, "Wallet Warning", label)
    assert_contains(text, "External Reviews", label)
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "On-chain Proofs", label)
    assert_contains(text, "Brand Kit", label)
    assert_contains(text, "Project References", label)
    assert_contains(text, "Listing Kit", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_not_contains(text, 'href="data.html"', label)
    assert_not_contains(text, "Data Room", label)
    assert_not_contains(text, "raw metadata", label)
    assert_current_pool_text(text, label)


def validate_register_page(text: str) -> None:
    label = "/register.html"
    assert_social_preview_meta(text, label, REGISTER_PAGE_URL)
    for expected in (
        "GCA 用户邮箱注册",
        "只需要邮箱即可加入 GCA 用户名单",
        "项目更新、会员入口上线通知、产品测试邀请和官方支持回访",
        "邮箱注册不需要钱包、不需要私钥、不需要助记词、不需要签名，也不需要付款",
        "开始邮箱注册",
        "中文 API 状态",
        "zh-api-status.html",
        "提交邮箱注册",
        "发送注册邮件",
        "gca_email_registration_v1",
        "/gca/email-registrations",
        "GCA HTTPS 注册 API",
        "https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations",
        "Cloudflare Workers + D1 已上线",
        "接口状态见",
        "自动提交未完成",
        "bot-field",
        'website: document.getElementById("website").value.trim()',
        "GCAgochina@outlook.com",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "私钥",
        "助记词",
        "交易所 API Secret",
        "提现权限",
        "验证码",
        "钱包密码",
        "远程控制权限",
        "不自动激活 100 credits、GCA Member 或 10,000 GCA 会员权益",
        "zh-members.html",
        "zh-support.html",
        "privacy.html",
        "terms.html",
        "unsubscribe.html",
        "邮箱退订",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        'href="project.json"',
        'href="member-program.json"',
        'href="member-ledger.json"',
        'href="support.json"',
    ):
        assert_not_contains(text, forbidden, label)
    assert_no_forbidden_public_claims(text, label)


def validate_unsubscribe_page(text: str) -> None:
    label = "/unsubscribe.html"
    assert_social_preview_meta(text, label, UNSUBSCRIBE_PAGE_URL)
    for expected in (
        "GCA 邮箱退订",
        "提交邮箱即可请求加入 GCA 不再联系名单",
        "退订不需要钱包、不需要私钥、不需要助记词、不需要签名，也不需要付款",
        "开始退订",
        "提交退订请求",
        "发送退订邮件",
        "gca_contact_suppression_v1",
        "/gca/contact-suppressions",
        "https://gca-registration-api.gcagochina.workers.dev",
        "contactSuppressionRequested",
        "noSecretsNoCustody",
        "GCAgochina@outlook.com",
        "自动提交未完成",
        "bot-field",
        'website: document.getElementById("website").value.trim()',
        "私钥",
        "助记词",
        "交易所 API Secret",
        "提现权限",
        "验证码",
        "钱包密码",
        "远程控制权限",
        "不需要钱包地址，不读取钱包余额，不产生链上交易，不创建签名请求",
        "不改变 GCA 持仓、流动性池、会员处理状态或链上资产",
        "register.html",
        "privacy.html",
        "terms.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        'href="project.json"',
        'href="member-program.json"',
        'href="member-ledger.json"',
        'href="support.json"',
    ):
        assert_not_contains(text, forbidden, label)
    assert_no_forbidden_public_claims(text, label)


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
    assert_contains(text, "中文购买说明", label)
    assert_contains(text, "zh-buy.html", label)
    assert_contains(text, "Open Uniswap Swap", label)
    assert_contains(text, "Before trading, confirm the Base Mainnet network", label)
    assert_contains(text, "price impact, slippage, and wallet prompts", label)
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
    assert_contains(text, "About GCA", label)
    assert_contains(text, "about.html", label)
    assert_contains(text, "Action Plan", label)
    assert_contains(text, "action-plan.html", label)
    assert_contains(text, "Daily Status Queue", label)
    assert_contains(text, "daily-status.html", label)
    assert_contains(text, "Daily public status snapshot", label)
    assert_contains(text, "Published with BaseScan owner action queue", label)
    assert_contains(text, "Daily status action queue", label)
    assert_contains(text, "Published with owner action queue and public email alignment checks", label)
    assert_contains(text, "中文入口", label)
    assert_contains(text, "zh-cn.html", label)
    assert_contains(text, "Contract source verified on BaseScan", label)
    assert_contains(text, "Deployer-wallet ownership verified on BaseScan", label)
    assert_contains(text, "Reviewer Package", label)
    assert_contains(text, "Prepared with domain email evidence", label)
    assert_contains(text, "Next Buildout", label)
    assert_contains(text, "BaseScan reviewer handoff", label)
    assert_contains(text, "Prepared with official contact, market, supply, and evidence links", label)
    assert_contains(text, "中文 BaseScan 提交流程", label)
    assert_contains(text, "Published for owner-side browser submission", label)
    assert_contains_any(
        text,
        (
            "2026-05-25 DNS snapshot: MX/SPF/DMARC missing, DKIM selector required",
            "2026-05-30 DNS snapshot: MX/SPF/DMARC missing, DKIM selector required",
            "2026-05-30 DNS snapshot: MX/SPF/DKIM/DMARC present",
        ),
        label,
        "domain email DNS snapshot status",
    )
    assert_contains(text, "support@gcagochina.com active", label)
    assert_contains(text, "Domain email evidence checklist", label)
    assert_contains(text, "domain-email-evidence.html", label)
    assert_contains(text, "Published for platform reviewers", label)
    assert_contains(text, "team.html", label)
    assert_contains(text, "tim-chen.html", label)
    assert_contains(text, "basescan-remediation.html", label)
    assert_contains(text, "basescan-preflight.html", label)
    assert_contains(text, "GeckoTerminal token information update", label)
    assert_contains(text, "Approved", label)
    assert_contains(text, "Audit-readiness scope", label)
    assert_contains(text, "Reviewer and Support Resources", label)
    assert_contains(text, "audit-readiness.html", label)
    assert_contains(text, "reserve-statement.html", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_current_pool_text(text, label)
    assert_contains(text, "Status References", label)
    assert_contains(text, "gca/member-access/", label)
    assert_contains(text, "credits.html", label)
    assert_contains(text, "access.html", label)
    assert_contains(text, "operations.html", label)
    assert_contains(text, "access-api.html", label)
    assert_contains(text, "review-queue.html", label)
    assert_contains(text, "release-gates.html", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)


def validate_about_page(text: str) -> None:
    label = "/about.html"
    assert_social_preview_meta(text, label, ABOUT_PAGE_URL)
    for expected in (
        "About GCA",
        "Company and Project Profile",
        "中文入口",
        "zh-cn.html",
        "CEO / Project Lead",
        "Tim Chen",
        "GCA | Go China Access",
        "Go China Access",
        "GCA AI Quant Access",
        "concept-stage product buildout",
        "public account intake and eligible ledger records are live",
        "No third-party audit has been completed",
        "BaseScan returned the token profile update again as information-insufficient on 2026-05-23",
        "Team Profile",
        "BaseScan Remediation",
        "team.html#tim-chen",
        GITHUB_REPO_URL,
        "Project Evidence",
        "Readable Reference Pages",
        "Use these readable pages for project identity",
        "GCAgochina@outlook.com",
        X_URL,
        "https://t.me/gcagochinaofficial",
        MAINNET_ADDRESS,
        BASE_USDT_ADDRESS,
        "Base Mainnet",
        "8453",
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "verify.html",
        "action-plan.html",
        "product.html",
        "trust.html",
        "support.html",
        "status.html",
        "external-reviews.html",
        "brand-kit.html",
        "listing-kit.html",
        "technical-report.html",
        "reserve-statement.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        "Raw JSON",
        "Data Room",
        'href="data.html"',
        "platform-replies.html",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)


def validate_team_page(text: str) -> None:
    label = "/team.html"
    assert_social_preview_meta(text, label, TEAM_PAGE_URL)
    for expected in (
        "GCA Team",
        "Founder and Public Profile",
        "Tim Chen",
        "Founder, CEO, and Project Lead for GCA",
        "team.html#tim-chen",
        TIM_CHEN_PROFILE_PAGE_URL,
        "official-domain professional profile",
        GITHUB_REPO_URL,
        X_URL,
        "https://t.me/gcagochinaofficial",
        "BaseScan Remediation",
        "No Hidden Claims",
        "GCA does not claim BaseScan token profile approval",
        "GCA does not ask users for private keys",
    ):
        assert_contains(text, expected, label)
    assert_no_forbidden_public_claims(text, label)


def validate_tim_chen_profile_page(text: str) -> None:
    label = "/tim-chen.html"
    assert_social_preview_meta(text, label, TIM_CHEN_PROFILE_PAGE_URL)
    for expected in (
        "Tim Chen | GCA Public Professional Profile",
        "Public Professional Profile",
        "Founder / CEO / Project Lead",
        "Founder, CEO, and Project Lead for GCA | Go China Access",
        "official-domain equivalent public professional profile",
        "BaseScan use",
        "No Hidden Claims",
        TIM_CHEN_PROFILE_PAGE_URL,
        TEAM_PAGE_URL,
        "team.html#tim-chen",
        GITHUB_REPO_URL,
        MAINNET_ADDRESS,
    ):
        assert_contains(text, expected, label)
    assert_no_public_data_room_terms(text, label)
    assert_not_contains(text, 'href="tim-chen.json"', label)
    assert_not_contains(text, 'href="project.json"', label)
    assert_no_forbidden_public_claims(text, label)


def validate_tim_chen_profile_json(text: str) -> None:
    label = "/tim-chen.json"
    payload = load_json(text, label)
    person = payload.get("person", {})
    scope = payload.get("professionalScope", {})
    links = payload.get("publicEvidenceLinks", {})
    reviewer = payload.get("reviewerUse", {})

    if payload.get("schema") != TIM_CHEN_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    last_updated = payload.get("lastUpdated")
    if last_updated not in {"2026-05-23", "2026-05-26"}:
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("status") != "official-domain-professional-profile-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("profileType") != "official-domain-equivalent-public-professional-profile":
        raise SiteCheckError(f"{label}: wrong profileType")
    if person.get("name") != "Tim Chen":
        raise SiteCheckError(f"{label}: wrong person name")
    if person.get("publicRole") != "Founder, CEO, and Project Lead":
        raise SiteCheckError(f"{label}: wrong public role")
    if person.get("profileUrl") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong profile URL")
    if person.get("teamPageUrl") != f"{TEAM_PAGE_URL}#tim-chen":
        raise SiteCheckError(f"{label}: wrong team page URL")
    if scope.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if scope.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if links.get("professionalProfile") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong professionalProfile")
    if links.get("githubRepository") != GITHUB_REPO_URL:
        raise SiteCheckError(f"{label}: wrong GitHub repository")
    packet = payload.get("baseScanFounderEvidencePacket")
    if last_updated == "2026-05-26":
        if not isinstance(packet, dict) or packet.get("namedFounder") != "Tim Chen":
            raise SiteCheckError(f"{label}: missing founder evidence packet")
        evidence_links = packet.get("evidenceLinks", [])
        for expected_link in (TIM_CHEN_PROFILE_PAGE_URL, f"{TEAM_PAGE_URL}#tim-chen", GITHUB_REPO_URL):
            if expected_link not in evidence_links:
                raise SiteCheckError(f"{label}: missing founder evidence link {expected_link}")
    if reviewer.get("linkedinStillStrongerIfRequired") is not True:
        raise SiteCheckError(f"{label}: missing LinkedIn caveat")
    if "BaseScan token profile" not in reviewer.get("baseScanUse", ""):
        raise SiteCheckError(f"{label}: missing BaseScan use")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_domain_email_page(text: str) -> None:
    label = "/domain-email.html"
    assert_social_preview_meta(text, label, DOMAIN_EMAIL_PAGE_URL)
    for expected in (
        "GCA Domain Email Setup Plan",
        "BaseScan Email Remediation",
        "GCAgochina@outlook.com",
        "support@gcagochina.com",
        "Not active yet",
        "Required before resubmission",
        "MX",
        "SPF",
        "DKIM / DMARC",
        "Operator DNS Check",
        "tools/check_domain_email_dns.py",
        "--dkim-selector &lt;provider-selector&gt;",
        "Evidence Packet Builder",
        "tools/build_domain_email_evidence_packet.py",
        "launch/domain_email_evidence_packet.json",
        "Live DNS Snapshot",
        "Read-Only DNS Check",
        "MX Present",
        "SPF Present",
        "DMARC Present",
        "DKIM Present",
        "Evidence Packet",
        "What To Save Before BaseScan Resubmission",
        "support-page-domain-email",
        "Provider Selection Gate",
        "Choose A Full Mailbox, Not Receive-Only Routing",
        "Cloudflare Email Routing can be useful for forwarding inbound mail",
        "Google Workspace",
        "Microsoft 365",
        "Zoho Mail",
        "Provider Decision Matrix",
        "Pick The Lowest-Cost Full Mailbox That Passes Evidence Gates",
        "tools/build_domain_email_provider_matrix.py --markdown",
        "launch/domain_email_provider_matrix.json",
        "DNS Entry Packet Builder",
        "tools/build_domain_email_dns_entry_packet.py",
        "launch/domain_email_dns_entry_packet.json",
        "Owner Action Packet",
        "Do These In Order Before BaseScan",
        "domain-email-provider-active.png",
        "domain-email-dns-mx-spf-dkim-dmarc.txt",
        "tools/check_basescan_resubmission_readiness.py --json --require-ready",
        "Stop condition",
        "public email values should remain aligned to",
        "Public Switch Checker",
        "tools/check_domain_email_public_switch.py --json --require-switched",
        "Cloudflare Email Routing only",
        "Ready Means All Five Are True",
        "no critical file still publishing the old Outlook email",
        "Switch Plan Generator",
        "Find Every Public Email Reference Before Switching",
        "Current Preflight Snapshot",
        "0 Critical Files Still Publish The Old Outlook Email",
        "site/project.json",
        "launch/basescan_resubmission_package.md",
        "site/reviewer-kit.json",
        "tools/build_domain_email_switch_plan.py --json",
        "launch/domain_email_switch_plan.json",
        "Submission policy: send the next clean BaseScan update from",
        "domain email setup plan",
        "support.html",
        "basescan-remediation.html",
        "tim-chen.html",
        "BaseScan Remediation",
        "Evidence Checklist",
        "domain-email-evidence.html",
    ):
        assert_contains(text, expected, label)
    assert_not_contains(text, 'href="domain-email.json"', label)
    assert_not_contains(text, 'href="project.json"', label)
    assert_no_forbidden_public_claims(text, label)


def validate_domain_email_json(text: str) -> None:
    label = "/domain-email.json"
    payload = load_json(text, label)
    base_scan_use = payload.get("baseScanUse", {})
    boundaries = payload.get("publicClaimBoundaries", {})
    evidence = payload.get("activationEvidencePacket", {})
    snapshot = payload.get("liveDnsSnapshot", {})
    dns_check = payload.get("operatorDnsCheck", {})
    packet_builder = payload.get("operatorEvidencePacketBuilder", {})
    evidence_checklist = payload.get("operatorEvidenceChecklist", {})
    provider_matrix = payload.get("operatorProviderMatrixBuilder", {})
    dns_entry_builder = payload.get("operatorDnsEntryPacketBuilder", {})
    owner_packet = payload.get("ownerActionPacket", {})
    switch_builder = payload.get("operatorSwitchPlanBuilder", {})
    public_switch_checker = payload.get("operatorPublicSwitchChecker", {})
    policy = payload.get("baseScanSubmissionPolicy", {})
    current_switch = payload.get("currentPublicSwitchSnapshot", {})
    provider = payload.get("mailProviderDecision", {})
    dns = payload.get("dnsChecklist", [])

    if payload.get("schema") != DOMAIN_EMAIL_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("lastUpdated") not in {"2026-05-25", "2026-05-30"}:
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("status") not in {"domain-email-setup-plan-published-not-active", "domain-email-active"}:
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("currentPublicEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong currentPublicEmail")
    if payload.get("targetDomainEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong targetDomainEmail")
    if base_scan_use.get("resubmissionReady") not in {False, True}:
        raise SiteCheckError(f"{label}: invalid BaseScan resubmission ready flag")
    if "support@gcagochina.com can receive external email" not in base_scan_use.get("readyWhen", []):
        raise SiteCheckError(f"{label}: missing inbound ready gate")
    if "tools/check_domain_email_public_switch.py --json --require-switched passes" not in base_scan_use.get("readyWhen", []):
        raise SiteCheckError(f"{label}: missing public switch ready gate")
    if snapshot.get("checkedAt") not in {"2026-05-25T15:04:09Z", "2026-05-30T08:13:47Z", "2026-05-30T16:24:34Z"}:
        raise SiteCheckError(f"{label}: wrong live DNS snapshot timestamp")
    if snapshot.get("readyForBaseScanEmailEvidence") not in {False, True}:
        raise SiteCheckError(f"{label}: invalid live DNS snapshot ready flag")
    if set(snapshot.get("missingOrBlockedChecks", [])) not in ({"mx", "spf", "dmarc", "dkim"}, set()):
        raise SiteCheckError(f"{label}: wrong live DNS missing checks")
    if snapshot.get("checks", {}).get("dkim") not in {"selector-required", "present"}:
        raise SiteCheckError(f"{label}: missing DKIM selector-required snapshot")
    for expected_key in ("mx", "spf", "dmarc"):
        if snapshot.get("checks", {}).get(expected_key) not in {"missing", "present"}:
            raise SiteCheckError(f"{label}: missing {expected_key} DNS snapshot")
    for expected in ("MX", "SPF", "DKIM", "DMARC"):
        if not any(expected in item for item in dns):
            raise SiteCheckError(f"{label}: missing DNS checklist item {expected}")
    if "full hosted mailbox" not in provider.get("requirement", ""):
        raise SiteCheckError(f"{label}: missing full-mailbox provider requirement")
    if "Cloudflare Email Routing" not in provider.get("notEnoughByItself", ""):
        raise SiteCheckError(f"{label}: missing Cloudflare receive-only caveat")
    for expected in ("Google Workspace", "Microsoft 365", "Zoho Mail"):
        if not any(expected in item for item in provider.get("acceptablePaths", [])):
            raise SiteCheckError(f"{label}: missing provider path {expected}")
    if "support@gcagochina.com" not in provider.get("decisionRule", ""):
        raise SiteCheckError(f"{label}: missing support mailbox decision rule")
    if "https://developers.cloudflare.com/email-routing/get-started/" not in provider.get("referenceDocs", []):
        raise SiteCheckError(f"{label}: missing Cloudflare reference doc")
    if provider_matrix.get("tool") != "tools/build_domain_email_provider_matrix.py":
        raise SiteCheckError(f"{label}: wrong provider matrix tool")
    if "--markdown" not in provider_matrix.get("command", ""):
        raise SiteCheckError(f"{label}: missing provider matrix markdown command")
    if "launch/domain_email_provider_matrix.json" not in provider_matrix.get("ownerArtifactCommand", ""):
        raise SiteCheckError(f"{label}: missing provider matrix owner artifact")
    if "without fetching live prices or guessing DNS records" not in provider_matrix.get("purpose", ""):
        raise SiteCheckError(f"{label}: missing provider matrix purpose boundary")
    if "Zoho Mail" not in provider_matrix.get("recommendedFirstCheck", ""):
        raise SiteCheckError(f"{label}: missing provider matrix recommended first check")
    if "Cloudflare Email Routing only" not in provider_matrix.get("notEnoughAlone", []):
        raise SiteCheckError(f"{label}: missing provider matrix Cloudflare caveat")
    if "mail provider purchase" not in provider_matrix.get("runBefore", []):
        raise SiteCheckError(f"{label}: missing provider matrix run-before gate")
    if "does not fetch live prices" not in provider_matrix.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing provider matrix price boundary")
    if "does not submit BaseScan request" not in provider_matrix.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing provider matrix BaseScan boundary")
    if dns_entry_builder.get("tool") != "tools/build_domain_email_dns_entry_packet.py":
        raise SiteCheckError(f"{label}: wrong DNS entry packet builder")
    if "launch/domain_email_dns_entry_packet.json" not in dns_entry_builder.get("commandTemplate", ""):
        raise SiteCheckError(f"{label}: missing DNS entry packet JSON output")
    if "provider-supplied MX, SPF, DKIM, and DMARC values" not in dns_entry_builder.get("purpose", ""):
        raise SiteCheckError(f"{label}: missing DNS entry packet purpose")
    if "provider dashboard shows exact MX/SPF/DKIM/DMARC values" not in dns_entry_builder.get("runAfter", []):
        raise SiteCheckError(f"{label}: missing DNS entry packet run-after gate")
    if "DNS record entry" not in dns_entry_builder.get("runBefore", []):
        raise SiteCheckError(f"{label}: missing DNS entry packet run-before gate")
    if "does not write DNS records" not in dns_entry_builder.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing DNS entry packet DNS-write boundary")
    if "does not store secrets" not in dns_entry_builder.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing DNS entry packet secrets boundary")
    if owner_packet.get("status") not in {
        "blocked-until-mailbox-dns-and-evidence-pass",
        "evidence-collected-ready-for-owner-resubmission",
    }:
        raise SiteCheckError(f"{label}: wrong owner action packet status")
    if not any(
        phrase in owner_packet.get("purpose", "")
        for phrase in ("remaining BaseScan domain-email blocker", "completed owner-side domain email evidence path")
    ):
        raise SiteCheckError(f"{label}: missing owner action packet purpose")
    if not any(
        phrase in step
        for step in owner_packet.get("stepsInOrder", [])
        for phrase in ("Enable a full mailbox for support@gcagochina.com", "support@gcagochina.com is enabled")
    ):
        raise SiteCheckError(f"{label}: missing owner mailbox action step")
    if "domain-email-provider-active.png" not in owner_packet.get("requiredEvidenceFiles", []):
        raise SiteCheckError(f"{label}: missing owner provider evidence file")
    if "domain-email-dns-mx-spf-dkim-dmarc.txt" not in owner_packet.get("requiredEvidenceFiles", []):
        raise SiteCheckError(f"{label}: missing owner DNS evidence file")
    if not any("check_basescan_resubmission_readiness.py --json --require-ready" in command for command in owner_packet.get("operatorCommands", [])):
        raise SiteCheckError(f"{label}: missing owner BaseScan preflight command")
    if not any("Outbound visible sender is not support@gcagochina.com" in item for item in owner_packet.get("stopConditions", [])):
        raise SiteCheckError(f"{label}: missing owner outbound stop condition")
    if "BaseScan resubmission preflight reports readyForBaseScanResubmission true" not in owner_packet.get("readyToResubmitWhen", []):
        raise SiteCheckError(f"{label}: missing owner preflight ready gate")
    if "does not submit BaseScan request" not in owner_packet.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing owner BaseScan boundary")
    if "Mail provider dashboard shows support@gcagochina.com as verified or active" not in evidence.get("requiredEvidence", []):
        raise SiteCheckError(f"{label}: missing provider-status evidence")
    if "domain-email-dns-mx-spf-dkim-dmarc.txt" not in evidence.get("recommendedFilenames", []):
        raise SiteCheckError(f"{label}: missing DNS evidence filename")
    if dns_check.get("tool") != "tools/check_domain_email_dns.py":
        raise SiteCheckError(f"{label}: wrong operator DNS check tool")
    if "--dkim-selector <provider-selector>" not in dns_check.get("command", ""):
        raise SiteCheckError(f"{label}: missing DKIM selector command")
    if "DKIM" not in dns_check.get("checks", []):
        raise SiteCheckError(f"{label}: missing DKIM operator DNS check")
    if "does not touch wallets or contracts" not in dns_check.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing operator DNS check wallet boundary")
    if packet_builder.get("tool") != "tools/build_domain_email_evidence_packet.py":
        raise SiteCheckError(f"{label}: wrong operator evidence packet builder")
    if "launch/domain_email_evidence_packet.json" not in packet_builder.get("outputs", []):
        raise SiteCheckError(f"{label}: missing evidence packet JSON output")
    if "readyForBaseScanEmailEvidence is true in the DNS check" not in packet_builder.get("readyRequires", []):
        raise SiteCheckError(f"{label}: missing DNS ready requirement for evidence packet")
    if "does not submit BaseScan request" not in packet_builder.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing packet builder BaseScan boundary")
    if evidence_checklist.get("pageUrl") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong evidence checklist page URL")
    if evidence_checklist.get("jsonUrl") != DOMAIN_EMAIL_EVIDENCE_URL:
        raise SiteCheckError(f"{label}: wrong evidence checklist JSON URL")
    if evidence_checklist.get("status") not in {
        "blocked-until-domain-email-evidence-collected",
        "evidence-collected-private-ready",
    }:
        raise SiteCheckError(f"{label}: wrong evidence checklist status")
    if "private domain email evidence packet" not in evidence_checklist.get("purpose", ""):
        raise SiteCheckError(f"{label}: missing evidence checklist purpose")
    if evidence_checklist.get("privateEvidenceDirectory") != "launch/domain_email_evidence":
        raise SiteCheckError(f"{label}: wrong evidence checklist private directory")
    if "domain-email-provider-active.png" not in evidence_checklist.get("requiredEvidenceFiles", []):
        raise SiteCheckError(f"{label}: missing checklist provider evidence file")
    if "support-page-domain-email.png" not in evidence_checklist.get("requiredEvidenceFiles", []):
        raise SiteCheckError(f"{label}: missing checklist support page proof")
    if "does not publish private mailbox screenshots" not in evidence_checklist.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing checklist private screenshot boundary")
    if "does not submit BaseScan request" not in evidence_checklist.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing checklist BaseScan boundary")
    if switch_builder.get("tool") != "tools/build_domain_email_switch_plan.py":
        raise SiteCheckError(f"{label}: wrong operator switch plan builder")
    if "--json" not in switch_builder.get("command", ""):
        raise SiteCheckError(f"{label}: missing switch plan JSON command")
    if "launch/domain_email_switch_plan.json" not in switch_builder.get("ownerArtifactCommand", ""):
        raise SiteCheckError(f"{label}: missing switch plan owner artifact")
    if "--patch" not in switch_builder.get("patchPreviewCommand", ""):
        raise SiteCheckError(f"{label}: missing switch plan patch preview command")
    if "launch/domain_email_switch_preview.patch" not in switch_builder.get("ownerPatchPreviewCommand", ""):
        raise SiteCheckError(f"{label}: missing switch plan patch preview artifact")
    if "legacy Outlook-email references" not in switch_builder.get("purpose", ""):
        raise SiteCheckError(f"{label}: missing legacy-email switch purpose")
    if "support@gcagochina.com" not in switch_builder.get("purpose", ""):
        raise SiteCheckError(f"{label}: missing target-email switch purpose")
    if "patch preview is generated only and not applied" not in switch_builder.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing switch plan patch preview boundary")
    if "does not edit files" not in switch_builder.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing switch plan edit boundary")
    if public_switch_checker.get("tool") != "tools/check_domain_email_public_switch.py":
        raise SiteCheckError(f"{label}: wrong public switch checker tool")
    if "--require-switched" not in public_switch_checker.get("command", ""):
        raise SiteCheckError(f"{label}: missing public switch checker require gate")
    if "no longer publish the previous public email" not in public_switch_checker.get("purpose", ""):
        raise SiteCheckError(f"{label}: missing public switch checker legacy-email purpose")
    if "support@gcagochina.com" not in public_switch_checker.get("purpose", ""):
        raise SiteCheckError(f"{label}: missing public switch checker target-email purpose")
    if "domain email switch plan has been reviewed" not in public_switch_checker.get("runAfter", []):
        raise SiteCheckError(f"{label}: missing public switch checker run-after gate")
    if "any critical file still contains the previous public email" not in public_switch_checker.get("blocksWhen", []):
        raise SiteCheckError(f"{label}: missing public switch checker legacy-email block")
    if "tools/check_basescan_resubmission_readiness.py" not in public_switch_checker.get("enforcedBy", []):
        raise SiteCheckError(f"{label}: missing public switch checker preflight enforcement")
    if "tools/build_basescan_submission_package.py" not in public_switch_checker.get("enforcedBy", []):
        raise SiteCheckError(f"{label}: missing public switch checker submission package enforcement")
    if "read-only check" not in public_switch_checker.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing public switch checker read-only boundary")
    if "does not edit files" not in public_switch_checker.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing public switch checker edit boundary")
    if policy.get("nextCleanSubmissionSender") not in {
        "support@gcagochina.com after activation",
        "support@gcagochina.com",
    }:
        raise SiteCheckError(f"{label}: wrong next BaseScan sender policy")
    if not any("evidence" in item for item in policy.get("doNotResubmitBefore", [])):
        raise SiteCheckError(f"{label}: missing evidence archive gate")
    if "site/support.html" not in payload.get("filesToUpdateAfterActivation", []):
        raise SiteCheckError(f"{label}: missing support update file")
    if current_switch.get("status") not in {"public-email-switch-pending", "public-email-switch-complete"}:
        raise SiteCheckError(f"{label}: wrong current public switch status")
    if current_switch.get("filesStillUsingCurrentEmail") not in {0, 15}:
        raise SiteCheckError(f"{label}: wrong current old-email file count")
    if current_switch.get("currentEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong current switch email")
    if current_switch.get("legacyEmail") != "GCAgochina@outlook.com":
        raise SiteCheckError(f"{label}: wrong current switch legacy email")
    if current_switch.get("targetDomainEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong current switch target email")
    if current_switch.get("status") != "public-email-switch-complete" and "site/project.json" not in current_switch.get("oldEmailFilePaths", []):
        raise SiteCheckError(f"{label}: missing current switch project file")
    if current_switch.get("status") != "public-email-switch-complete" and "launch/basescan_resubmission_package.md" not in current_switch.get("oldEmailFilePaths", []):
        raise SiteCheckError(f"{label}: missing current switch launch package file")
    if current_switch.get("status") != "public-email-switch-complete" and "site/reviewer-kit.json" not in current_switch.get("targetAwareButStillTracked", []):
        raise SiteCheckError(f"{label}: missing target-aware reviewer kit file")
    if (
        "tools/check_domain_email_public_switch.py --json --require-switched passes"
        not in current_switch.get("switchOnlyAfter", [])
        and "tools/check_domain_email_public_switch.py --json --require-switched passes"
        not in current_switch.get("switchCompletedAfter", [])
    ):
        raise SiteCheckError(f"{label}: missing current switch final checker gate")
    if not any("domain email" in item for item in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing safe setup-plan claim")
    if not any("BaseScan token profile approval" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing inactive-domain-email boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_domain_email_evidence_page(text: str) -> None:
    label = "/domain-email-evidence.html"
    assert_social_preview_meta(text, label, DOMAIN_EMAIL_EVIDENCE_PAGE_URL)
    for expected in (
        "GCA Domain Email Evidence Checklist",
        "Public Reviewer Checklist",
        "Evidence Collected",
        "support@gcagochina.com",
        "Target Domain Email",
        "private mailbox and DNS proof remain archived locally for reviewer follow-up",
        "launch/domain_email_evidence",
        "Current Boundary",
        "Active and aligned",
        "Reviewer Use",
        "Required Evidence Files",
        "Five Files To Save Privately Before Resubmission",
        "domain-email-provider-active.png",
        "domain-email-dns-mx-spf-dkim-dmarc.txt",
        "domain-email-inbound-test.png",
        "domain-email-outbound-test.png",
        "support-page-domain-email.png",
        "Execution Order",
        "Do These In Order",
        "readyForBaseScanEmailEvidence",
        "Operator Commands",
        "tools/build_domain_email_evidence_packet.py",
        "tools/check_domain_email_dns.py",
        "tools/check_basescan_resubmission_readiness.py --json --require-ready",
        "Stop Conditions",
        "readyForBaseScanResubmission",
        "Boundaries",
        "No DNS Writes",
        "No Email Sending",
        "No BaseScan Submission",
        "No Wallet Actions",
        "No Secret Storage",
        "No Private Screenshot Publishing",
        "domain-email.html",
        "basescan-remediation.html",
        "tim-chen.html",
        "platform-replies.html",
    ):
        assert_contains(text, expected, label)
    assert_not_contains(text, 'href="domain-email-evidence.json"', label)
    assert_not_contains(text, 'href="domain-email.json"', label)
    assert_not_contains(text, 'href="project.json"', label)
    assert_not_contains(text, "until domain email tests pass", label)
    assert_not_contains(text, "GCAgochina@outlook.com", label)
    assert_no_forbidden_public_claims(text, label)


def validate_domain_email_evidence_json(text: str) -> None:
    label = "/domain-email-evidence.json"
    payload = load_json(text, label)
    base_scan_use = payload.get("baseScanUse", {})
    commands = payload.get("commands", {})
    boundaries = payload.get("boundaries", {})
    related = payload.get("relatedPublicPages", {})
    evidence_files = payload.get("requiredEvidenceFiles", [])

    if payload.get("schema") != DOMAIN_EMAIL_EVIDENCE_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("lastUpdated") != "2026-05-30":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("status") not in {
        "blocked-until-domain-email-evidence-collected",
        "domain-email-evidence-collected-private-ready",
    }:
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("currentPublicEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong currentPublicEmail")
    if payload.get("targetDomainEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong targetDomainEmail")
    if payload.get("evidenceDirectory") != "launch/domain_email_evidence":
        raise SiteCheckError(f"{label}: wrong evidence directory")
    if payload.get("evidenceDirectoryIgnoredByGit") is not True:
        raise SiteCheckError(f"{label}: evidence directory must be git-ignored")
    if payload.get("publicSafe") is not True:
        raise SiteCheckError(f"{label}: publicSafe must be true")
    if payload.get("privateEvidencePublished") is not False:
        raise SiteCheckError(f"{label}: private evidence must not be public")
    if base_scan_use.get("readyForResubmission") not in {False, True}:
        raise SiteCheckError(f"{label}: invalid BaseScan resubmission ready flag")
    if base_scan_use.get("reviewerPage") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewerPage")
    if base_scan_use.get("setupPlan") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong setupPlan")
    if base_scan_use.get("baseScanRemediation") != BASESCAN_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanRemediation")
    if base_scan_use.get("founderProfile") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong founderProfile")

    expected_files = {
        "domain-email-provider-active.png",
        "domain-email-dns-mx-spf-dkim-dmarc.txt",
        "domain-email-inbound-test.png",
        "domain-email-outbound-test.png",
        "support-page-domain-email.png",
    }
    actual_files = {item.get("fileName") for item in evidence_files if isinstance(item, dict)}
    if expected_files != actual_files:
        raise SiteCheckError(f"{label}: wrong evidence file set")
    for item in evidence_files:
        if item.get("safeToCommit") is not False or item.get("keepPrivate") is not True:
            raise SiteCheckError(f"{label}: evidence file must stay private")
        if not item.get("path", "").startswith("launch/domain_email_evidence/"):
            raise SiteCheckError(f"{label}: evidence path outside private directory")

    for expected in (
        "Choose a full mailbox provider that can receive and send as support@gcagochina.com.",
        "Switch public support/BaseScan email values only after DNS and mail-flow evidence are complete.",
        "Build launch/domain_email_evidence_packet.json and run the BaseScan resubmission preflight.",
    ):
        if expected not in payload.get("stepsInOrder", []):
            raise SiteCheckError(f"{label}: missing step {expected}")
    if "build_domain_email_evidence_packet.py --init-evidence-dir" not in commands.get("initEvidenceDirectory", ""):
        raise SiteCheckError(f"{label}: missing init evidence command")
    if "--dkim-selector <provider-selector>" not in commands.get("dnsCheck", ""):
        raise SiteCheckError(f"{label}: missing DNS selector command")
    if "launch/domain_email_evidence_packet.json" not in commands.get("buildEvidencePacket", ""):
        raise SiteCheckError(f"{label}: missing evidence packet output")
    if commands.get("finalPreflight") != "python3 tools/check_basescan_resubmission_readiness.py --json --require-ready":
        raise SiteCheckError(f"{label}: wrong final preflight command")
    for expected in (
        "Any required evidence file is missing",
        "BaseScan resubmission preflight reports readyForBaseScanResubmission false",
    ):
        if not any(expected in item for item in payload.get("stopConditions", [])):
            raise SiteCheckError(f"{label}: missing stop condition {expected}")
    for expected_key in (
        "writesDnsRecords",
        "sendsEmail",
        "submitsBaseScanRequest",
        "touchesWalletsOrContracts",
        "storesSecrets",
        "commitsPrivateEvidence",
    ):
        if boundaries.get(expected_key) is not False:
            raise SiteCheckError(f"{label}: boundary {expected_key} must be false")
    if not any("BaseScan token profile approval" in item for item in payload.get("publicClaimBoundaries", [])):
        raise SiteCheckError(f"{label}: missing BaseScan public claim boundary")
    if related.get("domainEmailPlan") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong related domain email plan")
    if related.get("baseScanRemediation") != BASESCAN_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong related BaseScan remediation")
    if related.get("founderProfile") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong related founder profile")
    if related.get("platformReplies") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong related platform replies")
    if related.get("dataRoom") != DATA_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong related data room")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_basescan_remediation_page(text: str) -> None:
    label = "/basescan-remediation.html"
    assert_social_preview_meta(text, label, BASESCAN_REMEDIATION_PAGE_URL)
    for expected in (
        "GCA BaseScan Token Profile Remediation",
        "BaseScan Remediation / 2026-05-23",
        "2026-06-06T11:10:54Z",
        "public BaseScan preflight page now matches that package",
        "Ready for resubmission",
        "Domain Email",
        "Ready for owner resubmission",
        "support@gcagochina.com",
        "DNS snapshot",
        "MX / SPF / DKIM / DMARC present",
        "domain email evidence packet is ready",
        "Professional profile",
        TIM_CHEN_PROFILE_PAGE_URL,
        "Preflight checker",
        "tools/check_basescan_resubmission_readiness.py",
        "Readable preflight gate",
        BASESCAN_PREFLIGHT_PAGE_URL,
        "BaseScan values, domain email evidence packet, public email switch alignment, domain email snapshot alignment, and reviewer URLs",
        "Reviewer checklist",
        "Reviewer checklist required",
        "A ready reviewer checklist has been generated",
        "Current checklist artifacts are ready",
        "tools/build_basescan_reviewer_checklist.py --markdown",
        "launch/basescan_reviewer_checklist.json",
        "launch/basescan_reviewer_checklist.md",
        "completed domain email item",
        "Submission package",
        "tools/build_basescan_submission_package.py",
        "Final package ready",
        DOMAIN_EMAIL_PAGE_URL,
        DOMAIN_EMAIL_EVIDENCE_PAGE_URL,
        "Domain email evidence checklist",
        "Evidence Checklist",
        "BaseScan Handoff",
        "basescan-handoff.html",
        "Tim Chen",
        "team.html",
        GITHUB_REPO_URL,
        "Ready to resubmit today?",
        "Yes. Owner may submit one clean BaseScan token profile update",
        "Current email blocker",
        "Platform Replies",
        PLATFORM_REPLIES_PAGE_URL,
        "Platform Replies template",
        "Do not claim the BaseScan token profile is approved",
    ):
        assert_contains(text, expected, label)
    assert_no_forbidden_public_claims(text, label)
    assert_no_public_data_room_terms(text, label)
    assert_not_contains(text, "DRAFT ONLY - DO NOT SUBMIT BASESCAN YET.", label)


def validate_basescan_remediation_json(text: str) -> None:
    label = "/basescan-remediation.json"
    payload = load_json(text, label)
    identity = payload.get("officialIdentity", {})
    email_state = payload.get("currentEmailState", {})
    team = payload.get("teamTransparency", {})
    gate = payload.get("nextSubmissionGate", {})

    if payload.get("schema") != BASESCAN_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != BASESCAN_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("status") not in {
        "basescan-ready-for-owner-resubmission",
    }:
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if identity.get("team") != TEAM_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong team page")
    if identity.get("timChenProfessionalProfile") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong Tim Chen profile page")
    if identity.get("domainEmailSetupPlan") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailSetupPlan")
    if identity.get("domainEmailSetupPlanData") != DOMAIN_EMAIL_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailSetupPlanData")
    if identity.get("domainEmailEvidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailEvidenceChecklist")
    if identity.get("domainEmailEvidenceChecklistData") != DOMAIN_EMAIL_EVIDENCE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailEvidenceChecklistData")
    if identity.get("baseScanPreflightPage") != BASESCAN_PREFLIGHT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanPreflightPage")
    if identity.get("baseScanPreflightData") != BASESCAN_PREFLIGHT_URL:
        raise SiteCheckError(f"{label}: wrong baseScanPreflightData")
    if identity.get("platformRepliesPage") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesPage")
    if identity.get("platformRepliesData") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesData")
    if identity.get("github") != GITHUB_REPO_URL:
        raise SiteCheckError(f"{label}: wrong GitHub URL")
    if email_state.get("domainEmailRecommendedBeforeNextSubmission") not in {False, True}:
        raise SiteCheckError(f"{label}: missing domain email recommendation")
    if email_state.get("domainEmailSetupPlan") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong email-state domainEmailSetupPlan")
    if email_state.get("domainEmailSetupPlanData") != DOMAIN_EMAIL_URL:
        raise SiteCheckError(f"{label}: wrong email-state domainEmailSetupPlanData")
    if email_state.get("domainEmailEvidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong email-state domainEmailEvidenceChecklist")
    if email_state.get("domainEmailEvidenceChecklistData") != DOMAIN_EMAIL_EVIDENCE_URL:
        raise SiteCheckError(f"{label}: wrong email-state domainEmailEvidenceChecklistData")
    latest_dns = email_state.get("latestDnsSnapshot", {})
    if latest_dns.get("checkedAt") not in {"2026-05-25T15:04:09Z", "2026-05-30T08:13:47Z", "2026-05-30T16:24:34Z"}:
        raise SiteCheckError(f"{label}: wrong latest DNS snapshot timestamp")
    if latest_dns.get("readyForBaseScanEmailEvidence") not in {False, True}:
        raise SiteCheckError(f"{label}: invalid latest DNS snapshot ready flag")
    if set(latest_dns.get("missingOrBlockedChecks", [])) not in ({"mx", "spf", "dmarc", "dkim"}, set()):
        raise SiteCheckError(f"{label}: wrong latest DNS missing checks")
    if latest_dns.get("checks", {}).get("dkim") not in {"selector-required", "present"}:
        raise SiteCheckError(f"{label}: missing DKIM selector-required blocker")
    if latest_dns.get("evidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong latest DNS evidence checklist")
    if "support@gcagochina.com" not in email_state.get("recommendedDomainEmailExamples", []):
        raise SiteCheckError(f"{label}: missing recommended support domain email")
    if team.get("publicFounder") != "Tim Chen":
        raise SiteCheckError(f"{label}: wrong public founder")
    if team.get("officialTeamPage") != f"{TEAM_PAGE_URL}#tim-chen":
        raise SiteCheckError(f"{label}: wrong founder profile permalink")
    if team.get("officialProfessionalProfile") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong official professional profile")
    if team.get("officialProfessionalProfileData") != TIM_CHEN_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong official professional profile data")
    if team.get("equivalentOfficialProfessionalProfilePublished") is not True:
        raise SiteCheckError(f"{label}: missing official-domain professional profile")
    if team.get("externalProfessionalProfileStillRecommended") is not True:
        raise SiteCheckError(f"{label}: missing external professional profile recommendation")
    if gate.get("ready") not in {False, True}:
        raise SiteCheckError(f"{label}: invalid submission gate ready flag")
    final_package = gate.get("finalSubmissionPackage", {})
    if final_package.get("generatedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong final submission package timestamp")
    if final_package.get("markdown") != "launch/basescan_final_submission_package.md":
        raise SiteCheckError(f"{label}: wrong final submission markdown path")
    if final_package.get("json") != "launch/basescan_final_submission_package.json":
        raise SiteCheckError(f"{label}: wrong final submission json path")
    if final_package.get("preflightLastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong final submission preflight date")
    preflight = gate.get("preflightTool", {})
    if preflight.get("tool") != "tools/check_basescan_resubmission_readiness.py":
        raise SiteCheckError(f"{label}: wrong preflight tool")
    if "--require-ready" not in preflight.get("command", ""):
        raise SiteCheckError(f"{label}: missing preflight require-ready command")
    if "reviewer URLs are reachable" not in preflight.get("requires", []):
        raise SiteCheckError(f"{label}: missing reviewer URL preflight gate")
    if "public email switch alignment passes" not in preflight.get("requires", []):
        raise SiteCheckError(f"{label}: missing public email switch preflight gate")
    if "domain email snapshot alignment passes" not in preflight.get("requires", []):
        raise SiteCheckError(f"{label}: missing domain email snapshot alignment preflight gate")
    if "does not submit BaseScan request" not in preflight.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing preflight BaseScan boundary")
    checklist_builder = gate.get("reviewerChecklistBuilder", {})
    if checklist_builder.get("tool") != "tools/build_basescan_reviewer_checklist.py":
        raise SiteCheckError(f"{label}: wrong reviewer checklist builder")
    if "--markdown" not in checklist_builder.get("command", ""):
        raise SiteCheckError(f"{label}: missing reviewer checklist markdown command")
    if "launch/basescan_reviewer_checklist.json" not in checklist_builder.get("ownerArtifactCommand", ""):
        raise SiteCheckError(f"{label}: missing reviewer checklist owner artifact")
    if not any(
        phrase in checklist_builder.get("purpose", "")
        for phrase in ("sender-domain-email blocker", "current public GCA evidence")
    ):
        raise SiteCheckError(f"{label}: missing reviewer checklist domain-email purpose")
    if "does not sign wallet messages" not in checklist_builder.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing reviewer checklist wallet boundary")
    if checklist_builder.get("currentArtifactStatus") not in {
        "generated-blocked-before-domain-email-evidence",
        "ready-after-domain-email-evidence",
    }:
        raise SiteCheckError(f"{label}: wrong reviewer checklist artifact status")
    if "launch/basescan_reviewer_checklist.json" not in checklist_builder.get("currentArtifacts", []):
        raise SiteCheckError(f"{label}: missing current reviewer checklist JSON artifact")
    if "launch/basescan_reviewer_checklist.md" not in checklist_builder.get("currentArtifacts", []):
        raise SiteCheckError(f"{label}: missing current reviewer checklist markdown artifact")
    if checklist_builder.get("currentBlockedItems") not in (["sender-domain-email"], []):
        raise SiteCheckError(f"{label}: wrong current reviewer checklist blockers")
    if "domain email evidence packet is ready" not in checklist_builder.get("regenerateAfter", []):
        raise SiteCheckError(f"{label}: missing reviewer checklist domain-email evidence regeneration gate")
    if "public email switch alignment passes" not in checklist_builder.get("regenerateAfter", []):
        raise SiteCheckError(f"{label}: missing reviewer checklist public-switch regeneration gate")
    submission_builder = gate.get("submissionPackageBuilder", {})
    if submission_builder.get("tool") != "tools/build_basescan_submission_package.py":
        raise SiteCheckError(f"{label}: wrong submission package builder")
    if "launch/basescan_final_submission_package.json" not in submission_builder.get("outputs", []):
        raise SiteCheckError(f"{label}: missing final submission JSON output")
    if "readyForOwnerSubmission is true" not in submission_builder.get("readyRequires", []):
        raise SiteCheckError(f"{label}: missing final submission ready gate")
    if "public email switch alignment passes" not in submission_builder.get("readyRequires", []):
        raise SiteCheckError(f"{label}: missing final submission public switch gate")
    if "domain email snapshot alignment passes" not in submission_builder.get("readyRequires", []):
        raise SiteCheckError(f"{label}: missing final submission snapshot alignment gate")
    if "baseScanReviewerComment" not in submission_builder.get("copyPasteBlocks", []):
        raise SiteCheckError(f"{label}: missing final submission reviewer comment copy block")
    if submission_builder.get("blockedDraftMarker") != "DRAFT ONLY - DO NOT SUBMIT BASESCAN YET.":
        raise SiteCheckError(f"{label}: missing final submission blocked draft marker")
    if "does not sign wallet messages" not in submission_builder.get("boundaries", []):
        raise SiteCheckError(f"{label}: missing final submission wallet-signing boundary")
    if not any("https://gcagochina.com/platform-replies.html" in item for item in gate.get("requiredBeforeReady", [])):
        raise SiteCheckError(f"{label}: missing Platform Replies next-submission gate")
    if not any(
        DOMAIN_EMAIL_EVIDENCE_PAGE_URL in item
        or "domain email evidence packet" in item
        or "domain_email_evidence_packet" in item
        or "domain email evidence" in item
        for item in gate.get("requiredBeforeReady", []) + preflight.get("requires", [])
    ):
        raise SiteCheckError(f"{label}: missing domain email evidence checklist gate")
    if not any(
        "2026-05-25 DNS snapshot blockers" in item
        or "2026-05-30 DNS snapshot blockers" in item
        or "readyForBaseScanResubmission is true" in item
        for item in gate.get("requiredBeforeReady", []) + preflight.get("requires", [])
    ):
        raise SiteCheckError(f"{label}: missing latest DNS snapshot gate")
    assert_no_forbidden_public_claims(text, label)


def validate_basescan_preflight_page(text: str) -> None:
    label = "/basescan-preflight.html"
    assert_social_preview_meta(text, label, BASESCAN_PREFLIGHT_PAGE_URL)
    for expected in (
        "GCA BaseScan Resubmission Preflight",
        "BaseScan Preflight / Read-Only Gate",
        "Ready To Resubmit",
        "Yes",
        "Latest DNS Snapshot",
        "2026-05-30",
        "Preflight Refresh",
        "2026-06-07",
        "2026-06-06T11:10:54Z",
        "Main Blocker",
        "No local blocker",
        "Current Ready Evidence",
        "Required Inputs Before One Clean Submission",
        "support@gcagochina.com",
        "MX present",
        "SPF present",
        "DMARC present",
        "DKIM present",
        "MX/SPF/DKIM/DMARC present",
        "launch/domain_email_evidence_packet.json",
        "readyForBaseScanResubmission",
        "tools/check_domain_email_dns.py",
        "tools/build_domain_email_evidence_packet.py",
        "tools/check_domain_email_public_switch.py",
        "tools/check_domain_email_snapshot_alignment.py",
        "tools/check_basescan_resubmission_readiness.py",
        "tools/build_basescan_submission_package.py",
        "Final Package Is Ready Locally",
        "launch/basescan_final_submission_package.md",
        "Submit only one clean request",
        "reviewer comment is clean for submission",
        "Evidence Links To Include When Ready",
        "Tim Chen profile",
        "team.html#tim-chen",
        "domain-email.html",
        "domain-email-evidence.html",
        "basescan-remediation.html",
        "basescan-handoff.html",
        "BaseScan Handoff",
        GITHUB_REPO_URL,
        "GCA/USDT on Base Mainnet",
        "Submit Once And Keep Claim Boundaries",
        "does not sign wallet messages, submit forms, send email, write DNS records, or touch contracts",
    ):
        assert_contains(text, expected, label)
    assert_no_forbidden_public_claims(text, label)
    assert_no_public_data_room_terms(text, label)
    assert_not_contains(text, "DRAFT ONLY - DO NOT SUBMIT BASESCAN YET.", label)
    assert_not_contains(text, 'href="basescan-preflight.json"', label)


def validate_basescan_preflight_json(text: str) -> None:
    label = "/basescan-preflight.json"
    payload = load_json(text, label)
    commands = payload.get("commands", {})
    links = payload.get("evidenceLinks", {})
    boundaries = payload.get("boundaries", {})
    snapshot = payload.get("latestDnsSnapshot", {})

    if payload.get("schema") != BASESCAN_PREFLIGHT_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != BASESCAN_PREFLIGHT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("status") not in {
        "blocked-domain-email-before-basescan-resubmission",
        "ready-for-owner-basescan-resubmission",
    }:
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("readyForBaseScanResubmission") not in {False, True}:
        raise SiteCheckError(f"{label}: invalid ready flag")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("officialEmailCurrent") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong current official email")
    if payload.get("targetDomainEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong target domain email")
    refresh = payload.get("preflightRefresh", {})
    if refresh.get("finalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong final package refresh timestamp")
    if refresh.get("finalSubmissionPackageMarkdown") != "launch/basescan_final_submission_package.md":
        raise SiteCheckError(f"{label}: wrong final package markdown path")
    if refresh.get("finalSubmissionPackageJson") != "launch/basescan_final_submission_package.json":
        raise SiteCheckError(f"{label}: wrong final package json path")
    if snapshot.get("checkedAt") not in {"2026-05-30T08:13:47Z", "2026-05-30T16:24:34Z"}:
        raise SiteCheckError(f"{label}: wrong DNS snapshot")
    if snapshot.get("readyForBaseScanEmailEvidence") not in {False, True}:
        raise SiteCheckError(f"{label}: invalid DNS ready flag")
    if set(snapshot.get("missingOrBlockedChecks", [])) not in ({"mx", "spf", "dmarc", "dkim"}, set()):
        raise SiteCheckError(f"{label}: wrong missing DNS checks")
    for key in ("dnsCheck", "evidencePacket", "publicSwitchCheck", "snapshotAlignment", "baseScanPreflight", "finalDraft"):
        if key not in commands:
            raise SiteCheckError(f"{label}: missing command {key}")
    if "tools/check_basescan_resubmission_readiness.py --json --require-ready" not in commands.get("baseScanPreflight", ""):
        raise SiteCheckError(f"{label}: wrong BaseScan preflight command")
    if links.get("timChenProfessionalProfile") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong Tim Chen evidence link")
    if links.get("domainEmailEvidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong evidence checklist link")
    if links.get("baseScanRemediation") != BASESCAN_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong remediation link")
    if links.get("githubRepository") != GITHUB_REPO_URL:
        raise SiteCheckError(f"{label}: wrong GitHub link")
    if "readyForBaseScanResubmission is true" not in payload.get("doNotSubmitUntil", []):
        raise SiteCheckError(f"{label}: missing do-not-submit readiness gate")
    if "public token profile publication is not complete" not in payload.get("publicClaimBoundary", ""):
        raise SiteCheckError(f"{label}: missing public claim boundary")
    for key in (
        "submitsBaseScanRequest",
        "sendsEmail",
        "writesDnsRecords",
        "signsWalletMessages",
        "touchesWalletsOrContracts",
        "publishesPrivateMailboxScreenshots",
    ):
        if boundaries.get(key) is not False:
            raise SiteCheckError(f"{label}: boundary {key} must be false")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_basescan_handoff_page(text: str) -> None:
    label = "/basescan-handoff.html"
    assert_social_preview_meta(text, label, BASESCAN_HANDOFF_PAGE_URL)
    for expected in (
        "GCA BaseScan Handoff",
        "BaseScan Evidence Index",
        "Ready For Resubmission",
        "Yes",
        "support@gcagochina.com",
        "readyForBaseScanResubmission",
        "Final Copy Package",
        "Local path boundary",
        "owner-local artifacts, not public website links",
        "paste the generated text into BaseScan",
        "Package generated",
        "2026-06-06T11:10:54Z",
        "BaseScan Form Copy Blocks",
        "launch/basescan_final_submission_package.md",
        "tools/build_basescan_submission_package.py --json --require-ready",
        "Copy/Paste Reviewer Comment",
        "Please review the updated GCA token profile metadata",
        "Copy/Paste Basic Information",
        "Project Email Address: support@gcagochina.com",
        "Copy/Paste Evidence Links",
        "GitHub source repository: https://github.com/timchen078/gca_token",
        "Copy/Paste Market And Supply",
        "Official market route: GCA/USDT",
        "Reserve boundary: Do not describe the reserve as locked",
        "Copy/Paste Access And Claim Boundary",
        "Access and member-benefit boundaries",
        "Access API: https://gcagochina.com/access-api.html",
        "Review queue contract: https://gcagochina.com/review-queue.html",
        "No automatic token claim",
        "manual reserve-wallet processing",
        "BaseScan source verification",
        "Deployer-wallet ownership verification",
        "Returned again as information-insufficient on 2026-05-23",
        "2026-05-30: MX/SPF/DKIM/DMARC present",
        "Team Transparency",
        "Project Clarity",
        "Domain Email",
        "Contract Evidence",
        "Supply Disclosure",
        "Official Market Route",
        "Required Order",
        "tools/check_basescan_resubmission_readiness.py --json --require-ready",
        "Submit one clean BaseScan request only after the final preflight passes",
        "Readable Handoff Path",
        "does not submit BaseScan forms",
        "does not send email, write DNS records, sign messages, or touch wallets/contracts",
        "does not expose local",
        "package files as public website URLs",
        "does not claim BaseScan token profile approval",
        "does not publish private mailbox screenshots",
        "owner-side copy source, not a public evidence URL",
        MAINNET_ADDRESS,
        "Base Mainnet chain ID 8453",
        "team.html",
        "tim-chen.html",
        "domain-email.html",
        "domain-email-evidence.html",
        "basescan-preflight.html",
        "technical-report.html",
        "onchain-proofs.html",
        "token-safety.html",
        "reserve-statement.html",
        "holder-distribution.html",
        "liquidity.html",
        "platform-replies.html",
        "trust.html",
    ):
        assert_contains(text, expected, label)
    assert_no_forbidden_public_claims(text, label)
    assert_no_public_data_room_terms(text, label)
    assert_not_contains(text, 'href="basescan-handoff.json"', label)


def validate_basescan_handoff_json(text: str) -> None:
    label = "/basescan-handoff.json"
    payload = load_json(text, label)
    profile = payload.get("baseScanProfileStatus", {})
    final_package = payload.get("finalSubmissionPackage", {})
    dns = payload.get("domainEmailGate", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("boundaries", {})

    if payload.get("schema") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") not in {
        "blocked-until-domain-email-evidence-and-final-preflight-pass",
        "ready-for-owner-resubmission",
    }:
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if profile.get("readyForBaseScanResubmission") not in {False, True}:
        raise SiteCheckError(f"{label}: invalid ready flag")
    if profile.get("targetSender") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong target sender")
    if profile.get("currentActiveContact") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong current contact")
    if final_package.get("status") != "ready-for-owner-submission":
        raise SiteCheckError(f"{label}: wrong final package status")
    if final_package.get("generatedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong final package generatedAt")
    if "tools/build_basescan_submission_package.py --json --require-ready" not in final_package.get("builderCommand", ""):
        raise SiteCheckError(f"{label}: missing final package builder command")
    if final_package.get("outputMarkdown") != "launch/basescan_final_submission_package.md":
        raise SiteCheckError(f"{label}: wrong final package markdown output")
    if final_package.get("outputJson") != "launch/basescan_final_submission_package.json":
        raise SiteCheckError(f"{label}: wrong final package json output")
    if final_package.get("targetSender") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong final package target sender")
    if final_package.get("ownerOnly") is not True:
        raise SiteCheckError(f"{label}: final package should be owner-only")
    local_boundary = final_package.get("localPathBoundary", {})
    if local_boundary.get("mode") != "owner-local-artifact":
        raise SiteCheckError(f"{label}: wrong final package local boundary mode")
    if local_boundary.get("ownerPathPattern") != "launch/*.md/json":
        raise SiteCheckError(f"{label}: wrong final package local path pattern")
    if local_boundary.get("publicWebsitePathServed") is not False:
        raise SiteCheckError(f"{label}: launch package should not be served as public website path")
    if local_boundary.get("doNotPublishAsPublicUrl") is not True:
        raise SiteCheckError(f"{label}: launch package public-url guard missing")
    if "Paste the generated text into the BaseScan form" not in local_boundary.get("instruction", ""):
        raise SiteCheckError(f"{label}: missing local package paste instruction")
    public_pages = set(local_boundary.get("reviewerFacingPublicPages", []))
    for expected_page in (
        BASESCAN_HANDOFF_PAGE_URL,
        BASESCAN_PREFLIGHT_PAGE_URL,
        REVIEWER_KIT_PAGE_URL,
        DOMAIN_EMAIL_PAGE_URL,
        TIM_CHEN_PROFILE_PAGE_URL,
        TECHNICAL_REPORT_PAGE_URL,
        LIQUIDITY_PAGE_URL,
        PLATFORM_REPLIES_PAGE_URL,
    ):
        if expected_page not in public_pages:
            raise SiteCheckError(f"{label}: missing reviewer-facing public page {expected_page}")
    for expected_block in (
        "baseScanReviewerComment",
        "basicInformationPlainText",
        "evidenceLinksPlainText",
        "marketAndSupplyPlainText",
        "accessAndClaimBoundaryPlainText",
    ):
        if expected_block not in final_package.get("copyPasteBlocks", []):
            raise SiteCheckError(f"{label}: missing final package block {expected_block}")
        content = final_package.get("copyPasteContent", {}).get(expected_block, "")
        if not isinstance(content, str) or not content.strip():
            raise SiteCheckError(f"{label}: missing final package content {expected_block}")
    copy_content = final_package.get("copyPasteContent", {})
    for expected_text in (
        "Please review the updated GCA token profile metadata",
        "Project Email Address: support@gcagochina.com",
        "Tim Chen professional profile: https://gcagochina.com/tim-chen.html",
        "Official market route: GCA/USDT",
        "Reserve boundary: Do not describe the reserve as locked",
        "Access and member-benefit boundaries",
        "Review queue contract: https://gcagochina.com/review-queue.html",
        "No automatic token claim",
        "manual reserve-wallet processing",
    ):
        if not any(expected_text in str(value) for value in copy_content.values()):
            raise SiteCheckError(f"{label}: missing copy-paste text {expected_text}")
    final_boundaries = final_package.get("boundaries", {})
    for key in ("submitsBaseScanRequest", "sendsEmail", "signsWalletMessage", "touchesWalletOrContract"):
        if final_boundaries.get(key) is not False:
            raise SiteCheckError(f"{label}: final package boundary {key} must be false")
    if dns.get("readyForBaseScanEmailEvidence") not in {False, True}:
        raise SiteCheckError(f"{label}: invalid DNS evidence ready flag")
    if dns.get("snapshotPage") != f"{DOMAIN_EMAIL_PAGE_URL}#snapshotTitle":
        raise SiteCheckError(f"{label}: wrong DNS snapshot page")
    if dns.get("evidenceChecklistPage") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong evidence checklist page")
    if set(dns.get("missingOrBlockedChecks", [])) not in ({"mx", "spf", "dmarc", "dkim"}, set()):
        raise SiteCheckError(f"{label}: wrong DNS blockers")
    if links.get("baseScanHandoffPage") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong handoff page link")
    if links.get("baseScanHandoff") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong handoff data link")
    for key, expected in (
        ("reviewerKitPage", REVIEWER_KIT_PAGE_URL),
        ("baseScanPreflightPage", BASESCAN_PREFLIGHT_PAGE_URL),
        ("baseScanRemediationPage", BASESCAN_REMEDIATION_PAGE_URL),
        ("domainEmailPlanPage", DOMAIN_EMAIL_PAGE_URL),
        ("domainEmailEvidenceChecklistPage", DOMAIN_EMAIL_EVIDENCE_PAGE_URL),
        ("teamPage", TEAM_PAGE_URL),
        ("timChenProfessionalProfile", TIM_CHEN_PROFILE_PAGE_URL),
        ("technicalReportPage", TECHNICAL_REPORT_PAGE_URL),
        ("onchainProofsPage", ONCHAIN_PROOFS_PAGE_URL),
        ("tokenSafetyPage", TOKEN_SAFETY_PAGE_URL),
        ("reserveStatementPage", RESERVE_STATEMENT_PAGE_URL),
        ("holderDistributionPage", HOLDER_DISTRIBUTION_PAGE_URL),
        ("liquidityPage", LIQUIDITY_PAGE_URL),
        ("platformRepliesPage", PLATFORM_REPLIES_PAGE_URL),
        ("dataRoom", DATA_PAGE_URL),
    ):
        if links.get(key) != expected:
            raise SiteCheckError(f"{label}: wrong official link {key}")
    reason_text = json.dumps(payload.get("reviewerReasonMap", []))
    for expected in (
        "project/team information not clear enough",
        "sender email does not match official domain",
        "links, logo, website, and metadata need review",
        "contract, supply, and market evidence",
        "implemented-domain-email-ready",
        TIM_CHEN_PROFILE_PAGE_URL,
        DOMAIN_EMAIL_EVIDENCE_PAGE_URL,
        TECHNICAL_REPORT_PAGE_URL,
        LIQUIDITY_PAGE_URL,
    ):
        assert_contains(reason_text, expected, label)
    if "tools/check_basescan_resubmission_readiness.py --json --require-ready passes" not in payload.get("requiredBeforeNextSubmission", []):
        raise SiteCheckError(f"{label}: missing final preflight requirement")
    if "Regenerate launch/basescan_final_submission_package.md with tools/build_basescan_submission_package.py --json --require-ready." not in payload.get("submissionSequence", []):
        raise SiteCheckError(f"{label}: missing final package regeneration sequence")
    if "Submit one clean BaseScan request only after the final preflight passes." not in payload.get("submissionSequence", []):
        raise SiteCheckError(f"{label}: missing clean submission sequence")
    for key in (
        "submitsBaseScanRequest",
        "sendsEmail",
        "writesDns",
        "signsMessage",
        "touchesWalletOrContract",
        "claimsBaseScanApproval",
        "publishesPrivateMailboxEvidence",
        "publishesLocalLaunchArtifacts",
    ):
        if boundaries.get(key) is not False:
            raise SiteCheckError(f"{label}: boundary {key} must be false")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_action_plan_page(text: str) -> None:
    label = "/action-plan.html"
    assert_social_preview_meta(text, label, ACTION_PLAN_PAGE_URL)
    assert_contains(text, "About GCA", label)
    assert_contains(text, "about.html", label)
    for expected in (
        "GCA Action Plan",
        "Next-Step Operating Plan",
        "中文入口",
        "zh-cn.html",
        "What To Do Next",
        "Daily Status Queue",
        "daily-status.html",
        "BaseScan Action Queue From Latest Daily Status",
        "Old-email switch queue",
        "filesStillUsingOldEmail",
        "site/support.html",
        "site/project.json",
        "tools/check_basescan_resubmission_readiness.py --json --require-ready",
        "Maintain domain email gate",
        "support@gcagochina.com",
        "DNS snapshot",
        "MX present",
        "SPF present",
        "DMARC present",
        "DKIM present",
        "tools/check_domain_email_dns.py",
        "readyForBaseScanEmailEvidence",
        "Submit One Clean BaseScan Update",
        "Copy owner submission package",
        "BaseScan Handoff",
        "basescan-handoff.html",
        "中文 BaseScan 提交流程",
        "zh-basescan-submit.html",
        "no wallet transaction, approve, swap, or contract operation is needed",
        "private evidence packet ready for reviewer follow-up",
        "Duplicate BaseScan follow-ups",
        "public evidence checklist",
        "domain-email-evidence.html",
        "Email Evidence Checklist",
        "Improve Market Quality Legitimately",
        "Make Member Access Real",
        "Publish Consistent Content",
        "Choose Trust Upgrades When Needed",
        "Keep Boundaries Public",
        "Do Now",
        "Do Later",
        "What Not To Say",
        "Do not create fake trading activity",
        "Readable Reference Path",
        "Use These Pages First",
        "Normal users and community moderators should start from the readable verification",
        "BaseScan returned 2026-05-23; owner package ready",
        "domain-email.html",
        "Domain Email Plan",
        "basescan-remediation.html",
        "BaseScan Remediation",
        "basescan-preflight.html",
        "BaseScan Preflight",
        "Public account intake, read-only wallet checks, and eligible ledger records are live",
        "eligible ledger records are live",
        MAINNET_ADDRESS,
        BASE_USDT_ADDRESS,
        "Base Mainnet",
        "8453",
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "external-reviews.html",
        "reviewer-kit.html",
        "platform-replies.html",
        "market-quality.html",
        "access.html",
        "release-gates.html",
        "publishing-desk.html",
        "audit-readiness.html",
        "custody-roadmap.html",
        "site-map.html",
        "verify.html",
        "trust.html",
        "status.html",
        "support.html",
    ):
        assert_contains(text, expected, label)
    assert_no_public_data_room_terms(text, label)
    for forbidden_href in (
        "project.json",
        "tokenlist.json",
        "reviewer-kit.json",
        "platform-replies.json",
        "member-ledger.json",
    ):
        assert_not_contains(text, f'href="{forbidden_href}"', label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_cn_page(text: str) -> None:
    label = "/zh-cn.html"
    assert_social_preview_meta(text, label, ZH_CN_PAGE_URL)
    for expected in (
        "GCA 中文入口",
        "中文入口",
        "中文购买说明",
        "zh-buy.html",
        "中文参与指引",
        "zh-apply.html",
        "中文池子和流动性说明",
        "zh-liquidity.html",
        "中文总量和储备说明",
        "zh-supply.html",
        "中文安全和审计说明",
        "zh-security.html",
        "中文路线图",
        "zh-roadmap.html",
        "中文 FAQ",
        "zh-faq.html",
        "中文会员规则",
        "zh-members.html",
        "中文用户中心",
        "zh-access.html",
        "中文只读钱包验证",
        "zh-wallet-verify.html",
        "中文站点地图",
        "zh-site-map.html",
        "中文支持和资料提交",
        "zh-support.html",
        "邮箱注册",
        "register.html",
        "Base Mainnet",
        "chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "Tim Chen",
        "今日操作入口",
        "中文用户先打开这四个入口",
        "普通用户不需要打开原始数据文件",
        "合约和池子验证",
        "购买前检查",
        "邮箱注册用于项目更新、会员入口上线通知、产品测试邀请和官方支持回访",
        "会员入口和审核资料包",
        "打开会员入口",
        "用户可以生成可复制的审核资料包",
        "100 credits",
        "GCA Member 审核",
        "会员权益规则",
        "购买并连续持有 1,000,000 GCA 满 30 天后",
        "10,000 GCA 权益转账仍需人工审核",
        "项目方向",
        "Go China AI Quant Access",
        "China Narrative Radar",
        "AI Quant Access",
        "GCA Member Club",
        "中文 Web3 研究",
        "非托管量化风控工具",
        "清算复盘",
        "ENTRY_READY",
        "10,000 GCA",
        "100 GCA AI Quant Access credits",
        "1,000,000 GCA",
        "连续持有 30 天",
        "GCAgochina@outlook.com",
        "远程控制权限",
        X_URL,
        "https://t.me/gcagochinaofficial",
        "verify.html",
        "gca/member-access/",
        "buy.html",
        "zh-buy.html",
        "zh-member-checklist.html",
        "member-benefit-transfer.html",
        "members.html",
        "zh-apply.html",
        "zh-liquidity.html",
        "zh-supply.html",
        "zh-security.html",
        "zh-roadmap.html",
        "zh-members.html",
        "zh-access.html",
        "zh-support.html",
        "zh-site-map.html",
        "register.html",
        "member-ledger.html",
        "member-benefit.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        "中文 BaseScan 预检",
        "中文域名邮箱整改",
        "中文数据室说明",
        "zh-data.html",
        "平台审核资料",
        "结构化文件",
        "Platform Replies",
        "Technical Report",
        "Action Plan",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_buy_page(text: str) -> None:
    label = "/zh-buy.html"
    assert_social_preview_meta(text, label, ZH_BUY_PAGE_URL)
    for expected in (
        "GCA 中文购买说明",
        "中文购买说明",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        BASE_USDT_ADDRESS,
        "打开 Uniswap Swap",
        "中文池子说明",
        "中文安全说明",
        "不要从陌生链接开始",
        "MetaMask 手动导入",
        "Symbol",
        "GCA",
        "Decimals",
        "18",
        "小额测试",
        "expected output",
        "price impact",
        "slippage",
        "钱包不显示 GCA",
        "钱包地址、购买交易哈希、持有开始日期和只读余额验证结果",
        "私钥",
        "助记词",
        "交易所 API Secret",
        "提现权限",
        "验证码",
        "购买提示",
        "签名前确认这些内容",
        "购买入口只提供官方路线和核对参数",
        "确认钱包网络是 Base Mainnet / chainId 8453",
        "确认输出代币是 GCA",
        "确认使用的是 Base USDT 和官方 GCA/USDT 池",
        "如果钱包没有显示 GCA",
        "支持和官方资料",
        "中文站点地图",
        "zh-cn.html",
        "zh-apply.html",
        "zh-liquidity.html",
        "zh-supply.html",
        "zh-security.html",
        "zh-roadmap.html",
        "zh-faq.html",
        "zh-members.html",
        "zh-wallet-verify.html",
        "verify.html",
        "markets.html",
        "buy.html",
        "members.html",
        "support.html",
        "zh-support.html",
        "zh-site-map.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        "平台审核资料",
        "中文数据室说明",
        "Platform Replies",
        "zh-data.html",
        'href="data.html"',
        "zh-member-checklist.html",
        "中文会员审核资料清单",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_apply_page(text: str) -> None:
    label = "/zh-apply.html"
    assert_social_preview_meta(text, label, ZH_APPLY_PAGE_URL)
    for expected in (
        "GCA 中文参与指引",
        "中文参与指引",
        "中文购买说明",
        "zh-buy.html",
        "先验证 GCA",
        "中文会员规则",
        "中文池子和流动性说明",
        "zh-liquidity.html",
        "中文总量和储备说明",
        "zh-supply.html",
        "中文安全和审计说明",
        "zh-security.html",
        "Base Mainnet",
        "chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "可验证、可提交账户入口 / 会员资格人工确认",
        "公开账户入口",
        "受控 HTTPS 账户 UI",
        "100 credits 账本",
        "GCA Member 账本",
        "当前 GCA 仍处于早期建设阶段",
        "会员资格和权益处理仍需人工确认",
        "按这个顺序做",
        "钱包必须切到 Base Mainnet / chainId 8453",
        "官网公开路线是 Base 上的 GCA/USDT 池",
        "保存钱包地址、购买交易哈希、持有开始日期和只读余额验证结果",
        "10,000 GCA 路径",
        "100 GCA AI Quant Access credits",
        "1,000,000 GCA Member 路径",
        "连续持有至少 1,000,000 GCA 满 30 天",
        "10,000 GCA 会员权益审核",
        "不是现金、收入、交易结果承诺、费用返还、自动发放或风控豁免",
        "BaseScan 最终公开页面",
        "第三方审计",
        "没有独立审计报告",
        "私钥",
        "助记词",
        "交易所 API Secret",
        "提现权限",
        "不要通过人工制造交易活动或误导性宣传来改善市场数据",
        "参与、会员和钱包问题",
        "中文站点地图",
        "support@gcagochina.com",
        X_URL,
        "https://t.me/gcagochinaofficial",
        "zh-cn.html",
        "zh-liquidity.html",
        "zh-supply.html",
        "zh-security.html",
        "zh-faq.html",
        "zh-members.html",
        "verify.html",
        "buy.html",
        "zh-buy.html",
        "members.html",
        "member-ledger.html",
        "zh-wallet-verify.html",
        "zh-release-gates.html",
        "release-gates.html",
        "zh-support.html",
        "zh-site-map.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        "平台审核资料",
        "中文数据室说明",
        "Platform Replies",
        "zh-data.html",
        'href="data.html"',
        "zh-member-checklist.html",
        "中文会员审核资料清单",
        "仍需补域名邮箱后再提交",
        "2026-05-23 被退回整改",
        "GCAgochina@outlook.com",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_status_page(text: str) -> None:
    label = "/zh-status.html"
    assert_social_preview_meta(text, label, ZH_STATUS_PAGE_URL)
    for expected in (
        "GCA 中文项目进度",
        "中文项目进度",
        "BaseScan 源代码已验证",
        "会员入口和邮箱注册已上线",
        "Base Mainnet",
        "chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        BASE_USDT_ADDRESS,
        "zh-cn.html",
        "zh-apply.html",
        "zh-buy.html",
        "zh-liquidity.html",
        "zh-supply.html",
        "zh-security.html",
        "zh-faq.html",
        "zh-members.html",
        "zh-wallet-verify.html",
        "gca/member-access/",
        "register.html",
        "zh-support.html",
        "zh-roadmap.html",
        "zh-site-map.html",
        "tim-chen.html",
        "team.html",
        "product.html",
        "markets.html",
        "brand-kit.html",
        "whitepaper.html",
        "verify.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "中文审核状态",
        "BaseScan Token Profile",
        "退回整改",
        "已于 2026-05-23 被退回",
        "等待 BaseScan 官方审核和发布",
        "第三方审计",
        "LP 锁",
        "储备多签或锁仓",
        "尚未完成",
        "平台审核资料",
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        "Reviewer Kit",
        "zh-domain-email.html",
        "zh-basescan-preflight.html",
        "daily-status.html",
        "action-plan.html",
        "external-reviews.html",
        "wallet-warning.html",
        "blockaid-followup.html",
        "technical-report.html",
        "risk-remediation.html",
        "custody-roadmap.html",
        "audit-readiness.html",
        "data.html",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_domain_email_page(text: str) -> None:
    label = "/zh-domain-email.html"
    assert_social_preview_meta(text, label, ZH_DOMAIN_EMAIL_PAGE_URL)
    for expected in (
        "GCA 中文域名邮箱整改",
        "BaseScan 邮箱整改",
        "support@gcagochina.com",
        "旧 Outlook 邮箱",
        "2026-05-30 已通过",
        "可一次干净重提",
        "可以说已启用",
        "不能重复提交",
        "不能猜 DNS",
        "不能漏证据清单",
        "公开证据清单",
        "domain-email-evidence.html",
        "打开中文 BaseScan 预检",
        "zh-basescan-preflight.html",
        "BaseScan Handoff",
        "basescan-handoff.html",
        "每日状态队列",
        "daily-status.html",
        "下一步计划",
        "action-plan.html",
        "按 Daily Status 的 BaseScan 队列推进",
        "ownerActionQueue",
        "filesStillUsingOldEmail",
        "不能重复做",
        "Evidence Checklist",
        "私钥",
        "助记词",
        "交易所 API Secret",
        "提现权限",
        "正确复提交顺序",
        "DNS Entry Worksheet",
        "MX",
        "SPF",
        "DKIM",
        "DMARC",
        "邮箱服务商后台",
        "邮箱服务商选择",
        "要选完整邮箱，不要只选收信转发",
        "Cloudflare Email Routing 可以做收信转发",
        "Google Workspace",
        "Microsoft 365",
        "Zoho Mail",
        "邮箱方案矩阵",
        "先选能通过证据门槛的低成本完整邮箱",
        "tools/build_domain_email_provider_matrix.py --markdown",
        "launch/domain_email_provider_matrix.json",
        "tools/build_domain_email_dns_entry_packet.py",
        "launch/domain_email_dns_entry_packet.json",
        "Cloudflare Email Routing only",
        "root-domain SPF TXT",
        "--dkim-selector &lt;provider-selector&gt;",
        "2026-05-30 快照显示 MX/SPF/DKIM/DMARC present",
        "tools/check_domain_email_dns.py",
        "tools/build_domain_email_evidence_packet.py",
        "tools/check_basescan_resubmission_readiness.py",
        "中文预检页",
        "审核交接页",
        "tools/build_basescan_submission_package.py",
        "不会提交 BaseScan",
        "不会发送邮件",
        "不会写 DNS",
        "不会操作钱包或合约",
        "邮箱切换清单",
        "复核官网是否还残留旧邮箱引用",
        "当前预检快照",
        "旧 Outlook 邮箱残留数量为 0",
        "site/project.json",
        "launch/basescan_resubmission_package.md",
        "site/reviewer-kit.json",
        "tools/build_domain_email_switch_plan.py --json",
        "launch/domain_email_switch_plan.json",
        "公开邮箱切换检查",
        "tools/check_domain_email_public_switch.py --json --require-switched",
        "如果关键文件还出现",
        "公开邮箱切换门槛",
        "中文项目进度",
        "zh-status.html",
        "中文 BaseScan 预检",
        "zh-basescan-preflight.html",
        "中文支持",
        "zh-support.html",
        "中文站点地图",
        "zh-site-map.html",
        "Domain Email Plan",
        "domain-email.html",
        "DNS Worksheet",
        "domain-email.html#worksheetTitle",
        "BaseScan Remediation",
        "basescan-remediation.html",
        "Platform Replies",
        "platform-replies.html",
        "Tim Chen Profile",
        "tim-chen.html",
    ):
        assert_contains(text, expected, label)
    assert_not_contains(text, 'href="domain-email.json"', label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_basescan_preflight_page(text: str) -> None:
    label = "/zh-basescan-preflight.html"
    assert_social_preview_meta(text, label, ZH_BASESCAN_PREFLIGHT_PAGE_URL)
    for expected in (
        "GCA 中文 BaseScan 预检",
        "BaseScan 预检 / 只读门槛",
        "现在能重提吗",
        "可以准备一次",
        "最新 DNS 快照",
        "2026-05-30",
        "最终包刷新",
        "2026-06-07",
        "2026-06-06T11:10:54Z",
        "launch/",
        "本机 owner 工具输出",
        "不是公开证据链接",
        "主要卡点",
        "等待审核",
        "support@gcagochina.com",
        "MX present",
        "SPF present",
        "DMARC present",
        "DKIM present",
        "readyForBaseScanResubmission",
        "launch/domain_email_evidence_packet.json",
        "launch/basescan_reviewer_checklist.json",
        "launch/basescan_reviewer_checklist.md",
        "本地路径边界",
        "launch/*.md/json",
        "本机生成物",
        "不要把它当成官网 URL 提交",
        "tools/build_basescan_reviewer_checklist.py --markdown",
        "当前状态",
        "重提前必须有的材料",
        "服务商证明",
        "DNS 证明",
        "收件证明",
        "发件证明",
        "公开资料切换",
        "tools/check_domain_email_dns.py",
        "tools/build_domain_email_evidence_packet.py",
        "tools/check_domain_email_public_switch.py",
        "tools/check_domain_email_snapshot_alignment.py",
        "tools/check_basescan_resubmission_readiness.py",
        "tools/build_basescan_submission_package.py",
        "不会提交 BaseScan",
        "不会发送邮件",
        "不会写 DNS",
        "不会签名",
        "不会转账",
        "不会操作钱包或合约",
        "命令里的",
        "本地 JSON/MD 文件不对外发布",
        "https://gcagochina.com/...",
        "通过后要给 BaseScan 的证据链接",
        "tim-chen.html",
        "team.html#tim-chen",
        "domain-email.html",
        "domain-email-evidence.html",
        "BaseScan Handoff",
        "zh-basescan-handoff.html",
        "中文复审复制包",
        "zh-basescan-followup.html",
        "中文提交后跟进",
        "basescan-handoff.html",
        "zh-basescan-submit.html",
        "中文 BaseScan 提交流程",
        "basescan-remediation.html",
        GITHUB_REPO_URL,
        "Base Mainnet GCA/USDT",
        "现在不要做这些",
        "不要重复提交",
        "可以说邮箱已启用",
        "不要说 BaseScan 已通过",
        "最终提交包检查",
        "不要提交本地包地址",
        "launch/basescan_final_submission_package.md",
        "不要公开私密截图",
        "不要做链上动作",
        "本地 launch 包不是公网证据链接",
        "zh-domain-email.html",
        "zh-status.html",
        "zh-site-map.html",
        "basescan-preflight.html",
    ):
        assert_contains(text, expected, label)
    assert_not_contains(text, 'href="basescan-preflight.json"', label)
    assert_no_forbidden_public_claims(text, label)
    assert_not_contains(text, "DRAFT ONLY - DO NOT SUBMIT BASESCAN YET.", label)


def validate_zh_basescan_submit_page(text: str) -> None:
    label = "/zh-basescan-submit.html"
    assert_social_preview_meta(text, label, ZH_BASESCAN_SUBMIT_PAGE_URL)
    for expected in (
        "GCA 中文 BaseScan 提交流程",
        "BaseScan 提交 / owner 手动操作",
        "owner 在浏览器里手动提交 BaseScan Token Profile 更新",
        "support@gcagochina.com",
        "不会提交 BaseScan",
        "不会发送邮件",
        "不会连接钱包",
        "不会触碰合约",
        "不要把本机",
        "launch/*.md/json",
        "只用于本地生成复制文本",
        "给 BaseScan 的链接应来自",
        "gcagochina.com",
        "打开 BaseScan Token Update",
        "https://basescan.org/tokenupdate/",
        "zh-basescan-handoff.html",
        "中文复审复制包",
        "zh-basescan-followup.html",
        "提交后跟进",
        "BaseScan Handoff",
        "zh-basescan-preflight.html",
        "domain-email-evidence.html",
        "提交前确认",
        "readyForBaseScanResubmission",
        "Tim Chen 职业资料",
        "team.html#tim-chen",
        "官网、白皮书、品牌资料、支持页、GitHub、Telegram、X、GCA/USDT 池",
        "Access / Claim Boundary",
        "100 credits 是账户服务记录",
        "10,000 GCA 会员权益不是自动领取或自助转账",
        "本地包边界",
        "只作为本机复制来源",
        "不是公网 URL",
        "不要把它写进 BaseScan 的证据链接字段",
        "只开一次新的 BaseScan Token Profile update",
        "手动打开顺序",
        "选择 Base Mainnet",
        "access and claim boundary",
        MAINNET_ADDRESS,
        "Copy/Paste Basic Information",
        "Copy/Paste Reviewer Comment",
        "Copy/Paste Evidence Links",
        "Copy/Paste Market And Supply",
        "Copy/Paste Access And Claim Boundary",
        "100 credits 是账户服务记录，GCA Member 需要 1,000,000 GCA / 30 天证据",
        "Project Email Address: support@gcagochina.com",
        "Token Symbol: GCA",
        "Decimals: 18",
        "Total Supply: 1000000000",
        "https://gcagochina.com/assets/gca-logo.svg",
        "https://gcagochina.com/support.html",
        "提交后要保存什么",
        "BaseScan ticket",
        "签名记录",
        "不要说已通过",
        "不要换回旧邮箱",
        "不要使用旧池",
        "不要夸大安全",
        "第三方审计尚未完成",
        "不要说自动领取",
        "会员权益必须说成人工审核和储备钱包处理",
        "不要公开私密证据",
        "不要公开本地包",
        "任何本机路径当作官网链接提交",
        "不要碰钱包资产",
        "不需要授权、转账、approve、swap 或改池子",
        "本地 launch 包不是公网证据链接",
        "GCA/USDT",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        'href="basescan-handoff.json"',
        'href="basescan-preflight.json"',
        'href="domain-email-evidence.json"',
        "BaseScan Token Profile 已通过",
        "external audit completed",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_basescan_handoff_page(text: str) -> None:
    label = "/zh-basescan-handoff.html"
    assert_social_preview_meta(text, label, ZH_BASESCAN_HANDOFF_PAGE_URL)
    for expected in (
        "GCA 中文 BaseScan 复审复制包",
        "BaseScan 复审复制包 / Owner Handoff",
        "下一次 BaseScan Token Profile 复审需要复制的英文内容",
        "下面五个块",
        "Reviewer Comment",
        "Basic Information",
        "Evidence Links",
        "Market And Supply",
        "Access And Claim Boundary",
        "support@gcagochina.com",
        "Base Mainnet / 8453",
        "GCA/USDT",
        "不会提交 BaseScan",
        "不会发送邮件",
        "不会写 DNS",
        "不会连接钱包",
        "不会签名",
        "不会转账",
        "不会操作合约",
        "launch/*.md/json",
        "owner 本地复制源",
        "不是 gcagochina.com 的公开链接",
        "打开 BaseScan Token Update",
        "https://basescan.org/tokenupdate/",
        "zh-basescan-submit.html",
        "zh-basescan-preflight.html",
        "zh-basescan-followup.html",
        "提交后跟进",
        "basescan-handoff.html",
        "domain-email-evidence.html",
        "readyForBaseScanResubmission",
        "team.html#tim-chen",
        "tim-chen.html",
        "领取边界",
        "100 credits 是账户服务记录",
        "10,000 GCA 会员权益不是自动领取",
        "本地包边界",
        "只用于本地生成复制文本",
        "不要当成公网 URL 提交给 BaseScan",
        "对外用",
        "brand-kit.html",
        "domain-email.html",
        "domain-email-evidence.html",
        "Copy/Paste Reviewer Comment",
        "Please review the updated GCA token profile metadata",
        "Access and member-benefit boundaries",
        "Public email guard",
        "Official project email: support@gcagochina.com",
        "Access boundary: Public account intake and eligibility submission are live",
        "Not automatic: No automatic token claim",
        "Copy/Paste Basic Information",
        "Project Email Address: support@gcagochina.com",
        "32x32 SVG Logo: https://gcagochina.com/assets/gca-logo.svg",
        "Project Description: GCA is a fixed-supply ERC-20 token deployed on Base Mainnet",
        "Token Symbol: GCA",
        "Decimals: 18",
        "Total Supply: 1000000000",
        "Copy/Paste Evidence Links",
        "GitHub source repository: https://github.com/timchen078/gca_token",
        "Telegram: https://t.me/gcagochinaofficial",
        "X: https://x.com/GCAAIGoChina",
        "Access portal: https://gcagochina.com/access.html",
        "Review queue contract: https://gcagochina.com/review-queue.html",
        "Release gates: https://gcagochina.com/release-gates.html",
        "Member benefit rules: https://gcagochina.com/member-benefit.html",
        "Copy/Paste Market And Supply",
        "Official market route: GCA/USDT",
        "DEX: Uniswap v4",
        OFFICIAL_POOL_ADDRESS,
        OFFICIAL_GECKOTERMINAL_URL,
        OFFICIAL_DEXSCREENER_URL,
        "Target public allocation: 400000000",
        "Owner-held reserve: 600000000",
        RESERVE_WALLET,
        "Reserve boundary: Do not describe the reserve as locked",
        "Copy/Paste Access And Claim Boundary",
        "Access API: https://gcagochina.com/access-api.html",
        "manual reserve-wallet processing",
        "提交后保存记录",
        "BaseScan ticket",
        "不要说已通过",
        "不要使用旧邮箱",
        "不要使用旧池",
        "不要说外部审计完成",
        "不要说自动领取",
        "不要公开后台截图",
        "不要公开本地包",
        "launch/basescan_final_submission_package.md",
        "https://gcagochina.com/launch/...",
        "本机复制来源",
        "不要碰链上资产",
        "BaseScan 资料提交不需要 approve、swap、转账、改池子或任何合约操作",
        "本地 launch 包不是公网证据链接",
        MAINNET_ADDRESS,
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        'href="basescan-handoff.json"',
        'href="basescan-preflight.json"',
        'href="domain-email-evidence.json"',
        "BaseScan Token Profile 已通过",
        OLD_WETH_POOL_ADDRESS,
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_basescan_followup_page(text: str) -> None:
    label = "/zh-basescan-followup.html"
    assert_social_preview_meta(text, label, ZH_BASESCAN_FOLLOWUP_PAGE_URL)
    for expected in (
        "GCA 中文 BaseScan 跟进处理",
        "BaseScan 提交后跟进 / Reviewer Reply Handling",
        "owner 已经提交 BaseScan Token Profile 更新后",
        "support@gcagochina.com",
        "等待官方公开更新",
        MAINNET_ADDRESS,
        "GCA/USDT",
        "不会提交 BaseScan",
        "不会发送邮件",
        "不会上传文件",
        "不会连接钱包",
        "不会签名",
        "不会转账",
        "不会操作合约",
        "收到 BaseScan 邮件后先做三件事",
        "记录 ticket",
        "判断类型",
        "不重复提交",
        "如果 BaseScan 说已经处理",
        "如果仍说信息不足",
        "如果要求私密证据",
        "退回原因怎么处理",
        "官网不可访问或不安全",
        "tools/check_public_site.py --base-url https://gcagochina.com/ --timeout 20",
        "项目说明不清晰",
        "占位内容或坏链接",
        "团队资料不透明",
        "发件邮箱不匹配",
        "市场或供应说明不清",
        "verify.html",
        "support.html",
        "whitepaper.html",
        "brand-kit.html",
        "about.html",
        "utility.html",
        "product.html",
        "roadmap.html",
        "team.html#tim-chen",
        "tim-chen.html",
        "supply.html",
        "reserve-statement.html",
        "holder-distribution.html",
        OFFICIAL_POOL_ADDRESS,
        "可复制英文回复模板",
        "1. 收到退回后的确认回复",
        "We have received your feedback for the GCA token profile request.",
        "We will not open duplicate requests while this ticket is under review.",
        "2. 修复公开资料后的补证据回复",
        "Official project email: support@gcagochina.com",
        "Chinese owner handoff: https://gcagochina.com/zh-basescan-handoff.html",
        "We are not claiming BaseScan token profile approval before publication",
        "3. 对方要求私密邮箱或 DNS 证据时",
        "https://gcagochina.com/domain-email-evidence.html",
        "要保存的记录",
        "不要这样回复",
        "不要说已通过",
        "不要反复开新单",
        "不要夸大安全",
        "不要改回旧资料",
        "不要做链上动作",
        "BaseScan 资料跟进不需要 approve、swap、转账、签交易、改池子或操作合约",
        "zh-basescan-handoff.html",
        "zh-basescan-submit.html",
        "zh-basescan-preflight.html",
        "basescan-handoff.html",
        "platform-replies.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        'href="basescan-handoff.json"',
        'href="basescan-preflight.json"',
        'href="domain-email-evidence.json"',
        "BaseScan Token Profile 已通过",
        OLD_WETH_POOL_ADDRESS,
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_liquidity_page(text: str) -> None:
    label = "/zh-liquidity.html"
    assert_social_preview_meta(text, label, ZH_LIQUIDITY_PAGE_URL)
    for expected in (
        "GCA 中文池子和流动性说明",
        "中文池子和流动性说明",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        BASE_USDT_ADDRESS,
        "USDT 进入池子，GCA 从池子流出",
        "不会自动进入项目方个人钱包",
        "你的钱包里的 GCA 不会因为别人从池子买入而减少",
        "只有你自己签名确认转账、卖出、添加流动性或移除流动性",
        "LP 头寸",
        "用 USDT 不是降低成本",
        "减少价格影响和滑点",
        "LP 锁尚未完成",
        "不能宣传为锁定流动性",
        "不要通过人工制造交易活动、自我成交或误导性宣传来改善市场数据",
        "需要帮助",
        "购买、池子和钱包问题",
        "zh-cn.html",
        "zh-apply.html",
        "zh-support.html",
        "zh-members.html",
        "zh-faq.html",
        "verify.html",
        "buy.html",
        "markets.html",
        "liquidity.html",
        "market-quality.html",
        "holder-distribution.html",
        "support.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        "平台审核资料",
        "平台和审核入口",
        "Platform Replies",
        'href="data.html"',
        "reviewer-kit.html",
        "risk-remediation.html",
        "custody-roadmap.html",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_supply_page(text: str) -> None:
    label = "/zh-supply.html"
    assert_social_preview_meta(text, label, ZH_SUPPLY_PAGE_URL)
    for expected in (
        "GCA 中文总量和储备说明",
        "中文总量和储备说明",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "1,000,000,000 GCA",
        "链上 totalSupply",
        "合约没有后续增发函数",
        "400,000,000 GCA",
        "项目披露口径，不是链上强制限制",
        "600,000,000 GCA",
        "owner-held reserve",
        RESERVE_WALLET,
        RESERVE_TX_1,
        RESERVE_TX_2,
        "链上浏览器显示 10 亿不是错误",
        "平台可能继续按 1,000,000,000 GCA 读取",
        "不是锁仓，不是多签，不是归属合约，也不是销毁地址",
        "不能宣传为技术上不可流通",
        "储备多签、锁仓或归属合约尚未完成",
        "不要通过人工制造交易活动、自我成交或误导性宣传来改善市场数据",
        "供应资料",
        "继续查看总量和储备",
        "zh-cn.html",
        "zh-apply.html",
        "zh-status.html",
        "zh-liquidity.html",
        "zh-faq.html",
        "verify.html",
        "buy.html",
        "supply.html",
        "reserve-statement.html",
        "holder-distribution.html",
        "onchain-proofs.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in ("Platform-Only Evidence Path", "Reviewer Data Room", "平台审核资料", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_security_page(text: str) -> None:
    label = "/zh-security.html"
    assert_social_preview_meta(text, label, ZH_SECURITY_PAGE_URL)
    for expected in (
        "GCA 中文安全和审计说明",
        "中文安全和审计说明",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "BaseScan 源码已验证",
        "固定总量 1,000,000,000 GCA",
        "合约没有后续增发函数",
        "没有 owner/admin 角色",
        "没有代理升级路径",
        "没有黑名单",
        "没有暂停函数",
        "没有转账税或隐藏费用",
        "合约没有托管用户资金或项目方提款路径",
        "第三方审计尚未完成",
        "不能宣传为 Certik、Hacken、Trail of Bits 或其他独立审计方已经审计通过",
        "风险提示消失不等于永久批准",
        "LP 锁尚未完成",
        "不能宣传为锁定流动性",
        "600,000,000 GCA",
        "owner-held reserve",
        "不是锁仓、多签、归属合约或销毁地址",
        "价格影响和滑点可能很敏感",
        "小额买卖测试只能证明功能可用",
        "降低风险标记应靠真实证据",
        "不使用人工交易、误导性宣传或自我成交来改善市场数据",
        "不要说 GCA 已通过第三方审计",
        "不要说 Blockaid、MetaMask 或任何安全厂商永久批准 GCA",
        "不要承诺价格、成交量、流动性、上币、审核通过或永久无风险提示",
        "不要通过人工制造交易活动、自我成交或误导性宣传来改善市场数据",
        "安全资料",
        "继续查看安全说明",
        "zh-cn.html",
        "zh-status.html",
        "zh-liquidity.html",
        "zh-supply.html",
        "zh-faq.html",
        "verify.html",
        "token-safety.html",
        "technical-report.html",
        "blockaid-followup.html",
        "wallet-warning.html",
        "audit-readiness.html",
        "risk-remediation.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in ("Platform-Only Evidence Path", "Reviewer Data Room", "平台审核资料", 'href="data.html"', "reviewer-kit.html"):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_roadmap_page(text: str) -> None:
    label = "/zh-roadmap.html"
    assert_social_preview_meta(text, label, ZH_ROADMAP_PAGE_URL)
    for expected in (
        "GCA 中文路线图",
        "Go China AI Quant Access",
        "非托管量化研究",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "概念阶段产品建设",
        "阶段 0：身份可信",
        "阶段 1：叙事和资料",
        "阶段 2：产品接入",
        "受控 HTTPS 账户 UI",
        "只读钱包余额验证",
        "100 credits 账本",
        "GCA Member 账本",
        "30 天持有期复核",
        "Go China Narrative Radar",
        "Liquidation Replay",
        "Backtesting and Risk Alerts",
        "ENTRY_READY Review",
        "GCA AI Quant Access utility access",
        "10,000 GCA 持有者",
        "100 GCA AI Quant Access credits",
        "1,000,000 GCA 持有者",
        "连续持有 30 天",
        "一次性 10,000 GCA 会员权益审核路径",
        "账户提交入口",
        "已上线：符合条件写入账户级记录",
        "不能说第三方审计已经完成",
        "不能说 BaseScan Token Profile 已经通过",
        "不能承诺价格、成交量、流动性、上所、审核通过或交易结果",
        "继续查看产品路线",
        "zh-cn.html",
        "zh-apply.html",
        "zh-status.html",
        "zh-liquidity.html",
        "zh-supply.html",
        "zh-security.html",
        "zh-members.html",
        "zh-release-gates.html",
        "roadmap.html",
        "product.html",
        "utility.html",
        "release-gates.html",
        "support.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in ("Platform-Only Evidence Path", "Reviewer Data Room", "平台审核资料", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_faq_page(text: str) -> None:
    label = "/zh-faq.html"
    assert_social_preview_meta(text, label, ZH_FAQ_PAGE_URL)
    for expected in (
        "GCA 中文 FAQ",
        "GCA 中文常见问题",
        "中文用户常见问题",
        "中文参与指引",
        "zh-apply.html",
        "中文项目进度",
        "zh-status.html",
        "中文池子和流动性说明",
        "zh-liquidity.html",
        "中文总量和储备说明",
        "zh-supply.html",
        "中文安全和审计说明",
        "zh-security.html",
        "中文会员规则",
        "zh-members.html",
        "Base Mainnet",
        "chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "官方公开路线是 Base Mainnet 上的 GCA/USDT 池",
        "BaseScan 源码和部署钱包验证已完成",
        "support@gcagochina.com、Tim Chen 公开职业资料和最终提交包已准备",
        "BaseScan 公开代币资料仍待官方发布",
        "为什么钱包里看不到 GCA",
        "为什么有些平台显示流通量是 10 亿",
        "别人买了 GCA，我的钱包会收到钱吗",
        "别人买币，我钱包里的 GCA 会变少吗",
        "如果不走池子，怎么结算",
        "现在有没有第三方审计",
        "第三方审计尚未完成",
        "风险提示消失是不是永久安全",
        "会员规则是什么",
        "10,000 GCA",
        "100 GCA AI Quant Access credits",
        "1,000,000 GCA",
        "连续持有 1,000,000 GCA 满 30 天",
        "credits 和 GCA Member 账本记录可以写入",
        "不是投资建议",
        "不要把小额测试交易说成真实市场需求",
        "2026-06-06 最终提交包已准备",
        "不要通过人工制造交易量、自我成交或误导性宣传来改善市场数据",
        "常用官方页面",
        "support@gcagochina.com",
        X_URL,
        "https://t.me/gcagochinaofficial",
        "zh-cn.html",
        "zh-apply.html",
        "zh-status.html",
        "zh-liquidity.html",
        "zh-supply.html",
        "zh-security.html",
        "verify.html",
        "buy.html",
        "markets.html",
        "members.html",
        "zh-members.html",
        "中文会员审核资料清单",
        "zh-member-checklist.html",
        "member-ledger.html",
        "member-benefit.html",
        "zh-wallet-verify.html",
        "zh-release-gates.html",
        "release-gates.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        "平台审核资料",
        'href="data.html"',
        "reviewer-kit.html",
        "platform-replies.html",
        "仍需补域名邮箱后再提交",
        "BaseScan 公开代币资料 2026-05-23 被退回整改",
        "GCAgochina@outlook.com",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_support_page(text: str) -> None:
    label = "/zh-support.html"
    assert_social_preview_meta(text, label, ZH_SUPPORT_PAGE_URL)
    for expected in (
        "GCA 中文支持和资料提交",
        "邮箱注册",
        "register.html",
        "邮箱退订",
        "unsubscribe.html",
        "中文用户中心",
        "zh-access.html",
        "中文上线门槛",
        "zh-release-gates.html",
        "中文只读钱包验证",
        "zh-wallet-verify.html",
        "中文站点地图",
        "zh-site-map.html",
        "官方邮箱",
        "support@gcagochina.com",
        "https://t.me/gcagochinaofficial",
        "https://x.com/GCAAIGoChina",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "私钥",
        "助记词",
        "交易所 API Secret",
        "提现权限",
        "验证码",
        "远程控制权限",
        "承诺价格、收益、成交量、上所、审核通过或永久无风险提示",
        "会员资料支持",
        "优先在会员入口生成审核资料包",
        "钱包地址、购买交易哈希、持有开始日期、只读余额验证结果",
        "生成审核资料包",
        "10,000 GCA / 100 GCA AI Quant Access credits",
        "1,000,000 GCA / 30 天 GCA Member",
        "钱包显示或风险提示",
        "风险提示消失不等于永久批准",
        "资料显示不一致",
        "GCA 可以整理公开资料并提交更正请求",
        "不能保证第三方平台即时处理",
        "购买和池子问题",
        "GCA 官方不能替用户决定买卖、滑点、价格或交易时机",
        "安全或合约问题",
        "第三方审计尚未完成",
        "Certik、Hacken、Trail of Bits",
        "官方公告以官网、X 和 Telegram 官方频道为准",
        "不要相信私信里的替代合约、替代池子、空投领取或手动签名链接",
        "推荐邮件格式",
        "审核资料包",
        "可从会员入口生成并复制",
        "账户提交、审核资料包生成、只读钱包验证、符合条件的 credits / GCA Member 账本记录已经上线",
        "会员资格和权益处理仍需要人工确认",
        "BaseScan Token Profile",
        "BaseScan 最终公开页面",
        "LP 锁尚未完成",
        "支持不会提供买入、卖出、价格或收益建议",
        "支持处理路径",
        "普通用户优先使用官网页面、邮箱、会员入口、审核资料包和只读钱包验证",
        "zh-cn.html",
        "zh-buy.html",
        "zh-apply.html",
        "zh-liquidity.html",
        "zh-supply.html",
        "zh-security.html",
        "zh-roadmap.html",
        "zh-faq.html",
        "zh-members.html",
        "zh-access.html",
        "zh-site-map.html",
        "register.html",
        "unsubscribe.html",
        "support.html",
        "gca/member-access/",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        "平台审核资料",
        "中文数据室说明",
        "Platform Replies",
        "zh-data.html",
        'href="data.html"',
        "zh-member-checklist.html",
        "中文会员审核资料清单",
        "zh-domain-email.html",
        "中文域名邮箱整改",
        "zh-api-status.html",
        "Reviewer Kit",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_api_status_page(text: str) -> None:
    label = "/zh-api-status.html"
    assert_social_preview_meta(text, label, ZH_API_STATUS_PAGE_URL)
    for expected in (
        "GCA 中文 API 状态",
        "中文 API 状态 / 2026-06-07",
        "2026-06-07T13:06:12Z",
        "最新检查",
        "2026-06-07 通过",
        "邮箱注册和邮箱退订接口",
        "Cloudflare Workers + D1",
        "管理员读取接口仍需要本地管理 token",
        "不会激活 100 credits、GCA Member 或 10,000 GCA 会员权益",
        "gca-registration-api.gcagochina.workers.dev",
        "公开检查",
        "只读 / 不需要 secrets",
        "管理员读取",
        "token 保护",
        "当前已上线接口",
        "GET /health",
        "gca-registration-api",
        "POST /gca/email-registrations",
        "gca_email_registration_v1",
        "POST /gca/contact-suppressions",
        "gca_contact_suppression_v1",
        "GET /gca/access-config",
        "POST /gca/wallet-verifications",
        "POST /gca/member-access",
        "GET /gca/email-registrations",
        "没有 token 的公网访问应返回授权错误",
        "GET /gca/contact-suppressions",
        "GET /gca/credit-ledger",
        "GET /gca/member-ledger",
        "api.gcagochina.com",
        "python3 tools/check_gca_registration_api.py --public-only --timeout 30",
        "python3 tools/check_gca_registration_api.py --token-file cloudflare/gca-registration-worker/.env.admin.local --limit 5",
        "邮箱注册不需要钱包地址，不读取钱包余额",
        "邮箱注册不需要私钥、助记词、钱包签名、验证码、付款或交易所 API Secret",
        "会员账户入口可以写入符合条件的 100 credits / GCA Member 账本记录",
        "邮箱退订只影响后续联系导出",
        "tools/export_cloudflare_email_registrations.py",
        "tools/sync_cloudflare_email_registrations.py",
        "tools/export_gca_email_contacts.py",
        "tools/sync_cloudflare_contact_suppressions.py",
        "tools/run_gca_registration_ops.py",
        "中文运营流程",
        "zh-operations.html",
        "中文 API 状态引用",
        "普通用户可以使用当前中文页面",
        "api-status.html",
        "access-api.html",
        "operations.html",
        "privacy.html",
        "terms.html",
        "register.html",
        "unsubscribe.html",
        "zh-support.html",
        "zh-site-map.html",
    ):
        assert_contains(text, expected, label)
    assert_no_public_data_room_terms(text, label)
    for forbidden_href in ("api-status.json", "access-api.json", "operations.json"):
        assert_not_contains(text, f'href="{forbidden_href}"', label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_operations_page(text: str) -> None:
    label = "/zh-operations.html"
    assert_social_preview_meta(text, label, ZH_OPERATIONS_PAGE_URL)
    for expected in (
        "GCA 中文运营流程",
        "中文运营流程 / 2026-06-05",
        "用户在官网提交邮箱和会员账户资料以后",
        "同步 Cloudflare D1 记录",
        "导出联系名单",
        "处理退订",
        "保留本地账本",
        "当前邮箱注册、邮箱退订、账户入口、只读钱包验证、符合条件的 100 credits / GCA Member 账本记录已经上线",
        "Cloudflare Workers + D1 已上线",
        "gca-registration-api.gcagochina.workers.dev",
        "需要本地 ADMIN_READ_TOKEN",
        "符合条件写入 D1 账本记录",
        "用户提交邮箱后的六步流程",
        "公开 API 检查",
        "管理员导出",
        "同步本地账本",
        "同步退订记录",
        "导出联系名单",
        "记录运营汇总",
        "python3 tools/check_gca_registration_api.py --public-only --timeout 30",
        "python3 tools/run_gca_registration_ops.py --limit 100 --data-dir .gca_access_data",
        "会员后台运营流程",
        "tools/run_gca_member_access_ops.py",
        "cloudflare/gca-registration-worker/.env.admin.local",
        ".gca_access_data/cloudflare_member_access_export.json",
        ".gca_access_data/member_access_report/gca_member_access_summary.json",
        ".gca_access_data/member_access_report/gca_member_support_queue.csv",
        ".gca_access_data/member_access_report/gca_holding_period_summary.json",
        ".gca_access_data/gca_member_access_ops_summary.json",
        "--include-holding-report --holding-no-live-read",
        "tools/run_gca_daily_ops.py --build-digest --update-public-status",
        "不会自动转账 GCA",
        "不会请求签名、交易或钱包授权",
        ".gca_access_data/cloudflare_email_registrations_export.json",
        ".gca_access_data/email_registrations.jsonl",
        ".gca_access_data/gca_contact_suppressions.jsonl",
        ".gca_access_data/gca_email_contacts.csv",
        ".gca_access_data/gca_email_contacts_public_redacted.csv",
        ".gca_access_data/gca_registration_ops_summary.json",
        "只联系同意接收 GCA 更新的邮箱",
        "退订邮箱必须从后续联系导出中排除",
        "只能分享 public-redacted CSV 或统计摘要",
        "不进网页、不进 Git、不发给第三方",
        "不能自动激活 credits 或 GCA Member",
        "安全边界",
        "私钥",
        "助记词",
        "交易所 API Secret",
        "提现权限",
        "远程控制",
        "不能把完整用户邮箱、管理员 token、完整 D1 导出文件或本地账本发给外部平台",
        "不能用运营导出绕过钱包余额验证",
        "不能把本地运营汇总、public-redacted CSV 或人工审核记录说成第三方审计或平台批准",
        "和会员审核怎么连接",
        "只读 GCA 余额验证",
        "30 天持有资料",
        "支持审核队列",
        "运营支持入口",
        "继续处理用户流程",
        "zh-api-status.html",
        "zh-access.html",
        "zh-release-gates.html",
        "zh-support.html",
        "operations.html",
        "operator.html",
        "review-queue.html",
        "privacy.html",
        "terms.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in ("Platform-Only Evidence Path", "Reviewer Data Room", "平台审核资料", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_access_page(text: str) -> None:
    label = "/zh-access.html"
    assert_social_preview_meta(text, label, ZH_ACCESS_PAGE_URL)
    for expected in (
        "GCA 中文用户中心",
        "中文用户中心",
        "邮箱注册 API、受控 HTTPS 账户 UI、只读钱包余额验证",
        "中英双语会员入口",
        "可复制的会员审核资料包",
        "support@gcagochina.com",
        "Cloudflare Workers + D1 已上线",
        "受控 HTTPS 账户 UI 已上线",
        "公开账户提交",
        "100 credits 公开账本记录",
        "GCA Member 公开账本记录",
        "10,000 GCA 会员权益转账",
        "人工审核和储备钱包处理",
        "Base Mainnet chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "会员账户入口",
        "邮箱注册",
        "register.html",
        "邮箱退订",
        "unsubscribe.html",
        "中文 API 状态",
        "zh-api-status.html",
        "中文运营流程",
        "zh-operations.html",
        "中文会员规则",
        "zh-members.html",
        "后续增强",
        "用户中心继续建设方向",
        "运营处理事项",
        "zh-release-gates.html",
        "中文只读钱包验证",
        "zh-wallet-verify.html",
        "中文会员审核资料清单",
        "zh-member-checklist.html",
        "中文会员权益转账流程",
        "zh-member-benefit-transfer.html",
        "审核资料包",
        "生成会员审核资料包",
        "中文支持和资料提交",
        "zh-support.html",
        "只读余额验证",
        "10,000 GCA",
        "100 GCA AI Quant Access credits",
        "1,000,000 GCA",
        "30 天持有审核",
        "10,000 GCA 会员权益审核",
        "owner-held reserve",
        "不是新铸币",
        "私钥",
        "助记词",
        "钱包密码",
        "验证码",
        "交易所 API Secret",
        "提现权限",
        "不会自动激活 100 credits、GCA Member 或 10,000 GCA 会员权益",
        "未来交易相关功能必须先经过风控、模拟盘或测试环境",
        "用户资料入口",
        "继续查看账户资料",
        "access.html",
        "access-api.html",
        "operations.html",
        "review-queue.html",
        "credits.html",
        "member-ledger.html",
        "zh-release-gates.html",
        "release-gates.html",
        "gca/member-access/",
    ):
        assert_contains(text, expected, label)
    for forbidden in ("Platform-Only Evidence Path", "Reviewer Data Room", "平台审核资料", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_release_gates_page(text: str) -> None:
    label = "/zh-release-gates.html"
    assert_social_preview_meta(text, label, ZH_RELEASE_GATES_PAGE_URL)
    for expected in (
        "GCA 中文上线门槛",
        "中文上线门槛 / 2026-06-05",
        "邮箱注册 API 已上线",
        "Cloudflare Workers + D1 已上线",
        "受控 HTTPS 账户 UI",
        "只读钱包余额验证",
        "eth_call",
        "balanceOf",
        "100 credits",
        "GCA Member",
        "10,000 GCA 会员权益",
        "符合条件写入账本，会员权益仍需人工审核",
        "BaseScan 证据包",
        "Final package 2026-06-06T11:10:54Z",
        "daily status 2026-06-07T13:06:12Z",
        "不发起交易或签名",
        "支持审核队列",
        "风控",
        "模拟盘或测试环境",
        "私钥",
        "助记词",
        "钱包密码",
        "验证码",
        "交易所 API Secret",
        "提现权限",
        "上线资料",
        "继续查看上线门槛",
        "register.html",
        "zh-api-status.html",
        "中文运营流程",
        "zh-operations.html",
        "zh-access.html",
        "zh-members.html",
        "zh-support.html",
        "zh-wallet-verify.html",
        "中文会员审核资料清单",
        "zh-member-checklist.html",
        "zh-basescan-submit.html",
        "basescan-handoff.html",
        "daily-status.html",
        "zh-roadmap.html",
        "zh-status.html",
        "privacy.html",
        "terms.html",
        "release-gates.html",
        "access.html",
        "access-api.html",
        "operations.html",
        "review-queue.html",
        "credits.html",
        "member-ledger.html",
        "zh-wallet-verify.html",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
    ):
        assert_contains(text, expected, label)
    assert_not_contains(text, "不能说已经上线完整余额验证 UI", label)
    assert_not_contains(text, "只能说计划使用", label)
    for forbidden in ("Platform-Only Evidence Path", "Reviewer Data Room", "平台审核资料", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_wallet_verify_page(text: str) -> None:
    label = "/zh-wallet-verify.html"
    assert_social_preview_meta(text, label, ZH_WALLET_VERIFY_PAGE_URL)
    for expected in (
        "GCA 中文只读钱包验证",
        "只读钱包验证 / 2026-05-20",
        "公开账户入口、只读钱包验证和符合条件的 100 credits / GCA Member 账本写入已经上线",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "eth_call",
        "balanceOf",
        "只读",
        "不要求签名",
        "不发起交易",
        "不授权转移资产",
        "approve",
        "私钥",
        "助记词",
        "钱包密码",
        "验证码",
        "交易所 API Secret",
        "提现权限",
        "购买交易哈希",
        "持有开始日期",
        "10,000 GCA",
        "100 GCA AI Quant Access credits",
        "1,000,000 GCA",
        "连续持有 30 天",
        "GCA Member",
        "10,000 GCA 会员权益",
        "Cloudflare Workers + D1 已上线",
        "MetaMask",
        "gca/member-access/",
        "zh-cn.html",
        "zh-access.html",
        "zh-members.html",
        "中文会员审核资料清单",
        "zh-member-checklist.html",
        "中文会员权益转账流程",
        "zh-member-benefit-transfer.html",
        "zh-release-gates.html",
        "zh-api-status.html",
        "zh-support.html",
        "zh-buy.html",
        "zh-faq.html",
        "register.html",
        "access.html",
        "access-api.html",
        "review-queue.html",
        "operations.html",
        "member-ledger.html",
        "release-gates.html",
        "钱包验证入口",
        "继续完成账户资料",
    ):
        assert_contains(text, expected, label)
    for forbidden in ("Platform-Only Evidence Path", "Reviewer Data Room", "平台审核资料", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_member_checklist_page(text: str) -> None:
    label = "/zh-member-checklist.html"
    assert_social_preview_meta(text, label, ZH_MEMBER_CHECKLIST_PAGE_URL)
    for expected in (
        "GCA 中文会员审核资料清单",
        "会员审核资料清单 / 2026-05-20",
        "公开账户入口、只读钱包验证、100 credits 账本和 GCA Member 账本已经上线",
        "会员入口现在可以生成可复制的审核资料包",
        "support@gcagochina.com",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "eth_call",
        "balanceOf",
        "10,000 GCA / 100 credits 审核",
        "100 GCA AI Quant Access credits",
        "1,000,000 GCA / 30 天 GCA Member 审核",
        "连续持有至少 1,000,000 GCA 满 30 天",
        "10,000 GCA 会员权益审核",
        "不是新铸币",
        "受控 HTTPS 账户 UI",
        "100 credits 账本",
        "GCA Member 账本",
        "私钥",
        "助记词",
        "钱包密码",
        "验证码",
        "交易所 API Secret",
        "提现权限",
        "远程控制",
        "keystore",
        "钱包地址",
        "购买交易哈希",
        "持有开始日期",
        "只读余额验证结果",
        "审核资料包",
        "会员账户入口生成",
        "生成资料包",
        "register.html",
        "zh-members.html",
        "zh-wallet-verify.html",
        "zh-release-gates.html",
        "zh-support.html",
        "zh-access.html",
        "zh-api-status.html",
        "zh-site-map.html",
        "members.html",
        "gca/member-access/",
        "member-ledger.html",
        "member-benefit.html",
        "member-benefit-transfer.html",
        "review-queue.html",
        "普通用户审核路径",
        "优先打开这些页面",
        "会员入口和资料包",
        "会员资料、审核资料包、钱包验证、支持沟通和审核状态都应从可读页面进入",
        "中文站点地图",
        "中文支持",
    ):
        assert_contains(text, expected, label)
    assert_no_public_data_room_terms(text, label)
    for forbidden_href in (
        "member-program.json",
        "member-ledger.json",
        "member-benefit.json",
        "member-benefit-transfer.json",
        "review-queue.json",
    ):
        assert_not_contains(text, f'href="{forbidden_href}"', label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_member_benefit_transfer_page(text: str) -> None:
    label = "/zh-member-benefit-transfer.html"
    assert_social_preview_meta(text, label, ZH_MEMBER_BENEFIT_TRANSFER_PAGE_URL)
    for expected in (
        "GCA 中文会员权益转账流程",
        "中文会员权益转账流程 / 2026-06-05",
        "1,000,000 GCA 连续持有 30 天",
        "10,000 GCA 会员权益",
        "人工审核和手动转账",
        "不是自动领取页面",
        "不是新铸币",
        "GCA 合约没有后续增发函数",
        "owner-held reserve",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        RESERVE_WALLET,
        "memberBenefitTransferTx",
        "gca_member_preregistration_v2",
        "memberBenefitReviewEvidenceStatus",
        "evidenceTxHashFormatOk",
        "只读",
        "balanceOf",
        "连续持有至少 30 天",
        "只读 balanceOf 复核至少 1,000,000 GCA",
        "人工处理六步",
        "确认审核记录",
        "复核当前余额",
        "准备储备钱包",
        "手动发送 10,000 GCA",
        "记录公开交易哈希",
        "关闭审核记录",
        "私钥",
        "助记词",
        "交易所 API Secret",
        "提现权限",
        "验证码",
        "远程控制权限",
        "托管资金",
        "额外担保费",
        "不能说：持有 1,000,000 GCA 会自动触发转账",
        "不能说：10,000 GCA 会员权益今天可以自助领取",
        "不会自动转账",
        "不会托管资金",
        "不会要求用户签名授权",
        "zh-access.html",
        "zh-members.html",
        "zh-member-checklist.html",
        "zh-member-benefit-transfer.html",
        "zh-wallet-verify.html",
        "zh-operations.html",
        "zh-release-gates.html",
        "zh-support.html",
        "member-benefit-transfer.html",
        "gca/member-access/",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        "平台审核资料",
        'href="data.html"',
        'href="member-benefit-transfer.json"',
        "GCA/WETH",
        OLD_WETH_POOL_ADDRESS,
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_data_page(text: str) -> None:
    label = "/zh-data.html"
    assert_social_preview_meta(text, label, ZH_DATA_PAGE_URL)
    assert_platform_only_data_room(
        text,
        label,
        (
            "project.json",
            "tokenlist.json",
            "member-program.json",
            "member-ledger.json",
            "member-benefit.json",
            "member-benefit-transfer.json",
            "review-queue.json",
            "support.json",
            "access-api.json",
            "api-status.json",
            "technical-report.json",
            "reserve-statement.json",
        ),
    )
    for expected in (
        "GCA 中文数据室说明",
        "中文数据室说明 / 2026-05-20",
        "JSON 文件不是坏页面",
        "不是领取入口",
        "看起来像代码是正常的",
        "Raw JSON",
        "machine-readable files",
        "普通用户优先 HTML / 平台审核才用 JSON",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "不会发币",
        "不会创建账户",
        "不会激活 100 credits",
        "不会激活 GCA Member",
        "不会发放 10,000 GCA 会员权益",
        "私钥",
        "助记词",
        "keystore",
        "钱包密码",
        "验证码",
        "交易所 API Secret",
        "提现权限",
        "远程控制权限",
        "不会要求 approve",
        "不会要求",
        "中文站点地图",
        "zh-site-map.html",
        "Open Page",
        "data.html",
        "project.json",
        "tokenlist.json",
        "member-program.json",
        "member-ledger.json",
        "member-benefit.json",
        "member-benefit-transfer.json",
        "review-queue.json",
        "support.json",
        "access-api.json",
        "api-status.json",
        "technical-report.json",
        "reserve-statement.json",
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        "zh-cn.html",
        "zh-buy.html",
        "zh-apply.html",
        "zh-members.html",
        "zh-member-checklist.html",
        "zh-member-benefit-transfer.html",
        "zh-wallet-verify.html",
        "zh-access.html",
        "zh-release-gates.html",
        "zh-basescan-preflight.html",
        "zh-basescan-handoff.html",
        "中文 BaseScan 复审复制包",
        "zh-basescan-followup.html",
        "中文 BaseScan 跟进处理",
        "basescan-handoff.html",
        "zh-api-status.html",
        "zh-operations.html",
        "zh-support.html",
        "register.html",
        "zh-site-map.html",
        "site-map.html",
        "如果你想判断 BaseScan 现在能不能重提",
        "如果你要手动复制 BaseScan 复审材料",
        "如果你已经收到 BaseScan 邮件回复",
        "verify.html",
        "about.html",
        "status.html",
        "members.html",
        "member-ledger.html",
        "member-benefit.html",
        "member-benefit-transfer.html",
        "release-gates.html",
        "support.html",
        "reviewer-kit.html",
        "basescan-handoff.html",
        "platform-replies.html",
        "trust.html",
        "technical-report.html",
        "reserve-statement.html",
    ):
        assert_contains(text, expected, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_site_map_page(text: str) -> None:
    label = "/zh-site-map.html"
    assert_social_preview_meta(text, label, ZH_SITE_MAP_PAGE_URL)
    for expected in (
        "GCA 中文站点地图",
        "中文站点地图 / 2026-05-20",
        "Start Here / 用户入口",
        "start.html",
        "中文用户优先使用可读 HTML 页面",
        "如果你打开了无法阅读的原始资料页面",
        "Base Mainnet / chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "普通用户路径",
        "验证和购买",
        "参与和状态",
        "注册和支持",
        "会员和用户中心",
        "GCA Member / 100 credits / 钱包验证",
        "中文会员资料",
        "英文可读技术页",
        "产品和接口规划",
        "信任资料",
        "给用户和平台看的可读页面",
        "资料说明",
        "普通分享优先使用可读页面",
        "安全和审计状态",
        "第三方审计尚未完成",
        "链上和市场资料",
        "社群和公开内容",
        "项目更新、社群和内容发布",
        "官方渠道",
        "内容和发布",
        "完整英文索引",
        "安全边界",
        "私钥",
        "助记词",
        "keystore",
        "钱包密码",
        "验证码",
        "交易所 API Secret",
        "提现权限",
        "远程控制权限",
        "普通用户使用可读页面和官方支持",
        "不需要打开原始数据文件",
        "需要更多资料",
        "先打开可读资料页",
        "zh-cn.html",
        "zh-buy.html",
        "zh-apply.html",
        "zh-status.html",
        "zh-liquidity.html",
        "zh-supply.html",
        "zh-security.html",
        "zh-roadmap.html",
        "zh-faq.html",
        "zh-members.html",
        "zh-member-checklist.html",
        "zh-wallet-verify.html",
        "zh-access.html",
        "zh-release-gates.html",
        "zh-basescan-preflight.html",
        "zh-basescan-submit.html",
        "中文 BaseScan 提交流程",
        "zh-basescan-handoff.html",
        "中文 BaseScan 复审复制包",
        "zh-basescan-followup.html",
        "中文 BaseScan 跟进处理",
        "BaseScan Handoff",
        "basescan-handoff.html",
        "zh-api-status.html",
        "zh-operations.html",
        "zh-support.html",
        "register.html",
        "unsubscribe.html",
        "verify.html",
        "markets.html",
        "status.html",
        "action-plan.html",
        "members.html",
        "gca/member-access/",
        "credits.html",
        "member-ledger.html",
        "member-benefit.html",
        "member-benefit-transfer.html",
        "release-gates.html",
        "product.html",
        "utility.html",
        "access.html",
        "access-api.html",
        "operations.html",
        "review-queue.html",
        "operator.html",
        "basescan-handoff.html",
        "listing-kit.html",
        "security.html",
        "token-safety.html",
        "technical-report.html",
        "audit-readiness.html",
        "wallet-warning.html",
        "blockaid-followup.html",
        "trust.html",
        "onchain-proofs.html",
        "supply.html",
        "reserve-statement.html",
        "holder-distribution.html",
        "liquidity.html",
        "market-quality.html",
        "risk-remediation.html",
        "custody-roadmap.html",
        "community.html",
        "announcements.html",
        "campaign.html",
        "content-library.html",
        "publishing-desk.html",
        "narrative.html",
        "radar.html",
        "radar-issue-004.html",
        "member-access-brief-001.html",
        "site-map.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "Reviewer Data Room",
        "Platform-Only Evidence Path",
        "平台审核资料",
        "Raw JSON",
        "中文数据室",
        'href="data.html"',
        "zh-data.html",
        "reviewer-kit.html",
        "platform-replies.html",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_zh_members_page(text: str) -> None:
    label = "/zh-members.html"
    assert_social_preview_meta(text, label, ZH_MEMBERS_PAGE_URL)
    for expected in (
        "GCA 中文会员规则",
        "中文会员规则",
        "中文参与指引",
        "zh-apply.html",
        "中文项目进度",
        "zh-status.html",
        "中文池子和流动性说明",
        "zh-liquidity.html",
        "中文总量和储备说明",
        "zh-supply.html",
        "中文安全和审计说明",
        "zh-security.html",
        "Base Mainnet",
        "chainId 8453",
        MAINNET_ADDRESS,
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "账户提交和账本记录已上线",
        "10,000 GCA 持有者",
        "100 GCA AI Quant Access credits",
        "1,000,000 GCA 连续持有 30 天",
        "GCA Member",
        "10,000 GCA 会员权益审核",
        "会员账户入口",
        "只读验证余额",
        "写入符合条件的 100 credits / GCA Member 账本记录",
        "不能自动发放 10,000 GCA 会员权益",
        "账户提交",
        "账本记录",
        "受控 HTTPS 账户 UI",
        "已上线",
        "人工审核和储备钱包处理",
        "账户和账本进度",
        "会员功能状态",
        "支持跟进",
        "通过中文支持页提交公开交易哈希、持有开始日期和只读余额验证结果",
        "会员入口",
        "提交和跟进会员资料",
        "verify.html",
        "buy.html",
        "zh-apply.html",
        "zh-status.html",
        "zh-liquidity.html",
        "zh-supply.html",
        "zh-security.html",
        "members.html",
        "member-ledger.html",
        "member-benefit.html",
        "credits.html",
        "zh-wallet-verify.html",
        "中文会员审核资料清单",
        "zh-member-checklist.html",
        "中文会员权益转账流程",
        "zh-member-benefit-transfer.html",
        "zh-release-gates.html",
        "release-gates.html",
        "support.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "重要边界",
        "请这样对外描述",
        "Platform-Only Evidence Path",
        "Reviewer Data Room",
        'href="data.html"',
        "reviewer-kit.html",
        "platform-replies.html",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_data_page(text: str) -> None:
    label = "/data.html"
    assert_social_preview_meta(text, label, DATA_PAGE_URL)
    for expected in (
        "GCA Data Room",
        "JSON files are not broken pages",
        "machine-readable data files",
        "Regular visitors should use the HTML pages",
        "Human Site Map",
        "site-map.html",
        "中文站点地图",
        "zh-site-map.html",
        "中文数据室说明",
        "zh-data.html",
        "Human Listing Kit",
        "Choose the Right Link",
        "Platform-only structured metadata",
        "Open only when BaseScan, wallets, explorers, DEX tools, or security vendors ask for raw JSON",
        "Open Page",
        "Raw JSON for platforms only",
        "It can look like code in a browser",
        "Core Metadata",
        "Review Evidence",
        "Market and Supply",
        "Product and Member Program",
        "Operations, Policy, and Content",
        "Project data",
        "Token list",
        "Reviewer kit data",
        "Platform replies data",
        "Wallet security profile",
        "External reviews data",
        "Domain email setup data",
        "Domain email evidence checklist data",
        "BaseScan preflight data",
        "BaseScan handoff data",
        "Token safety data",
        "On-chain proofs data",
        "Liquidity statement data",
        "Market quality data",
        "Member ledger data",
        "Member benefit transfer data",
        "Member access brief data",
        "Operations runbook data",
        "Chinese operations guide",
        "Access API contract data",
        "API status data",
        "Daily status snapshot data",
        "Review queue data",
        "Release gates data",
        "Privacy notice data",
        "Participation terms data",
        "Roadmap data",
        "Narrative system data",
        "Weekly radar data",
        "Issue 004 data",
        "Publishing desk data",
        "Announcements data",
        "Content library data",
        MAINNET_ADDRESS,
        "Base Mainnet / chainId 8453",
        "project.json",
        "tokenlist.json",
        "reviewer-kit.json",
        "platform-replies.json",
        "external-reviews.json",
        "domain-email.json",
        "domain-email-evidence.json",
        "basescan-preflight.json",
        "basescan-handoff.json",
        "token-safety.json",
        "onchain-proofs.json",
        "liquidity.json",
        "market-quality.json",
        "member-ledger.json",
        "member-benefit-transfer.json",
        "member-access-brief-001.json",
        "operations.json",
        "zh-operations.html",
        "access-api.json",
        "api-status.json",
        "daily-status.json",
        "review-queue.json",
        "release-gates.json",
        "privacy.json",
        "terms.json",
        "roadmap.json",
        "narrative.json",
        "radar.json",
        "radar-issue-004.json",
        "publishing-desk.json",
    ):
        assert_contains(text, expected, label)
    assert_no_forbidden_public_claims(text, label)


def validate_site_map_page(text: str) -> None:
    label = "/site-map.html"
    assert_social_preview_meta(text, label, SITE_MAP_PAGE_URL)
    for expected in (
        "GCA Site Map",
        "Human-Readable Index",
        "Start Here",
        "start.html",
        "Normal visitors should open HTML pages first",
        "Use Readable Evidence Pages First",
        "Verify GCA",
        "Buy Guide",
        "About GCA",
        "中文入口",
        "zh-cn.html",
        "中文购买说明",
        "zh-buy.html",
        "中文参与指引",
        "zh-apply.html",
        "中文项目进度",
        "zh-status.html",
        "中文池子和流动性说明",
        "zh-liquidity.html",
        "中文总量和储备说明",
        "zh-supply.html",
        "中文安全和审计说明",
        "zh-security.html",
        "中文路线图",
        "zh-roadmap.html",
        "中文 FAQ",
        "zh-faq.html",
        "中文会员规则",
        "zh-members.html",
        "中文用户中心",
        "zh-access.html",
        "中文只读钱包验证",
        "zh-wallet-verify.html",
        "中文会员审核资料清单",
        "zh-member-checklist.html",
        "中文会员权益转账流程",
        "zh-member-benefit-transfer.html",
        "中文站点地图",
        "zh-site-map.html",
        "中文只读钱包验证",
        "zh-wallet-verify.html",
        "中文 API 状态",
        "zh-api-status.html",
        "中文运营流程",
        "zh-operations.html",
        "中文支持和资料提交",
        "zh-support.html",
        "邮箱注册",
        "register.html",
        "邮箱退订",
        "unsubscribe.html",
        "Member Access",
        "Trust Center",
        "Core User Path",
        "Verify and Buy",
        "Status and Help",
        "Official Docs",
        "Product and Members",
        "Product Map",
        "Member Program",
        "Operations",
        "API Status",
        "api-status.html",
        "Daily Status",
        "daily-status.html",
        "Trust and Review",
        "Domain Email Plan",
        "domain-email.html",
        "Domain Email Evidence Checklist",
        "domain-email-evidence.html",
        "BaseScan Preflight",
        "basescan-preflight.html",
        "BaseScan Handoff",
        "basescan-handoff.html",
        "zh-basescan-submit.html",
        "中文 BaseScan 提交流程",
        "zh-basescan-handoff.html",
        "中文 BaseScan 复审复制包",
        "Security Materials",
        "External Review",
        "Supply and Custody",
        "Content and Community",
        "Community Channels",
        "Campaign Desk",
        "Radar Issues",
        "Need Evidence",
        "Trust Center",
        MAINNET_ADDRESS,
        "Base Mainnet",
        "8453",
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "zh-site-map.html",
        "about.html",
        "support.html",
        "brand-kit.html",
        "onchain-proofs.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in ("Reviewer Data Room", "Platform-Only Evidence Path", 'href="data.html"', "zh-data.html"):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_404_page(text: str) -> None:
    label = "/404.html"
    assert_social_preview_meta(text, label, ERROR_PAGE_URL)
    for expected in (
        "Page Not Found",
        "This GCA page was not found.",
        "official human-readable pages",
        "Open Site Map",
        "中文站点地图",
        "Verify GCA",
        "Buy Guide",
        "Support",
        "For Users",
        "For Members",
        "For Project Evidence",
        "Trust Center",
        "On-chain Proofs",
        "Listing Kit",
        "Brand Kit",
        "Current Boundaries",
        "BaseScan source verification is complete",
        "GeckoTerminal token information was approved",
        "no third-party audit has been completed",
        MAINNET_ADDRESS,
        "Base Mainnet",
        "8453",
        "GCA/USDT",
        OFFICIAL_POOL_ADDRESS,
        "site-map.html",
        "verify.html",
        "buy.html",
        "support.html",
        "zh-site-map.html",
        "zh-support.html",
    ):
        assert_contains(text, expected, label)
    for forbidden in (
        "Reviewer Data Room",
        "Platform-Only Evidence Path",
        "Raw JSON",
        "Data Room",
        "中文数据室",
        'href="data.html"',
        "zh-data.html",
        "raw machine-readable",
    ):
        assert_not_contains(text, forbidden, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_listing_kit_page(text: str) -> None:
    label = "/listing-kit.html"
    assert_social_preview_meta(text, label, LISTING_KIT_PAGE_URL)
    assert_contains(text, "GCA Listing Kit", label)
    assert_contains(text, "Public URLs", label)
    assert_no_public_data_room_terms(text, label)
    for forbidden_href in (
        "data.html",
        "project.json",
        "product.json",
        "access.json",
        "operations.json",
        "access-api.json",
        "review-queue.json",
        "credits.json",
        "release-gates.json",
        "roadmap.json",
        "community.json",
        "brand-kit.json",
        "member-ledger.json",
        "member-benefit-transfer.json",
        "support.json",
        "privacy.json",
        "terms.json",
        "listing-readiness.json",
        "onchain-proofs.json",
        "wallet-warning.json",
        "external-reviews.json",
        "reviewer-kit.json",
        "platform-replies.json",
        "trust.json",
        "tokenlist.json",
        "supply.json",
        "member-program.json",
        ".well-known/gca-token.json",
    ):
        assert_not_contains(text, f'href="{forbidden_href}"', label)
    assert_contains(text, "Normal visitor path", label)
    assert_contains(text, "Readable Review Path", label)
    assert_contains(text, "Automated metadata files remain available", label)
    assert_contains(text, "Descriptions", label)
    assert_contains(text, "Official GCA/USDT route", label)
    assert_contains(text, "BaseScan", label)
    assert_contains(text, "returned again as information-insufficient on 2026-05-23", label)
    assert_contains(text, "The project-domain email is now ready; submit one clean update", label)
    assert_contains(text, "domain-email.html", label)
    assert_contains(text, "domain-email-evidence.html", label)
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
    assert_contains(text, "Security References", label)
    assert_no_public_data_room_terms(text, label)
    for forbidden in ("token-safety.json", "technical-report.json", "audit-readiness.json", "risk-remediation.json"):
        assert_not_contains(text, f'href="{forbidden}"', label)
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
    assert_contains(text, "The account UI, read-only GCA balance verification, credit ledger activation, and member ledger activation are live through Workers + D1", label)
    assert_contains(text, "not as a yield product", label)
    assert_contains(text, "not automatic and not newly minted", label)
    assert_contains(text, "This is not a substitute for a third-party audit", label)
    assert_contains(text, "no third-party audit has been completed", label)
    assert_contains(text, "returned again as information-insufficient on 2026-05-23", label)
    assert_contains(text, "domain-email.html#snapshotTitle", label)
    assert_contains(text, "public evidence checklist", label)
    assert_contains(text, "domain-email-evidence.html", label)
    assert_contains_any(text, ("2026-05-25 DNS snapshot", "2026-05-30 DNS snapshot"), label, "DNS snapshot")
    assert_contains(text, "MX/SPF/DKIM/DMARC present", label)
    assert_contains(text, "readyForBaseScanEmailEvidence", label)
    assert_contains(text, "support@gcagochina.com", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_current_pool_text(text, label)


def validate_token_safety_page(text: str) -> None:
    label = "/token-safety.html"
    assert_contains(text, "GCA Token Safety Checklist", label)
    assert_contains(text, "Platform Metadata", label)
    assert_contains(text, "Token Safety References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Verified Positive Controls", label)
    assert_contains(text, "Pending Or Not Claimed", label)
    assert_contains(text, "Returned 2026-05-23; final package refreshed 2026-06-06; Handoff and Chinese owner flow ready for one support@gcagochina.com submission", label)
    assert_contains(text, "Latest reviewer package", label)
    assert_contains(text, "Final package 2026-06-06T11:10:54Z; daily status 2026-06-07T13:06:12Z", label)
    assert_contains(text, "No mint function", label)
    assert_contains(text, "No third-party audit", label)
    assert_contains(text, "permanent warning-free status", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_current_pool_text(text, label)
    for forbidden in (
        'href="token-safety.json"',
        'href=".well-known/wallet-security.json"',
        'href=".well-known/gca-token.json"',
        'href="project.json"',
        'href="reviewer-kit.json"',
    ):
        assert_not_contains(text, forbidden, label)


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
    if pending.get("baseScanTokenProfile") != "ready-for-owner-resubmission":
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
    if links.get("riskRemediationPage") != RISK_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediationPage")
    if links.get("riskRemediation") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediation")
    if links.get("custodyRoadmapPage") != CUSTODY_ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmapPage")
    if links.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap")
    if links.get("auditReadinessPage") != AUDIT_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong auditReadinessPage")
    if links.get("auditReadiness") != AUDIT_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong auditReadiness")
    if links.get("liquidityPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityPage")
    if links.get("liquidity") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidity")
    if links.get("technicalReport") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technicalReport")
    if links.get("auditReadinessPage") != AUDIT_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong auditReadinessPage")
    if links.get("auditReadiness") != AUDIT_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong auditReadiness")
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
    assert_contains(text, "Readable Security Review Path", label)
    assert_contains(text, "Risk Factor Response", label)
    assert_contains(text, "Price Volatility", label)
    assert_contains(text, "LP Lock", label)
    assert_contains(text, "Supply Concentration", label)
    assert_contains(text, "Third-party Audit", label)
    assert_contains(text, "No LP lock is currently claimed", label)
    assert_contains(text, "No third-party audit has been completed", label)
    assert_contains(text, "Technical Report", label)
    assert_contains(text, "Audit Readiness", label)
    assert_contains(text, "Reserve Statement", label)
    assert_contains(text, "Risk Remediation", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, OFFICIAL_POOL_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)
    assert_no_public_data_room_terms(text, label)
    for forbidden in (
        'href="blockaid-followup.json"',
        'href="technical-report.json"',
        'href="reserve-statement.json"',
        'href="liquidity.json"',
        'href="holder-distribution.json"',
        'href="risk-remediation.json"',
        'href="wallet-warning.json"',
    ):
        assert_not_contains(text, forbidden, label)


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
    if responses.get("lpLock", {}).get("publicReference") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong LP lock publicReference")
    if responses.get("supplyConcentration", {}).get("reserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong reserve wallet")
    if responses.get("supplyConcentration", {}).get("publicReference") != HOLDER_DISTRIBUTION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong supply concentration publicReference")
    if responses.get("thirdPartyAudit", {}).get("status") != "not-completed":
        raise SiteCheckError(f"{label}: wrong audit response")
    if responses.get("thirdPartyAudit", {}).get("auditReadiness") != AUDIT_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong audit readiness reference")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong pool")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quote asset")
    if market.get("liquidityStatementPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityStatementPage")
    if market.get("liquidityStatement") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidityStatement")
    if market.get("lpLockClaimed") is not False:
        raise SiteCheckError(f"{label}: LP lock must not be claimed")
    if links.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup")
    if links.get("technicalReport") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technicalReport")
    if links.get("auditReadinessPage") != AUDIT_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong auditReadinessPage")
    if links.get("auditReadiness") != AUDIT_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong auditReadiness")
    if links.get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatement")
    if links.get("holderDistribution") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistribution")
    if links.get("riskRemediation") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediation")
    if links.get("liquidityPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityPage")
    if links.get("liquidity") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidity")
    if links.get("liquidityPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityPage")
    if links.get("liquidity") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidity")
    if "GCA has published an internal technical report and reserve address statement for reviewer triage." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing triage safe claim")
    if "LP lock before a verifiable lock exists" not in payload.get("publicClaimBoundaries", {}).get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing LP lock boundary")
    assert_current_pool_text(json.dumps(payload), label)
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_technical_report_page(text: str) -> None:
    label = "/technical-report.html"
    assert_contains(text, "GCA Technical Report", label)
    assert_contains(text, "Technical Report References", label)
    assert_no_public_data_room_terms(text, label)
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
    for forbidden in (
        'href="technical-report.json"',
        'href="token-safety.json"',
        'href="reserve-statement.json"',
        'href="onchain-proofs.json"',
        'href=".well-known/wallet-security.json"',
    ):
        assert_not_contains(text, forbidden, label)


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
    assert_contains(text, "Reserve References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Owner-controlled, not locked", label)
    assert_contains(text, "Custody Boundary", label)
    assert_contains(text, "On-chain Reserve Transfer Proofs", label)
    assert_contains(text, "LP lock claimed", label)
    assert_contains(text, "No LP lock is currently claimed", label)
    assert_contains(text, "Custody Roadmap", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_contains(text, RESERVE_TX_1, label)
    assert_contains(text, RESERVE_TX_2, label)
    assert_no_forbidden_public_claims(text, label)
    for forbidden in (
        'href="reserve-statement.json"',
        'href="holder-distribution.json"',
        'href="custody-roadmap.json"',
        'href="supply.json"',
        'href="onchain-proofs.json"',
    ):
        assert_not_contains(text, forbidden, label)


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
    if links.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap link")
    if links.get("holderDistribution") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistribution link")
    if "No LP lock is currently claimed." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing LP lock safe claim")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_members(text: str) -> None:
    label = "/members.html"
    assert_contains(text, "GCA Member Access", label)
    assert_contains(text, "Open Live Member Access", label)
    assert_contains(text, "live account path", label)
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
    assert_contains(text, "Member References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_contains(text, "member-ledger.html", label)
    assert_contains(text, "tools/gca_member_backend.py", label)
    assert_contains(text, "LOCAL_BACKEND_HOSTS", label)
    assert_contains(text, "local JSONL records", label)
    assert_contains(text, "support.html", label)
    assert_contains(text, "privacy.html", label)
    assert_contains(text, "terms.html", label)
    assert_contains(text, "180 days", label)
    assert_contains(text, "30 days", label)
    assert_contains(text, "5-10 business days", label)
    assert_contains(text, "Use the live public member access page", label)
    assert_contains(text, "No cash, income, reimbursement, trading permission, or risk-control bypass", label)
    assert_contains(text, "10,000 GCA member benefit", label)
    assert_contains(text, "Public transaction hash + holding start date", label)
    assert_not_contains(text, "eth_sendTransaction", label)
    assert_not_contains(text, "personal_sign", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)


def validate_member_access_page(text: str) -> None:
    label = "/gca/member-access/"
    assert_contains(text, "GCA Member Access", label)
    assert_contains(text, "GCA 会员账户入口", label)
    assert_contains(text, "中英双语会员入口", label)
    assert_contains(text, "controlled HTTPS account UI", label)
    assert_contains(text, "Create or Update Access Record", label)
    assert_contains(text, "创建或更新账户记录", label)
    assert_contains(text, "Live Result", label)
    assert_contains(text, "实时结果", label)
    assert_contains(text, "Access Boundaries", label)
    assert_contains(text, "安全边界", label)
    assert_contains(text, "Verify Wallet Only", label)
    assert_contains(text, "只验证钱包", label)
    assert_contains(text, "Submit Account + Write Ledgers", label)
    assert_contains(text, "提交账户并写入账本", label)
    assert_contains(text, "Review Packet", label)
    assert_contains(text, "审核资料包", label)
    assert_contains(text, "Build Review Packet", label)
    assert_contains(text, "生成资料包", label)
    assert_contains(text, "Copy Packet", label)
    assert_contains(text, "复制资料包", label)
    assert_contains(text, "mailto:support@gcagochina.com", label)
    assert_contains(text, "navigator.clipboard.writeText", label)
    assert_contains(text, "buildReviewPacketText", label)
    assert_contains(text, "Backend eth_call", label)
    assert_contains(text, "ERC-20 balanceOf", label)
    assert_contains(text, "Cloudflare Workers + D1", label)
    assert_contains(text, "https://gca-registration-api.gcagochina.workers.dev", label)
    assert_contains(text, "POST /gca/member-access", label)
    assert_contains(text, "POST /gca/wallet-verifications", label)
    assert_contains(text, "gca_member_access_v1", label)
    assert_contains(text, "10,000 GCA", label)
    assert_contains(text, "1,000,000 GCA", label)
    assert_contains(text, "100 GCA AI Quant Access credits", label)
    assert_contains(text, "credits ledger", label)
    assert_contains(text, "GCA Member ledger", label)
    assert_contains(text, "100 万枚 GCA 审核的持有开始日期", label)
    assert_contains(text, "公开交易哈希", label)
    assert_contains(text, "bot-field", label)
    assert_contains(text, "website: website.value.trim()", label)
    assert_contains(text, "not automatic", label)
    assert_contains(text, "manual reserve-wallet transfer review", label)
    assert_contains(text, "API And Account References", label)
    assert_contains(text, "Support page", label)
    assert_contains(text, "../../support.html", label)
    assert_not_contains(text, "wallet_switchEthereumChain", label)
    assert_not_contains(text, "wallet_addEthereumChain", label)
    assert_not_contains(text, "eth_sendTransaction", label)
    assert_not_contains(text, "personal_sign", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)
    assert_not_contains(text, "Platform-Only Evidence Path", label)
    assert_not_contains(text, "Data Room", label)
    assert_not_contains(text, "../../data.html", label)


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
    assert_contains(text, "Copy Contact Export Commands", label)
    assert_contains(text, "Email Registration Intake", label)
    assert_contains(text, "Member Access Ops Pipeline", label)
    assert_contains(text, "tools/run_gca_member_access_ops.py", label)
    assert_contains(text, "cloudflare/gca-registration-worker/.env.admin.local", label)
    assert_contains(text, "ADMIN_READ_TOKEN", label)
    assert_contains(text, ".gca_access_data/cloudflare_member_access_export.json", label)
    assert_contains(text, ".gca_access_data/member_access_report/gca_member_support_queue.csv", label)
    assert_contains(text, ".gca_access_data/member_access_report/gca_holding_period_summary.json", label)
    assert_contains(text, "No automatic member-benefit transfer", label)
    assert_contains(text, "Latest Email Registration Records", label)
    assert_contains(text, "Read-only API check command", label)
    assert_contains(text, "tools/check_gca_registration_api.py", label)
    assert_contains(text, "without writing production data", label)
    assert_contains(text, "tools/sync_cloudflare_email_registrations.py", label)
    assert_contains(text, "tools/export_gca_email_contacts.py", label)
    assert_contains(text, "tools/run_gca_registration_ops.py", label)
    assert_contains(text, "tools/suppress_gca_contact.py", label)
    assert_contains(text, "gca_email_contacts_public_redacted.csv", label)
    assert_contains(text, "gca_registration_ops_summary.json", label)
    assert_contains(text, "gca_contact_suppressions.jsonl", label)
    assert_contains(text, "contactConsentAccepted", label)
    assert_contains(text, 'id="emailRows"', label)
    assert_contains(text, "renderEmailRegistrations", label)
    assert_contains(text, "copyContactExportCommands", label)
    assert_contains(text, "Contact export commands copied", label)
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
    assert_contains(text, "Public website view: use /gca/member-access/ for Workers + D1 intake", label)
    assert_contains(text, "local JSONL ledger records", label)
    assert_contains(text, ".gca_access_data/", label)
    assert_contains(text, "Email registrations", label)
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
    assert_contains(text, "Email Registration", label)
    assert_contains(text, "register.html", label)
    assert_contains(text, "Support References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_contains(text, "Reviewer Kit", label)
    assert_contains(text, "Platform Replies", label)
    assert_contains(text, "Team Profile", label)
    assert_contains(text, "BaseScan Remediation", label)
    assert_contains(text, "Review Queue", label)
    assert_contains(text, "Operations Runbook", label)
    assert_contains(text, "GCAgochina@outlook.com", label)
    assert_contains(text, "Domain Email", label)
    assert_contains(text, "Owner action required before BaseScan resubmission", label)
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
    if payload.get("officialEmail") != "support@gcagochina.com":
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
    if links.get("baseScanHandoffPage") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoffPage")
    if links.get("baseScanHandoff") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoff")
    if links.get("platformRepliesPage") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesPage")
    if links.get("platformReplies") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong platformReplies")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_roadmap_page(text: str) -> None:
    label = "/roadmap.html"
    assert_contains(text, "GCA Roadmap", label)
    assert_contains(text, "Roadmap References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Concept-stage utility buildout", label)
    assert_contains(text, "account and ledger path live", label)
    assert_contains(text, "Controlled HTTPS member account UI", label)
    assert_contains(text, "Live at", label)
    assert_contains(text, "Read-only GCA balance verification", label)
    assert_contains(text, "Live via Worker eth_call", label)
    assert_contains(text, "100 GCA AI Quant Access credit records", label)
    assert_contains(text, "Live for eligible wallet records", label)
    assert_contains(text, "GCA Member records", label)
    assert_contains(text, "benefit remains manual review", label)
    assert_contains(text, "External Dependencies", label)
    assert_contains(text, "Returned 2026-05-23; final package refreshed 2026-06-06; Handoff and Chinese owner flow ready for one support@gcagochina.com submission", label)
    assert_contains(text, "Latest reviewer package", label)
    assert_contains(text, "Final package 2026-06-06T11:10:54Z; daily status 2026-06-07T13:06:12Z", label)
    assert_contains(text, "Owner observed no warning visible", label)
    assert_contains(text, "Pending independent report", label)
    assert_contains(text, "Account and Ledger", label)
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
    if payload.get("lastUpdated") != "2026-05-27":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
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
    if market.get("liquidityStatementPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityStatementPage")
    if market.get("liquidityStatement") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidityStatement")
    if market.get("lpLockClaimed") is not False:
        raise SiteCheckError(f"{label}: LP lock must not be claimed")
    if market.get("liquidityDepth") != "starter-depth-only":
        raise SiteCheckError(f"{label}: wrong liquidityDepth")
    if dependencies.get("baseScanTokenProfile") != "ready-for-owner-resubmission":
        raise SiteCheckError(f"{label}: wrong BaseScan status")
    if dependencies.get("blockaidMetaMaskWarning") != "owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong wallet warning status")
    if dependencies.get("thirdPartyAudit") != "not-completed-deferred":
        raise SiteCheckError(f"{label}: wrong audit status")
    if not any(priority.get("id") == "controlled-account-ui" for priority in payload.get("nextBuildPriorities", [])):
        raise SiteCheckError(f"{label}: missing controlled account UI priority")
    if not any(priority.get("id") == "utility-credit-ledger" for priority in payload.get("nextBuildPriorities", [])):
        raise SiteCheckError(f"{label}: missing utility credit ledger priority")
    if not any(milestone.get("id") == "account-ledger-path-live" for milestone in payload.get("completedMilestones", [])):
        raise SiteCheckError(f"{label}: missing account ledger live milestone")
    if "GCA is concept-stage and has live account intake, read-only wallet verification, eligible ledger records, and staged non-custodial quant research access." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing concept-stage safe claim")
    if "the 10,000 GCA member benefit is automatic or self-service transferred before holding-period verification, support approval, and manual reserve-wallet processing" not in payload.get("publicClaimBoundaries", {}).get("doNotClaim", []):
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
    if not any(milestone.get("id") == "weekly-go-china-radar-issue-003" for milestone in payload.get("completedMilestones", [])):
        raise SiteCheckError(f"{label}: missing weekly radar completed milestone")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_community_page(text: str) -> None:
    label = "/community.html"
    assert_contains(text, "GCA Community Kit", label)
    assert_contains(text, "Community References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Announcements", label)
    assert_contains(text, "Campaign Calendar", label)
    assert_contains(text, "Content Library", label)
    assert_contains(text, "Publishing Desk", label)
    assert_contains(text, "Official Telegram", label)
    assert_contains(text, "Safe Announcement Copy", label)
    assert_contains(text, "X Launch Pack", label)
    assert_contains(text, "First X Post", label)
    assert_contains(text, "Pinned X Post Draft", label)
    assert_contains(text, "First official X post", label)
    assert_contains(text, FIRST_X_POST_URL, label)
    assert_contains(text, "Latest official X post", label)
    assert_contains(text, LATEST_X_POST_URL, label)
    assert_contains(text, "Tim Chen public professional profile evidence, the domain email setup plan, public evidence checklist, activation evidence packet, BaseScan Handoff, Chinese owner flow, and support@gcagochina.com mailbox are ready", label)
    assert_contains(text, "one clean owner resubmission while waiting for BaseScan review", label)
    assert_contains(text, ANNOUNCEMENTS_PAGE_URL, label)
    assert_contains(text, CAMPAIGN_PAGE_URL, label)
    assert_contains(text, CONTENT_LIBRARY_PAGE_URL, label)
    assert_contains(text, PUBLISHING_DESK_PAGE_URL, label)
    assert_contains(text, "Moderator replies", label)
    assert_contains(text, SECURITY_PAGE_URL, label)
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
    if not any("BaseScan token profile was returned again as information-insufficient on 2026-05-23" in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing BaseScan pending announcement")
    if not any("Narrative meets risk control" in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing narrative announcement")
    if not any("Weekly Go China Radar: https://gcagochina.com/radar.html" in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing weekly radar announcement")
    if not any(FIRST_X_POST_URL in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing first X post announcement")
    if not any(LATEST_X_POST_URL in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing latest X post announcement")
    if not any(CAMPAIGN_PAGE_URL in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing campaign announcement")
    if not any(CONTENT_LIBRARY_PAGE_URL in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing content library announcement")
    if not any(PUBLISHING_DESK_PAGE_URL in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing publishing desk announcement")
    if not any(RADAR_ISSUE_004_PAGE_URL in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing issue 004 announcement")
    if not any(MEMBER_ACCESS_BRIEF_001_PAGE_URL in item for item in payload.get("safeAnnouncement", [])):
        raise SiteCheckError(f"{label}: missing member access brief announcement")
    announcement_hub = payload.get("announcementHub", {})
    if announcement_hub.get("status") != "public-announcement-hub-published":
        raise SiteCheckError(f"{label}: wrong announcementHub status")
    if announcement_hub.get("pageUrl") != ANNOUNCEMENTS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong announcementHub pageUrl")
    if announcement_hub.get("url") != ANNOUNCEMENTS_URL:
        raise SiteCheckError(f"{label}: wrong announcementHub url")
    if announcement_hub.get("latestPostUrl") != LATEST_X_POST_URL:
        raise SiteCheckError(f"{label}: wrong announcementHub latestPostUrl")
    campaign = payload.get("campaignCalendar", {})
    if campaign.get("status") != "public-campaign-calendar-published":
        raise SiteCheckError(f"{label}: wrong campaignCalendar status")
    if campaign.get("pageUrl") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignCalendar pageUrl")
    if campaign.get("url") != CAMPAIGN_URL:
        raise SiteCheckError(f"{label}: wrong campaignCalendar url")
    if campaign.get("operatorReviewRequired") is not True:
        raise SiteCheckError(f"{label}: campaign operator review must be required")
    content_library = payload.get("contentLibrary", {})
    if content_library.get("status") != "public-bilingual-content-library-published":
        raise SiteCheckError(f"{label}: wrong contentLibrary status")
    if content_library.get("pageUrl") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary pageUrl")
    if content_library.get("url") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary url")
    if content_library.get("draftCount") != 10:
        raise SiteCheckError(f"{label}: wrong contentLibrary draftCount")
    if content_library.get("languages") != ["en", "zh"]:
        raise SiteCheckError(f"{label}: wrong contentLibrary languages")
    if content_library.get("platforms") != ["X", "Telegram"]:
        raise SiteCheckError(f"{label}: wrong contentLibrary platforms")
    publishing_desk = payload.get("publishingDesk", {})
    if publishing_desk.get("status") != "public-publishing-desk-published":
        raise SiteCheckError(f"{label}: wrong publishingDesk status")
    if publishing_desk.get("pageUrl") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk pageUrl")
    if publishing_desk.get("url") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk url")
    if publishing_desk.get("nextPublishTargetDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong publishingDesk nextPublishTargetDate")
    if publishing_desk.get("manualPublishOnly") is not True:
        raise SiteCheckError(f"{label}: publishingDesk must be manual")
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
    if x_launch.get("latestPostUrl") != LATEST_X_POST_URL:
        raise SiteCheckError(f"{label}: wrong latestPostUrl")
    if x_launch.get("latestPostPublishedDate") != "2026-05-23":
        raise SiteCheckError(f"{label}: wrong latestPostPublishedDate")
    if "Tim Chen public professional profile evidence, the domain email setup plan, public evidence checklist, activation evidence packet, BaseScan Handoff, Chinese owner flow, and support@gcagochina.com mailbox are now ready" not in x_launch.get("currentStatusAfterLatestPost", ""):
        raise SiteCheckError(f"{label}: missing current status after latest post")
    if "one clean owner resubmission while waiting for BaseScan review and publication" not in x_launch.get("currentStatusAfterLatestPost", ""):
        raise SiteCheckError(f"{label}: missing current domain mailbox boundary")
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
    if links.get("announcementsPage") != ANNOUNCEMENTS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong announcementsPage")
    if links.get("announcements") != ANNOUNCEMENTS_URL:
        raise SiteCheckError(f"{label}: wrong announcements")
    if links.get("campaignPage") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignPage")
    if links.get("campaign") != CAMPAIGN_URL:
        raise SiteCheckError(f"{label}: wrong campaign")
    if links.get("contentLibraryPage") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibraryPage")
    if links.get("contentLibrary") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary")
    if links.get("publishingDeskPage") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDeskPage")
    if links.get("publishingDesk") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk")
    if links.get("narrativePage") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong narrativePage")
    if links.get("narrative") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong narrative")
    if links.get("weeklyRadarPage") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarPage")
    if links.get("weeklyRadar") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadar")
    if links.get("radarIssue004Page") != RADAR_ISSUE_004_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004Page")
    if links.get("radarIssue004") != RADAR_ISSUE_004_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004")
    if links.get("memberAccessBrief001Page") != MEMBER_ACCESS_BRIEF_001_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001Page")
    if links.get("memberAccessBrief001") != MEMBER_ACCESS_BRIEF_001_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001")
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


def validate_announcements_page(text: str) -> None:
    label = "/announcements.html"
    assert_social_preview_meta(text, label, ANNOUNCEMENTS_PAGE_URL)
    assert_contains(text, "GCA Announcements", label)
    assert_contains(text, "Announcement References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Campaign Calendar", label)
    assert_contains(text, "Content Library", label)
    assert_contains(text, "Official X", label)
    assert_contains(text, "Official Telegram", label)
    assert_contains(text, "Every 3 days", label)
    assert_contains(text, "Published X Posts", label)
    assert_contains(text, "Latest Post Text", label)
    assert_contains(text, "Current note after this post", label)
    assert_contains(text, "BaseScan Handoff, Chinese owner flow", label)
    assert_contains(text, "Next 3-Day Content Queue", label)
    assert_contains(text, "Safe Messaging Rules", label)
    assert_contains(text, "Do Not Claim", label)
    assert_contains(text, FIRST_X_POST_URL, label)
    assert_contains(text, LATEST_X_POST_URL, label)
    assert_contains(text, RADAR_ISSUE_004_PAGE_URL, label)
    assert_contains(text, PRODUCT_PAGE_URL, label)
    assert_contains(text, SECURITY_PAGE_URL, label)
    assert_contains(text, "No return promises", label)
    assert_contains(text, "operator-reviewed public updates", label)
    assert_contains(text, X_URL, label)
    assert_contains(text, "https://t.me/gcagochinaofficial", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_no_forbidden_public_claims(text, label)


def validate_announcements_json(text: str) -> None:
    label = "/announcements.json"
    payload = load_json(text, label)
    cadence = payload.get("contentCadence", {})
    posts = payload.get("publishedPosts", [])
    links = payload.get("publicLinks", {})

    if payload.get("schema") != ANNOUNCEMENTS_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != ANNOUNCEMENTS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-announcement-hub-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("officialX") != X_URL:
        raise SiteCheckError(f"{label}: wrong officialX")
    if payload.get("officialTelegram") != "https://t.me/gcagochinaofficial":
        raise SiteCheckError(f"{label}: wrong officialTelegram")
    if cadence.get("intervalDays") != 3:
        raise SiteCheckError(f"{label}: wrong content cadence")
    if cadence.get("operatorReviewRequired") is not True:
        raise SiteCheckError(f"{label}: operator review must be required")
    if not isinstance(posts, list) or len(posts) < 2:
        raise SiteCheckError(f"{label}: expected published posts")
    if not any(post.get("url") == FIRST_X_POST_URL for post in posts if isinstance(post, dict)):
        raise SiteCheckError(f"{label}: missing first X post")
    if not any(post.get("url") == LATEST_X_POST_URL for post in posts if isinstance(post, dict)):
        raise SiteCheckError(f"{label}: missing latest X post")
    latest_post = next((post for post in posts if isinstance(post, dict) and post.get("url") == LATEST_X_POST_URL), {})
    if "Tim Chen public professional profile evidence, the domain email setup plan, public evidence checklist, activation evidence packet, BaseScan Handoff, Chinese owner flow, and support@gcagochina.com mailbox are now ready" not in latest_post.get("currentStatusAfterPost", ""):
        raise SiteCheckError(f"{label}: missing latest post current status")
    if "one clean owner resubmission while waiting for BaseScan review and publication" not in latest_post.get("currentStatusAfterPost", ""):
        raise SiteCheckError(f"{label}: missing latest post domain mailbox boundary")
    if links.get("announcementsPage") != ANNOUNCEMENTS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong announcementsPage")
    if links.get("announcements") != ANNOUNCEMENTS_URL:
        raise SiteCheckError(f"{label}: wrong announcements")
    if links.get("campaignPage") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignPage")
    if links.get("campaign") != CAMPAIGN_URL:
        raise SiteCheckError(f"{label}: wrong campaign")
    if links.get("contentLibraryPage") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibraryPage")
    if links.get("contentLibrary") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary")
    if links.get("publishingDeskPage") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDeskPage")
    if links.get("publishingDesk") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk")
    if links.get("radarIssue004Page") != RADAR_ISSUE_004_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004Page")
    if links.get("radarIssue004") != RADAR_ISSUE_004_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004")
    if links.get("memberAccessBrief001Page") != MEMBER_ACCESS_BRIEF_001_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001Page")
    if links.get("memberAccessBrief001") != MEMBER_ACCESS_BRIEF_001_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001")
    if links.get("latestXPost") != LATEST_X_POST_URL:
        raise SiteCheckError(f"{label}: wrong latestXPost")
    if "2026-06-06T11:10:54Z" not in latest_post.get("currentStatusAfterPost", ""):
        raise SiteCheckError(f"{label}: missing final package refresh timestamp")
    if not any(item.get("topic") == "Product Utility Intro" and item.get("recommendedLink") == PRODUCT_PAGE_URL for item in payload.get("nextContentQueue", []) if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing product utility intro queue link")
    if not any(item.get("topic") == "Security Boundary" and item.get("recommendedLink") == SECURITY_PAGE_URL for item in payload.get("nextContentQueue", []) if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing security boundary queue link")
    if payload.get("campaignCalendar", {}).get("status") != "public-campaign-calendar-published":
        raise SiteCheckError(f"{label}: wrong campaign calendar status")
    content_library = payload.get("contentLibrary", {})
    if content_library.get("status") != "public-bilingual-content-library-published":
        raise SiteCheckError(f"{label}: wrong contentLibrary status")
    if content_library.get("pageUrl") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary pageUrl")
    if content_library.get("url") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary url")
    if content_library.get("draftCount") != 10:
        raise SiteCheckError(f"{label}: wrong contentLibrary draftCount")
    publishing_desk = payload.get("publishingDesk", {})
    if publishing_desk.get("status") != "public-publishing-desk-published":
        raise SiteCheckError(f"{label}: wrong publishingDesk status")
    if publishing_desk.get("pageUrl") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk pageUrl")
    if publishing_desk.get("url") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk url")
    if publishing_desk.get("manualPublishOnly") is not True:
        raise SiteCheckError(f"{label}: publishingDesk must be manual")
    if "third-party audit completion before an independent report is published" not in payload.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing audit boundary")
    if not any("starter-depth liquidity" in item for item in payload.get("safeMessagingRules", [])):
        raise SiteCheckError(f"{label}: missing liquidity safe messaging")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_campaign_page(text: str) -> None:
    label = "/campaign.html"
    assert_social_preview_meta(text, label, CAMPAIGN_PAGE_URL)
    assert_contains(text, "GCA Campaign Calendar", label)
    assert_contains(text, "Campaign References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Content Library", label)
    assert_contains(text, "Publishing Desk", label)
    assert_contains(text, "Every 3 days", label)
    assert_contains(text, "2026-05-20 to 2026-06-16", label)
    assert_contains(text, "10 posts", label)
    assert_contains(text, "Manual review before publish", label)
    assert_contains(text, "Next Copy-Ready X Draft", label)
    assert_contains(text, "2026-06-07", label)
    assert_contains(text, "30-Day Content Queue", label)
    assert_contains(text, "Weekly Go China Radar", label)
    assert_contains(text, "Member Access Buildout", label)
    assert_contains(text, "Verification First", label)
    assert_contains(text, "Do Not Publish", label)
    assert_contains(text, "No return promises", label)
    assert_contains(text, "Official links first. No price or return claim.", label)
    assert_contains(text, X_URL, label)
    assert_contains(text, "https://t.me/gcagochinaofficial", label)
    assert_contains(text, CONTENT_LIBRARY_PAGE_URL, label)
    assert_contains(text, PUBLISHING_DESK_PAGE_URL, label)
    assert_contains(text, RADAR_ISSUE_004_PAGE_URL, label)
    assert_contains(text, MEMBER_ACCESS_BRIEF_001_PAGE_URL, label)
    assert_contains(text, LATEST_X_POST_URL, label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "GCA/USDT", label)
    assert_no_forbidden_public_claims(text, label)


def validate_campaign_json(text: str) -> None:
    label = "/campaign.json"
    payload = load_json(text, label)
    window = payload.get("campaignWindow", {})
    draft = payload.get("nextCopyReadyDraft", {})
    queue = payload.get("contentQueue", [])
    links = payload.get("publicLinks", {})

    if payload.get("schema") != CAMPAIGN_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-campaign-calendar-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("officialX") != X_URL:
        raise SiteCheckError(f"{label}: wrong officialX")
    if window.get("intervalDays") != 3:
        raise SiteCheckError(f"{label}: wrong intervalDays")
    if window.get("draftCount") != 10:
        raise SiteCheckError(f"{label}: wrong draft count")
    if window.get("operatorReviewRequired") is not True:
        raise SiteCheckError(f"{label}: operator review must be required")
    if window.get("contentLibrary") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaign window content library")
    if draft.get("targetDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong next draft date")
    if draft.get("id") != "x-product-utility-intro-001":
        raise SiteCheckError(f"{label}: wrong next draft id")
    if draft.get("topic") != "Product Utility Intro":
        raise SiteCheckError(f"{label}: wrong next draft topic")
    if draft.get("recommendedLink") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong next draft link")
    if not isinstance(queue, list) or len(queue) != 10:
        raise SiteCheckError(f"{label}: expected 10 queued posts")
    if not any(item.get("topic") == "Verification First" for item in queue if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing verification post")
    if not any(item.get("recommendedLink") == "https://gcagochina.com/markets.html" for item in queue if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing market route post")
    if not any(item.get("recommendedLink") == RADAR_ISSUE_004_PAGE_URL for item in queue if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing issue 004 post")
    if not any(item.get("recommendedLink") == MEMBER_ACCESS_BRIEF_001_PAGE_URL for item in queue if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing member access brief post")
    content_library = payload.get("contentLibrary", {})
    if content_library.get("status") != "public-bilingual-content-library-published":
        raise SiteCheckError(f"{label}: wrong contentLibrary status")
    if content_library.get("pageUrl") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary pageUrl")
    if content_library.get("url") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary url")
    if content_library.get("draftCount") != 10:
        raise SiteCheckError(f"{label}: wrong contentLibrary draftCount")
    if content_library.get("languages") != ["en", "zh"]:
        raise SiteCheckError(f"{label}: wrong contentLibrary languages")
    if content_library.get("platforms") != ["X", "Telegram"]:
        raise SiteCheckError(f"{label}: wrong contentLibrary platforms")
    publishing_desk = payload.get("publishingDesk", {})
    if publishing_desk.get("status") != "public-publishing-desk-published":
        raise SiteCheckError(f"{label}: wrong publishingDesk status")
    if publishing_desk.get("pageUrl") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk pageUrl")
    if publishing_desk.get("url") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk url")
    if publishing_desk.get("nextPublishTargetDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong publishingDesk nextPublishTargetDate")
    if publishing_desk.get("manualPublishOnly") is not True:
        raise SiteCheckError(f"{label}: publishingDesk must be manual")
    if links.get("campaignPage") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignPage")
    if links.get("campaign") != CAMPAIGN_URL:
        raise SiteCheckError(f"{label}: wrong campaign")
    if links.get("contentLibraryPage") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibraryPage")
    if links.get("contentLibrary") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary")
    if links.get("publishingDeskPage") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDeskPage")
    if links.get("publishingDesk") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk")
    if links.get("radarIssue004Page") != RADAR_ISSUE_004_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004Page")
    if links.get("radarIssue004") != RADAR_ISSUE_004_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004")
    if links.get("memberAccessBrief001Page") != MEMBER_ACCESS_BRIEF_001_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001Page")
    if links.get("memberAccessBrief001") != MEMBER_ACCESS_BRIEF_001_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001")
    if links.get("announcementsPage") != ANNOUNCEMENTS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong announcementsPage")
    if links.get("latestXPost") != LATEST_X_POST_URL:
        raise SiteCheckError(f"{label}: wrong latestXPost")
    if "third-party audit claim until an independent report is public" not in payload.get("doNotPublish", []):
        raise SiteCheckError(f"{label}: missing audit boundary")
    if not any("Fixed-supply Base Mainnet" in item for item in payload.get("allowedAngles", [])):
        raise SiteCheckError(f"{label}: missing fixed supply angle")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_content_library_page(text: str) -> None:
    label = "/content-library.html"
    assert_social_preview_meta(text, label, CONTENT_LIBRARY_PAGE_URL)
    assert_contains(text, "Content References", label)
    assert_no_public_data_room_terms(text, label)
    for expected in (
        "GCA Content Library",
        "Publishing Desk",
        "10 bilingual drafts",
        "X and Telegram",
        "2026-05-20 to 2026-06-16",
        "Manual review before publish",
        "Bilingual Drafts",
        "Weekly Go China Radar",
        "Member Access Buildout",
        "Verification First",
        "Official Market Route",
        "Product Utility Intro",
        "Security Boundary",
        "Build Update Recap",
        "No return promises",
        "Official links first. No price or return claim.",
        "先核对官方链接。不做价格或收益承诺。",
        "Base Mainnet / chainId 8453",
        "GCA/USDT",
        RADAR_ISSUE_004_PAGE_URL,
        MEMBER_ACCESS_BRIEF_001_PAGE_URL,
        X_URL,
        "https://t.me/gcagochinaofficial",
        LATEST_X_POST_URL,
        MAINNET_ADDRESS,
    ):
        assert_contains(text, expected, label)
    assert_no_forbidden_public_claims(text, label)


def validate_content_library_json(text: str) -> None:
    label = "/content-library.json"
    payload = load_json(text, label)
    window = payload.get("campaignWindow", {})
    drafts = payload.get("drafts", [])
    links = payload.get("publicLinks", {})

    if payload.get("schema") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-bilingual-content-library-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("officialX") != X_URL:
        raise SiteCheckError(f"{label}: wrong officialX")
    if payload.get("officialTelegram") != "https://t.me/gcagochinaofficial":
        raise SiteCheckError(f"{label}: wrong officialTelegram")
    if window.get("intervalDays") != 3:
        raise SiteCheckError(f"{label}: wrong intervalDays")
    if window.get("draftCount") != 10:
        raise SiteCheckError(f"{label}: wrong draftCount")
    if window.get("operatorReviewRequired") is not True:
        raise SiteCheckError(f"{label}: operator review must be required")
    if not isinstance(drafts, list) or len(drafts) != 10:
        raise SiteCheckError(f"{label}: expected 10 bilingual drafts")
    if not any(item.get("topic") == "Weekly Go China Radar" for item in drafts if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing weekly radar draft")
    if not any(item.get("recommendedLink") == RADAR_ISSUE_004_PAGE_URL for item in drafts if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing issue 004 recommended link")
    if not any(item.get("recommendedLink") == MEMBER_ACCESS_BRIEF_001_PAGE_URL for item in drafts if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing member access brief recommended link")
    if not any(item.get("topic") == "Product Utility Intro" and item.get("recommendedLink") == PRODUCT_PAGE_URL for item in drafts if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing product utility intro draft")
    if not any(item.get("topic") == "Security Boundary" for item in drafts if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing security boundary draft")
    for item in drafts:
        if not isinstance(item, dict):
            raise SiteCheckError(f"{label}: draft must be object")
        for key in ("xEnglish", "xChinese", "telegram", "visualTheme", "claimBoundary"):
            if not item.get(key):
                raise SiteCheckError(f"{label}: draft missing {key}")
    if links.get("contentLibraryPage") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibraryPage")
    if links.get("contentLibrary") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary")
    if links.get("publishingDeskPage") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDeskPage")
    if links.get("publishingDesk") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk")
    if links.get("radarIssue004Page") != RADAR_ISSUE_004_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004Page")
    if links.get("radarIssue004") != RADAR_ISSUE_004_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004")
    if links.get("memberAccessBrief001Page") != MEMBER_ACCESS_BRIEF_001_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001Page")
    if links.get("memberAccessBrief001") != MEMBER_ACCESS_BRIEF_001_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001")
    if links.get("campaignPage") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignPage")
    if links.get("latestXPost") != LATEST_X_POST_URL:
        raise SiteCheckError(f"{label}: wrong latestXPost")
    if "third-party audit claim until an independent report is public" not in payload.get("doNotAdd", []):
        raise SiteCheckError(f"{label}: missing audit boundary")
    if not any("official GCA/USDT route" in item for item in payload.get("publicationGuardrails", [])):
        raise SiteCheckError(f"{label}: missing market-route guardrail")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_publishing_desk_page(text: str) -> None:
    label = "/publishing-desk.html"
    assert_social_preview_meta(text, label, PUBLISHING_DESK_PAGE_URL)
    assert_contains(text, "Publishing References", label)
    assert_no_public_data_room_terms(text, label)
    for expected in (
        "GCA Publishing Desk",
        "Manual publishing hub",
        "2026-06-07",
        "X and Telegram",
        "Ready for operator review",
        "Manual publish only",
        "Next X Draft",
        "Telegram Copy",
        "Copy English X",
        "Copy Chinese X",
        "Copy Telegram",
        "Post-Publish URL Recorder",
        "Generate Ledger Snippet",
        "Copy Ledger Snippet",
        'id="postLedgerSnippet"',
        'data-copy-target="postLedgerSnippet"',
        "generateLedgerSnippet",
        "publishedPost",
        "announcementLedgerUpdate",
        "communityUpdate",
        "projectUpdate",
        '"value" in target',
        'data-copy-target="xDraftCopy"',
        'data-copy-target="xChineseCopy"',
        'data-copy-target="telegramCopy"',
        "navigator.clipboard.writeText",
        'document.execCommand("copy")',
        "Pre-Publish Checks",
        "Do Not Publish",
        "Post-Publish Ledger Update",
        "Base Mainnet / chainId 8453",
        "GCA/USDT",
        "No return promises",
        "Official links first. No price or return claim.",
        "先核对官方链接。不做价格或收益承诺。",
        "Product-utility introduction only",
        X_URL,
        "https://t.me/gcagochinaofficial",
        CONTENT_LIBRARY_PAGE_URL,
        CAMPAIGN_PAGE_URL,
        PRODUCT_PAGE_URL,
        SECURITY_PAGE_URL,
        LATEST_X_POST_URL,
        MAINNET_ADDRESS,
    ):
        assert_contains(text, expected, label)
    assert_not_contains(text, "Member access education only", label)
    assert_not_contains(text, "https://gcagochina.com/publishing-desk.json", label)
    assert_no_forbidden_public_claims(text, label)


def validate_publishing_desk_json(text: str) -> None:
    label = "/publishing-desk.json"
    payload = load_json(text, label)
    next_action = payload.get("nextPublishAction", {})
    links = payload.get("publicLinks", {})

    if payload.get("schema") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-publishing-desk-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("officialX") != X_URL:
        raise SiteCheckError(f"{label}: wrong officialX")
    if payload.get("officialTelegram") != "https://t.me/gcagochinaofficial":
        raise SiteCheckError(f"{label}: wrong officialTelegram")
    if payload.get("officialMarketRoute") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialMarketRoute")
    if next_action.get("status") != "ready-for-operator-review":
        raise SiteCheckError(f"{label}: wrong next action status")
    if next_action.get("targetDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong targetDate")
    if next_action.get("sourceDraftId") != "gca-draft-2026-06-07-product-intro":
        raise SiteCheckError(f"{label}: wrong sourceDraftId")
    if next_action.get("topic") != "Product Utility Intro":
        raise SiteCheckError(f"{label}: wrong topic")
    if next_action.get("channels") != ["X", "Telegram"]:
        raise SiteCheckError(f"{label}: wrong channels")
    if next_action.get("recommendedLink") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong recommendedLink")
    if next_action.get("contentLibrary") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary")
    if next_action.get("campaignCalendar") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignCalendar")
    if next_action.get("requiresManualPosting") is not True:
        raise SiteCheckError(f"{label}: manual posting must be required")
    if next_action.get("requiresOperatorReview") is not True:
        raise SiteCheckError(f"{label}: operator review must be required")
    for key in ("xEnglish", "xChinese", "telegram", "hashtags"):
        if not next_action.get(key):
            raise SiteCheckError(f"{label}: missing next action {key}")
    if "Product-utility introduction only" not in next_action.get("claimBoundary", ""):
        raise SiteCheckError(f"{label}: wrong product claim boundary")
    if "third-party audit completion before an independent report is public" not in payload.get("doNotPublish", []):
        raise SiteCheckError(f"{label}: missing audit boundary")
    if not any("announcements.json" in item.get("target", "") for item in payload.get("postPublishLedgerUpdate", []) if isinstance(item, dict)):
        raise SiteCheckError(f"{label}: missing announcement ledger update")
    if links.get("publishingDeskPage") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDeskPage")
    if links.get("publishingDesk") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk")
    if links.get("contentLibraryPage") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibraryPage")
    if links.get("campaignPage") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignPage")
    if links.get("radarIssue004") != RADAR_ISSUE_004_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004")
    if links.get("announcementsPage") != ANNOUNCEMENTS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong announcementsPage")
    if links.get("officialX") != X_URL:
        raise SiteCheckError(f"{label}: wrong officialX link")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_narrative_page(text: str) -> None:
    label = "/narrative.html"
    assert_contains(text, "GCA Narrative System", label)
    assert_contains(text, "Narrative References", label)
    assert_no_public_data_room_terms(text, label)
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
    if payload.get("weeklyRadar", {}).get("status") != "weekly-go-china-radar-issue-003-published":
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
    assert_contains(text, "Radar References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Issue 003 / 2026-05-16", label)
    assert_contains(text, "not live market data", label)
    assert_contains(text, "not financial advice", label)
    assert_contains(text, "Narrative Radar Board", label)
    assert_contains(text, "Public activity without artificial volume", label)
    assert_contains(text, "Reviewer-ready trust links", label)
    assert_contains(text, "Member utility readiness", label)
    assert_contains(text, "Market Quality Check", label)
    assert_contains(text, "Reviewer Kit Handoff", label)
    assert_contains(text, "GCA Member Readiness", label)
    assert_contains(text, "No third-party audit has been completed", label)
    assert_contains(text, "artificial volume", label)
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
    if payload.get("status") != "weekly-go-china-radar-issue-003-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("issue") != "issue-003":
        raise SiteCheckError(f"{label}: wrong issue")
    if payload.get("issueDate") != "2026-05-16":
        raise SiteCheckError(f"{label}: wrong issueDate")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if "not live market data" not in payload.get("scope", ""):
        raise SiteCheckError(f"{label}: missing market-data boundary")
    for theme in ("Public activity without artificial volume", "Reviewer-ready trust links", "Member utility readiness"):
        if theme not in {item.get("name") for item in payload.get("narrativeThemes", [])}:
            raise SiteCheckError(f"{label}: missing theme {theme}")
    for hook in ("Market Quality Check", "Reviewer Kit Handoff", "GCA Member Readiness", "Risk-Control Education"):
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
    if "artificial volume, self-trading, wash trading, or misleading market activity" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing artificial-volume boundary")
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


def validate_radar_issue_004_page(text: str) -> None:
    label = "/radar-issue-004.html"
    assert_social_preview_meta(text, label, RADAR_ISSUE_004_PAGE_URL)
    assert_contains(text, "Issue 004 References", label)
    assert_no_public_data_room_terms(text, label)
    for expected in (
        "Weekly Go China Radar Issue 004",
        "Issue 004 / 2026-05-20 / Ready for review",
        "Ready for operator review",
        "Go China Access as a research corridor",
        "Risk-first quant utility",
        "Verification before interaction",
        "Liquidation Replay",
        "Backtesting",
        "Risk Alerts",
        "ENTRY_READY Review",
        "Position Sizing",
        "No third-party audit has been completed",
        "Copy-Ready Post",
        RADAR_ISSUE_004_PAGE_URL,
        MAINNET_ADDRESS,
        BASE_USDT_ADDRESS,
        "GCA/USDT",
        "not financial advice",
        "not live market data",
    ):
        assert_contains(text, expected, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_radar_issue_004_json(text: str) -> None:
    label = "/radar-issue-004.json"
    payload = load_json(text, label)
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})
    copy_ready = payload.get("copyReadyPost", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != RADAR_ISSUE_004_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != RADAR_ISSUE_004_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "weekly-go-china-radar-issue-004-ready-for-review":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("issue") != "issue-004":
        raise SiteCheckError(f"{label}: wrong issue")
    if payload.get("issueDate") != "2026-05-20":
        raise SiteCheckError(f"{label}: wrong issueDate")
    if payload.get("publicationStatus") != "operator-review-required-before-social-posting":
        raise SiteCheckError(f"{label}: wrong publicationStatus")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if "not live market data" not in payload.get("scope", ""):
        raise SiteCheckError(f"{label}: missing market-data boundary")
    for theme in ("Go China Access as a research corridor", "Risk-first quant utility", "Verification before interaction"):
        if theme not in {item.get("name") for item in payload.get("narrativeThemes", [])}:
            raise SiteCheckError(f"{label}: missing theme {theme}")
    for hook in ("Liquidation Replay", "Backtesting", "Risk Alerts", "ENTRY_READY Review", "Position Sizing"):
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
    if copy_ready.get("targetDate") != "2026-05-20":
        raise SiteCheckError(f"{label}: wrong copy target date")
    if copy_ready.get("channels") != ["X", "Telegram"]:
        raise SiteCheckError(f"{label}: wrong copy channels")
    if copy_ready.get("requiresOperatorReview") is not True:
        raise SiteCheckError(f"{label}: copy must require operator review")
    for key in ("xEnglish", "xChinese", "telegram"):
        if not copy_ready.get(key):
            raise SiteCheckError(f"{label}: missing copy field {key}")
    if "No third-party audit has been completed." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "buy or sell recommendation" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing recommendation boundary")
    if "return promise" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing return boundary")
    if links.get("radarIssue004Page") != RADAR_ISSUE_004_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004Page")
    if links.get("radarIssue004") != RADAR_ISSUE_004_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004")
    if links.get("publishingDeskPage") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDeskPage")
    if links.get("contentLibraryPage") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibraryPage")
    if links.get("campaignPage") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignPage")
    if links.get("verify") != VERIFY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong verify")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_member_access_brief_001_page(text: str) -> None:
    label = "/member-access-brief-001.html"
    assert_social_preview_meta(text, label, MEMBER_ACCESS_BRIEF_001_PAGE_URL)
    for expected in (
        "GCA Member Access Brief 001",
        "Review Queue",
        "review-queue.html",
        "Brief 001 / 2026-05-23 / Ready for review",
        "Ready for operator review",
        "1,000,000 GCA",
        "30 consecutive days",
        "10,000 GCA reserve transfer",
        "Purchase and hold at least 1,000,000 GCA",
        "Support and ledger approval required",
        "Project or owner-held reserve only; no new minting",
        "Account intake and eligible ledger records are live",
        "Copy-Ready Post",
        MEMBER_ACCESS_BRIEF_001_PAGE_URL,
        "member-benefit.html",
        "member-benefit-transfer.html",
        MAINNET_ADDRESS,
        "Base Mainnet / chainId 8453",
        "not financial advice",
    ):
        assert_contains(text, expected, label)
    assert_no_public_data_room_terms(text, label)
    assert_no_forbidden_public_claims(text, label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)


def validate_member_access_brief_001_json(text: str) -> None:
    label = "/member-access-brief-001.json"
    payload = load_json(text, label)
    rule = payload.get("memberRule", {})
    copy_ready = payload.get("copyReadyPost", {})
    boundaries = payload.get("publicClaimBoundaries", {})
    links = payload.get("officialLinks", {})

    if payload.get("schema") != MEMBER_ACCESS_BRIEF_001_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != MEMBER_ACCESS_BRIEF_001_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "member-access-brief-001-ready-for-review":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("briefId") != "member-access-brief-001":
        raise SiteCheckError(f"{label}: wrong briefId")
    if payload.get("targetDate") != "2026-05-23":
        raise SiteCheckError(f"{label}: wrong targetDate")
    if payload.get("publicationStatus") != "operator-review-required-before-social-posting":
        raise SiteCheckError(f"{label}: wrong publicationStatus")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if "member benefit is not automatic self-service transfer" not in payload.get("scope", ""):
        raise SiteCheckError(f"{label}: missing member-benefit boundary")
    if "not a promise of approval" not in payload.get("scope", ""):
        raise SiteCheckError(f"{label}: missing approval boundary")
    if rule.get("tierName") != "GCA Member":
        raise SiteCheckError(f"{label}: wrong tierName")
    if rule.get("minimumHolding") != "1,000,000 GCA":
        raise SiteCheckError(f"{label}: wrong minimumHolding")
    if rule.get("minimumHoldingPeriodDays") != 30:
        raise SiteCheckError(f"{label}: wrong minimumHoldingPeriodDays")
    if rule.get("memberBenefitAmount") != "10,000 GCA":
        raise SiteCheckError(f"{label}: wrong memberBenefitAmount")
    if "no new minting" not in rule.get("memberBenefitSource", ""):
        raise SiteCheckError(f"{label}: missing no-mint source")
    if not any("member benefit is not automatic or self-service transferred" in item for item in payload.get("releaseBoundaries", [])):
        raise SiteCheckError(f"{label}: missing self-service boundary")
    if not any("does not automatically trigger a transfer" in item for item in payload.get("releaseBoundaries", [])):
        raise SiteCheckError(f"{label}: missing automatic-transfer boundary")
    if copy_ready.get("targetDate") != "2026-05-23":
        raise SiteCheckError(f"{label}: wrong copy target date")
    if copy_ready.get("channels") != ["X", "Telegram"]:
        raise SiteCheckError(f"{label}: wrong copy channels")
    if copy_ready.get("requiresOperatorReview") is not True:
        raise SiteCheckError(f"{label}: copy must require operator review")
    for key in ("xEnglish", "xChinese", "telegram"):
        if not copy_ready.get(key):
            raise SiteCheckError(f"{label}: missing copy field {key}")
    if "Account intake, read-only wallet verification, and eligible ledger records are live; member benefit transfers remain manual review only." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing account-intake safe claim")
    if "holding 1,000,000 GCA automatically triggers a transfer" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing automatic-transfer boundary")
    if links.get("memberAccessBrief001Page") != MEMBER_ACCESS_BRIEF_001_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001Page")
    if links.get("memberAccessBrief001") != MEMBER_ACCESS_BRIEF_001_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001")
    if links.get("memberProgram") != MEMBER_PROGRAM_URL:
        raise SiteCheckError(f"{label}: wrong memberProgram")
    if links.get("memberBenefitPage") != MEMBER_BENEFIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitPage")
    if links.get("memberBenefit") != MEMBER_BENEFIT_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefit")
    if links.get("memberBenefitTransferPage") != MEMBER_BENEFIT_TRANSFER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberBenefitTransferPage")
    if links.get("campaignPage") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignPage")
    if links.get("contentLibraryPage") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibraryPage")
    if links.get("publishingDeskPage") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDeskPage")
    if links.get("verify") != VERIFY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong verify")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_utility_page(text: str) -> None:
    label = "/utility.html"
    assert_contains(text, "GCA Utility Thesis", label)
    assert_contains(text, "Utility References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "GCA AI Quant Access Specification", label)
    assert_contains(text, "GCA AI Quant Access non-custodial quant tools", label)
    assert_contains(text, "read-only wallet verification", label)
    assert_contains(text, "no custody", label)
    assert_contains(text, "no withdrawal permission", label)
    assert_contains(text, "no exchange API secret collection", label)
    assert_contains(text, "no platform revenue distribution", label)
    assert_contains(text, "controlled HTTPS account UI", label)
    assert_contains(text, "100 GCA AI Quant Access credits", label)
    assert_contains(text, "GCA Member status", label)
    assert_contains(text, "10,000 GCA member benefit", label)
    assert_contains(text, "Credits Catalog", label)
    assert_contains(text, "credits.html", label)
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
    if positioning.get("connectedProduct") != "GCA AI Quant Access non-custodial quant risk toolkit":
        raise SiteCheckError(f"{label}: wrong connectedProduct")
    if "read-only ERC-20 balance checks" not in " ".join(payload.get("bridgePrinciples", [])):
        raise SiteCheckError(f"{label}: missing read-only verification principle")
    if holder_bonus.get("minimumHolding") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder bonus minimum")
    if holder_bonus.get("creditAmount") != "100 GCA AI Quant Access credits":
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
    if "GCA has published a public access layer specification." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing utility safe claim")
    if not any("credits or member status are cash" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing credit/member boundary")
    if not any("10,000 GCA member benefit is automatic or self-service transferred" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing member benefit boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_product_page(text: str) -> None:
    label = "/product.html"
    assert_contains(text, "GCA AI Quant Access Product Spec", label)
    assert_contains(text, "Product References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Access Portal", label)
    assert_contains(text, "Access API", label)
    assert_contains(text, "Release Gates", label)
    assert_contains(text, "Credits Catalog", label)
    assert_contains(text, "public product spec only", label)
    assert_contains(text, "not a live trading terminal", label)
    assert_contains(text, "not live market data", label)
    assert_contains(text, "not financial advice", label)
    assert_contains(text, "Public Account UI", label)
    assert_contains(text, "Live at /gca/member-access/", label)
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
    if positioning.get("currentStage") != "account-ledger-path-live-product-tools-planned":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if positioning.get("publicAccountUiLive") is not True:
        raise SiteCheckError(f"{label}: publicAccountUiLive must be true")
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
    if "access-portal" not in release_gate_ids:
        raise SiteCheckError(f"{label}: missing access portal gate")
    if "access-api-contract" not in release_gate_ids:
        raise SiteCheckError(f"{label}: missing access API contract gate")
    if "review-queue-contract" not in release_gate_ids:
        raise SiteCheckError(f"{label}: missing review queue contract gate")
    if access.get("holderBonusMinimum") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder bonus minimum")
    if access.get("holderBonusCreditAmount") != "100 GCA AI Quant Access credits":
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
    if not any("full GCA AI Quant Access trading or research product is live" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing product live boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_access_page(text: str) -> None:
    label = "/access.html"
    assert_contains(text, "GCA Access Portal", label)
    assert_contains(text, "Access References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_contains(text, "Access API", label)
    assert_contains(text, "Review Queue", label)
    assert_contains(text, "controlled account UI live", label)
    assert_contains(text, "Live at /gca/member-access/", label)
    assert_contains(text, "Connected to Workers + D1", label)
    assert_contains(text, "eligible credit/member ledger records", label)
    assert_contains(text, "10,000 GCA member benefit remains manual review only", label)
    assert_contains(text, "read-only wallet verification", label)
    assert_contains(text, "eth_call", label)
    assert_contains(text, "balanceOf", label)
    assert_contains(text, "10,000 GCA", label)
    assert_contains(text, "100 GCA AI Quant Access credits", label)
    assert_contains(text, "1,000,000 GCA", label)
    assert_contains(text, "30 consecutive days", label)
    assert_contains(text, "GCA Member", label)
    assert_contains(text, "credit ledger activation", label)
    assert_contains(text, "Live for eligible records", label)
    assert_contains(text, "member ledger activation", label)
    assert_contains(text, "support review queue", label)
    assert_contains(text, "Review Queue Contract", label)
    assert_contains(text, "Operations Runbook", label)
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
    assert_contains(text, "live account UI", label)
    assert_contains(text, "gca/member-access/", label)
    assert_contains(text, "review-queue.html", label)
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
    if payload.get("status") != "public-access-portal-live":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if state.get("currentStage") != "controlled-account-ui-live":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("blueprintOnly") is not False:
        raise SiteCheckError(f"{label}: blueprintOnly must be false")
    if state.get("reviewQueueContract") != "published-manual-review-contract":
        raise SiteCheckError(f"{label}: wrong reviewQueueContract")
    for key in (
        "controlledHttpsAccountUiLive",
        "directSubmissionEndpointConfigured",
        "creditsEligibilitySubmissionLive",
        "gcaMemberEligibilitySubmissionLive",
        "walletVerificationLive",
        "creditLedgerWritesLive",
        "memberLedgerWritesLive",
    ):
        if state.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    if state.get("liveTradingEnabled") is not False:
        raise SiteCheckError(f"{label}: liveTradingEnabled must be false")
    if state.get("memberBenefitAutomaticTransfer") is not False:
        raise SiteCheckError(f"{label}: memberBenefitAutomaticTransfer must be false")
    if state.get("memberBenefitManualReviewOnly") is not True:
        raise SiteCheckError(f"{label}: memberBenefitManualReviewOnly must be true")
    for key in ("memberAccess", "accessConfig", "walletVerifications", "creditLedger", "memberLedger", "supportReview"):
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
    if thresholds.get("holderBonus", {}).get("creditAmount") != "100 GCA AI Quant Access credits":
        raise SiteCheckError(f"{label}: wrong credit amount")
    if thresholds.get("holderBonus", {}).get("notLive") is not False:
        raise SiteCheckError(f"{label}: holder path must be live")
    if thresholds.get("gcaMember", {}).get("minimumHolding") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member minimum")
    if thresholds.get("gcaMember", {}).get("minimumHoldingPeriod") != "30 consecutive days":
        raise SiteCheckError(f"{label}: wrong member holding period")
    if thresholds.get("gcaMember", {}).get("memberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    if thresholds.get("gcaMember", {}).get("notLive") is not False:
        raise SiteCheckError(f"{label}: member path must be live")
    for item in (
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
    if "GCA has a live public access portal at https://gcagochina.com/gca/member-access/." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing access safe claim")
    if not any("automatic or self-service transferred" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing member benefit boundary")
    if not any("cash, income" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing credit value boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_operations_page(text: str) -> None:
    label = "/operations.html"
    assert_social_preview_meta(text, label, OPERATIONS_PAGE_URL)
    assert_contains(text, "GCA Access Operations Runbook", label)
    assert_contains(text, "Operations References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_contains(text, "account intake live / operations runbook only", label)
    assert_contains(text, "account intake live", label)
    assert_contains(text, "not a public ledger browser", label)
    assert_contains(text, "Email Registration Ops Pipeline", label)
    assert_contains(text, "Email API", label)
    assert_contains(text, "Live on Workers + D1", label)
    assert_contains(text, "ADMIN_READ_TOKEN", label)
    assert_contains(text, "tools/check_gca_registration_api.py", label)
    assert_contains(text, "tools/export_cloudflare_email_registrations.py", label)
    assert_contains(text, "tools/run_gca_registration_ops.py", label)
    assert_contains(text, ".gca_access_data/email_registrations.jsonl", label)
    assert_contains(text, ".gca_access_data/gca_email_contacts_public_redacted.csv", label)
    assert_contains(text, ".gca_access_data/gca_registration_ops_summary.json", label)
    assert_contains(text, "Member Access Ops Pipeline", label)
    assert_contains(text, "tools/run_gca_member_access_ops.py", label)
    assert_contains(text, ".gca_access_data/cloudflare_member_access_export.json", label)
    assert_contains(text, ".gca_access_data/member_access_report/gca_member_access_summary.json", label)
    assert_contains(text, ".gca_access_data/member_access_report/gca_member_support_queue.csv", label)
    assert_contains(text, ".gca_access_data/member_access_report/gca_holding_period_summary.json", label)
    assert_contains(text, "--include-holding-report --holding-no-live-read", label)
    assert_contains(text, "No Automatic Transfer", label)
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
    assert_contains(text, "100 GCA AI Quant Access credits", label)
    assert_contains(text, "GCA Member", label)
    assert_contains(text, "gca_member_preregistration_v2", label)
    assert_contains(text, "holdingStartDate", label)
    assert_contains(text, "evidenceTxHash", label)
    assert_contains(text, "evidenceTxHashFormatOk", label)
    assert_contains(text, "Member evidence note", label)
    assert_contains(text, "Local Review Package Handoff", label)
    assert_contains(text, "redacted-public", label)
    assert_contains(text, "must not be used as a contactable support queue", label)
    assert_contains(text, "Do not send user replies from", label)
    assert_contains(text, "packageDigestSha256", label)
    assert_contains(text, "tools/export_gca_review_package.py", label)
    assert_contains(text, "tools/verify_gca_review_package.py", label)
    assert_contains(text, "No Replies From Redacted Exports", label)
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
    if state.get("currentStage") != "account-ledger-operations-live":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("publicRunbookOnly") is not False:
        raise SiteCheckError(f"{label}: publicRunbookOnly must be false")
    if state.get("runbookOnlyForManualReviewHandling") is not True:
        raise SiteCheckError(f"{label}: runbookOnlyForManualReviewHandling must be true")
    if state.get("emailRegistrationBackendLive") is not True:
        raise SiteCheckError(f"{label}: emailRegistrationBackendLive must be true")
    if state.get("contactSuppressionBackendLive") is not True:
        raise SiteCheckError(f"{label}: contactSuppressionBackendLive must be true")
    for key in (
        "backendLive",
        "accountAndMemberBackendLive",
        "controlledHttpsAccountUiLive",
        "creditsEligibilitySubmissionLive",
        "gcaMemberEligibilitySubmissionLive",
        "ledgerWritesLive",
    ):
        if state.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    for key in (
        "liveTradingEnabled",
    ):
        if state.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if state.get("publicSubmissionQueueLive") is not True:
        raise SiteCheckError(f"{label}: publicSubmissionQueueLive must be true")
    if identity.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong identity chainId")
    if identity.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong identity contractAddress")
    email_ops = payload.get("emailRegistrationOpsPipeline", {})
    if email_ops.get("status") != "production-email-registration-api-live-operator-sync-ready":
        raise SiteCheckError(f"{label}: wrong email ops status")
    if email_ops.get("provider") != "Cloudflare Workers + D1":
        raise SiteCheckError(f"{label}: wrong email ops provider")
    if email_ops.get("workerBaseUrl") != "https://gca-registration-api.gcagochina.workers.dev":
        raise SiteCheckError(f"{label}: wrong worker base url")
    if email_ops.get("publicOnlyCheckCommand") != "python3 tools/check_gca_registration_api.py --public-only --timeout 30":
        raise SiteCheckError(f"{label}: wrong public-only check command")
    if email_ops.get("publicOnlyCheckRequiresSecrets") is not False:
        raise SiteCheckError(f"{label}: public-only check must not require secrets")
    if email_ops.get("adminTokenPrinted") is not False:
        raise SiteCheckError(f"{label}: admin token must not print")
    if "tools/export_cloudflare_email_registrations.py" not in email_ops.get("adminExportCommand", ""):
        raise SiteCheckError(f"{label}: missing admin export command")
    if "tools/sync_cloudflare_email_registrations.py" not in email_ops.get("registrationSyncCommand", ""):
        raise SiteCheckError(f"{label}: missing registration sync command")
    if "tools/sync_cloudflare_contact_suppressions.py" not in email_ops.get("contactSuppressionSyncCommand", ""):
        raise SiteCheckError(f"{label}: missing contact suppression sync command")
    if "tools/run_gca_registration_ops.py" not in email_ops.get("combinedOpsCommand", ""):
        raise SiteCheckError(f"{label}: missing combined ops command")
    if email_ops.get("localSyncedLedger") != ".gca_access_data/email_registrations.jsonl":
        raise SiteCheckError(f"{label}: wrong local synced ledger")
    if email_ops.get("internalContactCsv") != ".gca_access_data/gca_email_contacts.csv":
        raise SiteCheckError(f"{label}: wrong internal contact csv")
    if email_ops.get("publicRedactedContactCsv") != ".gca_access_data/gca_email_contacts_public_redacted.csv":
        raise SiteCheckError(f"{label}: wrong public redacted contact csv")
    if email_ops.get("summaryOutput") != ".gca_access_data/gca_registration_ops_summary.json":
        raise SiteCheckError(f"{label}: wrong ops summary")
    if email_ops.get("boundaries", {}).get("publicRedactedCsvRequiredBeforeExternalSharing") is not True:
        raise SiteCheckError(f"{label}: missing redacted CSV boundary")
    member_ops = payload.get("memberAccessOpsPipeline", {})
    if member_ops.get("status") != "token-protected-member-ops-ready":
        raise SiteCheckError(f"{label}: wrong member ops status")
    if member_ops.get("provider") != "Cloudflare Workers + D1":
        raise SiteCheckError(f"{label}: wrong member ops provider")
    if member_ops.get("workerBaseUrl") != "https://gca-registration-api.gcagochina.workers.dev":
        raise SiteCheckError(f"{label}: wrong member ops worker base")
    if member_ops.get("adminTokenFile") != "cloudflare/gca-registration-worker/.env.admin.local":
        raise SiteCheckError(f"{label}: wrong member ops token file")
    if member_ops.get("adminTokenEnvironmentVariable") != "ADMIN_READ_TOKEN":
        raise SiteCheckError(f"{label}: wrong member ops token variable")
    if "tools/run_gca_member_access_ops.py" not in member_ops.get("pipelineCommand", ""):
        raise SiteCheckError(f"{label}: missing member ops pipeline command")
    if "--include-holding-report --holding-no-live-read" not in member_ops.get("offlineHoldingReportCommand", ""):
        raise SiteCheckError(f"{label}: missing offline holding command")
    if "tools/run_gca_daily_ops.py --build-digest --update-public-status" not in member_ops.get("digestRefreshCommand", ""):
        raise SiteCheckError(f"{label}: missing digest refresh command")
    if member_ops.get("localExportJson") != ".gca_access_data/cloudflare_member_access_export.json":
        raise SiteCheckError(f"{label}: wrong member export output")
    if member_ops.get("supportQueueOutput") != ".gca_access_data/member_access_report/gca_member_support_queue.csv":
        raise SiteCheckError(f"{label}: wrong support queue output")
    if member_ops.get("holdingPeriodSummaryOutput") != ".gca_access_data/member_access_report/gca_holding_period_summary.json":
        raise SiteCheckError(f"{label}: wrong holding summary output")
    member_boundaries = member_ops.get("boundaries", {})
    for key in (
        "operatorOnly",
        "ignoredLocalOutputs",
        "holdingReportLiveReadOptional",
        "holdingNoLiveReadUsesExistingSnapshots",
    ):
        if member_boundaries.get(key) is not True:
            raise SiteCheckError(f"{label}: missing member ops boundary {key}")
    for key in (
        "writesProductionData",
        "adminTokenPrinted",
        "requiresSignature",
        "requiresTransaction",
        "automaticTokenTransfer",
        "memberBenefitTransferAutomatic",
    ):
        if member_boundaries.get(key) is not False:
            raise SiteCheckError(f"{label}: unsafe member ops boundary {key}")
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
    if controls.get("emailRegistrationOpsAdminTokenPrinted") is not False:
        raise SiteCheckError(f"{label}: email ops token must not print")
    if controls.get("emailRegistrationOpsPublicCheckRequiresSecrets") is not False:
        raise SiteCheckError(f"{label}: public email ops check must not require secrets")
    for key in (
        "externalReviewPackageMustBeRedacted",
        "reviewPackageDigestRequiredBeforeSharing",
        "publicRedactedExportForReviewerHandoffOnly",
    ):
        if controls.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    for key in (
        "requiresSignatureForBalanceRead",
        "requiresTransactionForBalanceRead",
        "manualSupportCanOverrideBalanceVerification",
        "manualSupportCanBypassReleaseGates",
        "fullLocalPackageExternalSharingAllowed",
        "redactedExportCanGenerateUserReplies",
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
    if rules.get("holderBonusCreditAmount") != "100 GCA AI Quant Access credits":
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
    if thresholds.get("holderBonusCreditAmount") != "100 GCA AI Quant Access credits":
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
    if "GCA email registration and unsubscribe APIs are live on Cloudflare Workers + D1." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing email API safe claim")
    if "GCA operators can sync email registration records into an ignored local JSONL ledger and export public-redacted contact CSVs." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing email ops safe claim")
    if "Public-redacted exports are for reviewer evidence handoff only and cannot be used as contactable user support queues." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing redacted export safe claim")
    if not any("private-data dropbox" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing private-data boundary")
    if not any("support can override wallet-balance verification" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing support override boundary")
    if not any("redacted local review package" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing review package boundary")
    if not any("contactable support queue" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing redacted support queue boundary")
    assert_current_pool_text(json.dumps(payload), label)
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_access_api_page(text: str) -> None:
    label = "/access-api.html"
    assert_contains(text, "GCA Access API Contract", label)
    assert_contains(text, "API References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_contains(text, "Review Queue", label)
    assert_contains(text, "Operations Runbook", label)
    assert_contains(text, "member access API live", label)
    assert_contains(text, "Email + member access live", label)
    assert_contains(text, "member access and wallet verification", label)
    assert_contains(text, "tools/gca_member_backend.py", label)
    assert_contains(text, "tools/export_gca_review_package.py", label)
    assert_contains(text, "operator.html", label)
    assert_contains(text, "/gca/operator-summary", label)
    assert_contains(text, "local JSONL ledger records", label)
    assert_contains(text, "Email Registration", label)
    assert_contains(text, "Cloudflare Workers + D1", label)
    assert_contains(text, "cloudflare/gca-registration-worker/", label)
    assert_contains(text, "https://gca-registration-api.gcagochina.workers.dev", label)
    assert_contains(text, "Token protected", label)
    assert_contains(text, "tools/export_cloudflare_email_registrations.py", label)
    assert_contains(text, "tools/check_gca_registration_api.py", label)
    assert_contains(text, ".github/workflows/check-gca-registration-api.yml", label)
    assert_contains(text, "API Status", label)
    assert_contains(text, "api-status.html", label)
    assert_contains(text, "tools/sync_cloudflare_email_registrations.py", label)
    assert_contains(text, "tools/export_gca_email_contacts.py", label)
    assert_contains(text, "tools/run_gca_registration_ops.py", label)
    assert_contains(text, "tools/suppress_gca_contact.py", label)
    assert_contains(text, "Contact Suppression API", label)
    assert_contains(text, "gca_contact_suppression_v1", label)
    assert_contains(text, "/gca/contact-suppressions", label)
    assert_contains(text, "tools/sync_cloudflare_contact_suppressions.py", label)
    assert_contains(text, "cloudflare/gca-registration-worker/migrations/0002_contact_suppressions.sql", label)
    assert_contains(text, "api.gcagochina.com pending zone access", label)
    assert_contains(text, "API Health", label)
    assert_contains(text, "POST", label)
    assert_contains(text, "/gca/email-registrations", label)
    assert_contains(text, "/gca/access-config", label)
    assert_contains(text, "/gca/member-access", label)
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
    assert_contains(text, "100 GCA AI Quant Access credits", label)
    assert_contains(text, "GCA Member", label)
    assert_contains(text, "gca_member_access_v1", label)
    assert_contains(text, "memberBenefitReviewEvidence", label)
    assert_contains(text, "holdingStartDate", label)
    assert_contains(text, "evidenceTxHash", label)
    assert_contains(text, "evidenceTxHashFormatOk", label)
    assert_contains(text, "controlled HTTPS origin", label)
    assert_contains(text, "public email registration and unsubscribe routes require only form acknowledgements", label)
    assert_contains(text, "token-protected admin reads for Cloudflare registration and suppression records", label)
    assert_contains(text, "token-protected admin reads for account-level ledger routes", label)
    assert_contains(text, "ADMIN_READ_TOKEN protected operator read", label)
    assert_contains(text, "CSRF protection", label)
    assert_contains(text, "website / company / homepage honeypot bot-trap fields", label)
    assert_contains(text, "rate limits", label)
    assert_contains(text, "structured audit logs", label)
    assert_contains(text, "Private key or seed phrase", label)
    assert_contains(text, "Exchange API secret", label)
    assert_contains(text, "Withdrawal permission", label)
    assert_contains(text, "Custody request", label)
    assert_contains(text, "review-queue.html", label)
    assert_contains(text, "operations.html", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, BASE_USDT_ADDRESS, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)


def validate_access_api_json(text: str) -> None:
    label = "/access-api.json"
    payload = load_json(text, label)
    state = payload.get("currentState", {})
    local_backend = payload.get("localDevelopmentBackend", {})
    production_email_backend = payload.get("productionEmailRegistrationBackend", {})
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
    if payload.get("status") != "public-access-api-member-access-live":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if state.get("currentStage") != "member-access-api-live":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("contractOnly") is not False:
        raise SiteCheckError(f"{label}: contractOnly must be false")
    if state.get("reviewQueueContract") != "published-manual-review-contract":
        raise SiteCheckError(f"{label}: wrong reviewQueueContract")
    if state.get("memberPacketVersion") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong member packet version")
    if state.get("emailRegistrationPacketVersion") != "gca_email_registration_v1":
        raise SiteCheckError(f"{label}: wrong email registration packet version")
    if state.get("contactSuppressionPacketVersion") != "gca_contact_suppression_v1":
        raise SiteCheckError(f"{label}: wrong contact suppression packet version")
    if state.get("localDevelopmentBackendAvailable") is not True:
        raise SiteCheckError(f"{label}: local development backend should be available")
    for key in (
        "controlledHttpsAccountUiLive",
        "creditsEligibilitySubmissionLive",
        "gcaMemberEligibilitySubmissionLive",
        "walletVerificationLive",
        "creditLedgerWritesLive",
        "memberLedgerWritesLive",
    ):
        if state.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    if state.get("liveTradingEnabled") is not False:
        raise SiteCheckError(f"{label}: liveTradingEnabled must be false")
    for key in (
        "backendLive",
        "publicEndpointLive",
        "directSubmissionEndpointConfigured",
        "productionEmailRegistrationApiLive",
    ):
        if state.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
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
    if local_backend.get("localEmailRegistrationUrl") != "http://127.0.0.1:8787/register.html":
        raise SiteCheckError(f"{label}: wrong local email registration URL")
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
        raise SiteCheckError(f"{label}: local backend must not mark itself as production")
    if local_backend.get("automaticTokenTransfer") is not False:
        raise SiteCheckError(f"{label}: local backend must not automatically transfer tokens")
    if state.get("productionEmailRegistrationApiPrepared") is not True:
        raise SiteCheckError(f"{label}: production email API should be prepared")
    if production_email_backend.get("provider") != "Cloudflare Workers + D1":
        raise SiteCheckError(f"{label}: wrong production email backend provider")
    if production_email_backend.get("sourceDirectory") != "cloudflare/gca-registration-worker/":
        raise SiteCheckError(f"{label}: wrong production email backend source directory")
    if production_email_backend.get("submissionEndpoint") != "https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations":
        raise SiteCheckError(f"{label}: wrong production email submission endpoint")
    if production_email_backend.get("adminReadEndpoint") != "https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations":
        raise SiteCheckError(f"{label}: wrong production email admin read endpoint")
    if production_email_backend.get("adminExportTool") != "tools/export_cloudflare_email_registrations.py":
        raise SiteCheckError(f"{label}: wrong admin export tool")
    if production_email_backend.get("adminSyncTool") != "tools/sync_cloudflare_email_registrations.py":
        raise SiteCheckError(f"{label}: wrong admin sync tool")
    if production_email_backend.get("readOnlyApiCheckTool") != "tools/check_gca_registration_api.py":
        raise SiteCheckError(f"{label}: wrong read-only API check tool")
    if production_email_backend.get("publicOnlyApiCheckWorkflow") != ".github/workflows/check-gca-registration-api.yml":
        raise SiteCheckError(f"{label}: wrong public API check workflow")
    if production_email_backend.get("publicOnlyApiCheckRequiresSecrets") is not False:
        raise SiteCheckError(f"{label}: public API check workflow must not require secrets")
    if production_email_backend.get("contactCsvExportTool") != "tools/export_gca_email_contacts.py":
        raise SiteCheckError(f"{label}: wrong contact CSV export tool")
    if production_email_backend.get("registrationOpsTool") != "tools/run_gca_registration_ops.py":
        raise SiteCheckError(f"{label}: wrong registration ops tool")
    if production_email_backend.get("contactSuppressionTool") != "tools/suppress_gca_contact.py":
        raise SiteCheckError(f"{label}: wrong contact suppression tool")
    if production_email_backend.get("contactSuppressionMigration") != "cloudflare/gca-registration-worker/migrations/0002_contact_suppressions.sql":
        raise SiteCheckError(f"{label}: wrong contact suppression migration")
    if production_email_backend.get("contactSuppressionEndpoint") != "https://gca-registration-api.gcagochina.workers.dev/gca/contact-suppressions":
        raise SiteCheckError(f"{label}: wrong contact suppression endpoint")
    if production_email_backend.get("adminContactSuppressionReadEndpoint") != "https://gca-registration-api.gcagochina.workers.dev/gca/contact-suppressions":
        raise SiteCheckError(f"{label}: wrong admin contact suppression read endpoint")
    if production_email_backend.get("contactSuppressionSyncTool") != "tools/sync_cloudflare_contact_suppressions.py":
        raise SiteCheckError(f"{label}: wrong contact suppression sync tool")
    if production_email_backend.get("defaultAdminExportOutput") != ".gca_access_data/cloudflare_email_registrations_export.json":
        raise SiteCheckError(f"{label}: wrong default admin export output")
    if production_email_backend.get("publicRedactedAdminExportOutput") != ".gca_access_data/cloudflare_email_registrations_public_redacted.json":
        raise SiteCheckError(f"{label}: wrong public redacted admin export output")
    if production_email_backend.get("localSyncedLedger") != ".gca_access_data/email_registrations.jsonl":
        raise SiteCheckError(f"{label}: wrong local synced ledger")
    if production_email_backend.get("localContactCsvOutput") != ".gca_access_data/gca_email_contacts.csv":
        raise SiteCheckError(f"{label}: wrong local contact CSV output")
    if production_email_backend.get("publicRedactedContactCsvOutput") != ".gca_access_data/gca_email_contacts_public_redacted.csv":
        raise SiteCheckError(f"{label}: wrong public redacted contact CSV output")
    if production_email_backend.get("registrationOpsSummaryOutput") != ".gca_access_data/gca_registration_ops_summary.json":
        raise SiteCheckError(f"{label}: wrong registration ops summary output")
    if production_email_backend.get("contactSuppressionFile") != ".gca_access_data/gca_contact_suppressions.jsonl":
        raise SiteCheckError(f"{label}: wrong contact suppression file")
    if production_email_backend.get("adminReadTokenConfigured") is not True:
        raise SiteCheckError(f"{label}: admin read token should be configured")
    if production_email_backend.get("privacyHashSaltConfigured") is not True:
        raise SiteCheckError(f"{label}: privacy hash salt should be configured")
    if production_email_backend.get("requiresCloudflareAccountDeployment") is not False:
        raise SiteCheckError(f"{label}: Cloudflare deployment should be complete")
    if production_email_backend.get("requiresAdminReadTokenSecret") is not False:
        raise SiteCheckError(f"{label}: admin read token secret should already be configured")
    if production_email_backend.get("futureCustomDomain") != "https://api.gcagochina.com":
        raise SiteCheckError(f"{label}: wrong future custom domain")
    if production_email_backend.get("customDomainExampleConfig") != "cloudflare/gca-registration-worker/wrangler.custom-domain.example.toml":
        raise SiteCheckError(f"{label}: wrong custom domain example config")
    if production_email_backend.get("publicWebsiteFallback") != "official-email-fallback":
        raise SiteCheckError(f"{label}: wrong public website fallback")
    if set(production_email_backend.get("antiSpamHoneypotFields", [])) != {"website", "company", "homepage"}:
        raise SiteCheckError(f"{label}: wrong anti-spam honeypot fields")
    for ledger in ("email_registrations", "pre_registrations", "wallet_verifications", "credit_ledger", "member_ledger", "member_benefit_transfers", "support_reviews"):
        if ledger not in local_backend.get("writesJsonlLedgers", []):
            raise SiteCheckError(f"{label}: missing local ledger {ledger}")
    for key in (
        "controlledHttpsOriginRequired",
        "authenticatedAccountSessionRequired",
        "csrfProtectionRequiredForStateChangingRoutes",
        "honeypotBotTrapFieldsEnabled",
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
    expected_live_member_statuses = {
        "GET /gca/access-config": "production-workers-dev-live",
        "POST /gca/member-access": "production-workers-dev-live",
        "POST /gca/wallet-verifications": "production-workers-dev-live",
        "GET /gca/credit-ledger": "token-protected-admin-live",
        "GET /gca/member-ledger": "token-protected-admin-live",
    }
    for endpoint_key, expected_status in expected_live_member_statuses.items():
        endpoint = endpoint_map.get(endpoint_key)
        if endpoint is None:
            raise SiteCheckError(f"{label}: missing endpoint {endpoint_key}")
        if endpoint.get("status") != expected_status:
            raise SiteCheckError(f"{label}: endpoint {endpoint_key} should be {expected_status}")
    for endpoint_key in ("POST /gca/support-review", "GET /gca/member-review"):
        endpoint = endpoint_map.get(endpoint_key)
        if endpoint is None:
            raise SiteCheckError(f"{label}: missing endpoint {endpoint_key}")
        if endpoint.get("status") != "planned-not-live":
            raise SiteCheckError(f"{label}: endpoint {endpoint_key} should be planned-not-live")
    expected_email_statuses = {
        "POST /gca/email-registrations": "production-workers-dev-live",
        "GET /gca/email-registrations": "token-protected-admin-live",
    }
    for endpoint_key, expected_status in expected_email_statuses.items():
        endpoint = endpoint_map.get(endpoint_key)
        if endpoint is None:
            raise SiteCheckError(f"{label}: missing endpoint {endpoint_key}")
        if endpoint.get("status") != expected_status:
            raise SiteCheckError(f"{label}: endpoint {endpoint_key} should be {expected_status}")
    expected_contact_statuses = {
        "POST /gca/contact-suppressions": "production-workers-dev-live",
        "GET /gca/contact-suppressions": "token-protected-admin-live",
    }
    for endpoint_key, expected_status in expected_contact_statuses.items():
        endpoint = endpoint_map.get(endpoint_key)
        if endpoint is None:
            raise SiteCheckError(f"{label}: missing endpoint {endpoint_key}")
        if endpoint.get("status") != expected_status:
            raise SiteCheckError(f"{label}: endpoint {endpoint_key} should be {expected_status}")
    email_registration = endpoint_map["POST /gca/email-registrations"]
    for field in ("email", "acknowledgements.emailContactConsent", "acknowledgements.noSecretsNoCustody"):
        if field not in email_registration.get("requiredRequestFields", []):
            raise SiteCheckError(f"{label}: missing email registration request field {field}")
    for expected_check in (
        "email must be valid and normalized",
        "no wallet address is required",
        "website/company/homepage honeypot fields must be empty",
        "no credits, GCA Member status, or token transfer is automatically activated",
    ):
        if expected_check not in email_registration.get("serverChecks", []):
            raise SiteCheckError(f"{label}: missing email registration check {expected_check}")
    if "automaticTokenTransfer" not in email_registration.get("responseFields", []):
        raise SiteCheckError(f"{label}: missing email registration token transfer boundary")
    email_registration_read = endpoint_map["GET /gca/email-registrations"]
    if "authorization bearer token" not in email_registration_read.get("requiredRequestFields", []):
        raise SiteCheckError(f"{label}: missing email registration read auth field")
    if "limit" not in email_registration_read.get("optionalRequestFields", []):
        raise SiteCheckError(f"{label}: missing email registration read limit")
    if "received" not in email_registration_read.get("allowedStatuses", []):
        raise SiteCheckError(f"{label}: missing email registration read status")
    contact_suppression = endpoint_map["POST /gca/contact-suppressions"]
    for field in ("email", "acknowledgements.contactSuppressionRequested", "acknowledgements.noSecretsNoCustody"):
        if field not in contact_suppression.get("requiredRequestFields", []):
            raise SiteCheckError(f"{label}: missing contact suppression request field {field}")
    for expected_check in (
        "email must be valid and normalized",
        "suppression is idempotent by suppressionId",
        "website/company/homepage honeypot fields must be empty",
        "no wallet address is required",
        "no credits, GCA Member status, or token transfer is changed",
    ):
        if expected_check not in contact_suppression.get("serverChecks", []):
            raise SiteCheckError(f"{label}: missing contact suppression check {expected_check}")
    for expected_field in ("suppressionId", "emailSha256", "contactSuppressed", "automaticTokenTransfer"):
        if expected_field not in contact_suppression.get("responseFields", []):
            raise SiteCheckError(f"{label}: missing contact suppression response field {expected_field}")
    if "suppressed" not in contact_suppression.get("allowedStatuses", []):
        raise SiteCheckError(f"{label}: missing contact suppression status")
    contact_suppression_read = endpoint_map["GET /gca/contact-suppressions"]
    if "authorization bearer token" not in contact_suppression_read.get("requiredRequestFields", []):
        raise SiteCheckError(f"{label}: missing contact suppression read auth field")
    if "limit" not in contact_suppression_read.get("optionalRequestFields", []):
        raise SiteCheckError(f"{label}: missing contact suppression read limit")
    if "records" not in contact_suppression_read.get("responseFields", []):
        raise SiteCheckError(f"{label}: missing contact suppression read records field")
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
    if "website/company/homepage honeypot fields must be empty" not in wallet.get("serverChecks", []):
        raise SiteCheckError(f"{label}: missing wallet honeypot check")
    if payload.get("memberPacketVersion") != "gca_member_preregistration_v2":
        raise SiteCheckError(f"{label}: wrong top-level member packet version")
    if payload.get("emailRegistrationPacketVersion") != "gca_email_registration_v1":
        raise SiteCheckError(f"{label}: wrong top-level email registration packet version")
    if payload.get("contactSuppressionPacketVersion") != "gca_contact_suppression_v1":
        raise SiteCheckError(f"{label}: wrong top-level contact suppression packet version")
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
    member_access = endpoint_map["POST /gca/member-access"]
    for field in (
        "displayName",
        "holdingStartDate",
        "evidenceTxHash",
        "memberBenefitReviewEvidence",
    ):
        if field not in member_access.get("optionalRequestFields", []):
            raise SiteCheckError(f"{label}: missing member access optional field {field}")
    for field in (
        "email",
        "walletAddress",
        "acknowledgements.emailContactConsent",
        "acknowledgements.noSecretsNoCustody",
        "acknowledgements.termsAccepted",
    ):
        if field not in member_access.get("requiredRequestFields", []):
            raise SiteCheckError(f"{label}: missing member access request field {field}")
    if "website/company/homepage honeypot fields must be empty" not in member_access.get("serverChecks", []):
        raise SiteCheckError(f"{label}: missing member access honeypot check")
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
    if thresholds.get("holderBonusCreditAmount") != "100 GCA AI Quant Access credits":
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
    if "GCA has a live public access API for email registration, contact suppression, access config, member access, and read-only wallet verification." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing API safe claim")
    if not any("automatic or self-service transferred" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing member benefit boundary")
    if not any("private keys, seed phrases" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing sensitive data boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_api_status_page(text: str) -> None:
    label = "/api-status.html"
    assert_social_preview_meta(text, label, API_STATUS_PAGE_URL)
    assert_contains(text, "API Status References", label)
    assert_no_public_data_room_terms(text, label)
    for expected in (
        "GCA Registration API Status",
        "Registration API Status / 2026-06-07",
        "2026-06-07T13:06:12Z",
        "Cloudflare Workers + D1",
        "https://gca-registration-api.gcagochina.workers.dev",
        "Public Check",
        "Live / no secrets",
        "Latest Check",
        "2026-06-07 passed",
        "Admin Read",
        "Token protected",
        "api.gcagochina.com pending zone access",
        "tools/check_gca_registration_api.py",
        "check-gca-registration-api.yml",
        "GET",
        "/health",
        "POST",
        "/gca/email-registrations",
        "gca_email_registration_v1",
        "/gca/contact-suppressions",
        "gca_contact_suppression_v1",
        "/gca/access-config",
        "/gca/wallet-verifications",
        "/gca/member-access",
        "/gca/credit-ledger",
        "/gca/member-ledger",
        "Public visitors should receive an authorization error",
        "Public visitors cannot read the suppression ledger",
        "python3 tools/check_gca_registration_api.py --public-only --timeout 30",
        "python3 tools/check_gca_registration_api.py --token-file cloudflare/gca-registration-worker/.env.admin.local --limit 5",
        "tools/export_cloudflare_email_registrations.py",
        "tools/sync_cloudflare_email_registrations.py",
        "tools/export_gca_email_contacts.py",
        "tools/sync_cloudflare_contact_suppressions.py",
        "tools/run_gca_registration_ops.py",
        "Email registration does not require a wallet, wallet signature, payment, private key, seed phrase, exchange API secret, or withdrawal permission",
        "Contact suppression does not change GCA balances, pool state, credits, member status, or on-chain assets",
        "Public visitors cannot read the registration ledger or suppression ledger",
        "100 credits and GCA Member ledger records are live for eligible wallet submissions",
        "10,000 GCA member benefit remains manual review",
        "Daily Status Snapshot",
        "Access API Contract",
        "Operations Runbook",
        "Operator Console",
        "Privacy Notice",
    ):
        assert_contains(text, expected, label)
    assert_no_forbidden_public_claims(text, label)


def validate_api_status_json(text: str) -> None:
    label = "/api-status.json"
    payload = load_json(text, label)
    public_endpoints = {item.get("id"): item for item in payload.get("publicEndpoints", [])}
    admin_endpoints = {item.get("id"): item for item in payload.get("adminEndpoints", [])}
    checks = payload.get("checks", {})
    boundaries = payload.get("publicBoundaries", {})
    links = payload.get("officialLinks", {})

    if payload.get("schema") != API_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != API_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-member-access-api-status-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("latestPublicCheckAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong latest public check timestamp")
    if payload.get("latestPublicCheckStatus") != "passed":
        raise SiteCheckError(f"{label}: wrong latest public check status")
    if payload.get("latestDailyStatusSnapshot") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong latest daily status snapshot")
    if payload.get("apiBaseUrl") != "https://gca-registration-api.gcagochina.workers.dev":
        raise SiteCheckError(f"{label}: wrong API base URL")
    if payload.get("futureCustomDomain") != "https://api.gcagochina.com":
        raise SiteCheckError(f"{label}: wrong future custom domain")
    if payload.get("futureCustomDomainStatus") != "pending-cloudflare-zone-access":
        raise SiteCheckError(f"{label}: wrong future custom domain status")
    if payload.get("provider") != "Cloudflare Workers + D1":
        raise SiteCheckError(f"{label}: wrong provider")
    if payload.get("sourceDirectory") != "cloudflare/gca-registration-worker/":
        raise SiteCheckError(f"{label}: wrong source directory")
    if payload.get("workerMain") != "cloudflare/gca-registration-worker/src/worker.mjs":
        raise SiteCheckError(f"{label}: wrong worker main")
    health = payload.get("healthEndpoint", {})
    if health.get("url") != "https://gca-registration-api.gcagochina.workers.dev/health":
        raise SiteCheckError(f"{label}: wrong health endpoint")
    if health.get("expectedService") != "gca-registration-api":
        raise SiteCheckError(f"{label}: wrong expected service")
    if health.get("public") is not True or health.get("requiresSecret") is not False:
        raise SiteCheckError(f"{label}: wrong health endpoint public boundary")

    expected_public = {
        "email-registration-create": ("POST", "/gca/email-registrations", "gca_email_registration_v1"),
        "contact-suppression-create": ("POST", "/gca/contact-suppressions", "gca_contact_suppression_v1"),
        "wallet-verification-create": ("POST", "/gca/wallet-verifications", "gca_wallet_verification_v1"),
        "member-access-create": ("POST", "/gca/member-access", "gca_member_access_v1"),
    }
    for endpoint_id, (method, path, packet_version) in expected_public.items():
        endpoint = public_endpoints.get(endpoint_id)
        if endpoint is None:
            raise SiteCheckError(f"{label}: missing public endpoint {endpoint_id}")
        if endpoint.get("method") != method or endpoint.get("path") != path:
            raise SiteCheckError(f"{label}: wrong public endpoint route {endpoint_id}")
        if endpoint.get("status") != "live":
            raise SiteCheckError(f"{label}: public endpoint {endpoint_id} should be live")
        if endpoint.get("packetVersion") != packet_version:
            raise SiteCheckError(f"{label}: wrong packet version for {endpoint_id}")
        for key in ("requiresWallet", "requiresSignature", "requiresTransaction", "automaticTokenTransfer"):
            if key == "requiresWallet" and endpoint_id in {"wallet-verification-create", "member-access-create"}:
                if endpoint.get(key) is not True:
                    raise SiteCheckError(f"{label}: {endpoint_id} {key} must be true")
                continue
            if endpoint.get(key) is not False:
                raise SiteCheckError(f"{label}: {endpoint_id} {key} must be false")
    access_config = public_endpoints.get("access-config-read")
    if access_config is None:
        raise SiteCheckError(f"{label}: missing public access config endpoint")
    if access_config.get("method") != "GET" or access_config.get("path") != "/gca/access-config":
        raise SiteCheckError(f"{label}: wrong access config route")
    if access_config.get("status") != "live":
        raise SiteCheckError(f"{label}: access config should be live")

    expected_admin = {
        "email-registration-read": "/gca/email-registrations",
        "contact-suppression-read": "/gca/contact-suppressions",
        "wallet-verification-read": "/gca/wallet-verifications",
        "member-access-read": "/gca/member-access",
        "credit-ledger-read": "/gca/credit-ledger",
        "member-ledger-read": "/gca/member-ledger",
    }
    for endpoint_id, path in expected_admin.items():
        endpoint = admin_endpoints.get(endpoint_id)
        if endpoint is None:
            raise SiteCheckError(f"{label}: missing admin endpoint {endpoint_id}")
        if endpoint.get("method") != "GET" or endpoint.get("path") != path:
            raise SiteCheckError(f"{label}: wrong admin endpoint route {endpoint_id}")
        if endpoint.get("status") != "live-token-protected":
            raise SiteCheckError(f"{label}: wrong admin endpoint status {endpoint_id}")
        if endpoint.get("requiresAdminReadToken") is not True:
            raise SiteCheckError(f"{label}: admin endpoint should require token {endpoint_id}")
        if endpoint.get("publicLedgerReadable") is not False:
            raise SiteCheckError(f"{label}: admin endpoint ledger must not be public {endpoint_id}")

    if checks.get("tool") != "tools/check_gca_registration_api.py":
        raise SiteCheckError(f"{label}: wrong check tool")
    if checks.get("publicOnlyCommand") != "python3 tools/check_gca_registration_api.py --public-only --timeout 30":
        raise SiteCheckError(f"{label}: wrong public check command")
    if checks.get("adminCommand") != "python3 tools/check_gca_registration_api.py --token-file cloudflare/gca-registration-worker/.env.admin.local --limit 5":
        raise SiteCheckError(f"{label}: wrong admin check command")
    if checks.get("publicOnlyWorkflow") != ".github/workflows/check-gca-registration-api.yml":
        raise SiteCheckError(f"{label}: wrong public workflow")
    if checks.get("publicOnlyWorkflowRequiresSecrets") is not False:
        raise SiteCheckError(f"{label}: public workflow should not require secrets")
    if checks.get("adminCheckRequiresLocalTokenFile") is not True:
        raise SiteCheckError(f"{label}: admin check should require local token file")
    if checks.get("writesTestRecords") is not False or checks.get("readOnly") is not True:
        raise SiteCheckError(f"{label}: checks should be read-only")

    for key in (
        "noPrivateKeyCollection",
        "noSeedPhraseCollection",
        "noExchangeApiSecretCollection",
        "noWithdrawalPermission",
        "noWalletSignatureForEmailRegistration",
        "noPaymentForEmailRegistration",
        "noPublicLedgerRead",
        "noWalletSignatureForWalletVerification",
        "noTransactionForWalletVerification",
        "memberAccessWritesEligibleLedgers",
        "noAutomaticTokenTransfer",
        "memberBenefitManualReviewOnly",
    ):
        if boundaries.get(key) is not True:
            raise SiteCheckError(f"{label}: missing boundary {key}")
    for key in ("noSelfServiceCreditsActivation", "noSelfServiceMemberActivation"):
        if boundaries.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} should be false after ledger path launch")
    if links.get("registrationPage") != REGISTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong registration page")
    if links.get("unsubscribePage") != UNSUBSCRIBE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong unsubscribe page")
    if links.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong access API page")
    if links.get("dataRoom") != DATA_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong data room")
    if links.get("githubWorkflow") != "https://github.com/timchen078/gca_token/actions/workflows/check-gca-registration-api.yml":
        raise SiteCheckError(f"{label}: wrong GitHub workflow URL")
    if links.get("memberAccessPage") != MEMBER_ACCESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong member access page")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_daily_status_page(text: str) -> None:
    label = "/daily-status.html"
    assert_social_preview_meta(text, label, DAILY_STATUS_PAGE_URL)
    for expected in (
        "GCA Daily Status Snapshot",
        "public-site",
        "registration-api-public",
        "basescan-resubmission-preflight-status",
        "readyForBaseScanResubmission",
        "Ready for owner resubmission",
        "BaseScan Ready For Owner Submission",
        "Old Email Files",
        "files publishing the old Outlook email",
        "Old-email queue",
        "Missing target-email queue",
        "support@gcagochina.com",
        "does not write production data",
        "submit BaseScan forms",
        "Site Map",
        "API status",
        "domain email pages",
    ):
        assert_contains(text, expected, label)
    if not re.search(r"Daily Ops Snapshot / \d{4}-\d{2}-\d{2}", text):
        raise SiteCheckError(f"{label}: missing current daily ops snapshot date")
    assert_no_public_data_room_terms(text, label)
    assert_not_contains(text, 'href="daily-status.json"', label)
    assert_no_forbidden_public_claims(text, label)


def validate_daily_status_json(text: str) -> None:
    label = "/daily-status.json"
    payload = load_json(text, label)
    public_site = payload.get("publicSite", {})
    registration_api = payload.get("registrationApi", {})
    basescan = payload.get("baseScanPreflight", {})
    daily_ops = payload.get("dailyOps", {})
    boundaries = payload.get("boundaries", {})
    links = payload.get("links", {})

    if payload.get("schema") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "daily-public-ops-snapshot-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("project") != "GCA":
        raise SiteCheckError(f"{label}: wrong project")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contract address")
    if daily_ops.get("packetVersion") != "gca_daily_ops_summary_v1":
        raise SiteCheckError(f"{label}: wrong daily ops packet version")
    if daily_ops.get("ok") is not True:
        raise SiteCheckError(f"{label}: daily ops should be ok")
    if daily_ops.get("generatedAt") != payload.get("snapshotGeneratedAt"):
        raise SiteCheckError(f"{label}: daily ops generatedAt should match snapshotGeneratedAt")
    if daily_ops.get("publicOnlyByDefault") is not True:
        raise SiteCheckError(f"{label}: daily ops should be public-only by default")
    daily_steps = {item.get("id"): item for item in daily_ops.get("steps", []) if isinstance(item, dict)}
    for step_id in ("public-site", "registration-api-public", "basescan-resubmission-preflight-status"):
        step = daily_steps.get(step_id)
        if step is None:
            raise SiteCheckError(f"{label}: missing daily ops step {step_id}")
        if step.get("ok") is not True or step.get("status") != "passed":
            raise SiteCheckError(f"{label}: daily ops step should have passed {step_id}")
        command = str(step.get("command") or "")
        if "/Users/" in command or ".venv/bin/python" in command:
            raise SiteCheckError(f"{label}: daily ops command leaks local path {step_id}")
    if daily_steps["basescan-resubmission-preflight-status"].get("blocksSummaryOk") is not False:
        raise SiteCheckError(f"{label}: BaseScan daily ops step should remain non-blocking")
    if public_site.get("status") != "ok":
        raise SiteCheckError(f"{label}: public site check should be ok")
    if public_site.get("baseUrl") != DEFAULT_BASE_URL:
        raise SiteCheckError(f"{label}: wrong public site base URL")
    if registration_api.get("status") != "ok":
        raise SiteCheckError(f"{label}: registration API check should be ok")
    if registration_api.get("apiBaseUrl") != "https://gca-registration-api.gcagochina.workers.dev":
        raise SiteCheckError(f"{label}: wrong registration API base URL")
    if registration_api.get("publicOnly") is not True:
        raise SiteCheckError(f"{label}: registration API should be public-only")
    if registration_api.get("writesTestRecords") is not False:
        raise SiteCheckError(f"{label}: registration API check should not write test records")
    if basescan.get("status") != "ready-for-owner-resubmission":
        raise SiteCheckError(f"{label}: wrong BaseScan preflight status")
    if basescan.get("readyForBaseScanResubmission") is not True:
        raise SiteCheckError(f"{label}: BaseScan ready flag should be true")
    if basescan.get("publicEmailSwitchStatus") != "public-email-switch-complete":
        raise SiteCheckError(f"{label}: wrong public email switch status")
    if basescan.get("snapshotAlignmentStatus") != "aligned":
        raise SiteCheckError(f"{label}: wrong snapshot alignment status")
    if basescan.get("filesStillUsingOldEmail") != 0:
        raise SiteCheckError(f"{label}: wrong old-email file count")
    if basescan.get("oldEmailFilePaths") != []:
        raise SiteCheckError(f"{label}: old-email queue path should be empty")
    if not isinstance(basescan.get("missingTargetEmailFilePaths"), list):
        raise SiteCheckError(f"{label}: missing target-email queue should be a list")
    action_queue = payload.get("ownerActionQueue", [])
    if not isinstance(action_queue, list) or len(action_queue) < 3:
        raise SiteCheckError(f"{label}: missing owner action queue")
    action_ids = {item.get("id") for item in action_queue if isinstance(item, dict)}
    for action_id in (
        "maintain-domain-mailbox",
        "retain-domain-email-evidence",
        "final-basescan-preflight",
    ):
        if action_id not in action_ids:
            raise SiteCheckError(f"{label}: missing owner action {action_id}")
    if basescan.get("targetDomainEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong target domain email")
    if basescan.get("currentPublicEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong current public email")
    missing = set(basescan.get("missingOrBlockedRequirements", []))
    if missing:
        raise SiteCheckError(f"{label}: BaseScan blockers should be empty")
    for key in (
        "publicOnly",
        "adminTokenPrinted",
        "userEmailsPrinted",
        "writesProductionData",
        "submitsBaseScanRequest",
        "sendsEmail",
        "writesDns",
        "requiresSignature",
        "requiresTransaction",
        "touchesWalletsOrContracts",
    ):
        expected = True if key == "publicOnly" else False
        if boundaries.get(key) is not expected:
            raise SiteCheckError(f"{label}: wrong boundary {key}")
    if links.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong daily status page link")
    if links.get("apiStatusPage") != API_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong API status page link")
    if links.get("baseScanPreflightPage") != BASESCAN_PREFLIGHT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong BaseScan preflight page link")
    if links.get("domainEmailPage") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domain email page link")
    if links.get("dataRoom") != DATA_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong data room link")
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_review_queue_page(text: str) -> None:
    label = "/review-queue.html"
    assert_contains(text, "GCA Review Queue Contract", label)
    assert_contains(text, "Review Queue References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_contains(text, "Operations Runbook", label)
    assert_contains(text, "manual review contract", label)
    assert_contains(text, "account intake live", label)
    assert_contains(text, "not a public ledger browser", label)
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
    assert_contains(text, "100 GCA AI Quant Access credits", label)
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
    assert_contains(text, "operations.html", label)
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
        "controlledHttpsAccountUiLive",
        "creditsEligibilitySubmissionLive",
        "gcaMemberEligibilitySubmissionLive",
        "ledgerWritesLive",
        "creditLedgerRecordCreationLive",
        "memberLedgerRecordCreationLive",
        "manualReviewRequired",
    ):
        if state.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    for key in (
        "publicQueueLive",
        "publicSubmissionQueueLive",
        "memberBenefitSelfServiceClaimable",
        "memberBenefitAutomaticTransfer",
        "liveTradingEnabled",
    ):
        if state.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if "member-benefit transfer remains manual" not in state.get("publicClaimBoundary", ""):
        raise SiteCheckError(f"{label}: missing public claim boundary")
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
    if thresholds.get("holderBonusCreditAmount") != "100 GCA AI Quant Access credits":
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
    assert_contains(text, "Credit And Access References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_contains(text, "Access Portal", label)
    assert_contains(text, "Access API", label)
    assert_contains(text, "account ledger path live", label)
    assert_contains(text, "eligible ledger record live", label)
    assert_contains(text, "100 GCA AI Quant Access credits", label)
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
    assert_contains(text, "credit ledger record live for eligible holders", label)
    assert_contains(text, "member ledger record live for eligible holders", label)
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
    if payload.get("status") != "public-credits-catalog-ledger-path-live":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if state.get("currentStage") != "account-ledger-path-live":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("draftServiceCatalogOnly") is not False:
        raise SiteCheckError(f"{label}: draftServiceCatalogOnly must be false")
    for key in ("publicAccountUiLive", "creditsEligibilitySubmissionLive", "gcaMemberEligibilitySubmissionLive", "controlledHttpsAccountUiLive", "walletVerificationLive", "creditLedgerWritesLive", "memberLedgerWritesLive"):
        if state.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    if state.get("liveTradingEnabled") is not False:
        raise SiteCheckError(f"{label}: liveTradingEnabled must be false")
    if holder_bonus.get("minimumHolding") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder bonus minimum")
    if holder_bonus.get("creditAmount") != "100 GCA AI Quant Access credits":
        raise SiteCheckError(f"{label}: wrong holder bonus credit")
    if holder_bonus.get("notLive") is not False:
        raise SiteCheckError(f"{label}: holder bonus must be live")
    if member.get("minimumHolding") != "1000000 GCA":
        raise SiteCheckError(f"{label}: wrong member minimum")
    if member.get("minimumHoldingPeriod") != "30 consecutive days":
        raise SiteCheckError(f"{label}: wrong member holding period")
    if member.get("memberBenefitAmount") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong member benefit")
    if member.get("notLive") is not False:
        raise SiteCheckError(f"{label}: member must be live")
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
        if item.get("status") not in {"ledger-eligible-service-unit-staged", "member-ledger-eligible-service-unit-staged", "member-ledger-eligible-service-workflow-staged"}:
            raise SiteCheckError(f"{label}: wrong service status for {item.get('id')}")
        if item.get("unitType") not in {"draft service credit unit", "draft member credit unit", "member workflow priority"}:
            raise SiteCheckError(f"{label}: wrong unitType for {item.get('id')}")
    for key in (
        "accountLevelOnly",
        "requiresSupportReview",
    ):
        if redemption.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    if redemption.get("requiresControlledAccountUi") is not False:
        raise SiteCheckError(f"{label}: requiresControlledAccountUi should be false after account UI launch")
    if redemption.get("requiresLedgerActivation") is not False:
        raise SiteCheckError(f"{label}: requiresLedgerActivation should be false after ledger path launch")
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
    for item in ("eligible account record", "read-only GCA balance verification", "credit ledger record", "support/product review before service delivery"):
        if item not in release_gates.get("requiredBeforeCreditUse", []):
            raise SiteCheckError(f"{label}: missing credit gate {item}")
    for item in ("eligible account record", "read-only GCA balance verification", "member ledger record", "support review queue"):
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
    if "GCA has published a service catalog for GCA AI Quant Access credits." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing credits safe claim")
    if not any("automatic or self-service transferred" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing member benefit boundary")
    if not any("cash, income" in item for item in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing credit value boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_release_gates_page(text: str) -> None:
    label = "/release-gates.html"
    assert_contains(text, "GCA Product Release Gates", label)
    assert_contains(text, "Release References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
    assert_contains(text, "Credits Catalog", label)
    assert_contains(text, "Access Portal", label)
    assert_contains(text, "Operations Runbook", label)
    assert_contains(text, "Access API", label)
    assert_contains(text, "account ledger path live", label)
    assert_contains(text, "Public account UI, wallet verification, and eligible 100 credits / GCA Member ledger records are live", label)
    assert_contains(text, "Live at /gca/member-access/", label)
    assert_contains(text, "Eligible ledger records live", label)
    assert_contains(text, "controlled HTTPS account UI", label)
    assert_contains(text, "read-only GCA balance verification", label)
    assert_contains(text, "credit ledger activation", label)
    assert_contains(text, "member ledger activation", label)
    assert_contains(text, "risk-control review", label)
    assert_contains(text, "support review queue", label)
    assert_contains(text, "simulation or testnet first", label)
    assert_contains(text, "BaseScan token profile publication", label)
    assert_contains(text, "Returned 2026-05-23; final package refreshed 2026-06-06; Handoff and Chinese owner flow ready for one support@gcagochina.com submission", label)
    assert_contains(text, "Latest reviewer package", label)
    assert_contains(text, "Final package 2026-06-06T11:10:54Z; daily status 2026-06-07T13:06:12Z", label)
    assert_contains(text, "basescan-handoff.html", label)
    assert_contains(text, "daily-status.html", label)
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
    if payload.get("status") != "public-release-gates-account-ledger-path-live":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if state.get("currentStage") != "account-ledger-path-live":
        raise SiteCheckError(f"{label}: wrong currentStage")
    if state.get("publicProductSpecOnly") is not False:
        raise SiteCheckError(f"{label}: publicProductSpecOnly must be false")
    for key in ("publicAccountUiLive", "creditsEligibilitySubmissionLive", "gcaMemberEligibilitySubmissionLive", "walletVerificationLive", "creditLedgerWritesLive", "memberLedgerWritesLive", "memberBenefitManualReviewOnly"):
        if state.get(key) is not True:
            raise SiteCheckError(f"{label}: {key} must be true")
    if state.get("liveTradingEnabled") is not False:
        raise SiteCheckError(f"{label}: liveTradingEnabled must be false")
    if state.get("baseScanTokenProfile") != "ready-for-owner-resubmission":
        raise SiteCheckError(f"{label}: wrong BaseScan state")
    if state.get("baseScanTokenProfileLastCheckedDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong BaseScan last checked date")
    if state.get("baseScanFinalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong BaseScan final package timestamp")
    if state.get("dailyStatusGeneratedAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong daily status timestamp")
    if state.get("baseScanResubmissionReady") is not True:
        raise SiteCheckError(f"{label}: BaseScan resubmission should be ready")
    if state.get("thirdPartyAudit") != "not-completed":
        raise SiteCheckError(f"{label}: wrong audit state")
    for gate in (
        "access-portal",
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
        "basescan-token-profile",
    ):
        if gate not in gate_ids:
            raise SiteCheckError(f"{label}: missing gate {gate}")
    base_scan_gate = next((item for item in payload.get("releaseGates", []) if item.get("id") == "basescan-token-profile"), {})
    if base_scan_gate.get("status") != "ready-for-owner-resubmission":
        raise SiteCheckError(f"{label}: wrong BaseScan release gate status")
    if base_scan_gate.get("finalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong BaseScan release gate final package timestamp")
    if base_scan_gate.get("dailyStatusGeneratedAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong BaseScan release gate daily status timestamp")
    for item in (
        "read-only GCA balance verification",
        "credit ledger record",
        "member ledger record",
        "support review queue for member-benefit approval",
        "risk-control review",
        "simulation or testnet first for any future trading workflow",
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
    if links.get("baseScanHandoffPage") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoffPage")
    if links.get("baseScanHandoff") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoff")
    if links.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatusPage")
    if links.get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatus")
    if links.get("reviewerKitPage") != REVIEWER_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKitPage")
    if links.get("reviewerKit") != REVIEWER_KIT_URL:
        raise SiteCheckError(f"{label}: wrong reviewerKit")
    if links.get("trustCenterPage") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterPage")
    if links.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trustCenter")
    if links.get("zhBaseScanSubmit") != ZH_BASESCAN_SUBMIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong zhBaseScanSubmit")
    if not any("live controlled account UI" in item for item in payload.get("publicClaimBoundaries", {}).get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing release-gates safe claim")
    if "The latest BaseScan owner submission package was generated on 2026-06-06T11:10:54Z, and the daily public status snapshot was refreshed on 2026-06-07T13:06:12Z." not in payload.get("publicClaimBoundaries", {}).get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing latest BaseScan package safe claim")
    if not any("automatic or self-service transferred" in item for item in payload.get("publicClaimBoundaries", {}).get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing member benefit boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_privacy_page(text: str) -> None:
    label = "/privacy.html"
    assert_contains(text, "GCA Privacy Notice", label)
    assert_contains(text, "Privacy References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "live email registration", label)
    assert_contains(text, "contact suppression", label)
    assert_contains(text, "Email API live / member packet local", label)
    assert_contains(text, "Email Registration", label)
    assert_contains(text, "Email Unsubscribe", label)
    assert_contains(text, "register.html", label)
    assert_contains(text, "unsubscribe.html", label)
    assert_contains(text, "Cloudflare Workers + D1", label)
    assert_contains(text, "https://gca-registration-api.gcagochina.workers.dev", label)
    assert_contains(text, "local pre-registration packet", label)
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
    if payload.get("contactEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong contact email")
    if static.get("automaticServerStorage") is not True:
        raise SiteCheckError(f"{label}: email registration server storage should be disclosed")
    if static.get("directSubmissionEndpointConfigured") is not True:
        raise SiteCheckError(f"{label}: email direct submission should be disclosed")
    if static.get("emailRegistrationDirectSubmissionEndpointConfigured") is not True:
        raise SiteCheckError(f"{label}: email registration endpoint should be live")
    if static.get("contactSuppressionDirectSubmissionEndpointConfigured") is not True:
        raise SiteCheckError(f"{label}: contact suppression endpoint should be live")
    if static.get("memberPreRegistrationDirectSubmissionEndpointConfigured") is not False:
        raise SiteCheckError(f"{label}: member pre-registration direct submission must remain false")
    if static.get("emailRegistrationEndpoint") != "/gca/email-registrations":
        raise SiteCheckError(f"{label}: wrong email registration endpoint")
    if static.get("contactSuppressionEndpoint") != "/gca/contact-suppressions":
        raise SiteCheckError(f"{label}: wrong contact suppression endpoint")
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
    if links.get("emailRegistration") != REGISTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong email registration link")
    if links.get("emailUnsubscribe") != UNSUBSCRIBE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong email unsubscribe link")
    if links.get("memberLedgerSchema") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong ledger schema link")
    requests = payload.get("userRequests", {})
    if requests.get("unsubscribePage") != UNSUBSCRIBE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong unsubscribe page")
    if requests.get("contactSuppressionEndpoint") != "https://gca-registration-api.gcagochina.workers.dev/gca/contact-suppressions":
        raise SiteCheckError(f"{label}: wrong contact suppression endpoint")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_terms_page(text: str) -> None:
    label = "/terms.html"
    assert_contains(text, "GCA Participation Terms", label)
    assert_contains(text, "Participation References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Pre-Registration Only", label)
    assert_contains(text, "Email Registration", label)
    assert_contains(text, "Email Unsubscribe", label)
    assert_contains(text, "register.html", label)
    assert_contains(text, "unsubscribe.html", label)
    assert_contains(text, "Account-Level Service Access", label)
    assert_contains(text, "No Custody Or Withdrawal Permission", label)
    assert_contains(text, "No Outcome Promise", label)
    assert_contains(text, "Returned 2026-05-23; final package refreshed 2026-06-06; Handoff and Chinese owner flow ready for one support@gcagochina.com submission", label)
    assert_contains(text, "Latest reviewer package", label)
    assert_contains(text, "Final package 2026-06-06T11:10:54Z; daily status 2026-06-07T13:06:12Z", label)
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
    if boundaries.get("emailRegistrationLive") is not True:
        raise SiteCheckError(f"{label}: email registration should be live")
    if boundaries.get("emailContactSuppressionLive") is not True:
        raise SiteCheckError(f"{label}: email contact suppression should be live")
    if boundaries.get("publicSelfServiceClaimConnected") is not False:
        raise SiteCheckError(f"{label}: self-service claim must remain false")
    if boundaries.get("emailRegistrationTransfersTokens") is not False:
        raise SiteCheckError(f"{label}: email registration must not transfer tokens")
    if boundaries.get("emailContactSuppressionChangesChainState") is not False:
        raise SiteCheckError(f"{label}: email unsubscribe must not change chain state")
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
    email_registration = payload.get("emailRegistrationTerms", {})
    if email_registration.get("endpoint") != "https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations":
        raise SiteCheckError(f"{label}: wrong email registration endpoint")
    if "token transfer" not in email_registration.get("doesNotCreate", []):
        raise SiteCheckError(f"{label}: missing email registration token boundary")
    contact_suppression = payload.get("emailContactSuppressionTerms", {})
    if contact_suppression.get("endpoint") != "https://gca-registration-api.gcagochina.workers.dev/gca/contact-suppressions":
        raise SiteCheckError(f"{label}: wrong contact suppression endpoint")
    if "chain state" not in contact_suppression.get("doesNotChange", []):
        raise SiteCheckError(f"{label}: missing contact suppression chain boundary")
    if status.get("baseScanTokenProfile") != "ready-for-owner-resubmission":
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
    if links.get("emailRegistration") != REGISTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong email registration link")
    if links.get("emailUnsubscribe") != UNSUBSCRIBE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong email unsubscribe link")
    if links.get("memberLedgerSchema") != MEMBER_LEDGER_URL:
        raise SiteCheckError(f"{label}: wrong ledger schema link")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_supply_page(text: str) -> None:
    label = "/supply.html"
    assert_contains(text, "GCA Supply and Reserve", label)
    assert_contains(text, "Supply References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "1,000,000,000 GCA", label)
    assert_contains(text, "400,000,000 GCA / 40%", label)
    assert_contains(text, "600,000,000 GCA / 60%", label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_contains(text, RESERVE_TX_1, label)
    assert_contains(text, RESERVE_TX_2, label)
    assert_contains(text, "not be described as locked, vested, or multisig-controlled", label)
    assert_contains(text, "Do not claim the reserve provides price support", label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    for forbidden in (
        'href="supply.json"',
        'href="holder-distribution.json"',
        'href="reserve-statement.json"',
        'href="custody-roadmap.json"',
        'href="tokenlist.json"',
    ):
        assert_not_contains(text, forbidden, label)


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
    if links.get("holderDistribution") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistribution link")
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
    assert_contains(text, "Brand References", label)
    assert_no_public_data_room_terms(text, label)
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


def validate_project_profile_page(text: str) -> None:
    label = "/project-profile.html"
    assert_social_preview_meta(text, label, PROJECT_PROFILE_PAGE_URL)
    if text.count('<h1 id="title">GCA Project Profile</h1>') != 1:
        raise SiteCheckError(f"{label}: expected exactly one project profile h1")
    for expected in (
        "GCA Project Profile",
        "Readable Project Profile",
        "Go China Access",
        "Base Mainnet",
        "8453",
        MAINNET_ADDRESS,
        "1,000,000,000 GCA",
        "No post-deploy mint",
        "support@gcagochina.com",
        "Tim Chen",
        "Project Profile",
        "Token List Guide",
        "Member Program",
        "Reviewer Kit",
        "Listing Kit",
        "Data Room",
        "BaseScan Review Map",
        "Return Reason To Public Evidence",
        "Website accessible and safe to visit",
        "Clear token and project information",
        "Placeholders and broken links",
        "Founder and team transparency",
        "Sender email matches project domain",
        "Logo, social, and metadata URLs",
        "Source and deployer-wallet ownership are verified",
        "not approved until BaseScan publishes it",
        "MX/SPF/DKIM/DMARC present",
        "tools/check_public_site.py",
        "team.html#tim-chen",
        "domain-email-evidence.html",
    ):
        assert_contains(text, expected, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)
    for forbidden in ('href="project.json"', 'href="tokenlist.json"', 'href="member-program.json"'):
        assert_not_contains(text, forbidden, label)


def validate_tokenlist_page(text: str) -> None:
    label = "/tokenlist.html"
    assert_social_preview_meta(text, label, TOKENLIST_PAGE_URL)
    for expected in (
        "GCA Token List Guide",
        "Readable Token Metadata",
        "Wallet Import",
        "Manual Wallet Fields",
        "Base Mainnet",
        "8453",
        MAINNET_ADDRESS,
        "Token symbol",
        "Decimals",
        "assets/gca-logo.png",
        "Official Market Route",
        "Token Safety",
        "Platform Metadata",
        "Data Room",
    ):
        assert_contains(text, expected, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)
    for forbidden in ('href="tokenlist.json"', 'href="project.json"', 'href="member-program.json"'):
        assert_not_contains(text, forbidden, label)


def validate_member_program_page(text: str) -> None:
    label = "/member-program.html"
    assert_social_preview_meta(text, label, MEMBER_PROGRAM_PAGE_URL)
    for expected in (
        "GCA Member Program",
        "Readable Member Rules",
        "Holder Bonus",
        "10,000 GCA",
        "100 GCA AI Quant Access credits",
        "GCA Member",
        "1,000,000 GCA",
        "30 consecutive days",
        "manual reserve-wallet transfer",
        "read-only ERC-20 balanceOf call",
        "Open Member Access",
        "Email Register",
        "中文会员规则",
        "Member Benefit",
        "Support",
    ):
        assert_contains(text, expected, label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_no_forbidden_public_claims(text, label)
    for forbidden in (
        'href="member-program.json"',
        'href="member-ledger.json"',
        'href="member-benefit.json"',
        'href="support.json"',
        "Platform-Only Evidence Path",
    ):
        assert_not_contains(text, forbidden, label)


def validate_project_json(text: str) -> None:
    label = "/project.json"
    payload = load_json(text, label)
    market = payload.get("market", {})
    status = payload.get("platformStatus", {})
    member_program = payload.get("memberProgram", {})
    external_reviews = payload.get("externalReviewStatus", {})
    reason_map = payload.get("baseScanReviewerReasonMap", {})

    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
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
    if payload.get("announcementsPageUrl") != ANNOUNCEMENTS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong announcementsPageUrl")
    if payload.get("announcementsUrl") != ANNOUNCEMENTS_URL:
        raise SiteCheckError(f"{label}: wrong announcementsUrl")
    if payload.get("campaignPageUrl") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignPageUrl")
    if payload.get("campaignUrl") != CAMPAIGN_URL:
        raise SiteCheckError(f"{label}: wrong campaignUrl")
    if payload.get("contentLibraryPageUrl") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibraryPageUrl")
    if payload.get("contentLibraryUrl") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong contentLibraryUrl")
    if payload.get("publishingDeskPageUrl") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDeskPageUrl")
    if payload.get("publishingDeskUrl") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishingDeskUrl")
    if payload.get("narrativePageUrl") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong narrativePageUrl")
    if payload.get("narrativeUrl") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong narrativeUrl")
    if payload.get("weeklyRadarPageUrl") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarPageUrl")
    if payload.get("weeklyRadarUrl") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarUrl")
    if payload.get("radarIssue004PageUrl") != RADAR_ISSUE_004_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004PageUrl")
    if payload.get("radarIssue004Url") != RADAR_ISSUE_004_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004Url")
    if payload.get("memberAccessBrief001PageUrl") != MEMBER_ACCESS_BRIEF_001_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001PageUrl")
    if payload.get("memberAccessBrief001Url") != MEMBER_ACCESS_BRIEF_001_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001Url")
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
    if payload.get("dailyStatusPageUrl") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatusPageUrl")
    if payload.get("dailyStatusUrl") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatusUrl")
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
    if payload.get("baseScanHandoffPageUrl") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoffPageUrl")
    if payload.get("baseScanHandoffUrl") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoffUrl")
    if payload.get("baseScanHandoff", {}).get("status") != "ready-for-owner-resubmission":
        raise SiteCheckError(f"{label}: wrong baseScanHandoff status")
    if payload.get("baseScanHandoff", {}).get("pageUrl") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoff pageUrl")
    if payload.get("baseScanHandoff", {}).get("url") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoff url")
    if payload.get("baseScanHandoff", {}).get("finalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong baseScanHandoff finalSubmissionPackageGeneratedAt")
    if payload.get("baseScanHandoff", {}).get("dailyStatusGeneratedAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong baseScanHandoff dailyStatusGeneratedAt")
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
    if payload.get("liquidityPageUrl") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityPageUrl")
    if payload.get("liquidityUrl") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidityUrl")
    if payload.get("holderDistributionPageUrl") != HOLDER_DISTRIBUTION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong holderDistributionPageUrl")
    if payload.get("holderDistributionUrl") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistributionUrl")
    if payload.get("riskRemediationPageUrl") != RISK_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediationPageUrl")
    if payload.get("riskRemediationUrl") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediationUrl")
    if payload.get("custodyRoadmapPageUrl") != CUSTODY_ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmapPageUrl")
    if payload.get("custodyRoadmapUrl") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmapUrl")
    if payload.get("auditReadinessPageUrl") != AUDIT_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong auditReadinessPageUrl")
    if payload.get("auditReadinessUrl") != AUDIT_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong auditReadinessUrl")
    if payload.get("supplyDisclosureUrl") != SUPPLY_DISCLOSURE_URL:
        raise SiteCheckError(f"{label}: wrong supplyDisclosureUrl")
    if payload.get("onchainProofsPageUrl") != ONCHAIN_PROOFS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsPageUrl")
    if payload.get("onchainProofsUrl") != ONCHAIN_PROOFS_URL:
        raise SiteCheckError(f"{label}: wrong onchainProofsUrl")
    social_links = payload.get("officialSocialLinks", [])
    if not any(link.get("platform") == "X" and link.get("url") == X_URL for link in social_links):
        raise SiteCheckError(f"{label}: missing official X social link")
    if reason_map.get("status") != "published-on-project-profile":
        raise SiteCheckError(f"{label}: wrong BaseScan reviewer reason map status")
    if reason_map.get("sourceNoticeDate") != "2026-05-23":
        raise SiteCheckError(f"{label}: wrong BaseScan reviewer reason map notice date")
    if reason_map.get("pageUrl") != f"{PROJECT_PROFILE_PAGE_URL}#basescanMapTitle":
        raise SiteCheckError(f"{label}: wrong BaseScan reviewer reason map page")
    if "information-insufficient return reasons" not in reason_map.get("purpose", ""):
        raise SiteCheckError(f"{label}: missing BaseScan reviewer reason map purpose")
    reason_items = reason_map.get("items", [])
    if not isinstance(reason_items, list) or len(reason_items) != 6:
        raise SiteCheckError(f"{label}: expected six BaseScan reviewer reason map items")
    reason_items_by_id = {item.get("id"): item for item in reason_items if isinstance(item, dict)}
    expected_reason_ids = {
        "website-accessible-safe",
        "clear-project-token-information",
        "placeholder-broken-link-review",
        "founder-team-transparency",
        "domain-email-match",
        "logo-social-metadata",
    }
    if set(reason_items_by_id) != expected_reason_ids:
        raise SiteCheckError(f"{label}: wrong BaseScan reviewer reason map ids")
    founder_item = reason_items_by_id["founder-team-transparency"]
    if founder_item.get("status") != "implemented-official-domain-equivalent":
        raise SiteCheckError(f"{label}: wrong founder evidence status")
    for expected_link in (f"{TEAM_PAGE_URL}#tim-chen", TIM_CHEN_PROFILE_PAGE_URL, GITHUB_REPO_URL, X_URL):
        if expected_link not in founder_item.get("evidencePages", []):
            raise SiteCheckError(f"{label}: missing founder evidence link {expected_link}")
    domain_item = reason_items_by_id["domain-email-match"]
    if domain_item.get("status") != "implemented-domain-email-ready":
        raise SiteCheckError(f"{label}: wrong domain email reason status")
    if domain_item.get("officialEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong BaseScan reason map official email")
    if DOMAIN_EMAIL_PAGE_URL not in domain_item.get("evidencePages", []):
        raise SiteCheckError(f"{label}: missing domain email evidence page")
    if "MX/SPF/DKIM/DMARC present" not in domain_item.get("dnsEvidence", ""):
        raise SiteCheckError(f"{label}: missing domain email DNS evidence")
    placeholder_item = reason_items_by_id["placeholder-broken-link-review"]
    if "check_public_site.py" not in placeholder_item.get("checkCommand", ""):
        raise SiteCheckError(f"{label}: missing public site check command in reason map")
    logo_item = reason_items_by_id["logo-social-metadata"]
    for expected_link in ("https://gcagochina.com/assets/gca-logo.svg", BRAND_KIT_PAGE_URL, WHITEPAPER_PAGE_URL):
        if expected_link not in logo_item.get("evidencePages", []):
            raise SiteCheckError(f"{label}: missing logo/social metadata evidence link {expected_link}")
    if "pending until BaseScan publishes it" not in reason_map.get("currentBoundary", ""):
        raise SiteCheckError(f"{label}: missing BaseScan pending boundary")
    if market.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialPair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if status.get("baseScanTokenProfile") != "ready-for-owner-resubmission":
        raise SiteCheckError(f"{label}: unexpected BaseScan status")
    if status.get("baseScanTokenProfileLastCheckedDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong BaseScan profile last checked date")
    if "returned the token profile update again" not in status.get("baseScanTokenProfileLastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing BaseScan profile last checked result")
    if "2026-06-06T11:10:54Z" not in status.get("baseScanTokenProfileLastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing BaseScan final package timestamp")
    if "2026-06-07T13:06:12Z" not in status.get("baseScanTokenProfileLastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing daily status timestamp")
    if status.get("baseScanFinalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong baseScanFinalSubmissionPackageGeneratedAt")
    if status.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformStatus dailyStatusPage")
    if status.get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong platformStatus dailyStatus")
    if status.get("dailyStatusGeneratedAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong dailyStatusGeneratedAt")
    if status.get("externalReviewStatusLastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong externalReviewStatusLastUpdated")
    if status.get("domainEmailSetupPlan") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailSetupPlan")
    if status.get("domainEmailSetupPlanData") != DOMAIN_EMAIL_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailSetupPlanData")
    if status.get("domainEmailEvidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailEvidenceChecklist")
    if status.get("domainEmailEvidenceChecklistData") != DOMAIN_EMAIL_EVIDENCE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailEvidenceChecklistData")
    if "public evidence checklist" not in status.get("baseScanTokenProfileLastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing domain email evidence checklist status")
    if status.get("timChenProfessionalProfile") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong Tim Chen professional profile")
    if status.get("geckoTerminalTokenInfo") != "approved-2026-05-11":
        raise SiteCheckError(f"{label}: unexpected GeckoTerminal status")
    if external_reviews.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong external review lastUpdated")
    if external_reviews.get("baseScanTokenProfileLastCheckedDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong external review BaseScan last checked date")
    if "2026-06-06T11:10:54Z" not in external_reviews.get("baseScanTokenProfileLastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing external review BaseScan final package timestamp")
    if "2026-06-07T13:06:12Z" not in external_reviews.get("baseScanTokenProfileLastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing external review daily status timestamp")
    if external_reviews.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong external review dailyStatusPage")
    if external_reviews.get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong external review dailyStatus")
    if external_reviews.get("baseScanFinalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong external review baseScanFinalSubmissionPackageGeneratedAt")
    if external_reviews.get("dailyStatusGeneratedAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong external review dailyStatusGeneratedAt")
    if status.get("narrativeSystem") != "public-narrative-system-published":
        raise SiteCheckError(f"{label}: unexpected narrative system status")
    if status.get("weeklyGoChinaRadar") != "weekly-go-china-radar-issue-003-published":
        raise SiteCheckError(f"{label}: unexpected weekly radar status")
    if status.get("accessPortal") != "public-access-portal-live":
        raise SiteCheckError(f"{label}: unexpected access portal status")
    if status.get("accessApiContract") != "public-access-api-member-access-live":
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
    if status.get("liquidityStatement") != "public-liquidity-custody-statement-published":
        raise SiteCheckError(f"{label}: unexpected liquidity statement status")
    if status.get("holderDistribution") != "public-holder-distribution-disclosure-published":
        raise SiteCheckError(f"{label}: unexpected holder distribution status")
    if status.get("riskRemediation") != "public-risk-remediation-plan-published":
        raise SiteCheckError(f"{label}: unexpected risk remediation status")
    if status.get("custodyRoadmap") != "public-custody-roadmap-published":
        raise SiteCheckError(f"{label}: unexpected custody roadmap status")
    if status.get("auditReadiness") != "public-audit-readiness-package-published":
        raise SiteCheckError(f"{label}: unexpected audit readiness status")
    if status.get("announcementHub") != "public-announcement-hub-published":
        raise SiteCheckError(f"{label}: unexpected announcement hub status")
    if status.get("contentCampaign") != "public-campaign-calendar-published":
        raise SiteCheckError(f"{label}: unexpected content campaign status")
    if status.get("contentLibrary") != "public-bilingual-content-library-published":
        raise SiteCheckError(f"{label}: unexpected content library status")
    if status.get("publishingDesk") != "public-publishing-desk-published":
        raise SiteCheckError(f"{label}: unexpected publishing desk status")
    if payload.get("liquidityStatement", {}).get("status") != "public-liquidity-custody-statement-published":
        raise SiteCheckError(f"{label}: unexpected liquidity statement object status")
    if payload.get("liquidityStatement", {}).get("pageUrl") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidity statement page")
    if payload.get("liquidityStatement", {}).get("url") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidity statement url")
    if payload.get("holderDistribution", {}).get("status") != "public-holder-distribution-disclosure-published":
        raise SiteCheckError(f"{label}: unexpected holder distribution object status")
    if payload.get("holderDistribution", {}).get("pageUrl") != HOLDER_DISTRIBUTION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong holder distribution page")
    if payload.get("holderDistribution", {}).get("url") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holder distribution url")
    if payload.get("riskRemediation", {}).get("status") != "public-risk-remediation-plan-published":
        raise SiteCheckError(f"{label}: unexpected risk remediation object status")
    if payload.get("riskRemediation", {}).get("pageUrl") != RISK_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong risk remediation page")
    if payload.get("riskRemediation", {}).get("url") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong risk remediation url")
    if payload.get("custodyRoadmap", {}).get("status") != "public-custody-roadmap-published":
        raise SiteCheckError(f"{label}: unexpected custody roadmap object status")
    if payload.get("custodyRoadmap", {}).get("pageUrl") != CUSTODY_ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong custody roadmap page")
    if payload.get("custodyRoadmap", {}).get("url") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custody roadmap url")
    if payload.get("auditReadiness", {}).get("status") != "public-audit-readiness-package-published":
        raise SiteCheckError(f"{label}: unexpected audit readiness object status")
    if payload.get("auditReadiness", {}).get("pageUrl") != AUDIT_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong audit readiness page")
    if payload.get("auditReadiness", {}).get("url") != AUDIT_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong audit readiness url")
    if payload.get("announcementHub", {}).get("status") != "public-announcement-hub-published":
        raise SiteCheckError(f"{label}: unexpected announcement hub object status")
    if payload.get("announcementHub", {}).get("pageUrl") != ANNOUNCEMENTS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong announcement hub page")
    if payload.get("announcementHub", {}).get("url") != ANNOUNCEMENTS_URL:
        raise SiteCheckError(f"{label}: wrong announcement hub url")
    if payload.get("announcementHub", {}).get("latestPostUrl") != LATEST_X_POST_URL:
        raise SiteCheckError(f"{label}: wrong announcement hub latest post")
    if payload.get("contentCampaign", {}).get("status") != "public-campaign-calendar-published":
        raise SiteCheckError(f"{label}: unexpected content campaign object status")
    if payload.get("contentCampaign", {}).get("pageUrl") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong content campaign page")
    if payload.get("contentCampaign", {}).get("url") != CAMPAIGN_URL:
        raise SiteCheckError(f"{label}: wrong content campaign url")
    if payload.get("contentCampaign", {}).get("draftCount") != 10:
        raise SiteCheckError(f"{label}: wrong content campaign draft count")
    if payload.get("contentCampaign", {}).get("nextDraftLink") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong content campaign nextDraftLink")
    content_library = payload.get("contentLibrary", {})
    if content_library.get("status") != "public-bilingual-content-library-published":
        raise SiteCheckError(f"{label}: unexpected content library object status")
    if content_library.get("pageUrl") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong content library page")
    if content_library.get("url") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong content library url")
    if content_library.get("draftCount") != 10:
        raise SiteCheckError(f"{label}: wrong content library draft count")
    publishing_desk = payload.get("publishingDesk", {})
    if publishing_desk.get("status") != "public-publishing-desk-published":
        raise SiteCheckError(f"{label}: unexpected publishing desk object status")
    if publishing_desk.get("pageUrl") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishing desk page")
    if publishing_desk.get("url") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishing desk url")
    if publishing_desk.get("nextPublishTargetDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong publishing desk target date")
    if publishing_desk.get("manualPublishOnly") is not True:
        raise SiteCheckError(f"{label}: publishing desk must be manual")
    issue_004 = payload.get("weeklyGoChinaRadarIssue004", {})
    if issue_004.get("status") != "weekly-go-china-radar-issue-004-ready-for-review":
        raise SiteCheckError(f"{label}: wrong issue 004 status")
    if issue_004.get("pageUrl") != RADAR_ISSUE_004_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong issue 004 page")
    if issue_004.get("url") != RADAR_ISSUE_004_URL:
        raise SiteCheckError(f"{label}: wrong issue 004 url")
    if issue_004.get("operatorReviewRequired") is not True:
        raise SiteCheckError(f"{label}: issue 004 must require review")
    member_access_brief = payload.get("memberAccessBrief001", {})
    if member_access_brief.get("status") != "member-access-brief-001-ready-for-review":
        raise SiteCheckError(f"{label}: wrong member access brief status")
    if member_access_brief.get("pageUrl") != MEMBER_ACCESS_BRIEF_001_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong member access brief page")
    if member_access_brief.get("url") != MEMBER_ACCESS_BRIEF_001_URL:
        raise SiteCheckError(f"{label}: wrong member access brief url")
    if member_access_brief.get("targetDate") != "2026-05-23":
        raise SiteCheckError(f"{label}: wrong member access brief target date")
    if member_access_brief.get("minimumHolding") != "1,000,000 GCA":
        raise SiteCheckError(f"{label}: wrong member access brief threshold")
    if member_access_brief.get("minimumHoldingPeriod") != "30 consecutive days":
        raise SiteCheckError(f"{label}: wrong member access brief holding period")
    if member_access_brief.get("memberBenefitAmount") != "10,000 GCA":
        raise SiteCheckError(f"{label}: wrong member access brief amount")
    if member_access_brief.get("operatorReviewRequired") is not True:
        raise SiteCheckError(f"{label}: member access brief must require review")
    if member_program.get("status") != "account-ledger-path-live-manual-benefit-review":
        raise SiteCheckError(f"{label}: unexpected member program status")
    if member_program.get("supportIntake", {}).get("status") != "public-support-intake-published":
        raise SiteCheckError(f"{label}: unexpected support intake status")
    if member_program.get("ledgerSchema", {}).get("status") != "public-member-ledger-workers-d1-live":
        raise SiteCheckError(f"{label}: unexpected member ledger schema status")
    if member_program.get("privacyAndTerms", {}).get("status") != "public-privacy-and-terms-published":
        raise SiteCheckError(f"{label}: unexpected privacy and terms status")
    if payload.get("roadmap", {}).get("status") != "public-roadmap-published":
        raise SiteCheckError(f"{label}: unexpected roadmap status")
    if payload.get("roadmap", {}).get("publicEligibilitySubmissionLive") is not True:
        raise SiteCheckError(f"{label}: roadmap must mark account/ledger path live")
    if payload.get("utilityBridge", {}).get("status") != "public-utility-bridge-spec-published":
        raise SiteCheckError(f"{label}: unexpected access layer status")
    if payload.get("utilityBridge", {}).get("url") != UTILITY_URL:
        raise SiteCheckError(f"{label}: wrong access layer url")
    if payload.get("utilityBridge", {}).get("publicEligibilitySubmissionLive") is not True:
        raise SiteCheckError(f"{label}: access layer must mark account/ledger path live")
    if payload.get("utilityBridge", {}).get("requiresControlledWalletVerification") is not True:
        raise SiteCheckError(f"{label}: access layer must require controlled wallet verification")
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
    if payload.get("productSpec", {}).get("publicAccountUiLive") is not True:
        raise SiteCheckError(f"{label}: product account UI must be true")
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
    if credits.get("currentStage") != "account-ledger-path-live":
        raise SiteCheckError(f"{label}: wrong credits catalog stage")
    if credits.get("publicAccountUiLive") is not True:
        raise SiteCheckError(f"{label}: credits account UI must be true")
    if credits.get("creditsEligibilitySubmissionLive") is not True:
        raise SiteCheckError(f"{label}: credits eligibility submission must be true")
    if credits.get("gcaMemberEligibilitySubmissionLive") is not True:
        raise SiteCheckError(f"{label}: member eligibility submission must be true")
    if credits.get("holderBonusCreditAmount") != "100 GCA AI Quant Access credits":
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
    if review_queue.get("creditsEligibilitySubmissionLive") is not True:
        raise SiteCheckError(f"{label}: review queue credits must be true")
    for key in (
        "creditLedgerRecordCreationLive",
        "memberLedgerRecordCreationLive",
        "manualReviewRequired",
    ):
        if review_queue.get(key) is not True:
            raise SiteCheckError(f"{label}: review queue {key} must be true")
    for key in ("memberBenefitSelfServiceClaimable", "memberBenefitAutomaticTransfer"):
        if review_queue.get(key) is not False:
            raise SiteCheckError(f"{label}: review queue {key} must be false")
    if "wallet-balance-review" not in review_queue.get("lanes", []):
        raise SiteCheckError(f"{label}: missing review queue lane")
    operations = payload.get("accessOperationsRunbook", {})
    if operations.get("status") != "public-access-operations-runbook-published":
        raise SiteCheckError(f"{label}: unexpected operations object status")
    if operations.get("pageUrl") != OPERATIONS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong operations page")
    if operations.get("url") != OPERATIONS_URL:
        raise SiteCheckError(f"{label}: wrong operations url")
    if operations.get("publicRunbookOnly") is not False:
        raise SiteCheckError(f"{label}: operations must mark live account/ledger flow")
    if operations.get("runbookOnlyForManualReviewHandling") is not True:
        raise SiteCheckError(f"{label}: operations must keep manual-review runbook boundary")
    if operations.get("ledgerWritesLive") is not True:
        raise SiteCheckError(f"{label}: operations ledger writes must be true")
    if payload.get("releaseGates", {}).get("status") != "public-release-gates-published":
        raise SiteCheckError(f"{label}: unexpected release gates object status")
    if payload.get("releaseGates", {}).get("pageUrl") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong release gates page")
    if payload.get("releaseGates", {}).get("url") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong release gates url")
    if payload.get("releaseGates", {}).get("publicAccountUiLive") is not True:
        raise SiteCheckError(f"{label}: release gates account UI must be true")
    if payload.get("releaseGates", {}).get("creditsEligibilitySubmissionLive") is not True:
        raise SiteCheckError(f"{label}: release gates credits must be true")
    if payload.get("releaseGates", {}).get("gcaMemberEligibilitySubmissionLive") is not True:
        raise SiteCheckError(f"{label}: release gates member status must be true")
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
    if payload.get("weeklyGoChinaRadar", {}).get("status") != "weekly-go-china-radar-issue-003-published":
        raise SiteCheckError(f"{label}: unexpected weekly radar object status")
    if payload.get("weeklyGoChinaRadar", {}).get("pageUrl") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weekly radar object page")
    if payload.get("weeklyGoChinaRadar", {}).get("url") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weekly radar object url")
    if payload.get("weeklyGoChinaRadar", {}).get("issue") != "issue-003":
        raise SiteCheckError(f"{label}: wrong weekly radar issue")
    if payload.get("weeklyGoChinaRadar", {}).get("issueDate") != "2026-05-16":
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
    if extensions.get("announcementsPage") != ANNOUNCEMENTS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong announcementsPage")
    if extensions.get("announcements") != ANNOUNCEMENTS_URL:
        raise SiteCheckError(f"{label}: wrong announcements")
    if extensions.get("campaignPage") != CAMPAIGN_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong campaignPage")
    if extensions.get("campaign") != CAMPAIGN_URL:
        raise SiteCheckError(f"{label}: wrong campaign")
    if extensions.get("contentLibraryPage") != CONTENT_LIBRARY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong contentLibraryPage")
    if extensions.get("contentLibrary") != CONTENT_LIBRARY_URL:
        raise SiteCheckError(f"{label}: wrong contentLibrary")
    if extensions.get("publishingDeskPage") != PUBLISHING_DESK_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong publishingDeskPage")
    if extensions.get("publishingDesk") != PUBLISHING_DESK_URL:
        raise SiteCheckError(f"{label}: wrong publishingDesk")
    if extensions.get("narrativePage") != NARRATIVE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong narrativePage")
    if extensions.get("narrative") != NARRATIVE_URL:
        raise SiteCheckError(f"{label}: wrong narrative")
    if extensions.get("weeklyRadarPage") != RADAR_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadarPage")
    if extensions.get("weeklyRadar") != RADAR_URL:
        raise SiteCheckError(f"{label}: wrong weeklyRadar")
    if extensions.get("radarIssue004Page") != RADAR_ISSUE_004_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004Page")
    if extensions.get("radarIssue004") != RADAR_ISSUE_004_URL:
        raise SiteCheckError(f"{label}: wrong radarIssue004")
    if extensions.get("memberAccessBrief001Page") != MEMBER_ACCESS_BRIEF_001_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001Page")
    if extensions.get("memberAccessBrief001") != MEMBER_ACCESS_BRIEF_001_URL:
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001")
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
    if extensions.get("accessPortalStatus") != "public-access-portal-live":
        raise SiteCheckError(f"{label}: wrong accessPortalStatus")
    if extensions.get("accessApiPage") != ACCESS_API_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong accessApiPage")
    if extensions.get("accessApi") != ACCESS_API_URL:
        raise SiteCheckError(f"{label}: wrong accessApi")
    if extensions.get("accessApiStatus") != "public-access-api-member-access-live":
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
    if extensions.get("liquidityStatementPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityStatementPage")
    if extensions.get("liquidityStatement") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidityStatement")
    if extensions.get("liquidityPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityPage")
    if extensions.get("liquidity") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidity")
    if extensions.get("holderDistributionPage") != HOLDER_DISTRIBUTION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong holderDistributionPage")
    if extensions.get("holderDistribution") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistribution")
    if extensions.get("riskRemediationPage") != RISK_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediationPage")
    if extensions.get("riskRemediation") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediation")
    if extensions.get("custodyRoadmapPage") != CUSTODY_ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmapPage")
    if extensions.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap")
    if extensions.get("auditReadinessPage") != AUDIT_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong auditReadinessPage")
    if extensions.get("auditReadiness") != AUDIT_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong auditReadiness")
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
    if extensions.get("weeklyRadarStatus") != "weekly-go-china-radar-issue-003-published":
        raise SiteCheckError(f"{label}: wrong weeklyRadarStatus")
    if extensions.get("radarIssue004Status") != "weekly-go-china-radar-issue-004-ready-for-review":
        raise SiteCheckError(f"{label}: wrong radarIssue004Status")
    if extensions.get("memberAccessBrief001Status") != "member-access-brief-001-ready-for-review":
        raise SiteCheckError(f"{label}: wrong memberAccessBrief001Status")
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
    if extensions.get("liquidityStatementStatus") != "public-liquidity-custody-statement-published":
        raise SiteCheckError(f"{label}: wrong liquidityStatementStatus")
    if extensions.get("holderDistributionStatus") != "public-holder-distribution-disclosure-published":
        raise SiteCheckError(f"{label}: wrong holderDistributionStatus")
    if extensions.get("riskRemediationStatus") != "public-risk-remediation-plan-published":
        raise SiteCheckError(f"{label}: wrong riskRemediationStatus")
    if extensions.get("custodyRoadmapStatus") != "public-custody-roadmap-published":
        raise SiteCheckError(f"{label}: wrong custodyRoadmapStatus")
    if extensions.get("auditReadinessStatus") != "public-audit-readiness-package-published":
        raise SiteCheckError(f"{label}: wrong auditReadinessStatus")
    if extensions.get("memberLedgerStatus") != "public-member-ledger-workers-d1-live":
        raise SiteCheckError(f"{label}: wrong memberLedgerStatus")
    if extensions.get("supportIntakeStatus") != "public-support-intake-published":
        raise SiteCheckError(f"{label}: wrong supportIntakeStatus")
    if extensions.get("roadmapStatus") != "public-roadmap-published":
        raise SiteCheckError(f"{label}: wrong roadmapStatus")
    if extensions.get("communityKitStatus") != "public-community-kit-published":
        raise SiteCheckError(f"{label}: wrong communityKitStatus")
    if extensions.get("announcementHubStatus") != "public-announcement-hub-published":
        raise SiteCheckError(f"{label}: wrong announcementHubStatus")
    if extensions.get("contentCampaignStatus") != "public-campaign-calendar-published":
        raise SiteCheckError(f"{label}: wrong contentCampaignStatus")
    if extensions.get("contentLibraryStatus") != "public-bilingual-content-library-published":
        raise SiteCheckError(f"{label}: wrong contentLibraryStatus")
    if extensions.get("publishingDeskStatus") != "public-publishing-desk-published":
        raise SiteCheckError(f"{label}: wrong publishingDeskStatus")
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
    if urls.get("liquidityPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityPage")
    if urls.get("liquidity") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidity")
    if urls.get("holderDistributionPage") != HOLDER_DISTRIBUTION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong holderDistributionPage")
    if urls.get("holderDistribution") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistribution")
    if urls.get("riskRemediationPage") != RISK_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediationPage")
    if urls.get("riskRemediation") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediation")
    if urls.get("custodyRoadmapPage") != CUSTODY_ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmapPage")
    if urls.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap")
    if urls.get("auditReadinessPage") != AUDIT_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong auditReadinessPage")
    if urls.get("auditReadiness") != AUDIT_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong auditReadiness")
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
    if market.get("liquidityStatementPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityStatementPage")
    if market.get("liquidityStatement") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidityStatement")
    if market.get("lpLockClaimed") is not False:
        raise SiteCheckError(f"{label}: LP lock must not be claimed")
    if security.get("thirdPartyAuditCompleted") is not False:
        raise SiteCheckError(f"{label}: third-party audit status must remain false")
    if payload.get("platformStatus", {}).get("platformReplies") != "public-platform-reply-kit-published":
        raise SiteCheckError(f"{label}: wrong platformReplies status")
    if payload.get("platformStatus", {}).get("trustCenter") != "public-trust-center-published":
        raise SiteCheckError(f"{label}: wrong trustCenter status")
    if payload.get("platformStatus", {}).get("narrativeSystem") != "public-narrative-system-published":
        raise SiteCheckError(f"{label}: wrong narrativeSystem status")
    if payload.get("platformStatus", {}).get("weeklyGoChinaRadar") != "weekly-go-china-radar-issue-003-published":
        raise SiteCheckError(f"{label}: wrong weeklyGoChinaRadar status")
    if payload.get("platformStatus", {}).get("accessPortal") != "public-access-portal-live":
        raise SiteCheckError(f"{label}: wrong accessPortal status")
    if payload.get("platformStatus", {}).get("accessApiContract") != "public-access-api-member-access-live":
        raise SiteCheckError(f"{label}: wrong accessApiContract status")
    if payload.get("platformStatus", {}).get("reviewQueueContract") != "public-review-queue-contract-published":
        raise SiteCheckError(f"{label}: wrong reviewQueueContract status")
    if payload.get("platformStatus", {}).get("accessOperationsRunbook") != "public-access-operations-runbook-published":
        raise SiteCheckError(f"{label}: wrong operations runbook status")
    if payload.get("platformStatus", {}).get("utilityBridge") != "public-utility-bridge-spec-published":
        raise SiteCheckError(f"{label}: wrong utilityBridge status")
    if payload.get("platformStatus", {}).get("liquidityStatement") != "public-liquidity-custody-statement-published":
        raise SiteCheckError(f"{label}: wrong liquidityStatement status")
    if payload.get("platformStatus", {}).get("holderDistribution") != "public-holder-distribution-disclosure-published":
        raise SiteCheckError(f"{label}: wrong holderDistribution status")
    if payload.get("platformStatus", {}).get("riskRemediation") != "public-risk-remediation-plan-published":
        raise SiteCheckError(f"{label}: wrong riskRemediation status")
    if payload.get("platformStatus", {}).get("custodyRoadmap") != "public-custody-roadmap-published":
        raise SiteCheckError(f"{label}: wrong custodyRoadmap status")
    if payload.get("platformStatus", {}).get("auditReadiness") != "public-audit-readiness-package-published":
        raise SiteCheckError(f"{label}: wrong auditReadiness status")
    if payload.get("platformStatus", {}).get("productSpec") != "public-product-spec-published":
        raise SiteCheckError(f"{label}: wrong productSpec status")
    if payload.get("platformStatus", {}).get("releaseGates") != "public-release-gates-published":
        raise SiteCheckError(f"{label}: wrong releaseGates status")
    if payload.get("productSpec", {}).get("pageUrl") != PRODUCT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong productSpec page")
    if payload.get("productSpec", {}).get("url") != PRODUCT_URL:
        raise SiteCheckError(f"{label}: wrong productSpec url")
    if payload.get("productSpec", {}).get("publicAccountUiLive") is not True:
        raise SiteCheckError(f"{label}: product account UI must be true")
    if payload.get("productSpec", {}).get("liveTradingEnabled") is not False:
        raise SiteCheckError(f"{label}: product live trading must be false")
    if payload.get("releaseGates", {}).get("pageUrl") != RELEASE_GATES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates page")
    if payload.get("releaseGates", {}).get("url") != RELEASE_GATES_URL:
        raise SiteCheckError(f"{label}: wrong releaseGates url")
    if payload.get("releaseGates", {}).get("creditsEligibilitySubmissionLive") is not True:
        raise SiteCheckError(f"{label}: release gates credits must be true")
    if payload.get("releaseGates", {}).get("gcaMemberEligibilitySubmissionLive") is not True:
        raise SiteCheckError(f"{label}: release gates member must be true")
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
    if payload.get("accessOperationsRunbook", {}).get("publicRunbookOnly") is not False:
        raise SiteCheckError(f"{label}: operations must mark live account/ledger flow")
    if payload.get("accessOperationsRunbook", {}).get("runbookOnlyForManualReviewHandling") is not True:
        raise SiteCheckError(f"{label}: operations must keep manual-review runbook boundary")
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
    if basescan.get("tokenProfile") != "ready-for-owner-resubmission":
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
    if links.get("holderDistribution") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistribution")
    if links.get("riskRemediation") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediation")
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
    if holder_bonus.get("creditAmount") != "100 GCA AI Quant Access credits":
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
    if preview.get("status") != "live-member-access-wallet-read":
        raise SiteCheckError(f"{label}: wrong browser preview status")
    if "eligible credit and member ledger records" not in preview.get("ledgerEffect", ""):
        raise SiteCheckError(f"{label}: browser preview/member access ledger effect must be live")
    if preview.get("requiresSignature") is not False:
        raise SiteCheckError(f"{label}: browser preview must not require signature")
    if preview.get("requiresTransaction") is not False:
        raise SiteCheckError(f"{label}: browser preview must not require transaction")
    if preview.get("finalEligibilityStillRequiresControlledAccountUi") is not False:
        raise SiteCheckError(f"{label}: member access page must not require another controlled UI")
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
    if support.get("contactEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong support contact")
    if "ledger_recorded" not in support.get("reviewStatuses", []):
        raise SiteCheckError(f"{label}: missing ledger_recorded status")
    if not any("live account and eligible ledger intake" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing live account safe claim")
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
    assert_contains(text, "Member Benefit References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
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
    assert_contains(text, "Member Transfer References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
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
    assert_contains(text, "The transfer is not automatic", label)
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
    if payload.get("status") != "public-member-ledger-workers-d1-live":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if token.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if urls.get("memberProgramRules") != MEMBER_PROGRAM_URL:
        raise SiteCheckError(f"{label}: wrong memberProgramRules")
    if urls.get("memberAccess") != "https://gcagochina.com/gca/member-access/":
        raise SiteCheckError(f"{label}: wrong memberAccess")
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
    if preview.get("finalEligibilityStillRequiresControlledAccountUi") is not False:
        raise SiteCheckError(f"{label}: browser balance preview should reflect live controlled UI")
    if thresholds.get("holderBonusMinimum") != "10000 GCA":
        raise SiteCheckError(f"{label}: wrong holder threshold")
    if thresholds.get("holderBonusCreditAmount") != "100 GCA AI Quant Access credits":
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
    if not any("public member access page can submit account intake" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing live member access safe claim")
    if not any("browser-only read-only GCA balance preview" in claim for claim in boundaries.get("safeClaims", [])):
        raise SiteCheckError(f"{label}: missing browser preview safe claim")
    if not any("credits or membership are cash" in claim for claim in boundaries.get("doNotClaim", [])):
        raise SiteCheckError(f"{label}: missing self-service boundary")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_member_ledger_page(text: str) -> None:
    label = "/member-ledger.html"
    assert_contains(text, "GCA Member Ledger Schema", label)
    assert_contains(text, "Member Ledger References", label)
    assert_contains(text, "gca/member-access/", label)
    for forbidden in ("Platform-Only Evidence Path", "Data Room", 'href="data.html"'):
        assert_not_contains(text, forbidden, label)
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
    assert_contains(text, "eligible 10,000 GCA holders can create one account-level 100 GCA AI Quant Access credits ledger record", label)
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
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
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
    if payload.get("canonicalLinks", {}).get("baseScanHandoffPage") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoffPage")
    if payload.get("canonicalLinks", {}).get("baseScanHandoff") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoff")
    if payload.get("canonicalLinks", {}).get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatusPage")
    if payload.get("canonicalLinks", {}).get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatus")
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
    base_scan_profile = next((check for check in checks if check.get("id") == "basescan-token-profile"), {})
    if base_scan_profile.get("lastCheckedDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong BaseScan profile last checked date")
    if base_scan_profile.get("finalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong BaseScan final package timestamp")
    if base_scan_profile.get("dailyStatusGeneratedAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong daily status timestamp")
    if "returned again by BaseScan as information-insufficient on 2026-05-23" not in base_scan_profile.get("evidence", ""):
        raise SiteCheckError(f"{label}: missing BaseScan profile last checked evidence")
    if "2026-06-06T11:10:54Z" not in base_scan_profile.get("evidence", ""):
        raise SiteCheckError(f"{label}: missing BaseScan final package evidence")
    if "2026-06-07T13:06:12Z" not in base_scan_profile.get("evidence", ""):
        raise SiteCheckError(f"{label}: missing daily status evidence")
    if "domain email setup plan" not in base_scan_profile.get("evidence", ""):
        raise SiteCheckError(f"{label}: missing domain email setup evidence")
    if "public evidence checklist" not in base_scan_profile.get("evidence", ""):
        raise SiteCheckError(f"{label}: missing domain email evidence checklist")
    if "activation evidence packet" not in base_scan_profile.get("evidence", ""):
        raise SiteCheckError(f"{label}: missing domain email activation evidence packet")
    if "Use the domain email setup plan at https://gcagochina.com/domain-email.html and evidence checklist at https://gcagochina.com/domain-email-evidence.html, keep support@gcagochina.com active, archive the activation evidence packet before the next BaseScan submission, and submit one clean BaseScan update from the official domain mailbox." not in payload.get("nextActions", []):
        raise SiteCheckError(f"{label}: missing domain email setup next action")
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
    assert_contains(text, "Market Quality References", label)
    assert_no_public_data_room_terms(text, label)
    assert_not_contains(text, 'href="market-quality.json"', label)
    assert_contains(text, "transparent liquidity", label)
    assert_contains(text, "legitimate public participation", label)
    assert_contains(text, "Starter-depth only", label)
    assert_contains(text, "Do not use artificial activity", label)
    assert_contains(text, "Self-trading or wash trading", label)
    assert_contains(text, "Misleading volume", label)
    assert_contains(text, "CoinGecko or CoinMarketCap submission", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)


def validate_liquidity_json(text: str) -> None:
    label = "/liquidity.json"
    payload = load_json(text, label)
    market = payload.get("officialMarket", {})
    custody = payload.get("lpCustody", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-liquidity-custody-statement-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if market.get("pair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong pair")
    if market.get("dex") != "Uniswap v4":
        raise SiteCheckError(f"{label}: wrong DEX")
    if market.get("feeTier") != "0.01%":
        raise SiteCheckError(f"{label}: wrong feeTier")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if market.get("geckoTerminal") != OFFICIAL_GECKOTERMINAL_URL:
        raise SiteCheckError(f"{label}: wrong geckoTerminal")
    if market.get("dexScreener") != OFFICIAL_DEXSCREENER_URL:
        raise SiteCheckError(f"{label}: wrong dexScreener")
    if market.get("liquidityDepthStatus") != "starter-depth-only":
        raise SiteCheckError(f"{label}: wrong liquidityDepthStatus")
    if custody.get("lpLockClaimed") is not False:
        raise SiteCheckError(f"{label}: LP lock must not be claimed")
    if custody.get("lpBurnClaimed") is not False:
        raise SiteCheckError(f"{label}: LP burn must not be claimed")
    if custody.get("multisigLpCustodyClaimed") is not False:
        raise SiteCheckError(f"{label}: LP multisig must not be claimed")
    if custody.get("canLiquidityChange") is not True:
        raise SiteCheckError(f"{label}: must disclose that liquidity can change")
    if custody.get("doNotDescribeAsLocked") is not True:
        raise SiteCheckError(f"{label}: missing locked wording boundary")
    if "lock transaction hash" not in custody.get("futureLockEvidenceRequired", []):
        raise SiteCheckError(f"{label}: missing future lock evidence requirement")
    if payload.get("officialLinks", {}).get("liquidityPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityPage link")
    if payload.get("officialLinks", {}).get("liquidity") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidity link")
    if payload.get("officialLinks", {}).get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap link")
    if "No LP lock is currently claimed." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing no-LP-lock safe claim")
    if "LP lock before verifiable on-chain evidence exists" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing LP lock claim boundary")
    assert_current_pool_text(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_liquidity_page(text: str) -> None:
    label = "/liquidity.html"
    assert_contains(text, "GCA Liquidity And LP Custody", label)
    assert_contains(text, "Liquidity References", label)
    assert_no_public_data_room_terms(text, label)
    assert_not_contains(text, 'href="liquidity.json"', label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, "GCA/USDT", label)
    assert_contains(text, "Starter-depth only", label)
    assert_contains(text, "LP Lock Claim", label)
    assert_contains(text, "Not claimed", label)
    assert_contains(text, "LP Custody Boundary", label)
    assert_contains(text, "No LP lock, LP burn, or LP multisig custody is currently claimed", label)
    assert_contains(text, "Future LP Lock Evidence Requirements", label)
    assert_contains(text, "Custody Roadmap", label)
    assert_contains(text, "Do not claim deep liquidity", label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_current_pool_text(text, label)


def validate_holder_distribution_json(text: str) -> None:
    label = "/holder-distribution.json"
    payload = load_json(text, label)
    allocation = payload.get("allocationDisclosure", {})
    responses = payload.get("riskFactorResponses", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})
    transfer_hashes = [
        entry.get("transactionHash")
        for entry in payload.get("reserveTransferEvidence", [])
        if isinstance(entry, dict)
    ]

    if payload.get("schema") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != HOLDER_DISTRIBUTION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-holder-distribution-disclosure-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("totalSupply") != "1000000000":
        raise SiteCheckError(f"{label}: wrong totalSupply")
    if payload.get("fixedSupply") is not True:
        raise SiteCheckError(f"{label}: fixedSupply must be true")
    if "not a live holder-ranking feed" not in payload.get("snapshotBasis", ""):
        raise SiteCheckError(f"{label}: missing live-ranking boundary")
    if allocation.get("targetPublicAllocation") != "400000000":
        raise SiteCheckError(f"{label}: wrong target public allocation")
    if allocation.get("ownerHeldReserve") != "600000000":
        raise SiteCheckError(f"{label}: wrong owner reserve")
    if allocation.get("ownerReserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong reserve wallet")
    if allocation.get("reserveLocked") is not False:
        raise SiteCheckError(f"{label}: reserveLocked must be false")
    if allocation.get("vestingContract") is not False:
        raise SiteCheckError(f"{label}: vestingContract must be false")
    if allocation.get("multisig") is not False:
        raise SiteCheckError(f"{label}: multisig must be false")
    if transfer_hashes != [RESERVE_TX_1, RESERVE_TX_2]:
        raise SiteCheckError(f"{label}: wrong reserve transfer evidence")
    if responses.get("supplyConcentration", {}).get("status") != "acknowledged-and-disclosed":
        raise SiteCheckError(f"{label}: wrong supply concentration response")
    if responses.get("reserveCustody", {}).get("status") != "owner-controlled-not-locked":
        raise SiteCheckError(f"{label}: wrong reserve custody response")
    if responses.get("liquidityCustody", {}).get("publicReference") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidity custody reference")
    if links.get("holderDistribution") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistribution link")
    if links.get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatement link")
    if links.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap link")
    if links.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup link")
    if "Supply concentration remains a disclosed risk." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing concentration safe claim")
    if "the reserve removes holder concentration risk" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing concentration boundary")
    assert_no_forbidden_public_claims(json.dumps(payload), label)
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(json.dumps(payload), "GCA/WETH", label)


def validate_holder_distribution_page(text: str) -> None:
    label = "/holder-distribution.html"
    assert_contains(text, "GCA Holder Distribution", label)
    assert_contains(text, "Holder References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, "1,000,000,000 GCA", label)
    assert_contains(text, "400,000,000 GCA / 40%", label)
    assert_contains(text, "600,000,000 GCA / 60%", label)
    assert_contains(text, "Not A Live Holder Ranking", label)
    assert_contains(text, "Supply concentration remains a disclosed risk", label)
    assert_contains(text, "Custody Roadmap", label)
    assert_contains(text, "Owner-controlled, not locked", label)
    assert_contains(text, "Reserve Transfer Proofs", label)
    assert_contains(text, "Do not say the reserve removes holder concentration risk", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_contains(text, RESERVE_TX_1, label)
    assert_contains(text, RESERVE_TX_2, label)
    assert_no_forbidden_public_claims(text, label)
    assert_not_contains(text, OLD_WETH_POOL_ADDRESS, label)
    assert_not_contains(text, "GCA/WETH", label)
    for forbidden in (
        'href="holder-distribution.json"',
        'href="supply.json"',
        'href="reserve-statement.json"',
        'href="custody-roadmap.json"',
        'href="liquidity.json"',
    ):
        assert_not_contains(text, forbidden, label)


def validate_risk_remediation_json(text: str) -> None:
    label = "/risk-remediation.json"
    payload = load_json(text, label)
    controls = payload.get("currentPositiveControls", {})
    market = payload.get("officialMarket", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})
    risk_items = {item.get("id"): item for item in payload.get("riskItems", []) if isinstance(item, dict)}

    if payload.get("schema") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != RISK_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-risk-remediation-plan-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if "not a third-party audit" not in payload.get("scopeBoundary", ""):
        raise SiteCheckError(f"{label}: missing scope boundary")
    for item_id in ("price-volatility", "lp-custody", "supply-concentration", "third-party-audit"):
        if item_id not in risk_items:
            raise SiteCheckError(f"{label}: missing risk item {item_id}")
    if risk_items["price-volatility"].get("currentEvidence") != MARKET_QUALITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong price-volatility evidence")
    if risk_items["lp-custody"].get("currentStatus") != "not-locked-not-claimed":
        raise SiteCheckError(f"{label}: wrong LP custody status")
    if risk_items["lp-custody"].get("currentEvidence") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong LP custody evidence")
    if risk_items["supply-concentration"].get("reserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong reserve wallet")
    if risk_items["supply-concentration"].get("reserveTransferTxs") != [RESERVE_TX_1, RESERVE_TX_2]:
        raise SiteCheckError(f"{label}: wrong reserve tx list")
    if risk_items["supply-concentration"].get("currentEvidence") != HOLDER_DISTRIBUTION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong supply concentration evidence")
    if risk_items["third-party-audit"].get("currentStatus") != "not-completed-deferred":
        raise SiteCheckError(f"{label}: wrong audit status")
    if risk_items["third-party-audit"].get("currentEvidence") != TECHNICAL_REPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong audit evidence")
    if controls.get("sourceVerifiedOnBaseScan") is not True:
        raise SiteCheckError(f"{label}: source verification must be true")
    if controls.get("fixedSupply") is not True:
        raise SiteCheckError(f"{label}: fixedSupply must be true")
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
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if market.get("lpLockClaimed") is not False:
        raise SiteCheckError(f"{label}: LP lock must not be claimed")
    if links.get("riskRemediation") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediation link")
    if links.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap link")
    if links.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup link")
    if links.get("liquidity") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidity link")
    if links.get("holderDistribution") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistribution link")
    if "GCA has published a public risk-remediation plan." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing remediation safe claim")
    if "risk factors are fully solved" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing solved-risk boundary")
    assert_current_pool_text(json.dumps(payload), label)
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_risk_remediation_page(text: str) -> None:
    label = "/risk-remediation.html"
    assert_social_preview_meta(text, label, RISK_REMEDIATION_PAGE_URL)
    assert_contains(text, "GCA Risk Remediation Plan", label)
    assert_contains(text, "Risk Remediation References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Custody Roadmap", label)
    assert_contains(text, "Price Volatility", label)
    assert_contains(text, "LP Custody", label)
    assert_contains(text, "Supply Concentration", label)
    assert_contains(text, "Third-party Audit", label)
    assert_contains(text, "not a third-party audit", label)
    assert_contains(text, "not an LP lock claim", label)
    assert_contains(text, "Actions That Would Reduce Review Risk", label)
    assert_contains(text, "Do not say risk factors are fully solved", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)
    for forbidden in (
        'href="risk-remediation.json"',
        'href="blockaid-followup.json"',
        'href="liquidity.json"',
        'href="holder-distribution.json"',
        'href="custody-roadmap.json"',
        'href="technical-report.json"',
        'href="market-quality.json"',
    ):
        assert_not_contains(text, forbidden, label)


def validate_custody_roadmap_json(text: str) -> None:
    label = "/custody-roadmap.json"
    payload = load_json(text, label)
    current = payload.get("currentCustodyStatus", {})
    links = payload.get("officialLinks", {})
    phases = {item.get("id"): item for item in payload.get("roadmapPhases", []) if isinstance(item, dict)}
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != CUSTODY_ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-custody-roadmap-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if "not a reserve lock claim" not in payload.get("scopeBoundary", ""):
        raise SiteCheckError(f"{label}: missing reserve-lock scope boundary")
    if current.get("ownerReserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong reserve wallet")
    if current.get("ownerHeldReserve") != "600000000":
        raise SiteCheckError(f"{label}: wrong ownerHeldReserve")
    if current.get("reserveCustodyType") != "normal-owner-controlled-wallet":
        raise SiteCheckError(f"{label}: wrong reserve custody type")
    for key in ("reserveLocked", "reserveVestingContract", "reserveMultisig", "lpLockClaimed", "lpBurnClaimed", "multisigLpCustodyClaimed"):
        if current.get(key) is not False:
            raise SiteCheckError(f"{label}: {key} must be false")
    if current.get("officialPool") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong officialPool")
    if current.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    for phase_id in ("disclosure-baseline", "safe-multisig-evaluation", "reserve-lock-or-vesting", "lp-lock-evaluation", "independent-audit-handoff"):
        if phase_id not in phases:
            raise SiteCheckError(f"{label}: missing phase {phase_id}")
    if phases["disclosure-baseline"].get("status") != "published":
        raise SiteCheckError(f"{label}: wrong baseline status")
    if phases["safe-multisig-evaluation"].get("status") != "not-started":
        raise SiteCheckError(f"{label}: multisig should be not-started")
    if phases["lp-lock-evaluation"].get("status") != "not-started":
        raise SiteCheckError(f"{label}: LP lock should be not-started")
    if links.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap link")
    if links.get("riskRemediation") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediation link")
    if links.get("liquidity") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidity link")
    if links.get("reserveStatement") != RESERVE_STATEMENT_URL:
        raise SiteCheckError(f"{label}: wrong reserveStatement link")
    if "GCA has published a custody roadmap and evidence checklist." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing custody roadmap safe claim")
    if "reserve is locked before on-chain custody changes" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing reserve-lock boundary")
    assert_current_pool_text(json.dumps(payload), label)
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_custody_roadmap_page(text: str) -> None:
    label = "/custody-roadmap.html"
    assert_social_preview_meta(text, label, CUSTODY_ROADMAP_PAGE_URL)
    assert_contains(text, "GCA Custody Roadmap", label)
    assert_contains(text, "Readable Custody Review Path", label)
    assert_contains(text, "Reserve Wallet", label)
    assert_contains(text, "Owner-controlled, not locked", label)
    assert_contains(text, "No LP lock claimed", label)
    assert_contains(text, "not a reserve lock claim", label)
    assert_contains(text, "Future Evidence Required", label)
    assert_contains(text, "Safe multisig", label)
    assert_contains(text, "Do not say LP is locked before verifiable lock evidence exists", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, RESERVE_WALLET, label)
    assert_current_pool_text(text, label)
    assert_no_forbidden_public_claims(text, label)
    assert_no_public_data_room_terms(text, label)
    for forbidden in (
        'href="custody-roadmap.json"',
        'href="reserve-statement.json"',
        'href="holder-distribution.json"',
        'href="liquidity.json"',
        'href="risk-remediation.json"',
        'href="onchain-proofs.json"',
    ):
        assert_not_contains(text, forbidden, label)


def validate_audit_readiness_json(text: str) -> None:
    label = "/audit-readiness.json"
    payload = load_json(text, label)
    status = payload.get("currentAuditStatus", {})
    scope = payload.get("contractScope", {})
    links = payload.get("officialLinks", {})
    boundaries = payload.get("publicClaimBoundaries", {})

    if payload.get("schema") != AUDIT_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != AUDIT_READINESS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-audit-readiness-package-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if "not a completed third-party audit" not in payload.get("scopeBoundary", ""):
        raise SiteCheckError(f"{label}: missing audit scope boundary")
    if status.get("thirdPartyAuditCompleted") is not False:
        raise SiteCheckError(f"{label}: thirdPartyAuditCompleted must be false")
    if status.get("thirdPartyAuditStatus") != "not-completed-deferred":
        raise SiteCheckError(f"{label}: wrong thirdPartyAuditStatus")
    if status.get("internalTechnicalReportPage") != TECHNICAL_REPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong internal technical report page")
    if scope.get("sourceFile") != "token/contracts/GCAToken.sol":
        raise SiteCheckError(f"{label}: wrong source file")
    if scope.get("standardJsonInput") != "verification/GCAToken.standard-json-input.json":
        raise SiteCheckError(f"{label}: wrong standard JSON input")
    if "Verified source matches deployed bytecode." not in payload.get("reviewChecklist", []):
        raise SiteCheckError(f"{label}: missing review checklist item")
    if "final report URL or signed PDF" not in payload.get("expectedAuditorDeliverables", []):
        raise SiteCheckError(f"{label}: missing auditor deliverable")
    if links.get("auditReadiness") != AUDIT_READINESS_URL:
        raise SiteCheckError(f"{label}: wrong auditReadiness link")
    if links.get("technicalReport") != TECHNICAL_REPORT_URL:
        raise SiteCheckError(f"{label}: wrong technicalReport link")
    if links.get("blockaidFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong blockaidFollowup link")
    if "No third-party audit has been completed." not in boundaries.get("safeClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "third-party audit completion before an independent final report is public" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing audit boundary")
    assert_contains(json.dumps(payload), MAINNET_ADDRESS, label)
    assert_no_forbidden_public_claims(json.dumps(payload), label)


def validate_audit_readiness_page(text: str) -> None:
    label = "/audit-readiness.html"
    assert_social_preview_meta(text, label, AUDIT_READINESS_PAGE_URL)
    assert_contains(text, "GCA Audit Readiness", label)
    assert_contains(text, "Readable Auditor Intake Path", label)
    assert_contains(text, "No completed third-party audit", label)
    assert_contains(text, "not a completed third-party audit", label)
    assert_contains(text, "Contract Scope", label)
    assert_contains(text, "token/contracts/GCAToken.sol", label)
    assert_contains(text, "verification/GCAToken.standard-json-input.json", label)
    assert_contains(text, "Review Checklist", label)
    assert_contains(text, "Expected Deliverables", label)
    assert_contains(text, "Do not say third-party audit completion before an independent final report is public", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_no_forbidden_public_claims(text, label)
    assert_no_public_data_room_terms(text, label)
    for forbidden in (
        'href="audit-readiness.json"',
        'href="technical-report.json"',
        'href="token-safety.json"',
        'href="blockaid-followup.json"',
        'href="risk-remediation.json"',
        'href="custody-roadmap.json"',
    ):
        assert_not_contains(text, forbidden, label)


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
    assert_contains(text, "On-chain References", label)
    assert_no_public_data_room_terms(text, label)
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
    handoff = payload.get("baseScanResubmissionHandoff", {})

    if payload.get("schema") != REVIEWER_KIT_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != REVIEWER_KIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("status") != "public-reviewer-kit-published":
        raise SiteCheckError(f"{label}: wrong status")
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
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
    if links.get("holderDistribution") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistribution")
    if links.get("riskRemediation") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediation")
    if links.get("custodyRoadmapPage") != CUSTODY_ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmapPage")
    if links.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap")
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
    if links.get("domainEmailSetupPlanPage") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailSetupPlanPage")
    if links.get("domainEmailSetupPlan") != DOMAIN_EMAIL_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailSetupPlan")
    if links.get("domainEmailEvidenceChecklistPage") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailEvidenceChecklistPage")
    if links.get("domainEmailEvidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailEvidenceChecklist")
    if links.get("baseScanHandoffPage") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoffPage")
    if links.get("baseScanHandoff") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoff")
    if links.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatusPage")
    if links.get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatus")
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
    if reviews.get("baseScanTokenProfile") != "ready-for-owner-resubmission":
        raise SiteCheckError(f"{label}: wrong BaseScan profile status")
    if reviews.get("baseScanTokenProfileLastCheckedDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong BaseScan profile last checked date")
    if reviews.get("baseScanFinalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong BaseScan final package timestamp")
    if reviews.get("dailyStatusGeneratedAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong daily status timestamp")
    if reviews.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong external-review dailyStatusPage")
    if reviews.get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong external-review dailyStatus")
    if reviews.get("baseScanDomainEmailGate") != "ready-domain-email-evidence-2026-05-30":
        raise SiteCheckError(f"{label}: wrong BaseScan domain email gate")
    if reviews.get("baseScanDomainEmailTarget") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong BaseScan domain email target")
    dns_snapshot = reviews.get("baseScanDomainEmailDnsSnapshot", {})
    if dns_snapshot.get("readyForBaseScanEmailEvidence") is not True:
        raise SiteCheckError(f"{label}: domain email DNS snapshot should be ready")
    if dns_snapshot.get("snapshotPage") not in {f"{DOMAIN_EMAIL_PAGE_URL}#snapshotTitle", None}:
        raise SiteCheckError(f"{label}: wrong domain email DNS snapshot page")
    if dns_snapshot.get("evidencePacket") not in {f"{DOMAIN_EMAIL_PAGE_URL}#evidenceTitle", None}:
        raise SiteCheckError(f"{label}: wrong domain email evidence packet")
    if dns_snapshot.get("evidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domain email evidence checklist")
    for key in ("mx", "spf", "dmarc", "dkim"):
        if dns_snapshot.get("checks", {}).get(key) != "present":
            raise SiteCheckError(f"{label}: {key} should be present")
    if set(dns_snapshot.get("missingOrBlockedChecks", [])) != set():
        raise SiteCheckError(f"{label}: wrong missing domain email checks")
    if reviews.get("blockaidMetaMask") != "owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong Blockaid status")
    if reviews.get("blockaidFollowUpSubmissionDate") != "2026-05-13":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up date")
    if reviews.get("geckoTerminal") != "approved-2026-05-11":
        raise SiteCheckError(f"{label}: wrong GeckoTerminal status")
    if reviews.get("coinGecko") != "deferred":
        raise SiteCheckError(f"{label}: wrong CoinGecko status")
    if handoff.get("status") != "ready-for-owner-resubmission":
        raise SiteCheckError(f"{label}: wrong BaseScan handoff status")
    if handoff.get("pageUrl") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong BaseScan handoff pageUrl")
    if handoff.get("dataUrl") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong BaseScan handoff dataUrl")
    if handoff.get("targetSender") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong BaseScan handoff target sender")
    if handoff.get("currentActiveContact") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong BaseScan handoff current contact")
    if handoff.get("readyForBaseScanResubmission") is not True:
        raise SiteCheckError(f"{label}: BaseScan handoff should be ready")
    if handoff.get("finalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong BaseScan handoff final package timestamp")
    if handoff.get("dailyStatusGeneratedAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong BaseScan handoff daily status timestamp")
    if handoff.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong BaseScan handoff dailyStatusPage")
    if handoff.get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong BaseScan handoff dailyStatus")
    required = set(handoff.get("requiredBeforeNextSubmission", []))
    if "tools/check_basescan_resubmission_readiness.py --json --require-ready passes" not in required:
        raise SiteCheckError(f"{label}: missing final preflight requirement")
    handoff_ids = {item.get("id") for item in handoff.get("evidenceIndex", [])}
    for expected_id in (
        "founder-team-transparency",
        "domain-email-plan",
        "domain-email-evidence-checklist",
        "basescan-preflight",
        "daily-status-queue",
        "technical-report",
        "onchain-proofs",
        "reserve-and-holder-disclosure",
        "official-market-route",
        "platform-reply-copy",
    ):
        if expected_id not in handoff_ids:
            raise SiteCheckError(f"{label}: missing BaseScan handoff evidence {expected_id}")
    handoff_text = json.dumps(handoff)
    for expected in (
        TIM_CHEN_PROFILE_PAGE_URL,
        DOMAIN_EMAIL_PAGE_URL,
        DOMAIN_EMAIL_EVIDENCE_PAGE_URL,
        BASESCAN_PREFLIGHT_PAGE_URL,
        DAILY_STATUS_PAGE_URL,
        TECHNICAL_REPORT_PAGE_URL,
        ONCHAIN_PROOFS_PAGE_URL,
        RESERVE_STATEMENT_PAGE_URL,
        HOLDER_DISTRIBUTION_PAGE_URL,
        LIQUIDITY_PAGE_URL,
        PLATFORM_REPLIES_PAGE_URL,
    ):
        assert_contains(handoff_text, expected, label)
    for key in ("submitsBaseScanRequest", "sendsEmail", "writesDns", "claimsBaseScanApproval", "publishesPrivateMailboxEvidence"):
        if handoff.get("boundaries", {}).get(key) is not False:
            raise SiteCheckError(f"{label}: BaseScan handoff boundary {key} must be false")
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
    if payload.get("evidenceLinks", {}).get("liquidityStatement") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidity evidence link")
    if payload.get("evidenceLinks", {}).get("baseScanResubmissionHandoff") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong BaseScan handoff evidence link")
    if payload.get("evidenceLinks", {}).get("custodyRoadmap") != CUSTODY_ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong custody roadmap evidence link")
    if payload.get("evidenceLinks", {}).get("domainEmailSetupPlan") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domain email setup evidence link")
    if payload.get("evidenceLinks", {}).get("domainEmailDnsSnapshot") != f"{DOMAIN_EMAIL_PAGE_URL}#snapshotTitle":
        raise SiteCheckError(f"{label}: wrong domain email DNS snapshot evidence link")
    if payload.get("evidenceLinks", {}).get("domainEmailEvidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domain email evidence checklist link")
    if payload.get("evidenceLinks", {}).get("domainEmailActivationEvidencePacket") != f"{DOMAIN_EMAIL_PAGE_URL}#evidenceTitle":
        raise SiteCheckError(f"{label}: wrong domain email activation evidence link")
    if payload.get("evidenceLinks", {}).get("dailyStatus") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong daily status evidence link")
    next_actions = " ".join(payload.get("reviewerUse", {}).get("nextActions", []))
    if DOMAIN_EMAIL_EVIDENCE_PAGE_URL not in next_actions:
        raise SiteCheckError(f"{label}: missing domain email evidence checklist next action")
    if "2026-06-06T11:10:54Z" not in next_actions:
        raise SiteCheckError(f"{label}: missing final package timestamp next action")
    if "2026-06-07T13:06:12Z" not in next_actions:
        raise SiteCheckError(f"{label}: missing daily status timestamp next action")
    if "security-vendor approval, permanent warning-free status, or cross-wallet warning removal before vendor/current wallet UI confirms it" not in boundaries.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing warning boundary")
    assert_current_pool_text(json.dumps(payload), label)


def validate_reviewer_kit_page(text: str) -> None:
    label = "/reviewer-kit.html"
    assert_contains(text, "GCA Reviewer Kit", label)
    assert_contains(text, "BaseScan Resubmission Handoff", label)
    assert_contains(text, "BaseScan Handoff", label)
    assert_contains(text, "basescan-handoff.html", label)
    assert_contains(text, "Readable Reviewer Path", label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "GCA/USDT", label)
    assert_contains(text, "Contract Facts", label)
    assert_contains(text, "Blockaid / MetaMask", label)
    assert_contains(text, "Blockaid Follow-up", label)
    assert_contains(text, "Follow-up submitted on 2026-05-13", label)
    assert_contains(text, "Liquidity Statement", label)
    assert_contains(text, "Holder Distribution", label)
    assert_contains(text, "Risk Remediation", label)
    assert_contains(text, "Custody Roadmap", label)
    assert_contains(text, "BaseScan Profile", label)
    assert_contains(text, "Current gate", label)
    assert_contains(text, "readyForBaseScanResubmission", label)
    assert_contains(text, "submit one clean owner-controlled request", label)
    assert_contains(text, "Founder / team transparency", label)
    assert_contains(text, "Team profile", label)
    assert_contains(text, "Tim Chen professional profile", label)
    assert_contains(text, "Domain Email Gate", label)
    assert_contains(text, "Final preflight gate", label)
    assert_contains(text, "Daily Status Queue", label)
    assert_contains(text, "Latest reviewer package", label)
    assert_contains(text, "Final package generated 2026-06-06T11:10:54Z; daily status refreshed 2026-06-07T13:06:12Z", label)
    assert_contains(text, "2026-06-06T11:10:54Z", label)
    assert_contains(text, "2026-06-07T13:06:12Z", label)
    assert_contains(text, "Contract and safety evidence", label)
    assert_contains(text, "Supply and reserve evidence", label)
    assert_contains(text, "Market route evidence", label)
    assert_contains(text, "Reviewer copy", label)
    assert_contains_any(text, ("2026-05-25 DNS snapshot", "2026-05-30 DNS snapshot"), label, "DNS snapshot")
    assert_contains(text, "MX/SPF/DKIM/DMARC present", label)
    assert_contains(text, "readyForBaseScanEmailEvidence", label)
    assert_contains(text, "domain-email.html#snapshotTitle", label)
    assert_contains(text, "domain-email-evidence.html", label)
    assert_contains(text, "Evidence Checklist", label)
    assert_contains(text, "public evidence checklist", label)
    assert_contains(text, "domain-email.html#evidenceTitle", label)
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
    assert_no_public_data_room_terms(text, label)
    for forbidden in (
        'href="reviewer-kit.json"',
        'href="project.json"',
        'href="tokenlist.json"',
        'href=".well-known/gca-token.json"',
        'href=".well-known/wallet-security.json"',
        'href="blockaid-followup.json"',
        'href="liquidity.json"',
        'href="holder-distribution.json"',
        'href="risk-remediation.json"',
        'href="custody-roadmap.json"',
        'href="audit-readiness.json"',
        'href="technical-report.json"',
        'href="reserve-statement.json"',
    ):
        assert_not_contains(text, forbidden, label)


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
    if payload.get("officialEmail") != "support@gcagochina.com":
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
    if links.get("teamPage") != TEAM_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong teamPage")
    if links.get("timChenProfessionalProfile") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong timChenProfessionalProfile")
    if links.get("timChenProfessionalProfileData") != TIM_CHEN_PROFILE_URL:
        raise SiteCheckError(f"{label}: wrong timChenProfessionalProfileData")
    if links.get("baseScanRemediationPage") != BASESCAN_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanRemediationPage")
    if links.get("baseScanRemediation") != BASESCAN_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong baseScanRemediation")
    if links.get("domainEmailSetupPlan") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailSetupPlan")
    if links.get("domainEmailSetupPlanData") != DOMAIN_EMAIL_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailSetupPlanData")
    if links.get("domainEmailEvidenceChecklistPage") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailEvidenceChecklistPage")
    if links.get("domainEmailEvidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailEvidenceChecklist")
    if links.get("supportPage") != SUPPORT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong supportPage")
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
    basescan_body = "\n".join(templates.get("baseScanProfile", {}).get("body", []))
    for expected in (
        "BaseScan returned the request again as information-insufficient on 2026-05-23",
        "Tim Chen professional profile: https://gcagochina.com/tim-chen.html",
        "Domain email setup plan: https://gcagochina.com/domain-email.html",
        "Domain email setup data: https://gcagochina.com/domain-email.json",
        "Domain email evidence checklist: https://gcagochina.com/domain-email-evidence.html",
        "Domain email evidence checklist data: https://gcagochina.com/domain-email-evidence.json",
        "Domain email activation evidence packet: https://gcagochina.com/domain-email.html#evidenceTitle",
        "Latest domain email DNS snapshot: https://gcagochina.com/domain-email.html#snapshotTitle",
        "Return-notice response:",
        "the current active project-domain email is support@gcagochina.com",
        "public evidence checklist at https://gcagochina.com/domain-email-evidence.html defines the provider-status",
        "private screenshots remain local until a reviewer asks for them",
        "read-only DNS snapshot shows MX/SPF/DKIM/DMARC present",
        "readyForBaseScanEmailEvidence is true",
        "activation evidence packet defines the provider-status, DNS, inbound, outbound, and website-email proof",
        "We will not claim BaseScan token profile approval until BaseScan publishes the profile.",
    ):
        if expected not in basescan_body:
            raise SiteCheckError(f"{label}: BaseScan template missing {expected}")
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
    assert_contains(text, "Readable Platform Reply Path", label)
    assert_no_public_data_room_terms(text, label)
    for forbidden in (
        "platform-replies.json",
        "reviewer-kit.json",
        "wallet-warning.json",
        "external-reviews.json",
        "listing-readiness.json",
        "project.json",
    ):
        assert_not_contains(text, f'href="{forbidden}"', label)
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "Wallet Warning Reviewer", label)
    assert_contains(text, "BaseScan Token Profile", label)
    assert_contains(text, "BaseScan returned the request again as information-insufficient on 2026-05-23", label)
    assert_contains(text, "Tim Chen professional profile: https://gcagochina.com/tim-chen.html", label)
    assert_contains(text, "BaseScan remediation tracker: https://gcagochina.com/basescan-remediation.html", label)
    assert_contains(text, "Domain email setup plan: https://gcagochina.com/domain-email.html", label)
    assert_contains(text, "Domain email setup data: https://gcagochina.com/domain-email.json", label)
    assert_contains(text, "Domain email evidence checklist: https://gcagochina.com/domain-email-evidence.html", label)
    assert_contains(text, "Domain email evidence checklist data: https://gcagochina.com/domain-email-evidence.json", label)
    assert_contains(text, "Domain email activation evidence packet: https://gcagochina.com/domain-email.html#evidenceTitle", label)
    assert_contains(text, "Latest domain email DNS snapshot: https://gcagochina.com/domain-email.html#snapshotTitle", label)
    assert_contains(text, "the current active project-domain email is support@gcagochina.com", label)
    assert_contains(text, "public evidence checklist at https://gcagochina.com/domain-email-evidence.html defines the provider-status", label)
    assert_contains(text, "private screenshots remain local until a reviewer asks for them", label)
    assert_contains(text, "read-only DNS snapshot shows MX/SPF/DKIM/DMARC present", label)
    assert_contains(text, "readyForBaseScanEmailEvidence is true", label)
    assert_contains(text, "activation evidence packet defines the provider-status, DNS, inbound, outbound, and website-email proof", label)
    assert_contains(text, "Metadata Correction", label)
    assert_contains(text, "Local Review Package Handoff", label)
    assert_contains(text, "Community Moderator", label)
    assert_contains(text, "Tracked Listing Deferred", label)
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
    if payload.get("lastUpdated") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong lastUpdated")
    if payload.get("chainId") != 8453:
        raise SiteCheckError(f"{label}: wrong chainId")
    if payload.get("contractAddress") != MAINNET_ADDRESS:
        raise SiteCheckError(f"{label}: wrong contractAddress")
    if payload.get("officialEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong officialEmail")
    if links.get("trustCenterPage") != TRUST_CENTER_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong trustCenterPage")
    if links.get("trustCenter") != TRUST_CENTER_URL:
        raise SiteCheckError(f"{label}: wrong trustCenter")
    for key, expected in {
        "verify": "https://gcagochina.com/verify.html",
        "reviewerKit": REVIEWER_KIT_URL,
        "platformReplies": PLATFORM_REPLIES_URL,
        "domainEmailSetupPlanPage": DOMAIN_EMAIL_PAGE_URL,
        "domainEmailSetupPlan": DOMAIN_EMAIL_URL,
        "domainEmailEvidenceChecklistPage": DOMAIN_EMAIL_EVIDENCE_PAGE_URL,
        "domainEmailEvidenceChecklist": DOMAIN_EMAIL_EVIDENCE_URL,
        "dailyStatusPage": DAILY_STATUS_PAGE_URL,
        "dailyStatus": DAILY_STATUS_URL,
        "walletWarningEvidence": WALLET_WARNING_URL,
        "blockaidFollowup": BLOCKAID_FOLLOWUP_URL,
        "walletSecurityProfile": WALLET_SECURITY_PROFILE_URL,
        "tokenSafetyPage": TOKEN_SAFETY_PAGE_URL,
        "tokenSafety": TOKEN_SAFETY_URL,
        "liquidity": LIQUIDITY_URL,
        "liquidityPage": LIQUIDITY_PAGE_URL,
        "holderDistribution": HOLDER_DISTRIBUTION_URL,
        "holderDistributionPage": HOLDER_DISTRIBUTION_PAGE_URL,
        "riskRemediation": RISK_REMEDIATION_URL,
        "riskRemediationPage": RISK_REMEDIATION_PAGE_URL,
        "custodyRoadmap": CUSTODY_ROADMAP_URL,
        "custodyRoadmapPage": CUSTODY_ROADMAP_PAGE_URL,
        "auditReadiness": AUDIT_READINESS_URL,
        "auditReadinessPage": AUDIT_READINESS_PAGE_URL,
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
    if snapshot.get("baseScanTokenProfile") != "ready-for-owner-resubmission":
        raise SiteCheckError(f"{label}: wrong BaseScan token profile status")
    if snapshot.get("baseScanTokenProfileLastCheckedDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong BaseScan token profile last checked date")
    if snapshot.get("baseScanFinalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong BaseScan final package timestamp")
    if snapshot.get("dailyStatusGeneratedAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong daily status timestamp")
    if snapshot.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong snapshot dailyStatusPage")
    if snapshot.get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong snapshot dailyStatus")
    if snapshot.get("baseScanDomainEmailGate") != "ready-domain-email-evidence-2026-05-30":
        raise SiteCheckError(f"{label}: wrong BaseScan domain email gate")
    if snapshot.get("baseScanDomainEmailTarget") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong BaseScan domain email target")
    dns_snapshot = snapshot.get("baseScanDomainEmailDnsSnapshot", {})
    if dns_snapshot.get("readyForBaseScanEmailEvidence") is not True:
        raise SiteCheckError(f"{label}: domain email DNS snapshot should be ready")
    if dns_snapshot.get("snapshotPage") not in {f"{DOMAIN_EMAIL_PAGE_URL}#snapshotTitle", None}:
        raise SiteCheckError(f"{label}: wrong domain email DNS snapshot page")
    if dns_snapshot.get("evidencePacket") not in {f"{DOMAIN_EMAIL_PAGE_URL}#evidenceTitle", None}:
        raise SiteCheckError(f"{label}: wrong domain email evidence packet")
    if dns_snapshot.get("evidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domain email evidence checklist")
    for key in ("mx", "spf", "dmarc", "dkim"):
        if dns_snapshot.get("checks", {}).get(key) != "present":
            raise SiteCheckError(f"{label}: {key} should be present")
    if set(dns_snapshot.get("missingOrBlockedChecks", [])) != set():
        raise SiteCheckError(f"{label}: wrong missing domain email checks")
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
    if market.get("liquidityStatementPage") != LIQUIDITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong liquidityStatementPage")
    if market.get("liquidityStatement") != LIQUIDITY_URL:
        raise SiteCheckError(f"{label}: wrong liquidityStatement")
    if market.get("lpLockClaimed") is not False:
        raise SiteCheckError(f"{label}: LP lock must not be claimed")
    if supply.get("ownerReserveWallet") != RESERVE_WALLET:
        raise SiteCheckError(f"{label}: wrong ownerReserveWallet")
    if supply.get("holderDistribution") != HOLDER_DISTRIBUTION_URL:
        raise SiteCheckError(f"{label}: wrong holderDistribution")
    if supply.get("custodyRoadmapPage") != CUSTODY_ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmapPage")
    if supply.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap")
    if supply.get("ownerReserveTransferTxs") != [RESERVE_TX_1, RESERVE_TX_2]:
        raise SiteCheckError(f"{label}: wrong reserve transfer txs")
    if payload.get("blockaidFollowup", {}).get("status") != "public-blockaid-followup-package-published":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up status")
    if payload.get("blockaidFollowup", {}).get("url") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up URL")
    if reviews.get("thirdPartyAudit") != "not-completed-deferred":
        raise SiteCheckError(f"{label}: wrong third-party audit status")
    if reviews.get("baseScanTokenProfileLastCheckedDate") != "2026-06-07":
        raise SiteCheckError(f"{label}: wrong external-review BaseScan last checked date")
    if reviews.get("baseScanFinalSubmissionPackageGeneratedAt") != "2026-06-06T11:10:54Z":
        raise SiteCheckError(f"{label}: wrong external-review final package timestamp")
    if reviews.get("dailyStatusGeneratedAt") != "2026-06-07T13:06:12Z":
        raise SiteCheckError(f"{label}: wrong external-review daily status timestamp")
    if reviews.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong external-review dailyStatusPage")
    if reviews.get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong external-review dailyStatus")
    if reviews.get("baseScanDomainEmailGate") != "ready-domain-email-evidence-2026-05-30":
        raise SiteCheckError(f"{label}: wrong external-review domain email gate")
    if reviews.get("baseScanDomainEmailTarget") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong external-review domain email target")
    if "The official domain email support@gcagochina.com is active, public DNS records pass MX/SPF/DKIM/DMARC checks, and private mail-flow evidence is retained for reviewer follow-up." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing domain email safe claim")
    if "The latest BaseScan owner submission package was generated on 2026-06-06T11:10:54Z, and the daily public status snapshot was refreshed on 2026-06-07T13:06:12Z." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing latest BaseScan package safe claim")
    if "No third-party audit has been completed." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    if "security-vendor approval, permanent warning-free status, or cross-wallet warning removal before vendor/current wallet UI confirms it" not in payload.get("doNotClaim", []):
        raise SiteCheckError(f"{label}: missing warning do-not-claim")
    assert_current_pool_text(json.dumps(payload), label)


def validate_trust_page(text: str) -> None:
    label = "/trust.html"
    assert_contains(text, "GCA Trust Center", label)
    assert_contains(text, "Trust References", label)
    assert_no_public_data_room_terms(text, label)
    for forbidden in ("trust.json", ".well-known/wallet-security.json", "tokenlist.json", "project.json", ".well-known/gca-token.json"):
        assert_not_contains(text, f'href="{forbidden}"', label)
    assert_contains(text, "Verification Snapshot", label)
    assert_contains(text, "Contract Facts", label)
    assert_contains(text, "Market And Liquidity", label)
    assert_contains(text, "Supply And Reserve", label)
    assert_contains(text, "Evidence Links", label)
    assert_contains(text, "Normal visitor path", label)
    assert_contains(text, "Blockaid Follow-up", label)
    assert_contains(text, "Liquidity Statement", label)
    assert_contains(text, "Holder Distribution", label)
    assert_contains(text, "Risk Remediation", label)
    assert_contains(text, "Custody Roadmap", label)
    assert_contains(text, "Public Claim Boundaries", label)
    assert_contains(text, "Base Mainnet / 8453", label)
    assert_contains(text, MAINNET_ADDRESS, label)
    assert_contains(text, "BaseScan source code", label)
    assert_contains(text, "Returned 2026-05-23; final package refreshed 2026-06-06; Handoff and Chinese owner flow ready for one support@gcagochina.com submission", label)
    assert_contains(text, "BaseScan domain email evidence", label)
    assert_contains(text, "Latest reviewer package", label)
    assert_contains(text, "Final package 2026-06-06T11:10:54Z; daily status 2026-06-07T13:06:12Z", label)
    assert_contains(text, "2026-06-06T11:10:54Z", label)
    assert_contains(text, "2026-06-07T13:06:12Z", label)
    assert_contains_any(text, ("2026-05-25 DNS snapshot", "2026-05-30 DNS snapshot"), label, "DNS snapshot")
    assert_contains(text, "MX/SPF/DKIM/DMARC present", label)
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
    email_alignment = payload.get("emailAlignment", {})

    if payload.get("schema") != EXTERNAL_REVIEW_URL:
        raise SiteCheckError(f"{label}: wrong schema")
    if payload.get("pageUrl") != EXTERNAL_REVIEW_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong pageUrl")
    if payload.get("lastUpdated") not in {"2026-05-25", "2026-05-30", "2026-06-02", "2026-06-05", "2026-06-07"}:
        raise SiteCheckError(f"{label}: wrong lastUpdated")
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
    if links.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatusPage")
    if links.get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatus")
    if links.get("platformRepliesPage") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformRepliesPage")
    if links.get("platformReplies") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong platformReplies")
    if links.get("marketQualityPage") != MARKET_QUALITY_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong marketQualityPage")
    if links.get("teamPage") != TEAM_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong teamPage")
    if links.get("baseScanHandoffPage") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoffPage")
    if links.get("baseScanHandoff") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoff")
    if links.get("baseScanChineseOwnerFlow") != ZH_BASESCAN_SUBMIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanChineseOwnerFlow")
    if email_alignment.get("currentPublicEmail") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong currentPublicEmail")
    if email_alignment.get("targetDomainEmailAfterActivation") != "support@gcagochina.com":
        raise SiteCheckError(f"{label}: wrong targetDomainEmailAfterActivation")
    if email_alignment.get("status") != "target-domain-email-active-evidence-ready":
        raise SiteCheckError(f"{label}: wrong email alignment status")
    if email_alignment.get("domainEmailSetupPlan") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong email alignment domainEmailSetupPlan")
    if email_alignment.get("domainEmailEvidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong email alignment domainEmailEvidenceChecklist")
    if email_alignment.get("activationEvidencePacket") != f"{DOMAIN_EMAIL_PAGE_URL}#evidenceTitle":
        raise SiteCheckError(f"{label}: wrong email alignment activationEvidencePacket")
    if "Use support@gcagochina.com" not in email_alignment.get("baseScanUse", ""):
        raise SiteCheckError(f"{label}: missing email alignment boundary")
    base_scan_profile = reviews.get("baseScanTokenProfile", {})
    if base_scan_profile.get("professionalProfile") != TIM_CHEN_PROFILE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong professionalProfile")
    if base_scan_profile.get("domainEmailSetupPlan") != DOMAIN_EMAIL_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailSetupPlan")
    if base_scan_profile.get("domainEmailSetupPlanData") != DOMAIN_EMAIL_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailSetupPlanData")
    if base_scan_profile.get("domainEmailDnsSnapshot") != f"{DOMAIN_EMAIL_PAGE_URL}#snapshotTitle":
        raise SiteCheckError(f"{label}: wrong domainEmailDnsSnapshot")
    if base_scan_profile.get("domainEmailEvidenceChecklist") != DOMAIN_EMAIL_EVIDENCE_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailEvidenceChecklist")
    if base_scan_profile.get("domainEmailEvidenceChecklistData") != DOMAIN_EMAIL_EVIDENCE_URL:
        raise SiteCheckError(f"{label}: wrong domainEmailEvidenceChecklistData")
    if base_scan_profile.get("domainEmailActivationEvidencePacket") != "https://gcagochina.com/domain-email.html#evidenceTitle":
        raise SiteCheckError(f"{label}: wrong domainEmailActivationEvidencePacket")
    if "archive the activation evidence packet" not in base_scan_profile.get("nextAction", ""):
        raise SiteCheckError(f"{label}: missing activation evidence packet next action")
    if DOMAIN_EMAIL_EVIDENCE_PAGE_URL not in base_scan_profile.get("nextAction", ""):
        raise SiteCheckError(f"{label}: missing domain email evidence checklist next action")
    if BASESCAN_HANDOFF_PAGE_URL not in base_scan_profile.get("nextAction", ""):
        raise SiteCheckError(f"{label}: missing BaseScan handoff next action")
    if ZH_BASESCAN_SUBMIT_PAGE_URL not in base_scan_profile.get("nextAction", ""):
        raise SiteCheckError(f"{label}: missing Chinese owner flow next action")
    dns_readiness = base_scan_profile.get("domainEmailDnsReadiness", {})
    if dns_readiness.get("readyForBaseScanEmailEvidence") is not True:
        raise SiteCheckError(f"{label}: domain email DNS readiness should be true")
    for key in ("mx", "spf", "dmarc", "dkim"):
        if dns_readiness.get("checks", {}).get(key) != "present":
            raise SiteCheckError(f"{label}: {key} should be present")
    if set(dns_readiness.get("missingOrBlockedChecks", [])) != set():
        raise SiteCheckError(f"{label}: wrong domain email missing checks")
    if links.get("baseScanRemediationPage") != BASESCAN_REMEDIATION_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanRemediationPage")
    if links.get("baseScanRemediation") != BASESCAN_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong baseScanRemediation")
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
    if links.get("riskRemediation") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong riskRemediation")
    if links.get("custodyRoadmapPage") != CUSTODY_ROADMAP_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmapPage")
    if links.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong custodyRoadmap")
    if market.get("officialPair") != "GCA/USDT":
        raise SiteCheckError(f"{label}: wrong officialPair")
    if market.get("poolAddress") != OFFICIAL_POOL_ADDRESS:
        raise SiteCheckError(f"{label}: wrong poolAddress")
    if market.get("quoteAssetAddress") != BASE_USDT_ADDRESS:
        raise SiteCheckError(f"{label}: wrong quoteAssetAddress")
    if reviews.get("baseScanSource", {}).get("status") != "verified":
        raise SiteCheckError(f"{label}: wrong BaseScan source status")
    if base_scan_profile.get("status") != "ready-for-owner-resubmission":
        raise SiteCheckError(f"{label}: wrong BaseScan profile status")
    if base_scan_profile.get("lastCheckedDate") not in {"2026-05-30", "2026-06-02", "2026-06-05", "2026-06-07"}:
        raise SiteCheckError(f"{label}: wrong BaseScan profile last checked date")
    if "Tim Chen official-domain professional profile evidence is published" not in base_scan_profile.get("lastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing BaseScan profile last checked result")
    if "domain email setup plan" not in base_scan_profile.get("lastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing BaseScan domain email plan result")
    if "public evidence checklist" not in base_scan_profile.get("lastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing BaseScan domain email evidence checklist result")
    if "activation evidence packet" not in base_scan_profile.get("lastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing BaseScan domain email evidence packet result")
    if not (
        "2026-05-25 DNS snapshot" in base_scan_profile.get("lastCheckedResult", "")
        or "2026-05-30 DNS snapshot" in base_scan_profile.get("lastCheckedResult", "")
    ):
        raise SiteCheckError(f"{label}: missing latest DNS snapshot result")
    if "readyForBaseScanEmailEvidence is true" not in base_scan_profile.get("lastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing readyForBaseScanEmailEvidence boundary")
    if base_scan_profile.get("domainEmailActivationEvidencePacket") != "https://gcagochina.com/domain-email.html#evidenceTitle":
        raise SiteCheckError(f"{label}: wrong domainEmailActivationEvidencePacket")
    if "expanded BaseScan reply template" not in base_scan_profile.get("lastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing BaseScan reply template result")
    if "BaseScan Handoff copy blocks" not in base_scan_profile.get("lastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing BaseScan handoff result")
    if "Chinese owner submission flow" not in base_scan_profile.get("lastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing Chinese owner flow result")
    if "2026-06-06T11:10:54Z" not in base_scan_profile.get("lastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing final owner package timestamp")
    if "2026-06-07T13:06:12Z" not in base_scan_profile.get("lastCheckedResult", ""):
        raise SiteCheckError(f"{label}: missing daily status snapshot timestamp")
    if base_scan_profile.get("baseScanHandoffPage") != BASESCAN_HANDOFF_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoffPage")
    if base_scan_profile.get("baseScanHandoff") != BASESCAN_HANDOFF_URL:
        raise SiteCheckError(f"{label}: wrong baseScanHandoff")
    if base_scan_profile.get("dailyStatusPage") != DAILY_STATUS_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatusPage")
    if base_scan_profile.get("dailyStatus") != DAILY_STATUS_URL:
        raise SiteCheckError(f"{label}: wrong dailyStatus")
    if base_scan_profile.get("chineseOwnerSubmissionFlow") != ZH_BASESCAN_SUBMIT_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong chineseOwnerSubmissionFlow")
    if base_scan_profile.get("platformReplyTemplate") != PLATFORM_REPLIES_PAGE_URL:
        raise SiteCheckError(f"{label}: wrong platformReplyTemplate")
    if base_scan_profile.get("platformReplyTemplateData") != PLATFORM_REPLIES_URL:
        raise SiteCheckError(f"{label}: wrong platformReplyTemplateData")
    blockaid = reviews.get("blockaidMetaMask", {})
    if blockaid.get("status") != "owner-observed-no-warning-visible":
        raise SiteCheckError(f"{label}: wrong Blockaid status")
    if blockaid.get("submissionDate") != "2026-05-10":
        raise SiteCheckError(f"{label}: wrong Blockaid submission date")
    if blockaid.get("followUpSubmissionDate") != "2026-05-13":
        raise SiteCheckError(f"{label}: wrong Blockaid follow-up date")
    if blockaid.get("riskFactorFollowup") != BLOCKAID_FOLLOWUP_URL:
        raise SiteCheckError(f"{label}: wrong Blockaid risk-factor follow-up URL")
    if blockaid.get("riskRemediation") != RISK_REMEDIATION_URL:
        raise SiteCheckError(f"{label}: wrong Blockaid risk remediation URL")
    if blockaid.get("custodyRoadmap") != CUSTODY_ROADMAP_URL:
        raise SiteCheckError(f"{label}: wrong Blockaid custody roadmap URL")
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
    if "The BaseScan domain email evidence gate is ready after the 2026-05-30 DNS snapshot: MX/SPF/DKIM/DMARC present." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing domain email safe claim")
    if "The latest BaseScan final submission package was generated on 2026-06-06T11:10:54Z, and the daily public status snapshot confirms readyForBaseScanResubmission is true." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing final package safe claim")
    if "No third-party audit has been completed." not in payload.get("safePublicClaims", []):
        raise SiteCheckError(f"{label}: missing audit safe claim")
    assert_not_contains(json.dumps(payload), OLD_WETH_POOL_ADDRESS, label)


def validate_external_reviews_page(text: str) -> None:
    label = "/external-reviews.html"
    assert_contains(text, "GCA External Review Status", label)
    assert_contains(text, "Wallet Warning Evidence", label)
    assert_contains(text, "Blockaid Follow-up", label)
    assert_contains(text, "Risk Remediation", label)
    assert_contains(text, "Custody Roadmap", label)
    assert_contains(text, "External Review References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Trust Center", label)
    assert_contains(text, "Returned 2026-05-23; final package refreshed 2026-06-06 for one support@gcagochina.com submission", label)
    assert_contains(text, "Tim Chen profile, domain email plan, evidence checklist, activation evidence packet, reply template, BaseScan Handoff copy blocks, Chinese owner flow, and support@gcagochina.com evidence are ready", label)
    assert_contains(text, "2026-06-06T11:10:54Z", label)
    assert_contains(text, "2026-06-07T13:06:12Z", label)
    assert_contains(text, "tim-chen.html", label)
    assert_contains(text, "Domain Email Plan", label)
    assert_contains(text, "DNS Snapshot", label)
    assert_contains(text, "Email Evidence Packet", label)
    assert_contains(text, "BaseScan Handoff", label)
    assert_contains(text, "basescan-handoff.html", label)
    assert_contains(text, "中文 BaseScan 提交流程", label)
    assert_contains(text, "zh-basescan-submit.html", label)
    assert_contains(text, "no wallet transaction, approve, swap, or contract operation is needed", label)
    assert_contains(text, "domain-email.html#snapshotTitle", label)
    assert_contains(text, "domain-email-evidence.html", label)
    assert_contains(text, "Evidence Checklist", label)
    assert_contains(text, "Domain email evidence checklist", label)
    assert_contains(text, "domain-email.html#evidenceTitle", label)
    assert_contains(text, "domain-email.html", label)
    assert_contains(text, "BaseScan domain email evidence", label)
    assert_contains(text, "Domain Email Alignment", label)
    assert_contains(text, "support@gcagochina.com", label)
    assert_contains(text, "Active and evidence-ready", label)
    assert_contains_any(text, ("2026-05-25 DNS snapshot", "2026-05-30 DNS snapshot"), label, "DNS snapshot")
    assert_contains(text, "MX/SPF/DKIM/DMARC present", label)
    assert_contains(text, "readyForBaseScanEmailEvidence true", label)
    assert_contains(text, "expanded BaseScan reply template", label)
    assert_contains(text, "Platform Replies", label)
    assert_contains(text, "platform-replies.html", label)
    assert_contains(text, "Owner observed no warning visible 2026-05-14", label)
    assert_contains(text, "Approved 2026-05-11", label)
    assert_contains(text, "CoinGecko tracked listing submission", label)
    assert_contains(text, "CoinMarketCap tracked listing submission", label)
    assert_contains(text, "No third-party audit has been completed", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)
    for forbidden in (
        'href="external-reviews.json"',
        'href="project.json"',
        'href="reviewer-kit.json"',
        'href="listing-readiness.json"',
        'href="market-quality.json"',
        'href="wallet-warning.json"',
    ):
        assert_not_contains(text, forbidden, label)


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
    assert_contains(text, "Token Safety Checklist", label)
    assert_contains(text, "Wallet Warning References", label)
    assert_no_public_data_room_terms(text, label)
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
    for forbidden in (
        'href="wallet-warning.json"',
        'href=".well-known/wallet-security.json"',
        'href="project.json"',
        'href="token-safety.json"',
        'href="reviewer-kit.json"',
    ):
        assert_not_contains(text, forbidden, label)


def validate_listing_readiness_page(text: str) -> None:
    label = "/listing-readiness.html"
    assert_contains(text, "GCA Listing Readiness", label)
    assert_contains(text, "Listing Readiness References", label)
    assert_no_public_data_room_terms(text, label)
    assert_contains(text, "Status: Deferred", label)
    assert_contains(text, "Early-stage", label)
    assert_contains(text, "Deferred pending independent report", label)
    assert_contains(text, "DEX metadata and wallet identity review", label)
    assert_contains(text, "CoinGecko tracked listing request", label)
    assert_contains(text, "CoinMarketCap tracked listing request", label)
    assert_contains(text, "Returned again 2026-05-23; final package refreshed 2026-06-06; Handoff and Chinese owner flow ready for one support@gcagochina.com submission", label)
    assert_contains(text, "Tim Chen profile, domain email plan, evidence checklist, activation evidence packet, BaseScan Handoff, Chinese owner flow, and support@gcagochina.com evidence are ready", label)
    assert_contains(text, "Plan, public evidence checklist, and packet path published; mailbox active and evidence retained privately", label)
    assert_contains(text, "Snapshot refreshed 2026-06-07T13:06:12Z", label)
    assert_contains(text, "Final submission package generated 2026-06-06T11:10:54Z", label)
    assert_contains(text, "Domain Email Evidence Checklist", label)
    assert_contains(text, "domain-email-evidence.html", label)
    assert_contains(text, "Tim Chen Professional Profile", label)
    assert_contains(text, "Approved 2026-05-11", label)
    assert_contains(text, "No artificial activity policy", label)
    assert_contains(text, OFFICIAL_DEXSCREENER_URL, label)
    assert_contains(text, OFFICIAL_GECKOTERMINAL_URL, label)
    assert_current_pool_text(text, label)


def validate_security_txt(text: str) -> None:
    label = "/.well-known/security.txt"
    assert_contains(text, "Contact: mailto:support@gcagochina.com", label)
    assert_contains(text, "Preferred-Languages: en, zh", label)
    assert_contains(text, "Policy: https://gcagochina.com/security.html", label)
    assert_contains(text, "Canonical: https://gcagochina.com/.well-known/security.txt", label)
    assert_contains(text, "Expires: 2027-05-12T00:00:00+07:00", label)
    assert_not_contains(text, "GCAgochina@outlook.com", label)


def validate_sitemap(text: str) -> None:
    label = "/sitemap.xml"

    def assert_sitemap_lastmod(path: str, expected: str) -> None:
        pattern = re.compile(
            rf"<loc>https://gcagochina\.com/{re.escape(path)}</loc>\s*<lastmod>(?P<lastmod>[^<]+)</lastmod>"
        )
        match = pattern.search(text)
        if not match:
            raise SiteCheckError(f"{label}: missing sitemap entry for {path}")
        if match.group("lastmod") != expected:
            raise SiteCheckError(f"{label}: wrong lastmod for {path}")

    for expected in (
        "https://gcagochina.com/start.html",
        "https://gcagochina.com/about.html",
        "https://gcagochina.com/team.html",
        "https://gcagochina.com/tim-chen.html",
        "https://gcagochina.com/tim-chen.json",
        "https://gcagochina.com/domain-email.html",
        "https://gcagochina.com/domain-email.json",
        "https://gcagochina.com/domain-email-evidence.html",
        "https://gcagochina.com/domain-email-evidence.json",
        "https://gcagochina.com/basescan-remediation.html",
        "https://gcagochina.com/basescan-remediation.json",
        "https://gcagochina.com/basescan-preflight.html",
        "https://gcagochina.com/basescan-preflight.json",
        "https://gcagochina.com/basescan-handoff.html",
        "https://gcagochina.com/basescan-handoff.json",
        "https://gcagochina.com/action-plan.html",
        "https://gcagochina.com/register.html",
        "https://gcagochina.com/unsubscribe.html",
        "https://gcagochina.com/zh-cn.html",
        "https://gcagochina.com/zh-buy.html",
        "https://gcagochina.com/zh-apply.html",
        "https://gcagochina.com/zh-status.html",
        "https://gcagochina.com/zh-domain-email.html",
        "https://gcagochina.com/zh-basescan-preflight.html",
        "https://gcagochina.com/zh-basescan-submit.html",
        "https://gcagochina.com/zh-basescan-handoff.html",
        "https://gcagochina.com/zh-basescan-followup.html",
        "https://gcagochina.com/zh-liquidity.html",
        "https://gcagochina.com/zh-supply.html",
        "https://gcagochina.com/zh-security.html",
        "https://gcagochina.com/zh-roadmap.html",
        "https://gcagochina.com/zh-faq.html",
        "https://gcagochina.com/zh-members.html",
        "https://gcagochina.com/zh-support.html",
        "https://gcagochina.com/zh-access.html",
        "https://gcagochina.com/zh-release-gates.html",
        "https://gcagochina.com/zh-wallet-verify.html",
        "https://gcagochina.com/zh-member-checklist.html",
        "https://gcagochina.com/zh-member-benefit-transfer.html",
        "https://gcagochina.com/zh-site-map.html",
        "https://gcagochina.com/zh-data.html",
        "https://gcagochina.com/zh-api-status.html",
        "https://gcagochina.com/zh-operations.html",
        "https://gcagochina.com/data.html",
        "https://gcagochina.com/site-map.html",
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
        "https://gcagochina.com/liquidity.html",
        "https://gcagochina.com/liquidity.json",
        "https://gcagochina.com/holder-distribution.html",
        "https://gcagochina.com/holder-distribution.json",
        "https://gcagochina.com/risk-remediation.html",
        "https://gcagochina.com/risk-remediation.json",
        "https://gcagochina.com/custody-roadmap.html",
        "https://gcagochina.com/custody-roadmap.json",
        "https://gcagochina.com/audit-readiness.html",
        "https://gcagochina.com/audit-readiness.json",
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
        "https://gcagochina.com/announcements.html",
        "https://gcagochina.com/announcements.json",
        "https://gcagochina.com/campaign.html",
        "https://gcagochina.com/campaign.json",
        "https://gcagochina.com/content-library.html",
        "https://gcagochina.com/content-library.json",
        "https://gcagochina.com/publishing-desk.html",
        "https://gcagochina.com/publishing-desk.json",
        "https://gcagochina.com/narrative.html",
        "https://gcagochina.com/narrative.json",
        "https://gcagochina.com/radar.html",
        "https://gcagochina.com/radar.json",
        "https://gcagochina.com/radar-issue-004.html",
        "https://gcagochina.com/radar-issue-004.json",
        "https://gcagochina.com/member-access-brief-001.html",
        "https://gcagochina.com/member-access-brief-001.json",
        "https://gcagochina.com/gca/member-access/",
        "https://gcagochina.com/member-program.html",
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
        "https://gcagochina.com/api-status.html",
        "https://gcagochina.com/api-status.json",
        "https://gcagochina.com/daily-status.html",
        "https://gcagochina.com/daily-status.json",
        "https://gcagochina.com/review-queue.html",
        "https://gcagochina.com/review-queue.json",
        "https://gcagochina.com/credits.html",
        "https://gcagochina.com/credits.json",
        "https://gcagochina.com/release-gates.html",
        "https://gcagochina.com/release-gates.json",
        "https://gcagochina.com/supply.json",
        "https://gcagochina.com/listing-readiness.html",
        "https://gcagochina.com/listing-readiness.json",
        "https://gcagochina.com/project-profile.html",
        "https://gcagochina.com/project.json",
        "https://gcagochina.com/tokenlist.html",
        "https://gcagochina.com/tokenlist.json",
        "https://gcagochina.com/.well-known/gca-token.json",
        "https://gcagochina.com/.well-known/wallet-security.json",
        "https://gcagochina.com/.well-known/security.txt",
    ):
        assert_contains(text, expected, label)
    for path in (
        "api-status.html",
        "api-status.json",
        "zh-api-status.html",
        "daily-status.html",
        "daily-status.json",
        "basescan-remediation.html",
        "basescan-remediation.json",
        "basescan-preflight.html",
        "basescan-preflight.json",
        "zh-basescan-preflight.html",
        "external-reviews.html",
        "external-reviews.json",
        "listing-readiness.html",
        "listing-readiness.json",
        "project.json",
        "reviewer-kit.html",
        "reviewer-kit.json",
        "release-gates.html",
        "release-gates.json",
        "trust.html",
        "trust.json",
        "terms.html",
        "token-safety.html",
        "verify.html",
        "roadmap.html",
        "zh-release-gates.html",
    ):
        assert_sitemap_lastmod(path, "2026-06-07")
    for path in (
        "basescan-handoff.html",
        "basescan-handoff.json",
        "zh-basescan-handoff.html",
    ):
        assert_sitemap_lastmod(path, "2026-06-06")


def validate_robots(text: str) -> None:
    label = "/robots.txt"
    assert_contains(text, "Allow: /start.html", label)
    assert_contains(text, "Allow: /about.html", label)
    assert_contains(text, "Allow: /team.html", label)
    assert_contains(text, "Allow: /tim-chen.html", label)
    assert_contains(text, "Allow: /tim-chen.json", label)
    assert_contains(text, "Allow: /domain-email.html", label)
    assert_contains(text, "Allow: /domain-email.json", label)
    assert_contains(text, "Allow: /domain-email-evidence.html", label)
    assert_contains(text, "Allow: /domain-email-evidence.json", label)
    assert_contains(text, "Allow: /basescan-remediation.html", label)
    assert_contains(text, "Allow: /basescan-remediation.json", label)
    assert_contains(text, "Allow: /basescan-preflight.html", label)
    assert_contains(text, "Allow: /basescan-preflight.json", label)
    assert_contains(text, "Allow: /basescan-handoff.html", label)
    assert_contains(text, "Allow: /basescan-handoff.json", label)
    assert_contains(text, "Allow: /action-plan.html", label)
    assert_contains(text, "Allow: /register.html", label)
    assert_contains(text, "Allow: /unsubscribe.html", label)
    assert_contains(text, "Allow: /zh-cn.html", label)
    assert_contains(text, "Allow: /zh-buy.html", label)
    assert_contains(text, "Allow: /zh-apply.html", label)
    assert_contains(text, "Allow: /zh-status.html", label)
    assert_contains(text, "Allow: /zh-domain-email.html", label)
    assert_contains(text, "Allow: /zh-basescan-preflight.html", label)
    assert_contains(text, "Allow: /zh-basescan-submit.html", label)
    assert_contains(text, "Allow: /zh-basescan-handoff.html", label)
    assert_contains(text, "Allow: /zh-basescan-followup.html", label)
    assert_contains(text, "Allow: /zh-liquidity.html", label)
    assert_contains(text, "Allow: /zh-supply.html", label)
    assert_contains(text, "Allow: /zh-security.html", label)
    assert_contains(text, "Allow: /zh-roadmap.html", label)
    assert_contains(text, "Allow: /zh-faq.html", label)
    assert_contains(text, "Allow: /zh-members.html", label)
    assert_contains(text, "Allow: /zh-support.html", label)
    assert_contains(text, "Allow: /zh-access.html", label)
    assert_contains(text, "Allow: /zh-release-gates.html", label)
    assert_contains(text, "Allow: /zh-wallet-verify.html", label)
    assert_contains(text, "Allow: /zh-member-checklist.html", label)
    assert_contains(text, "Allow: /zh-member-benefit-transfer.html", label)
    assert_contains(text, "Allow: /zh-site-map.html", label)
    assert_contains(text, "Allow: /zh-data.html", label)
    assert_contains(text, "Allow: /zh-api-status.html", label)
    assert_contains(text, "Allow: /zh-operations.html", label)
    assert_contains(text, "Allow: /site-map.html", label)
    assert_contains(text, "Allow: /verify.html", label)
    assert_contains(text, "Allow: /data.html", label)
    assert_contains(text, "Allow: /status.html", label)
    assert_contains(text, "Allow: /listing-kit.html", label)
    assert_contains(text, "Allow: /whitepaper.html", label)
    assert_contains(text, "Allow: /buy.html", label)
    assert_contains(text, "Allow: /markets.html", label)
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
    assert_contains(text, "Allow: /announcements.html", label)
    assert_contains(text, "Allow: /announcements.json", label)
    assert_contains(text, "Allow: /campaign.html", label)
    assert_contains(text, "Allow: /campaign.json", label)
    assert_contains(text, "Allow: /content-library.html", label)
    assert_contains(text, "Allow: /content-library.json", label)
    assert_contains(text, "Allow: /publishing-desk.html", label)
    assert_contains(text, "Allow: /publishing-desk.json", label)
    assert_contains(text, "Allow: /narrative.html", label)
    assert_contains(text, "Allow: /narrative.json", label)
    assert_contains(text, "Allow: /radar.html", label)
    assert_contains(text, "Allow: /radar.json", label)
    assert_contains(text, "Allow: /radar-issue-004.html", label)
    assert_contains(text, "Allow: /radar-issue-004.json", label)
    assert_contains(text, "Allow: /member-access-brief-001.html", label)
    assert_contains(text, "Allow: /member-access-brief-001.json", label)
    assert_contains(text, "Allow: /market-quality.html", label)
    assert_contains(text, "Allow: /market-quality.json", label)
    assert_contains(text, "Allow: /liquidity.html", label)
    assert_contains(text, "Allow: /liquidity.json", label)
    assert_contains(text, "Allow: /holder-distribution.html", label)
    assert_contains(text, "Allow: /holder-distribution.json", label)
    assert_contains(text, "Allow: /risk-remediation.html", label)
    assert_contains(text, "Allow: /risk-remediation.json", label)
    assert_contains(text, "Allow: /custody-roadmap.html", label)
    assert_contains(text, "Allow: /custody-roadmap.json", label)
    assert_contains(text, "Allow: /audit-readiness.html", label)
    assert_contains(text, "Allow: /audit-readiness.json", label)
    assert_contains(text, "Allow: /token-safety.html", label)
    assert_contains(text, "Allow: /token-safety.json", label)
    assert_contains(text, "Allow: /blockaid-followup.html", label)
    assert_contains(text, "Allow: /blockaid-followup.json", label)
    assert_contains(text, "Allow: /technical-report.html", label)
    assert_contains(text, "Allow: /technical-report.json", label)
    assert_contains(text, "Allow: /reserve-statement.html", label)
    assert_contains(text, "Allow: /reserve-statement.json", label)
    assert_contains(text, "Allow: /supply.html", label)
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
    assert_contains(text, "Allow: /members.html", label)
    assert_contains(text, "Allow: /member-program.html", label)
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
    assert_contains(text, "Allow: /api-status.html", label)
    assert_contains(text, "Allow: /api-status.json", label)
    assert_contains(text, "Allow: /daily-status.html", label)
    assert_contains(text, "Allow: /daily-status.json", label)
    assert_contains(text, "Allow: /review-queue.html", label)
    assert_contains(text, "Allow: /review-queue.json", label)
    assert_contains(text, "Allow: /credits.html", label)
    assert_contains(text, "Allow: /credits.json", label)
    assert_contains(text, "Allow: /release-gates.html", label)
    assert_contains(text, "Allow: /release-gates.json", label)
    assert_contains(text, "Allow: /project-profile.html", label)
    assert_contains(text, "Allow: /project.json", label)
    assert_contains(text, "Allow: /tokenlist.html", label)
    assert_contains(text, "Allow: /tokenlist.json", label)
    assert_contains(text, "Allow: /.well-known/gca-token.json", label)
    assert_contains(text, "Allow: /.well-known/wallet-security.json", label)
    assert_contains(text, "Allow: /.well-known/security.txt", label)
    assert_contains(text, "Sitemap: https://gcagochina.com/sitemap.xml", label)


CHECKS: list[EndpointCheck] = [
    ("/", validate_root),
    ("/start.html", validate_start_page),
    ("/register.html", validate_register_page),
    ("/unsubscribe.html", validate_unsubscribe_page),
    ("/about.html", validate_about_page),
    ("/team.html", validate_team_page),
    ("/tim-chen.html", validate_tim_chen_profile_page),
    ("/tim-chen.json", validate_tim_chen_profile_json),
    ("/domain-email.html", validate_domain_email_page),
    ("/domain-email.json", validate_domain_email_json),
    ("/domain-email-evidence.html", validate_domain_email_evidence_page),
    ("/domain-email-evidence.json", validate_domain_email_evidence_json),
    ("/basescan-remediation.html", validate_basescan_remediation_page),
    ("/basescan-remediation.json", validate_basescan_remediation_json),
    ("/basescan-preflight.html", validate_basescan_preflight_page),
    ("/basescan-preflight.json", validate_basescan_preflight_json),
    ("/basescan-handoff.html", validate_basescan_handoff_page),
    ("/basescan-handoff.json", validate_basescan_handoff_json),
    ("/action-plan.html", validate_action_plan_page),
    ("/zh-cn.html", validate_zh_cn_page),
    ("/zh-buy.html", validate_zh_buy_page),
    ("/zh-apply.html", validate_zh_apply_page),
    ("/zh-status.html", validate_zh_status_page),
    ("/zh-domain-email.html", validate_zh_domain_email_page),
    ("/zh-basescan-preflight.html", validate_zh_basescan_preflight_page),
    ("/zh-basescan-submit.html", validate_zh_basescan_submit_page),
    ("/zh-basescan-handoff.html", validate_zh_basescan_handoff_page),
    ("/zh-basescan-followup.html", validate_zh_basescan_followup_page),
    ("/zh-liquidity.html", validate_zh_liquidity_page),
    ("/zh-supply.html", validate_zh_supply_page),
    ("/zh-security.html", validate_zh_security_page),
    ("/zh-roadmap.html", validate_zh_roadmap_page),
    ("/zh-faq.html", validate_zh_faq_page),
    ("/zh-members.html", validate_zh_members_page),
    ("/zh-support.html", validate_zh_support_page),
    ("/zh-access.html", validate_zh_access_page),
    ("/zh-release-gates.html", validate_zh_release_gates_page),
    ("/zh-wallet-verify.html", validate_zh_wallet_verify_page),
    ("/zh-member-checklist.html", validate_zh_member_checklist_page),
    ("/zh-member-benefit-transfer.html", validate_zh_member_benefit_transfer_page),
    ("/zh-site-map.html", validate_zh_site_map_page),
    ("/zh-data.html", validate_zh_data_page),
    ("/zh-api-status.html", validate_zh_api_status_page),
    ("/zh-operations.html", validate_zh_operations_page),
    ("/data.html", validate_data_page),
    ("/site-map.html", validate_site_map_page),
    ("/verify.html", validate_verify),
    ("/status.html", validate_status_page),
    ("/listing-kit.html", validate_listing_kit_page),
    ("/whitepaper.html", validate_whitepaper_page),
    ("/project-profile.html", validate_project_profile_page),
    ("/tokenlist.html", validate_tokenlist_page),
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
    ("/liquidity.html", validate_liquidity_page),
    ("/liquidity.json", validate_liquidity_json),
    ("/holder-distribution.html", validate_holder_distribution_page),
    ("/holder-distribution.json", validate_holder_distribution_json),
    ("/risk-remediation.html", validate_risk_remediation_page),
    ("/risk-remediation.json", validate_risk_remediation_json),
    ("/custody-roadmap.html", validate_custody_roadmap_page),
    ("/custody-roadmap.json", validate_custody_roadmap_json),
    ("/audit-readiness.html", validate_audit_readiness_page),
    ("/audit-readiness.json", validate_audit_readiness_json),
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
    ("/member-program.html", validate_member_program_page),
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
    ("/announcements.html", validate_announcements_page),
    ("/announcements.json", validate_announcements_json),
    ("/campaign.html", validate_campaign_page),
    ("/campaign.json", validate_campaign_json),
    ("/content-library.html", validate_content_library_page),
    ("/content-library.json", validate_content_library_json),
    ("/publishing-desk.html", validate_publishing_desk_page),
    ("/publishing-desk.json", validate_publishing_desk_json),
    ("/narrative.html", validate_narrative_page),
    ("/narrative.json", validate_narrative_json),
    ("/radar.html", validate_radar_page),
    ("/radar.json", validate_radar_json),
    ("/radar-issue-004.html", validate_radar_issue_004_page),
    ("/radar-issue-004.json", validate_radar_issue_004_json),
    ("/member-access-brief-001.html", validate_member_access_brief_001_page),
    ("/member-access-brief-001.json", validate_member_access_brief_001_json),
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
    ("/api-status.html", validate_api_status_page),
    ("/api-status.json", validate_api_status_json),
    ("/daily-status.html", validate_daily_status_page),
    ("/daily-status.json", validate_daily_status_json),
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
            assert_not_contains(body, LEGACY_PERSONAL_GMAIL, path)
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
