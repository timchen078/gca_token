#!/usr/bin/env python3
"""Record a manual GCA Member eligibility review in the production Worker.

This operator tool writes a review decision to D1. It never connects a wallet,
signs a message, sends a transaction, or transfers GCA.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.export_cloudflare_email_registrations import (  # noqa: E402
    DEFAULT_API_BASE,
    DEFAULT_CA_FILE,
    DEFAULT_TOKEN_FILE,
    ExportError,
    load_admin_token,
)


MEMBER_REVIEW_VERSION = "gca_member_review_v1"
DECISIONS = ("approved", "rejected", "needs_more_information")
MEMBER_LEDGER_ID_RE = re.compile(r"^gca_member_[a-f0-9]{20}$")


class MemberReviewError(RuntimeError):
    """Raised for expected operator-facing member review failures."""


def build_review_payload(
    *,
    member_ledger_id: str,
    decision: str,
    reason_code: str,
    reviewer_id: str,
    operator_note: str = "",
    evidence_reviewed: bool = False,
) -> dict[str, Any]:
    clean_ledger_id = member_ledger_id.strip().lower()
    clean_decision = decision.strip().lower()
    clean_reason = reason_code.strip().lower()
    clean_reviewer = reviewer_id.strip().lower()
    if not MEMBER_LEDGER_ID_RE.fullmatch(clean_ledger_id):
        raise MemberReviewError("member ledger id must match gca_member_ plus 20 lowercase hex characters")
    if clean_decision not in DECISIONS:
        raise MemberReviewError(f"decision must be one of: {', '.join(DECISIONS)}")
    if not clean_reason:
        raise MemberReviewError("reason code is required")
    if not clean_reviewer:
        raise MemberReviewError("reviewer id is required")
    if clean_decision == "approved" and not evidence_reviewed:
        raise MemberReviewError("approved reviews require --confirm-evidence-reviewed")
    return {
        "packetVersion": MEMBER_REVIEW_VERSION,
        "memberLedgerId": clean_ledger_id,
        "decision": clean_decision,
        "reasonCode": clean_reason,
        "reviewerId": clean_reviewer,
        "operatorNote": operator_note.strip()[:500],
        "source": "gca-member-review-operator-cli",
        "acknowledgements": {
            "manualEvidenceReviewCompleted": True,
            "noAutomaticTokenTransfer": True,
        },
    }


def submit_member_review(
    *,
    base_url: str,
    token: str,
    payload: dict[str, Any],
    timeout: float = 20,
    cafile: str = "",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/gca/member-reviews"
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "user-agent": "GCA-Operator-Member-Review/1.0",
        },
    )
    kwargs: dict[str, Any] = {"timeout": timeout}
    if opener is urlopen:
        ca_path = cafile or os.environ.get("SSL_CERT_FILE", "")
        if not ca_path and Path(DEFAULT_CA_FILE).exists():
            ca_path = DEFAULT_CA_FILE
        if ca_path:
            kwargs["context"] = ssl.create_default_context(cafile=ca_path)
    try:
        with opener(request, **kwargs) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
            detail = str(error_payload.get("error") or f"HTTP {exc.code}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            detail = f"HTTP {exc.code}"
        raise MemberReviewError(f"member review API rejected the request: {detail}") from exc
    except URLError as exc:
        raise MemberReviewError(f"member review API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise MemberReviewError("member review API returned invalid JSON") from exc
    if result.get("ok") is not True:
        raise MemberReviewError("member review API did not return ok=true")
    if not isinstance(result.get("memberReview"), dict) or not isinstance(result.get("memberLedger"), dict):
        raise MemberReviewError("member review API response is missing review or ledger data")
    return result


def safe_result(payload: dict[str, Any]) -> dict[str, Any]:
    review = payload.get("memberReview", {})
    ledger = payload.get("memberLedger", {})
    boundaries = payload.get("boundaries", {})
    return {
        "ok": True,
        "memberReviewId": review.get("memberReviewId", ""),
        "memberLedgerId": review.get("memberLedgerId", ""),
        "decision": review.get("decision", ""),
        "resultingMemberStatus": review.get("resultingMemberStatus", ""),
        "memberBenefitClaimStatus": ledger.get("memberBenefitClaimStatus", ""),
        "automaticTokenTransfer": bool(boundaries.get("automaticTokenTransfer", False)),
        "authorizesMemberBenefitTransfer": bool(boundaries.get("authorizesMemberBenefitTransfer", False)),
        "adminTokenPrinted": False,
        "walletPrinted": False,
        "emailPrinted": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record a token-protected manual GCA Member review in Cloudflare D1.",
    )
    parser.add_argument("--member-ledger-id", required=True, help="Target gca_member_* ledger id.")
    parser.add_argument("--decision", required=True, choices=DECISIONS, help="Manual review decision.")
    parser.add_argument("--reason-code", required=True, help="Short lowercase review reason identifier.")
    parser.add_argument("--reviewer-id", default="gca-operator", help="Short operator identifier.")
    parser.add_argument("--note", default="", help="Optional operator note, maximum 500 characters.")
    parser.add_argument(
        "--confirm-evidence-reviewed",
        action="store_true",
        help="Required for approval after manually checking the holding evidence.",
    )
    parser.add_argument(
        "--confirm-production-write",
        action="store_true",
        help="Required because this command writes a review record to production D1.",
    )
    parser.add_argument("--base-url", default=DEFAULT_API_BASE, help=f"Worker API base URL. Default: {DEFAULT_API_BASE}")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE, help="Path to ignored local admin env file.")
    parser.add_argument("--timeout", type=float, default=20, help="HTTP timeout in seconds. Default: 20.")
    parser.add_argument("--cafile", default="", help=f"Optional CA bundle path. Default fallback: {DEFAULT_CA_FILE}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if not args.confirm_production_write:
            raise MemberReviewError("--confirm-production-write is required")
        payload = build_review_payload(
            member_ledger_id=args.member_ledger_id,
            decision=args.decision,
            reason_code=args.reason_code,
            reviewer_id=args.reviewer_id,
            operator_note=args.note,
            evidence_reviewed=args.confirm_evidence_reviewed,
        )
        token = load_admin_token(args.token_file)
        result = submit_member_review(
            base_url=args.base_url,
            token=token,
            payload=payload,
            timeout=args.timeout,
            cafile=args.cafile,
        )
    except (ExportError, MemberReviewError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(safe_result(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
