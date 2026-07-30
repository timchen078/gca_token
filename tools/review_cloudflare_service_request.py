#!/usr/bin/env python3
"""Record a protected manual review for one GCA service request.

The Worker applies the server-side service catalog, requires approval before
delivery, and deducts credits at most once when delivery is recorded. This
tool never connects a wallet, signs a message, sends a transaction, transfers
GCA, or creates trading permission.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
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


SERVICE_REQUEST_REVIEW_VERSION = "gca_service_request_review_v1"
DECISIONS = (
    "approved",
    "rejected",
    "needs_more_information",
    "delivered",
)
SERVICE_REQUEST_ID_RE = re.compile(r"^gca_service_req_[a-f0-9]{20}$")
CLIENT_REVIEW_ID_RE = re.compile(
    r"^gca_client_review_[A-Za-z0-9_-]{22,64}$"
)
OPERATOR_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
REASON_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


class ServiceRequestReviewError(RuntimeError):
    """Raised for expected operator-facing service review failures."""


def build_client_review_id(
    *,
    service_request_id: str,
    decision: str,
    reason_code: str,
    delivery_reference: str = "",
) -> str:
    material = "|".join(
        (
            service_request_id.strip().lower(),
            decision.strip().lower(),
            reason_code.strip().lower(),
            delivery_reference.strip(),
        )
    ).encode("utf-8")
    digest = hashlib.sha256(material).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"gca_client_review_{encoded[:32]}"


def build_review_payload(
    *,
    service_request_id: str,
    decision: str,
    reason_code: str,
    reviewer_id: str,
    client_review_id: str = "",
    operator_note: str = "",
    delivery_reference: str = "",
    manual_review_confirmed: bool = False,
    no_secrets_no_custody_confirmed: bool = False,
    no_trading_permission_confirmed: bool = False,
    delivery_completed: bool = False,
    credit_settlement_accepted: bool = False,
) -> dict[str, Any]:
    clean_request_id = service_request_id.strip().lower()
    clean_decision = decision.strip().lower()
    clean_reason = reason_code.strip().lower()
    clean_reviewer = reviewer_id.strip().lower()
    clean_delivery_reference = delivery_reference.strip()[:300]
    clean_client_review_id = client_review_id.strip() or build_client_review_id(
        service_request_id=clean_request_id,
        decision=clean_decision,
        reason_code=clean_reason,
        delivery_reference=clean_delivery_reference,
    )

    if not SERVICE_REQUEST_ID_RE.fullmatch(clean_request_id):
        raise ServiceRequestReviewError(
            "service request id must match gca_service_req_ plus 20 lowercase hex characters"
        )
    if clean_decision not in DECISIONS:
        raise ServiceRequestReviewError(
            f"decision must be one of: {', '.join(DECISIONS)}"
        )
    if not REASON_CODE_RE.fullmatch(clean_reason):
        raise ServiceRequestReviewError(
            "reason code must be a short lowercase identifier"
        )
    if not OPERATOR_ID_RE.fullmatch(clean_reviewer):
        raise ServiceRequestReviewError(
            "reviewer id must be a short lowercase operator identifier"
        )
    if not CLIENT_REVIEW_ID_RE.fullmatch(clean_client_review_id):
        raise ServiceRequestReviewError(
            "client review id must match gca_client_review_ plus 22-64 URL-safe characters"
        )
    if not manual_review_confirmed:
        raise ServiceRequestReviewError(
            "--confirm-manual-review is required"
        )
    if not no_secrets_no_custody_confirmed:
        raise ServiceRequestReviewError(
            "--confirm-no-secrets-no-custody is required"
        )
    if not no_trading_permission_confirmed:
        raise ServiceRequestReviewError(
            "--confirm-no-trading-permission is required"
        )
    if clean_decision == "delivered" and not delivery_completed:
        raise ServiceRequestReviewError(
            "delivered reviews require --confirm-delivery-completed"
        )
    if clean_decision == "delivered" and not credit_settlement_accepted:
        raise ServiceRequestReviewError(
            "delivered reviews require --confirm-credit-settlement"
        )
    if clean_decision == "delivered" and not clean_delivery_reference:
        raise ServiceRequestReviewError(
            "delivered reviews require --delivery-reference"
        )

    return {
        "packetVersion": SERVICE_REQUEST_REVIEW_VERSION,
        "serviceRequestId": clean_request_id,
        "clientReviewId": clean_client_review_id,
        "decision": clean_decision,
        "reasonCode": clean_reason,
        "reviewerId": clean_reviewer,
        "operatorNote": operator_note.strip()[:500],
        "deliveryReference": clean_delivery_reference,
        "source": "gca-service-request-review-operator-cli",
        "acknowledgements": {
            "manualReviewCompleted": True,
            "noSecretsNoCustody": True,
            "noTradingPermission": True,
            "deliveryCompleted": clean_decision == "delivered",
            "creditSettlementAccepted": clean_decision == "delivered",
        },
    }


def submit_service_request_review(
    *,
    base_url: str,
    token: str,
    payload: dict[str, Any],
    timeout: float = 20,
    cafile: str = "",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/gca/service-request-reviews"
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "user-agent": "GCA-Operator-Service-Request-Review/1.0",
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
            detail = str(
                error_payload.get("error") or f"HTTP {exc.code}"
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            detail = f"HTTP {exc.code}"
        raise ServiceRequestReviewError(
            f"service review API rejected the request: {detail}"
        ) from exc
    except URLError as exc:
        raise ServiceRequestReviewError(
            f"service review API request failed: {exc.reason}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ServiceRequestReviewError(
            "service review API returned invalid JSON"
        ) from exc
    if result.get("ok") is not True:
        raise ServiceRequestReviewError(
            "service review API did not return ok=true"
        )
    if not isinstance(
        result.get("serviceRequestReview"), dict
    ) or not isinstance(result.get("serviceRequest"), dict):
        raise ServiceRequestReviewError(
            "service review API response is missing review or request data"
        )
    return result


def safe_result(payload: dict[str, Any]) -> dict[str, Any]:
    review = payload.get("serviceRequestReview", {})
    service_request = payload.get("serviceRequest", {})
    credit_usage = payload.get("creditUsage") or {}
    credit_ledger = payload.get("creditLedger") or {}
    boundaries = payload.get("boundaries", {})
    return {
        "ok": True,
        "idempotentReplay": bool(
            payload.get("idempotentReplay", False)
        ),
        "serviceRequestReviewId": review.get(
            "serviceRequestReviewId", ""
        ),
        "serviceRequestId": review.get("serviceRequestId", ""),
        "decision": review.get("decision", ""),
        "requestStatus": service_request.get("status", ""),
        "creditUsageId": credit_usage.get("creditUsageId", ""),
        "creditAmountUsed": int(
            credit_usage.get("creditAmountUsed", 0) or 0
        ),
        "remainingCredits": credit_ledger.get(
            "remainingCredits"
        ),
        "adminTokenPrinted": False,
        "emailPrinted": False,
        "walletPrinted": False,
        "operatorNotePrinted": False,
        "requiresSignature": bool(
            boundaries.get("requiresSignature", False)
        ),
        "requiresTransaction": bool(
            boundaries.get("requiresTransaction", False)
        ),
        "automaticTokenTransfer": bool(
            boundaries.get("automaticTokenTransfer", False)
        ),
        "createsTradingPermission": bool(
            boundaries.get("createsTradingPermission", False)
        ),
    }


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Record a token-protected manual review or completed "
            "delivery for one GCA service request."
        ),
    )
    parser.add_argument(
        "--service-request-id",
        required=True,
        help="Target gca_service_req_* request id.",
    )
    parser.add_argument(
        "--decision",
        required=True,
        choices=DECISIONS,
        help="Manual review decision.",
    )
    parser.add_argument(
        "--reason-code",
        required=True,
        help="Short lowercase review reason identifier.",
    )
    parser.add_argument(
        "--reviewer-id",
        default="gca-operator",
        help="Short operator identifier.",
    )
    parser.add_argument(
        "--client-review-id",
        default="",
        help=(
            "Optional idempotency key. The tool derives one from the "
            "request and decision when omitted."
        ),
    )
    parser.add_argument(
        "--note",
        default="",
        help="Optional private operator note, maximum 500 characters.",
    )
    parser.add_argument(
        "--delivery-reference",
        default="",
        help=(
            "Non-secret delivery reference, maximum 300 characters; "
            "required when decision is delivered."
        ),
    )
    parser.add_argument(
        "--confirm-manual-review",
        action="store_true",
        help="Confirm that a human reviewed the request.",
    )
    parser.add_argument(
        "--confirm-no-secrets-no-custody",
        action="store_true",
        help="Confirm that the review requests no secrets or custody.",
    )
    parser.add_argument(
        "--confirm-no-trading-permission",
        action="store_true",
        help="Confirm that the action creates no trading permission.",
    )
    parser.add_argument(
        "--confirm-delivery-completed",
        action="store_true",
        help="Required only when decision is delivered.",
    )
    parser.add_argument(
        "--confirm-credit-settlement",
        action="store_true",
        help="Required only when decision is delivered.",
    )
    parser.add_argument(
        "--confirm-production-write",
        action="store_true",
        help="Required because this command writes production D1 records.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_API_BASE,
        help=f"Worker API base URL. Default: {DEFAULT_API_BASE}",
    )
    parser.add_argument(
        "--token-file",
        type=Path,
        default=DEFAULT_TOKEN_FILE,
        help="Path to ignored local admin env file.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20,
        help="HTTP timeout in seconds. Default: 20.",
    )
    parser.add_argument(
        "--cafile",
        default="",
        help=f"Optional CA bundle path. Default fallback: {DEFAULT_CA_FILE}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if not args.confirm_production_write:
            raise ServiceRequestReviewError(
                "--confirm-production-write is required"
            )
        payload = build_review_payload(
            service_request_id=args.service_request_id,
            decision=args.decision,
            reason_code=args.reason_code,
            reviewer_id=args.reviewer_id,
            client_review_id=args.client_review_id,
            operator_note=args.note,
            delivery_reference=args.delivery_reference,
            manual_review_confirmed=args.confirm_manual_review,
            no_secrets_no_custody_confirmed=(
                args.confirm_no_secrets_no_custody
            ),
            no_trading_permission_confirmed=(
                args.confirm_no_trading_permission
            ),
            delivery_completed=args.confirm_delivery_completed,
            credit_settlement_accepted=(
                args.confirm_credit_settlement
            ),
        )
        token = load_admin_token(args.token_file)
        result = submit_service_request_review(
            base_url=args.base_url,
            token=token,
            payload=payload,
            timeout=args.timeout,
            cafile=args.cafile,
        )
    except (ExportError, ServiceRequestReviewError) as exc:
        print(
            json.dumps(
                {"ok": False, "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            safe_result(result),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
