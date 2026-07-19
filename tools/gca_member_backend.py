#!/usr/bin/env python3
"""Local-only GCA member access backend.

This server is intentionally small and conservative:
- serves the static site from ``site/``
- accepts local member pre-registration packets on localhost
- accepts local email-only GCA user registrations on localhost
- verifies GCA balances with read-only Base Mainnet ``eth_call``
- writes append-only JSONL records under a local data directory

It never asks for private keys, seed phrases, signatures, withdrawal
permission, custody, or exchange API credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


CHAIN_ID = 8453
CONTRACT_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6"
BASE_RPC_URL = "https://mainnet.base.org"
BASESCAN_TX_URL = "https://basescan.org/tx/"
BALANCE_OF_SELECTOR = "0x70a08231"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TOKEN_DECIMALS = 18
TOKEN_UNIT = 10**TOKEN_DECIMALS
HOLDER_THRESHOLD_UNITS = 10_000 * TOKEN_UNIT
MEMBER_THRESHOLD_UNITS = 1_000_000 * TOKEN_UNIT
MEMBER_BENEFIT_UNITS = 10_000 * TOKEN_UNIT
MEMBER_HOLD_DAYS = 30
CREDIT_AMOUNT = 100
CREDIT_EXPIRY_DAYS = 180
MEMBER_REFRESH_DAYS = 30
MEMBER_BENEFIT_AMOUNT = "10000 GCA"
CREDIT_SERVICE_CATALOG = {
    "liquidation-replay-report": {"name": "Liquidation Replay", "creditUnit": 30},
    "risk-warning-review": {"name": "Risk Warning Review", "creditUnit": 10},
    "backtest-lab-run": {"name": "Backtest Lab", "creditUnit": 20},
    "entry-ready-review": {"name": "ENTRY_READY Review", "creditUnit": 15},
    "position-size-calculator": {"name": "Position Size Calculator", "creditUnit": 5},
    "risk-control-training": {"name": "Risk-Control Training", "creditUnit": 10},
    "member-research-notes": {"name": "Member Research Notes", "creditUnit": 20},
    "support-review-queue": {"name": "Support Review Queue", "creditUnit": 0},
}
PACKET_VERSION = "gca_member_preregistration_v2"
EMAIL_REGISTRATION_VERSION = "gca_email_registration_v1"
CREDIT_USAGE_VERSION = "gca_credit_usage_v1"
SERVICE_REQUEST_VERSION = "gca_service_request_v1"
CONTACT_EMAIL = "support@gcagochina.com"
ALLOWED_PROGRAM_INTENTS = {"holder_bonus", "gca_member", "general_waitlist"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
TX_HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
EMAIL_TEXT_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
FORBIDDEN_KEY_PATTERNS = (
    "privatekey",
    "seedphrase",
    "mnemonic",
    "apisecret",
    "withdrawalpermission",
    "recoveryphrase",
    "onetimecode",
)
LEDGER_NAMES = (
    "email_registrations",
    "pre_registrations",
    "wallet_verifications",
    "credit_ledger",
    "service_requests",
    "credit_usage",
    "member_ledger",
    "member_benefit_transfers",
    "support_reviews",
)
LOCAL_CLIENTS = {"127.0.0.1", "::1", "localhost"}
REDACTED_EXTERNAL_VALUE = "[redacted-for-external-sharing]"
REDACTED_EXTERNAL_KEYS = {"email", "telegram", "reviewerNote", "supportNote", "evidenceNote"}
PACKAGE_DIGEST_ALGORITHM = "sha256-json-sort-keys-excluding-packageDigestSha256"
SUPPORT_REVIEW_AUDIT_VERSION = "gca_support_review_audit_v1"
SUPPORT_REVIEW_AUDIT_ALGORITHM = "sha256-canonical-json-chain"
SUPPORT_REVIEW_AUDIT_GENESIS_HASH = "0" * 64
SUPPORT_REVIEW_AUDIT_FIELDS = (
    "auditChainVersion",
    "auditHashAlgorithm",
    "auditSequence",
    "auditPreviousHash",
    "auditRecordHash",
    "auditLegacyPrefixCount",
    "auditLegacyPrefixSha256",
)
OPERATOR_DIGEST_VERSION = "gca_operator_digest_v1"
OPERATOR_DIGEST_FILE = "gca_operator_digest.json"
OPERATOR_ACTION_PLAN_VERSION = "gca_operator_action_plan_v1"
DOMAIN_EMAIL_EVIDENCE_PACKET_COMMAND = (
    ".venv/bin/python tools/build_domain_email_evidence_packet.py "
    "--dkim-selector PROVIDER_SELECTOR "
    "--evidence-dir launch/domain_email_evidence "
    "--website-email-updated "
    "--output-json launch/domain_email_evidence_packet.json "
    "--output-md launch/domain_email_evidence_packet.md "
    "--json"
)
SUPPORT_REVIEW_UPDATE_STATUSES = {
    "received",
    "wallet_pending",
    "eligible",
    "needs_more_information",
    "rejected",
    "ledger_recorded",
    "below_threshold",
    "contacted",
    "waiting_for_user_evidence",
    "waiting_for_operator_review",
    "pending_manual_reserve_transfer",
    "closed_resolved",
    "closed_no_action",
}
SERVICE_REQUEST_STATUSES = {
    "queued_operator_review",
    "queued_missing_credit_ledger",
    "queued_insufficient_credits",
}


class BackendError(ValueError):
    """User-facing API validation error."""

    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, *parts: Any) -> str:
    encoded = "|".join(str(part).strip().lower() for part in parts).encode()
    digest = hashlib.sha256(encoded).hexdigest()[:20]
    return f"{prefix}_{digest}"


def is_wallet_address(value: str) -> bool:
    return bool(ADDRESS_RE.match(str(value or "").strip()))


def normalize_email(value: str) -> str:
    email = str(value or "").strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise BackendError("email must be a valid email address")
    return email


def normalize_wallet(value: str) -> str:
    wallet = str(value or "").strip()
    if not is_wallet_address(wallet):
        raise BackendError("walletAddress must be a valid EVM address")
    return wallet.lower()


def is_tx_hash(value: str) -> bool:
    return bool(TX_HASH_RE.match(str(value or "").strip()))


def parse_gca_to_units(value: Any) -> int:
    normalized = str(value or "0").replace(",", "").strip()
    if not normalized:
        return 0
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise BackendError("declaredGcaBalance must be a decimal number") from exc
    if amount < 0:
        raise BackendError("declaredGcaBalance cannot be negative")
    return int(amount * TOKEN_UNIT)


def units_to_gca(units: int) -> str:
    whole, fraction = divmod(int(units), TOKEN_UNIT)
    if fraction == 0:
        return str(whole)
    fraction_text = str(fraction).rjust(TOKEN_DECIMALS, "0").rstrip("0")
    if len(fraction_text) > 6:
        fraction_text = fraction_text[:6].rstrip("0")
    return f"{whole}.{fraction_text}" if fraction_text else str(whole)


def safe_operator_text(value: Any, limit: int = 500) -> str:
    text = str(value or "").strip()
    text = EMAIL_TEXT_RE.sub("[redacted-email]", text)
    return text[:limit]


def safe_operator_bool(value: Any) -> bool:
    return value is True


def safe_operator_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def safe_operator_mapping(payload: Any, allowed_keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    safe: dict[str, Any] = {}
    for key in allowed_keys:
        if key not in payload:
            continue
        value = payload.get(key)
        if isinstance(value, bool):
            safe[key] = value
        elif isinstance(value, int):
            safe[key] = value
        elif isinstance(value, dict):
            safe[key] = {
                safe_operator_text(item_key, 80): safe_operator_int(item_value)
                for item_key, item_value in value.items()
            }
        else:
            safe[key] = safe_operator_text(value)
    return safe


def balance_of_calldata(wallet: str) -> str:
    normalized = normalize_wallet(wallet).removeprefix("0x")
    return f"{BALANCE_OF_SELECTOR}{normalized.rjust(64, '0')}"


def holding_days_from_date(value: str, today: date | None = None) -> int:
    if not value:
        return 0
    try:
        start = date.fromisoformat(value)
    except ValueError:
        return 0
    today = today or utc_now().date()
    if start > today:
        return 0
    return (today - start).days


def reject_forbidden_keys(payload: Any, path: str = "") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if any(pattern in normalized for pattern in FORBIDDEN_KEY_PATTERNS):
                raise BackendError(f"Forbidden sensitive field is not accepted: {path}{key}")
            reject_forbidden_keys(value, f"{path}{key}.")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            reject_forbidden_keys(value, f"{path}{index}.")


def read_json_request(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise BackendError("Request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise BackendError("Request body must be a JSON object")
    reject_forbidden_keys(payload)
    return payload


def extract_user(packet: dict[str, Any]) -> dict[str, str]:
    user = packet.get("user") if isinstance(packet.get("user"), dict) else {}
    email = normalize_email(str(packet.get("email") or user.get("email") or ""))
    telegram = str(packet.get("telegram") or user.get("telegram") or "").strip()
    wallet = normalize_wallet(str(packet.get("walletAddress") or user.get("walletAddress") or ""))
    return {"email": email, "telegram": telegram, "walletAddress": wallet}


def extract_email_registration(packet: dict[str, Any]) -> dict[str, Any]:
    if packet.get("packetVersion") not in (None, EMAIL_REGISTRATION_VERSION):
        raise BackendError(f"packetVersion must be {EMAIL_REGISTRATION_VERSION}")
    user = packet.get("user") if isinstance(packet.get("user"), dict) else {}
    email = normalize_email(str(packet.get("email") or user.get("email") or ""))
    display_name = str(packet.get("displayName") or user.get("displayName") or "").strip()[:120]
    source = str(packet.get("source") or "register.html").strip()[:120]
    language = str(packet.get("language") or user.get("language") or "zh-CN").strip()[:32]
    interests = packet.get("interests")
    if not isinstance(interests, list):
        interests = ["gca_updates"]
    clean_interests = [str(item).strip()[:64] for item in interests if str(item).strip()]
    acknowledgements = packet.get("acknowledgements")
    if not isinstance(acknowledgements, dict):
        acknowledgements = {}
    contact_consent = bool(packet.get("contactConsentAccepted") or acknowledgements.get("emailContactConsent"))
    security_boundary = bool(packet.get("securityBoundaryAccepted") or acknowledgements.get("noSecretsNoCustody"))
    if not contact_consent:
        raise BackendError("email contact consent is required")
    if not security_boundary:
        raise BackendError("security boundary acknowledgement is required")
    return {
        "email": email,
        "displayName": display_name,
        "source": source,
        "language": language,
        "interests": clean_interests,
        "contactConsentAccepted": contact_consent,
        "securityBoundaryAccepted": security_boundary,
    }


def extract_acknowledgements(packet: dict[str, Any]) -> dict[str, bool]:
    acknowledgements = packet.get("acknowledgements")
    if not isinstance(acknowledgements, dict):
        acknowledgements = {}
    terms = bool(packet.get("termsAccepted") or acknowledgements.get("preRegistrationOnly"))
    security = bool(packet.get("securityBoundaryAccepted") or acknowledgements.get("noSecretsNoCustody"))
    if not terms:
        raise BackendError("terms acknowledgement is required")
    if not security:
        raise BackendError("security boundary acknowledgement is required")
    return {"termsAccepted": terms, "securityBoundaryAccepted": security}


def extract_member_evidence(packet: dict[str, Any]) -> dict[str, Any]:
    evidence = packet.get("memberBenefitReviewEvidence")
    if not isinstance(evidence, dict):
        evidence = {}
    holding_start = str(evidence.get("holdingStartDate") or packet.get("holdingStartDate") or "").strip()
    tx_hash = str(evidence.get("evidenceTxHash") or packet.get("evidenceTxHash") or "").strip()
    holding_days = holding_days_from_date(holding_start)
    return {
        "status": "user_supplied_pending_review",
        "purpose": "GCA Member 1,000,000 GCA / 30-day holding-period review",
        "minimumHolding": "1000000 GCA",
        "minimumHoldingPeriod": f"{MEMBER_HOLD_DAYS} consecutive days",
        "holdingStartDate": holding_start,
        "holdingPeriodDaysVerified": holding_days,
        "holdingPeriodPreviewEligible": holding_days >= MEMBER_HOLD_DAYS,
        "evidenceTxHash": tx_hash,
        "evidenceTxHashFormatOk": is_tx_hash(tx_hash),
        "evidenceNote": str(evidence.get("evidenceNote") or packet.get("evidenceNote") or "").strip(),
        "finalEligibilityStillRequiresSupportAndLedgerReview": True,
        "doesNotCreateLedgerRecord": False,
    }


def extract_credit_usage(packet: dict[str, Any]) -> dict[str, Any]:
    if packet.get("packetVersion") not in (None, CREDIT_USAGE_VERSION):
        raise BackendError(f"packetVersion must be {CREDIT_USAGE_VERSION}")
    credit_ledger_id = str(packet.get("creditLedgerId") or "").strip()
    service_id = str(packet.get("serviceId") or "").strip()
    service = CREDIT_SERVICE_CATALOG.get(service_id)
    if not credit_ledger_id:
        raise BackendError("creditLedgerId is required")
    if not service:
        raise BackendError("serviceId is not supported")
    raw_amount = packet.get("creditAmountUsed", service["creditUnit"])
    try:
        credit_amount_used = int(raw_amount)
    except (TypeError, ValueError) as exc:
        raise BackendError("creditAmountUsed must be an integer between 0 and 100") from exc
    if credit_amount_used < 0 or credit_amount_used > CREDIT_AMOUNT:
        raise BackendError("creditAmountUsed must be an integer between 0 and 100")
    if credit_amount_used == 0 and int(service["creditUnit"]) != 0:
        raise BackendError("creditAmountUsed must be greater than 0 for this service")
    wallet_address = str(packet.get("walletAddress") or "").strip()
    if wallet_address:
        wallet_address = normalize_wallet(wallet_address)
    return {
        "creditLedgerId": credit_ledger_id,
        "serviceId": service_id,
        "serviceName": str(service["name"]),
        "creditAmountUsed": credit_amount_used,
        "walletAddress": wallet_address,
        "operatorNote": safe_operator_text(packet.get("operatorNote"), 500),
        "source": safe_operator_text(packet.get("source") or "local-credit-usage-operator", 120),
    }


def extract_service_request(packet: dict[str, Any]) -> dict[str, Any]:
    if packet.get("packetVersion") not in (None, SERVICE_REQUEST_VERSION):
        raise BackendError(f"packetVersion must be {SERVICE_REQUEST_VERSION}")
    email = normalize_email(str(packet.get("email") or ""))
    service_id = str(packet.get("serviceId") or "").strip()
    service = CREDIT_SERVICE_CATALOG.get(service_id)
    if not service:
        raise BackendError("serviceId is not supported")
    acknowledgements = packet.get("acknowledgements")
    if not isinstance(acknowledgements, dict):
        acknowledgements = {}
    no_secrets = bool(packet.get("securityBoundaryAccepted") or acknowledgements.get("noSecretsNoCustody"))
    manual_review = bool(packet.get("manualReviewAccepted") or acknowledgements.get("manualReviewOnly"))
    no_trading_permission = bool(packet.get("noTradingPermissionAccepted") or acknowledgements.get("noTradingPermission"))
    if not no_secrets:
        raise BackendError("security boundary acknowledgement is required")
    if not manual_review:
        raise BackendError("manual review acknowledgement is required")
    if not no_trading_permission:
        raise BackendError("no trading permission acknowledgement is required")
    wallet_address = str(packet.get("walletAddress") or "").strip()
    if wallet_address:
        wallet_address = normalize_wallet(wallet_address)
    credit_ledger_id = str(packet.get("creditLedgerId") or "").strip()
    requested_credit_hold = int(service["creditUnit"])
    raw_requested_credit_hold = packet.get("requestedCreditHold")
    if raw_requested_credit_hold not in (None, ""):
        try:
            requested_credit_hold = int(raw_requested_credit_hold)
        except (TypeError, ValueError) as exc:
            raise BackendError("requestedCreditHold must be an integer between 0 and 100") from exc
    if requested_credit_hold < 0 or requested_credit_hold > CREDIT_AMOUNT:
        raise BackendError("requestedCreditHold must be an integer between 0 and 100")
    if requested_credit_hold == 0 and int(service["creditUnit"]) != 0:
        raise BackendError("requestedCreditHold must be greater than 0 for this service")
    return {
        "email": email,
        "walletAddress": wallet_address,
        "creditLedgerId": credit_ledger_id,
        "serviceId": service_id,
        "serviceName": str(service["name"]),
        "requestedCreditHold": requested_credit_hold,
        "requestTitle": safe_operator_text(packet.get("requestTitle"), 140),
        "requestSummary": safe_operator_text(packet.get("requestSummary"), 1200),
        "marketContext": safe_operator_text(packet.get("marketContext"), 500),
        "preferredLanguage": safe_operator_text(packet.get("preferredLanguage") or "zh-CN", 32),
        "source": safe_operator_text(packet.get("source") or "local-service-request", 120),
        "acknowledgements": {
            "noSecretsNoCustody": no_secrets,
            "manualReviewOnly": manual_review,
            "noTradingPermission": no_trading_permission,
        },
    }


def latest_records_by(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        record_id = str(record.get(key) or "")
        if record_id:
            latest[record_id] = record
    return list(latest.values())


def redact_for_external_sharing(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key in REDACTED_EXTERNAL_KEYS and item not in ("", None):
                redacted[key] = REDACTED_EXTERNAL_VALUE
            else:
                redacted[key] = redact_for_external_sharing(item)
        return redacted
    if isinstance(value, list):
        return [redact_for_external_sharing(item) for item in value]
    return value


def add_package_digest(package: dict[str, Any]) -> dict[str, Any]:
    package["packageDigestAlgorithm"] = PACKAGE_DIGEST_ALGORITHM
    package["packageDigestSha256"] = compute_package_digest(package)
    return package


def compute_package_digest(package: dict[str, Any]) -> str:
    digest_source = dict(package)
    digest_source.pop("packageDigestSha256", None)
    canonical = json.dumps(digest_source, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_package_digest(package: dict[str, Any]) -> dict[str, Any]:
    expected = str(package.get("packageDigestSha256") or "").strip().lower()
    algorithm = str(package.get("packageDigestAlgorithm") or "").strip()
    computed = compute_package_digest(package)
    digest_format_ok = bool(re.fullmatch(r"[a-f0-9]{64}", expected))
    algorithm_ok = algorithm == PACKAGE_DIGEST_ALGORITHM
    digest_matches = digest_format_ok and computed == expected
    ok = algorithm_ok and digest_matches
    status = "verified" if ok else "digest_mismatch"
    if not algorithm_ok:
        status = "unsupported_digest_algorithm"
    elif not digest_format_ok:
        status = "invalid_digest_format"
    return {
        "ok": ok,
        "status": status,
        "packageType": package.get("packageType", ""),
        "generatedAt": package.get("generatedAt", ""),
        "redactedForExternalSharing": bool(package.get("redactedForExternalSharing")),
        "packageDigestAlgorithm": algorithm,
        "expectedDigest": expected,
        "computedDigest": computed,
        "recordManifest": package.get("recordManifest", {}),
        "supportReviewAudit": package.get("recordManifest", {}).get("supportReviewAudit", {}),
    }


def canonical_sha256(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def support_review_legacy_prefix_digest(records: list[dict[str, Any]]) -> str:
    return canonical_sha256(records)


def compute_support_review_audit_hash(record: dict[str, Any]) -> str:
    digest_source = dict(record)
    digest_source.pop("auditRecordHash", None)
    return canonical_sha256(digest_source)


def verify_support_review_audit(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify the local continuity chain attached to support review records.

    Existing pre-chain records remain in place. The first chained record commits
    their count and canonical SHA-256 digest. Record mutation, reordering, or an
    interior deletion is detectable while a later chained record remains. Without
    an independently retained head, tail truncation or full-ledger replacement is
    outside this verifier's proof scope.
    """

    result: dict[str, Any] = {
        "ok": False,
        "status": "invalid",
        "auditChainVersion": SUPPORT_REVIEW_AUDIT_VERSION,
        "auditHashAlgorithm": SUPPORT_REVIEW_AUDIT_ALGORITHM,
        "recordCount": len(records),
        "legacyPrefixRecordCount": 0,
        "chainedRecordCount": 0,
        "chainHeadHash": "",
        "coversAllRecords": False,
        "tamperEvident": False,
        "tailTruncationDetectableWithoutExternalHead": False,
        "fullLedgerReplacementDetectableWithoutExternalHead": False,
        "independentAuthenticityProof": False,
        "firstInvalidRecordIndex": None,
        "firstInvalidReviewId": "",
        "failureReason": "",
        "sourceScope": "complete-local-support-reviews-ledger",
        "packageSliceRecomputationSupported": False,
    }
    if not records:
        result.update({
            "ok": True,
            "status": "empty",
            "coversAllRecords": True,
        })
        return result

    first_chained_index = next(
        (
            index
            for index, record in enumerate(records)
            if any(field in record for field in SUPPORT_REVIEW_AUDIT_FIELDS)
        ),
        None,
    )
    if first_chained_index is None:
        result.update({
            "status": "legacy-prefix-awaiting-anchor",
            "legacyPrefixRecordCount": len(records),
            "failureReason": "No chained support review record has anchored the legacy JSONL prefix yet.",
        })
        return result

    legacy_prefix = records[:first_chained_index]
    chained_records = records[first_chained_index:]
    legacy_prefix_digest = support_review_legacy_prefix_digest(legacy_prefix)
    result.update({
        "legacyPrefixRecordCount": len(legacy_prefix),
        "chainedRecordCount": len(chained_records),
    })

    def fail(index: int, record: dict[str, Any], reason: str) -> dict[str, Any]:
        result.update({
            "status": "invalid",
            "firstInvalidRecordIndex": index,
            "firstInvalidReviewId": str(record.get("reviewId") or ""),
            "failureReason": reason,
        })
        return result

    previous_hash = SUPPORT_REVIEW_AUDIT_GENESIS_HASH
    for sequence, record in enumerate(chained_records, start=1):
        absolute_index = first_chained_index + sequence - 1
        missing_fields = [field for field in SUPPORT_REVIEW_AUDIT_FIELDS if field not in record]
        if missing_fields:
            return fail(absolute_index, record, f"Missing audit field(s): {', '.join(missing_fields)}")
        if record.get("auditChainVersion") != SUPPORT_REVIEW_AUDIT_VERSION:
            return fail(absolute_index, record, "Unsupported support review audit chain version.")
        if record.get("auditHashAlgorithm") != SUPPORT_REVIEW_AUDIT_ALGORITHM:
            return fail(absolute_index, record, "Unsupported support review audit hash algorithm.")
        if type(record.get("auditSequence")) is not int or record.get("auditSequence") != sequence:
            return fail(absolute_index, record, "Audit sequence is missing, duplicated, or out of order.")
        if record.get("auditPreviousHash") != previous_hash:
            return fail(absolute_index, record, "Audit previous hash does not match the verified chain head.")
        if record.get("auditLegacyPrefixCount") != len(legacy_prefix):
            return fail(absolute_index, record, "Legacy prefix record count does not match the anchored count.")
        if record.get("auditLegacyPrefixSha256") != legacy_prefix_digest:
            return fail(absolute_index, record, "Legacy prefix digest does not match the current JSONL prefix.")
        record_hash = str(record.get("auditRecordHash") or "").lower()
        if not re.fullmatch(r"[a-f0-9]{64}", record_hash):
            return fail(absolute_index, record, "Audit record hash format is invalid.")
        if compute_support_review_audit_hash(record) != record_hash:
            return fail(absolute_index, record, "Audit record hash does not match the canonical record content.")
        previous_hash = record_hash

    result.update({
        "ok": True,
        "status": "verified-with-legacy-prefix" if legacy_prefix else "verified",
        "chainHeadHash": previous_hash,
        "coversAllRecords": True,
        "tamperEvident": True,
        "failureReason": "",
    })
    return result


@dataclass
class BaseRpcBalanceReader:
    rpc_url: str = BASE_RPC_URL
    timeout: float = 20.0

    def rpc(self, method: str, params: list[Any]) -> Any:
        request_payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": method,
            "params": params,
        }
        request = Request(
            self.rpc_url,
            data=json.dumps(request_payload).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "gca-member-backend/1.0"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode())
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise BackendError(f"Base RPC read failed: {exc}", HTTPStatus.BAD_GATEWAY) from exc
        if "error" in payload:
            raise BackendError(f"Base RPC error: {payload['error']}", HTTPStatus.BAD_GATEWAY)
        return payload.get("result")

    def get_balance_units(self, wallet: str) -> int:
        result = self.rpc("eth_call", [{"to": CONTRACT_ADDRESS, "data": balance_of_calldata(wallet)}, "latest"])
        result = str(result or "0x0")
        return int(result, 16)

    def get_transfer_evidence(self, tx_hash: str, recipient_wallet: str, source_wallet: str = "") -> dict[str, Any]:
        normalized_tx = str(tx_hash or "").strip().lower()
        recipient = normalize_wallet(recipient_wallet)
        source = normalize_wallet(source_wallet) if source_wallet else ""
        receipt = self.rpc("eth_getTransactionReceipt", [normalized_tx])
        evidence = {
            "status": "not_found",
            "chainId": CHAIN_ID,
            "contractAddress": CONTRACT_ADDRESS,
            "transactionHash": normalized_tx,
            "recipientWallet": recipient,
            "sourceWallet": source,
            "expectedMinimumAmount": MEMBER_BENEFIT_AMOUNT,
            "expectedMinimumAmountUnits": str(MEMBER_BENEFIT_UNITS),
            "matchedTransfer": False,
            "matchedTransferAmount": "",
            "matchedTransferAmountUnits": "0",
            "matchedFrom": "",
            "matchedTo": "",
            "receiptStatus": "",
            "readOnlyRpcMethod": "eth_getTransactionReceipt",
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTransfer": False,
        }
        if not isinstance(receipt, dict):
            return evidence

        receipt_status = str(receipt.get("status") or "").lower()
        evidence["receiptStatus"] = "success" if receipt_status == "0x1" else "failed"
        if receipt_status != "0x1":
            evidence["status"] = "tx_failed"
            return evidence

        recipient_suffix = recipient.removeprefix("0x").lower()
        source_suffix = source.removeprefix("0x").lower() if source else ""
        best_units = 0
        for log in receipt.get("logs") or []:
            if not isinstance(log, dict):
                continue
            log_address = str(log.get("address") or "").lower()
            topics = [str(topic or "").lower() for topic in (log.get("topics") or [])]
            if log_address != CONTRACT_ADDRESS.lower() or len(topics) < 3 or topics[0] != TRANSFER_TOPIC:
                continue
            from_wallet = "0x" + topics[1][-40:]
            to_wallet = "0x" + topics[2][-40:]
            if to_wallet.lower() != recipient.lower():
                continue
            if source_suffix and from_wallet.lower().removeprefix("0x") != source_suffix:
                continue
            try:
                amount_units = int(str(log.get("data") or "0x0"), 16)
            except ValueError:
                continue
            if amount_units > best_units:
                best_units = amount_units
                evidence.update({
                    "matchedTransferAmount": units_to_gca(amount_units),
                    "matchedTransferAmountUnits": str(amount_units),
                    "matchedFrom": from_wallet.lower(),
                    "matchedTo": to_wallet.lower(),
                })

        if best_units >= MEMBER_BENEFIT_UNITS:
            evidence["status"] = "verified"
            evidence["matchedTransfer"] = True
        else:
            evidence["status"] = "contract_or_amount_mismatch"
        return evidence


class JsonlLedgerStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ledger_lock = threading.RLock()

    def path(self, name: str) -> Path:
        return self.data_dir / f"{name}.jsonl"

    def append(self, name: str, record: dict[str, Any]) -> dict[str, Any]:
        with self._ledger_lock:
            if name == "support_reviews":
                existing_records = self.read_all(name)
                audit = verify_support_review_audit(existing_records)
                if audit["status"] not in {"empty", "legacy-prefix-awaiting-anchor"} and not audit["ok"]:
                    raise BackendError(
                        "support review audit chain integrity check failed; refusing to append",
                        HTTPStatus.CONFLICT,
                    )

                for field in SUPPORT_REVIEW_AUDIT_FIELDS:
                    record.pop(field, None)
                if audit["ok"] and audit["status"] != "empty":
                    sequence = int(audit["chainedRecordCount"]) + 1
                    previous_hash = str(audit["chainHeadHash"])
                    legacy_prefix_count = int(audit["legacyPrefixRecordCount"])
                    first_chained_index = legacy_prefix_count
                    first_chained = existing_records[first_chained_index]
                    legacy_prefix_digest = str(first_chained["auditLegacyPrefixSha256"])
                else:
                    sequence = 1
                    previous_hash = SUPPORT_REVIEW_AUDIT_GENESIS_HASH
                    legacy_prefix_count = len(existing_records)
                    legacy_prefix_digest = support_review_legacy_prefix_digest(existing_records)

                record.update({
                    "auditChainVersion": SUPPORT_REVIEW_AUDIT_VERSION,
                    "auditHashAlgorithm": SUPPORT_REVIEW_AUDIT_ALGORITHM,
                    "auditSequence": sequence,
                    "auditPreviousHash": previous_hash,
                    "auditLegacyPrefixCount": legacy_prefix_count,
                    "auditLegacyPrefixSha256": legacy_prefix_digest,
                })
                record["auditRecordHash"] = compute_support_review_audit_hash(record)

            path = self.path(name)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
                handle.write("\n")
                handle.flush()
        return record

    def read_all(self, name: str) -> list[dict[str, Any]]:
        with self._ledger_lock:
            path = self.path(name)
            if not path.exists():
                return []
            records: list[dict[str, Any]] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    records.append(json.loads(line))
            return records

    def find(self, name: str, **filters: str) -> list[dict[str, Any]]:
        records = self.read_all(name)
        for key, value in filters.items():
            if value:
                normalized = value.lower()
                records = [record for record in records if str(record.get(key, "")).lower() == normalized]
        return records

    def exists(self, name: str, record_id_key: str, record_id: str) -> bool:
        return any(record.get(record_id_key) == record_id for record in self.read_all(name))


class GcaMemberBackend:
    def __init__(self, store: JsonlLedgerStore, balance_reader: Any):
        self.store = store
        self.balance_reader = balance_reader

    def support_review_audit(self) -> dict[str, Any]:
        return verify_support_review_audit(self.store.read_all("support_reviews"))

    def require_writable_support_review_audit(self) -> dict[str, Any]:
        audit = self.support_review_audit()
        if audit["status"] not in {"empty", "legacy-prefix-awaiting-anchor"} and not audit["ok"]:
            raise BackendError(
                "support review audit chain integrity check failed; repair or restore the local ledger before writing",
                HTTPStatus.CONFLICT,
            )
        return audit

    def submit_email_registration(self, packet: dict[str, Any]) -> dict[str, Any]:
        registration_input = extract_email_registration(packet)
        email = registration_input["email"]
        registration_id = stable_id("gca_email", email)
        existing = self.store.find("email_registrations", emailRegistrationId=registration_id)
        if existing:
            latest = existing[-1]
            return {
                "ok": True,
                "emailRegistration": latest,
                "alreadyRegistered": True,
                "nextStep": "Email is already on the GCA user list. No wallet action, signature, or payment is required for email registration.",
            }

        created_at = iso_now()
        record = {
            "emailRegistrationId": registration_id,
            "packetVersion": EMAIL_REGISTRATION_VERSION,
            "createdAt": created_at,
            "source": registration_input["source"],
            "status": "received",
            "email": email,
            "displayName": registration_input["displayName"],
            "language": registration_input["language"],
            "interests": registration_input["interests"],
            "contactConsentAccepted": registration_input["contactConsentAccepted"],
            "securityBoundaryAccepted": registration_input["securityBoundaryAccepted"],
            "walletRequired": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "requiresPrivateKey": False,
            "requiresSeedPhrase": False,
            "requiresExchangeApiSecret": False,
            "requiresWithdrawalPermission": False,
            "publicSelfServiceClaim": False,
            "automaticTokenTransfer": False,
            "nextStep": "GCA support can contact this email when customer registration, member access, or product updates are ready.",
        }
        self.store.append("email_registrations", record)
        return {
            "ok": True,
            "emailRegistration": record,
            "alreadyRegistered": False,
            "nextStep": record["nextStep"],
        }

    def submit_pre_registration(self, packet: dict[str, Any]) -> dict[str, Any]:
        self.require_writable_support_review_audit()
        if packet.get("packetVersion") not in (None, PACKET_VERSION):
            raise BackendError(f"packetVersion must be {PACKET_VERSION}")
        user = extract_user(packet)
        acknowledgements = extract_acknowledgements(packet)
        program_intent = str(packet.get("programIntent") or "general_waitlist").strip()
        if program_intent not in ALLOWED_PROGRAM_INTENTS:
            raise BackendError("programIntent is not supported")
        declared_units = parse_gca_to_units(packet.get("declaredGcaBalance"))
        evidence = extract_member_evidence(packet)
        created_at = iso_now()
        registration_id = stable_id("gca_reg", user["email"], user["walletAddress"], created_at)
        registration = {
            "registrationId": registration_id,
            "packetVersion": PACKET_VERSION,
            "createdAt": created_at,
            "source": "local-gca-member-backend",
            "status": "received",
            "email": user["email"],
            "telegram": user["telegram"],
            "walletAddress": user["walletAddress"],
            "declaredGcaBalance": units_to_gca(declared_units),
            "programIntent": program_intent,
            "termsAccepted": acknowledgements["termsAccepted"],
            "securityBoundaryAccepted": acknowledgements["securityBoundaryAccepted"],
            "memberBenefitReviewEvidence": evidence,
        }
        self.store.append("pre_registrations", registration)
        wallet_verification = self.verify_wallet(
            user["walletAddress"],
            registration_id=registration_id,
            email=user["email"],
            member_evidence=evidence,
            write_record=True,
        )
        credit = self.maybe_create_credit_ledger(registration, wallet_verification)
        member = self.maybe_create_member_ledger(registration, wallet_verification, evidence)
        review = self.create_review_record(registration, wallet_verification, evidence, credit, member)
        return {
            "ok": True,
            "registration": registration,
            "walletVerification": wallet_verification,
            "creditLedger": credit,
            "memberLedger": member,
            "memberReview": review,
            "nextStep": review["nextStep"],
        }

    def verify_wallet(
        self,
        wallet: str,
        *,
        registration_id: str | None = None,
        email: str = "",
        member_evidence: dict[str, Any] | None = None,
        write_record: bool = True,
    ) -> dict[str, Any]:
        wallet_address = normalize_wallet(wallet)
        checked_at = iso_now()
        member_evidence = member_evidence or {}
        raw_balance = self.balance_reader.get_balance_units(wallet_address)
        holder_eligible = raw_balance >= HOLDER_THRESHOLD_UNITS
        member_balance_eligible = raw_balance >= MEMBER_THRESHOLD_UNITS
        holding_days = int(member_evidence.get("holdingPeriodDaysVerified") or 0)
        tx_ok = bool(member_evidence.get("evidenceTxHashFormatOk"))
        member_period_eligible = member_balance_eligible and holding_days >= MEMBER_HOLD_DAYS and tx_ok
        status = "verified" if holder_eligible else "below_threshold"
        record = {
            "walletVerificationId": stable_id("gca_wallet", registration_id or "", wallet_address, checked_at),
            "registrationId": registration_id or "",
            "email": email,
            "walletAddress": wallet_address,
            "chainId": CHAIN_ID,
            "contractAddress": CONTRACT_ADDRESS,
            "checkedAt": checked_at,
            "rawBalance": str(raw_balance),
            "gcaBalance": units_to_gca(raw_balance),
            "holderBonusEligible": holder_eligible,
            "gcaMemberEligible": member_balance_eligible,
            "gcaMemberHoldingPeriodEligible": member_period_eligible,
            "holdingPeriodDaysVerified": holding_days,
            "evidenceTxHashFormatOk": tx_ok,
            "verificationProvider": "Base Mainnet public RPC eth_call balanceOf",
            "requiresSignature": False,
            "requiresTransaction": False,
            "status": status,
        }
        if write_record:
            self.store.append("wallet_verifications", record)
        return record

    def wallet_verification_from_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        wallet = str(payload.get("walletAddress") or "")
        evidence = payload.get("memberBenefitReviewEvidence")
        if not isinstance(evidence, dict):
            evidence = extract_member_evidence(payload)
        registration_id = str(payload.get("registrationId") or "")
        email = str(payload.get("email") or "").strip().lower()
        return self.verify_wallet(wallet, registration_id=registration_id, email=email, member_evidence=evidence)

    def maybe_create_credit_ledger(
        self,
        registration: dict[str, Any],
        wallet_verification: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not wallet_verification["holderBonusEligible"]:
            return None
        credit_id = stable_id("gca_credit", registration["email"], registration["walletAddress"])
        if self.store.exists("credit_ledger", "creditLedgerId", credit_id):
            existing = self.store.find("credit_ledger", creditLedgerId=credit_id)
            return existing[-1] if existing else None
        activated = utc_now()
        record = {
            "creditLedgerId": credit_id,
            "registrationId": registration["registrationId"],
            "email": registration["email"],
            "walletAddress": registration["walletAddress"],
            "creditAmount": CREDIT_AMOUNT,
            "creditType": "GCA AI Quant Access credits",
            "activatedAt": activated.isoformat().replace("+00:00", "Z"),
            "expiresAt": (activated + timedelta(days=CREDIT_EXPIRY_DAYS)).isoformat().replace("+00:00", "Z"),
            "remainingCredits": CREDIT_AMOUNT,
            "source": "local-wallet-balance-verification",
            "selfServicePublicClaim": False,
            "transferable": False,
            "cashRedeemable": False,
            "status": "ledger_recorded",
        }
        return self.store.append("credit_ledger", record)

    def record_service_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.require_writable_support_review_audit()
        request_input = extract_service_request(payload)
        credit = None
        remaining_credits = ""
        if request_input["creditLedgerId"]:
            credit_versions = self.store.find("credit_ledger", creditLedgerId=request_input["creditLedgerId"])
            if not credit_versions:
                raise BackendError("creditLedgerId was not found", HTTPStatus.NOT_FOUND)
            credit = credit_versions[-1]
            if str(credit.get("email") or "").lower() != request_input["email"]:
                raise BackendError("email must match the credit ledger email")
            if request_input["walletAddress"] and request_input["walletAddress"] != str(credit.get("walletAddress") or "").lower():
                raise BackendError("walletAddress must match the credit ledger wallet")
            remaining_credits = safe_operator_int(credit.get("remainingCredits"))
            status = (
                "queued_operator_review"
                if request_input["requestedCreditHold"] <= remaining_credits
                else "queued_insufficient_credits"
            )
        else:
            status = "queued_missing_credit_ledger"

        requested_at = iso_now()
        service_request_id = stable_id(
            "gca_service_req",
            request_input["email"],
            request_input["serviceId"],
            requested_at,
        )
        service_request = {
            "serviceRequestId": service_request_id,
            "packetVersion": SERVICE_REQUEST_VERSION,
            "createdAt": requested_at,
            "status": status,
            "email": request_input["email"],
            "walletAddress": request_input["walletAddress"] or (str(credit.get("walletAddress") or "") if credit else ""),
            "creditLedgerId": request_input["creditLedgerId"],
            "serviceId": request_input["serviceId"],
            "serviceName": request_input["serviceName"],
            "requestedCreditHold": request_input["requestedCreditHold"],
            "remainingCreditsAtRequest": remaining_credits,
            "requestTitle": request_input["requestTitle"],
            "requestSummary": request_input["requestSummary"],
            "marketContext": request_input["marketContext"],
            "preferredLanguage": request_input["preferredLanguage"],
            "source": request_input["source"],
            "acknowledgements": request_input["acknowledgements"],
            "localOnly": True,
            "operatorReviewRequired": True,
            "doesNotDeductCredits": True,
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTokenTransfer": False,
            "writesWallet": False,
            "createsTradingPermission": False,
        }
        self.store.append("service_requests", service_request)

        review_status = "received" if status == "queued_operator_review" else "needs_more_information"
        next_step = "Operator should review the request, confirm service scope, and only record credit usage after delivery evidence exists."
        if status == "queued_missing_credit_ledger":
            next_step = "Ask the user to complete member access and wallet verification before service fulfillment."
        if status == "queued_insufficient_credits":
            next_step = "Confirm remaining credits or route the request to support before any service delivery."
        review = {
            "reviewId": stable_id("gca_review_service_request", service_request_id),
            "registrationId": str(credit.get("registrationId") or "") if credit else "",
            "lane": "gca-service-request",
            "status": review_status,
            "updatedAt": requested_at,
            "walletAddress": service_request["walletAddress"],
            "holderBonusEligible": bool(credit),
            "gcaMemberEligible": False,
            "serviceRequestId": service_request_id,
            "creditLedgerId": request_input["creditLedgerId"],
            "serviceId": request_input["serviceId"],
            "serviceName": request_input["serviceName"],
            "requestedCreditHold": request_input["requestedCreditHold"],
            "remainingCreditsAtRequest": remaining_credits,
            "memberLedgerId": "",
            "memberBenefitClaimStatus": "",
            "nextStep": next_step,
            "publicEvidenceReference": service_request_id,
            "supportNote": request_input["requestSummary"] or "GCA AI Quant Access service request queued for operator review.",
            "source": "local-service-request",
            "localOnly": True,
            "selfServicePublicClaim": False,
            "automaticUserReply": False,
            "automaticTokenTransfer": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "writesProductionData": False,
        }
        self.store.append("support_reviews", review)

        return {
            "ok": True,
            "packetVersion": SERVICE_REQUEST_VERSION,
            "serviceRequest": service_request,
            "supportReview": review,
            "creditLedger": credit,
            "nextStep": next_step,
            "boundaries": {
                "localhostOnly": True,
                "localJsonlLedgerOnly": True,
                "writesProductionData": False,
                "walletCalls": False,
                "deductsCredits": False,
                "requiresSignature": False,
                "requiresTransaction": False,
                "automaticTokenTransfer": False,
                "writesWallet": False,
                "createsTradingPermission": False,
            },
        }

    def record_credit_usage(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.require_writable_support_review_audit()
        usage_input = extract_credit_usage(payload)
        credit_versions = self.store.find("credit_ledger", creditLedgerId=usage_input["creditLedgerId"])
        if not credit_versions:
            raise BackendError("creditLedgerId was not found", HTTPStatus.NOT_FOUND)
        credit = credit_versions[-1]
        wallet_address = usage_input["walletAddress"]
        if wallet_address and wallet_address != str(credit.get("walletAddress") or "").lower():
            raise BackendError("walletAddress must match the credit ledger wallet")

        remaining_before = safe_operator_int(credit.get("remainingCredits"))
        if usage_input["creditAmountUsed"] > remaining_before:
            raise BackendError("creditAmountUsed exceeds remaining credits", HTTPStatus.CONFLICT)

        used_at = iso_now()
        remaining_after = remaining_before - usage_input["creditAmountUsed"]
        usage_id = stable_id(
            "gca_credit_use",
            usage_input["creditLedgerId"],
            usage_input["serviceId"],
            usage_input["creditAmountUsed"],
            used_at,
        )
        status = "exhausted" if remaining_after == 0 else "usage_recorded"
        usage_record = {
            "creditUsageId": usage_id,
            "creditLedgerId": usage_input["creditLedgerId"],
            "registrationId": credit.get("registrationId", ""),
            "email": credit.get("email", ""),
            "walletAddress": credit.get("walletAddress", ""),
            "serviceId": usage_input["serviceId"],
            "serviceName": usage_input["serviceName"],
            "creditAmountUsed": usage_input["creditAmountUsed"],
            "remainingCreditsBefore": remaining_before,
            "remainingCreditsAfter": remaining_after,
            "usedAt": used_at,
            "source": usage_input["source"],
            "operatorNote": usage_input["operatorNote"],
            "status": status,
            "localOnly": True,
            "selfServicePublicClaim": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTokenTransfer": False,
            "writesWallet": False,
        }
        self.store.append("credit_usage", usage_record)

        updated_credit = dict(credit)
        updated_credit.update({
            "remainingCredits": remaining_after,
            "lastUsedAt": used_at,
            "lastCreditUsageId": usage_id,
            "lastServiceId": usage_input["serviceId"],
            "status": "exhausted" if remaining_after == 0 else "ledger_recorded",
        })
        self.store.append("credit_ledger", updated_credit)

        review = {
            "reviewId": stable_id("gca_review_credit_usage", usage_id),
            "registrationId": credit.get("registrationId", ""),
            "lane": "gca-credit-usage",
            "status": "ledger_recorded",
            "updatedAt": used_at,
            "walletAddress": credit.get("walletAddress", ""),
            "holderBonusEligible": True,
            "gcaMemberEligible": False,
            "creditLedgerId": usage_input["creditLedgerId"],
            "creditUsageId": usage_id,
            "serviceId": usage_input["serviceId"],
            "serviceName": usage_input["serviceName"],
            "creditAmountUsed": usage_input["creditAmountUsed"],
            "remainingCreditsBefore": remaining_before,
            "remainingCreditsAfter": remaining_after,
            "memberLedgerId": "",
            "memberBenefitClaimStatus": "",
            "nextStep": "Credit usage was recorded in the local operator ledger. Confirm service delivery evidence before any support follow-up.",
            "publicEvidenceReference": usage_id,
            "supportNote": usage_input["operatorNote"] or "GCA AI Quant Access credit usage recorded by local operator backend.",
            "source": "local-credit-usage-operator",
            "localOnly": True,
            "selfServicePublicClaim": False,
            "automaticUserReply": False,
            "automaticTokenTransfer": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "writesProductionData": False,
        }
        self.store.append("support_reviews", review)

        return {
            "ok": True,
            "packetVersion": CREDIT_USAGE_VERSION,
            "creditUsage": usage_record,
            "creditLedger": updated_credit,
            "supportReview": review,
            "alreadyRecorded": False,
            "boundaries": {
                "localhostOnly": True,
                "localJsonlLedgerOnly": True,
                "writesProductionData": False,
                "walletCalls": False,
                "requiresSignature": False,
                "requiresTransaction": False,
                "automaticTokenTransfer": False,
                "writesWallet": False,
            },
        }

    def maybe_create_member_ledger(
        self,
        registration: dict[str, Any],
        wallet_verification: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not wallet_verification["gcaMemberEligible"]:
            return None
        member_id = stable_id("gca_member", registration["email"], registration["walletAddress"])
        if self.store.exists("member_ledger", "memberLedgerId", member_id):
            existing = self.store.find("member_ledger", memberLedgerId=member_id)
            return existing[-1] if existing else None
        activated = utc_now()
        evidence_status = (
            "eligible"
            if wallet_verification["gcaMemberHoldingPeriodEligible"]
            else "needs_more_information"
        )
        status = "active" if evidence_status == "eligible" else "queued"
        record = {
            "memberLedgerId": member_id,
            "registrationId": registration["registrationId"],
            "email": registration["email"],
            "walletAddress": registration["walletAddress"],
            "tierName": "GCA Member",
            "verifiedBalance": wallet_verification["gcaBalance"],
            "holdingPeriodStartedAt": evidence.get("holdingStartDate", ""),
            "holdingStartDate": evidence.get("holdingStartDate", ""),
            "holdingPeriodDaysVerified": wallet_verification["holdingPeriodDaysVerified"],
            "holdingPeriodPreviewEligible": evidence.get("holdingPeriodPreviewEligible", False),
            "evidenceTxHash": evidence.get("evidenceTxHash", ""),
            "evidenceTxHashFormatOk": evidence.get("evidenceTxHashFormatOk", False),
            "memberBenefitReviewEvidenceStatus": evidence_status,
            "memberBenefitAmount": MEMBER_BENEFIT_AMOUNT,
            "memberBenefitClaimStatus": "pending_manual_reserve_transfer",
            "memberBenefitTransferTx": "",
            "activatedAt": activated.isoformat().replace("+00:00", "Z") if status == "active" else "",
            "memberBenefitClaimedAt": "",
            "nextRefreshDueAt": (activated + timedelta(days=MEMBER_REFRESH_DAYS)).isoformat().replace("+00:00", "Z") if status == "active" else "",
            "selfServicePublicClaim": False,
            "automaticTransfer": False,
            "requiresManualReserveTransferReview": True,
            "status": status,
        }
        return self.store.append("member_ledger", record)

    def create_review_record(
        self,
        registration: dict[str, Any],
        wallet_verification: dict[str, Any],
        evidence: dict[str, Any],
        credit: dict[str, Any] | None,
        member: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not wallet_verification["holderBonusEligible"]:
            status = "below_threshold"
            next_step = "Wallet balance is below 10,000 GCA. No credit or member ledger record was created."
        elif member and member["status"] == "active":
            status = "ledger_recorded"
            next_step = "100 credits and GCA Member records were created locally. Member benefit transfer still requires manual reserve-wallet approval."
        elif credit and wallet_verification["gcaMemberEligible"]:
            status = "needs_more_information"
            next_step = "100 credits record was created. GCA Member record needs valid 30-day holding evidence before activation."
        else:
            status = "ledger_recorded"
            next_step = "100 credits record was created locally. GCA Member threshold was not met."
        record = {
            "reviewId": stable_id("gca_review", registration["registrationId"], wallet_verification["walletVerificationId"]),
            "registrationId": registration["registrationId"],
            "lane": "gca-member-local-intake",
            "status": status,
            "updatedAt": iso_now(),
            "walletAddress": registration["walletAddress"],
            "holderBonusEligible": wallet_verification["holderBonusEligible"],
            "gcaMemberEligible": wallet_verification["gcaMemberEligible"],
            "holdingStartDate": evidence.get("holdingStartDate", ""),
            "holdingPeriodDaysVerified": wallet_verification["holdingPeriodDaysVerified"],
            "evidenceTxHash": evidence.get("evidenceTxHash", ""),
            "evidenceTxHashFormatOk": evidence.get("evidenceTxHashFormatOk", False),
            "memberBenefitReviewEvidenceStatus": member["memberBenefitReviewEvidenceStatus"] if member else "not_applicable",
            "creditLedgerId": credit["creditLedgerId"] if credit else "",
            "memberLedgerId": member["memberLedgerId"] if member else "",
            "nextStep": next_step,
            "publicEvidenceReference": "local-only-backend",
            "supportNote": "Created by local GCA member backend; public self-service claim remains off.",
        }
        return self.store.append("support_reviews", record)

    def record_member_benefit_transfer(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.require_writable_support_review_audit()
        member_id = str(payload.get("memberLedgerId") or "").strip()
        transfer_tx = str(payload.get("memberBenefitTransferTx") or "").strip()
        source_wallet = str(payload.get("sourceWallet") or "").strip()
        recipient_wallet = str(payload.get("recipientWallet") or "").strip()
        reviewer_note = str(payload.get("reviewerNote") or "").strip()

        if not member_id:
            raise BackendError("memberLedgerId is required")
        if not is_tx_hash(transfer_tx):
            raise BackendError("memberBenefitTransferTx must be a valid transaction hash")
        transfer_tx = transfer_tx.lower()
        if source_wallet:
            source_wallet = normalize_wallet(source_wallet)
        if recipient_wallet:
            recipient_wallet = normalize_wallet(recipient_wallet)

        member_versions = self.store.find("member_ledger", memberLedgerId=member_id)
        if not member_versions:
            raise BackendError("memberLedgerId was not found", HTTPStatus.NOT_FOUND)
        member = member_versions[-1]

        transfer_id = stable_id("gca_transfer", member_id, transfer_tx)
        if self.store.exists("member_benefit_transfers", "transferRecordId", transfer_id):
            existing = self.store.find("member_benefit_transfers", transferRecordId=transfer_id)
            return {
                "transferRecord": existing[-1],
                "memberLedger": member,
                "supportReview": None,
                "alreadyRecorded": True,
            }

        if member.get("status") != "active":
            raise BackendError("member ledger record must be active before transfer can be recorded")
        if member.get("memberBenefitClaimStatus") != "pending_manual_reserve_transfer":
            raise BackendError("member benefit is not pending manual reserve transfer", HTTPStatus.CONFLICT)
        if recipient_wallet and recipient_wallet != member.get("walletAddress"):
            raise BackendError("recipientWallet must match the verified member wallet")
        recipient_wallet = recipient_wallet or str(member.get("walletAddress") or "")
        transfer_evidence = self.balance_reader.get_transfer_evidence(
            transfer_tx,
            recipient_wallet=recipient_wallet,
            source_wallet=source_wallet,
        )
        if not isinstance(transfer_evidence, dict) or transfer_evidence.get("matchedTransfer") is not True:
            raise BackendError(
                "memberBenefitTransferTx was not verified as a matching GCA transfer to the member wallet",
                HTTPStatus.CONFLICT,
            )

        transferred_at = iso_now()
        basescan_url = f"{BASESCAN_TX_URL}{transfer_tx}"
        transfer_record = {
            "transferRecordId": transfer_id,
            "memberLedgerId": member_id,
            "registrationId": member.get("registrationId", ""),
            "email": member.get("email", ""),
            "sourceWallet": source_wallet,
            "recipientWallet": recipient_wallet,
            "walletAddress": recipient_wallet,
            "memberBenefitAmount": MEMBER_BENEFIT_AMOUNT,
            "memberBenefitTransferTx": transfer_tx,
            "memberBenefitTransferUrl": basescan_url,
            "transferVerificationStatus": transfer_evidence.get("status", ""),
            "transferVerification": transfer_evidence,
            "transferredAt": transferred_at,
            "reviewerNote": reviewer_note,
            "source": "local-operator-manual-reserve-transfer-record",
            "automaticTransfer": False,
            "selfServicePublicClaim": False,
            "status": "transferred",
        }
        self.store.append("member_benefit_transfers", transfer_record)

        updated_member = dict(member)
        updated_member.update({
            "memberBenefitClaimStatus": "transferred",
            "memberBenefitTransferTx": transfer_tx,
            "memberBenefitTransferUrl": basescan_url,
            "memberBenefitClaimedAt": transferred_at,
            "transferVerificationStatus": transfer_evidence.get("status", ""),
            "sourceWallet": source_wallet,
            "recipientWallet": recipient_wallet,
            "transferRecordId": transfer_id,
            "updatedAt": transferred_at,
            "automaticTransfer": False,
            "selfServicePublicClaim": False,
        })
        self.store.append("member_ledger", updated_member)

        review = {
            "reviewId": stable_id("gca_review", member_id, transfer_tx),
            "registrationId": member.get("registrationId", ""),
            "lane": "gca-member-benefit-transfer",
            "status": "ledger_recorded",
            "updatedAt": transferred_at,
            "walletAddress": recipient_wallet,
            "holderBonusEligible": True,
            "gcaMemberEligible": True,
            "holdingStartDate": member.get("holdingStartDate", ""),
            "holdingPeriodDaysVerified": member.get("holdingPeriodDaysVerified", 0),
            "evidenceTxHash": member.get("evidenceTxHash", ""),
            "evidenceTxHashFormatOk": member.get("evidenceTxHashFormatOk", False),
            "memberBenefitReviewEvidenceStatus": member.get("memberBenefitReviewEvidenceStatus", ""),
            "creditLedgerId": "",
            "memberLedgerId": member_id,
            "memberBenefitClaimStatus": "transferred",
            "memberBenefitTransferTx": transfer_tx,
            "memberBenefitTransferUrl": basescan_url,
            "transferVerificationStatus": transfer_evidence.get("status", ""),
            "transferRecordId": transfer_id,
            "nextStep": "Manual reserve-wallet transfer was recorded locally. Verify the transaction on BaseScan before public support follow-up.",
            "publicEvidenceReference": transfer_tx,
            "supportNote": reviewer_note or "Manual GCA Member benefit transfer recorded by local operator backend.",
        }
        self.store.append("support_reviews", review)

        return {
            "transferRecord": transfer_record,
            "memberLedger": updated_member,
            "supportReview": review,
            "alreadyRecorded": False,
        }

    def record_support_review_update(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.require_writable_support_review_audit()
        status = str(payload.get("status") or "").strip()
        if status not in SUPPORT_REVIEW_UPDATE_STATUSES:
            raise BackendError("status is not supported for a support review update")

        parent_review_id = str(payload.get("parentReviewId") or payload.get("reviewId") or "").strip()
        member_id = str(payload.get("memberLedgerId") or "").strip()
        credit_id = str(payload.get("creditLedgerId") or "").strip()
        registration_id = str(payload.get("registrationId") or "").strip()
        wallet = str(payload.get("walletAddress") or "").strip()
        next_step = safe_operator_text(payload.get("nextStep"), 500)
        support_note = safe_operator_text(payload.get("supportNote"), 1000)
        reviewer_note = safe_operator_text(payload.get("reviewerNote"), 1000)
        public_reference = safe_operator_text(payload.get("publicEvidenceReference"), 160)
        lane = safe_operator_text(payload.get("lane") or "gca-member-operator-follow-up", 120)

        if not any((parent_review_id, member_id, credit_id, registration_id, wallet)):
            raise BackendError("reviewId, memberLedgerId, creditLedgerId, registrationId, or walletAddress is required")
        if not next_step:
            raise BackendError("nextStep is required")

        parent_review: dict[str, Any] = {}
        if parent_review_id:
            parent_versions = self.store.find("support_reviews", reviewId=parent_review_id)
            if parent_versions:
                parent_review = parent_versions[-1]

        member: dict[str, Any] = {}
        if member_id:
            member_versions = self.store.find("member_ledger", memberLedgerId=member_id)
            if not member_versions:
                raise BackendError("memberLedgerId was not found", HTTPStatus.NOT_FOUND)
            member = member_versions[-1]

        credit: dict[str, Any] = {}
        if credit_id:
            credit_versions = self.store.find("credit_ledger", creditLedgerId=credit_id)
            if not credit_versions:
                raise BackendError("creditLedgerId was not found", HTTPStatus.NOT_FOUND)
            credit = credit_versions[-1]

        registration_id = registration_id or str(parent_review.get("registrationId") or member.get("registrationId") or credit.get("registrationId") or "")
        wallet = wallet or str(parent_review.get("walletAddress") or member.get("walletAddress") or credit.get("walletAddress") or "")
        if wallet:
            wallet = normalize_wallet(wallet)
        member_id = member_id or str(parent_review.get("memberLedgerId") or "")
        credit_id = credit_id or str(parent_review.get("creditLedgerId") or "")
        updated_at = iso_now()

        review = {
            "reviewId": stable_id("gca_review_update", parent_review_id, registration_id, wallet, status, updated_at),
            "parentReviewId": parent_review_id,
            "registrationId": registration_id,
            "lane": lane,
            "status": status,
            "updatedAt": updated_at,
            "walletAddress": wallet,
            "holderBonusEligible": bool(parent_review.get("holderBonusEligible") or credit or member),
            "gcaMemberEligible": bool(parent_review.get("gcaMemberEligible") or member),
            "holdingStartDate": safe_operator_text(
                payload.get("holdingStartDate") or parent_review.get("holdingStartDate") or member.get("holdingStartDate"),
                80,
            ),
            "holdingPeriodDaysVerified": safe_operator_int(
                payload.get("holdingPeriodDaysVerified")
                or parent_review.get("holdingPeriodDaysVerified")
                or member.get("holdingPeriodDaysVerified")
            ),
            "evidenceTxHash": safe_operator_text(
                payload.get("evidenceTxHash") or parent_review.get("evidenceTxHash") or member.get("evidenceTxHash"),
                120,
            ),
            "evidenceTxHashFormatOk": bool(parent_review.get("evidenceTxHashFormatOk") or member.get("evidenceTxHashFormatOk")),
            "memberBenefitReviewEvidenceStatus": safe_operator_text(
                payload.get("memberBenefitReviewEvidenceStatus")
                or parent_review.get("memberBenefitReviewEvidenceStatus")
                or member.get("memberBenefitReviewEvidenceStatus")
                or "not_applicable",
                120,
            ),
            "creditLedgerId": credit_id,
            "memberLedgerId": member_id,
            "memberBenefitClaimStatus": safe_operator_text(
                payload.get("memberBenefitClaimStatus")
                or parent_review.get("memberBenefitClaimStatus")
                or member.get("memberBenefitClaimStatus"),
                120,
            ),
            "memberBenefitTransferTx": safe_operator_text(
                payload.get("memberBenefitTransferTx")
                or parent_review.get("memberBenefitTransferTx")
                or member.get("memberBenefitTransferTx"),
                120,
            ),
            "nextStep": next_step,
            "publicEvidenceReference": public_reference or safe_operator_text(parent_review.get("publicEvidenceReference"), 160) or "local-operator-update",
            "supportNote": support_note,
            "reviewerNote": reviewer_note,
            "source": "local-operator-support-review-update",
            "localOnly": True,
            "selfServicePublicClaim": False,
            "automaticUserReply": False,
            "automaticTokenTransfer": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "writesProductionData": False,
        }
        self.store.append("support_reviews", review)
        return {
            "ok": True,
            "supportReview": review,
            "alreadyRecorded": False,
            "boundaries": {
                "localhostOnly": True,
                "localJsonlLedgerOnly": True,
                "writesProductionData": False,
                "walletCalls": False,
                "requiresSignature": False,
                "requiresTransaction": False,
                "automaticUserReply": False,
                "automaticTokenTransfer": False,
                "memberBenefitTransferAutomatic": False,
            },
        }

    def query(self, ledger: str, query: dict[str, list[str]]) -> list[dict[str, Any]]:
        filters: dict[str, str] = {}
        for key in (
            "emailRegistrationId",
            "reviewId",
            "parentReviewId",
            "walletAddress",
            "email",
            "registrationId",
            "creditLedgerId",
            "serviceRequestId",
            "creditUsageId",
            "serviceId",
            "memberLedgerId",
            "transferRecordId",
            "memberBenefitTransferTx",
        ):
            value = query.get(key, [""])[0]
            if value:
                filters[key] = value.lower() if key in {"walletAddress", "email"} else value
        return self.store.find(ledger, **filters)

    def operator_summary(self, limit: int = 25) -> dict[str, Any]:
        ledgers = {name: self.store.read_all(name) for name in LEDGER_NAMES}
        credit_records = latest_records_by(ledgers["credit_ledger"], "creditLedgerId")
        service_request_records = latest_records_by(ledgers["service_requests"], "serviceRequestId")
        credit_usage_records = latest_records_by(ledgers["credit_usage"], "creditUsageId")
        member_records = latest_records_by(ledgers["member_ledger"], "memberLedgerId")
        transfer_records = latest_records_by(ledgers["member_benefit_transfers"], "transferRecordId")
        review_records = ledgers["support_reviews"]
        support_review_audit = verify_support_review_audit(review_records)
        summary = {
            "ok": True,
            "service": "gca-member-backend",
            "generatedAt": iso_now(),
            "chainId": CHAIN_ID,
            "contractAddress": CONTRACT_ADDRESS,
            "publicSelfServiceClaim": False,
            "automaticTokenTransfer": False,
            "localJsonlDataOnly": True,
            "supportReviewAudit": support_review_audit,
            "dataLedgers": {
                name: {
                    "count": len(records),
                    "latest": records[-limit:][::-1],
                }
                for name, records in ledgers.items()
            },
            "totals": {
                "emailRegistrations": len(ledgers["email_registrations"]),
                "preRegistrations": len(ledgers["pre_registrations"]),
                "walletVerifications": len(ledgers["wallet_verifications"]),
                "creditLedgerRecords": len(credit_records),
                "serviceRequests": len(service_request_records),
                "serviceRequestsPendingOperatorReview": sum(
                    1
                    for record in service_request_records
                    if record.get("status") == "queued_operator_review"
                ),
                "serviceRequestsNeedingMoreInformation": sum(
                    1
                    for record in service_request_records
                    if record.get("status") in {"queued_missing_credit_ledger", "queued_insufficient_credits"}
                ),
                "requestedCreditHolds": sum(int(record.get("requestedCreditHold") or 0) for record in service_request_records),
                "creditUsageRecords": len(credit_usage_records),
                "creditsConsumed": sum(int(record.get("creditAmountUsed") or 0) for record in credit_usage_records),
                "exhaustedCreditLedgers": sum(1 for record in credit_records if record.get("status") == "exhausted"),
                "memberLedgerRecords": len(member_records),
                "activeMembers": sum(1 for record in member_records if record.get("status") == "active"),
                "queuedMembers": sum(1 for record in member_records if record.get("status") == "queued"),
                "memberBenefitTransfers": len(transfer_records),
                "transferredMemberBenefits": sum(1 for record in member_records if record.get("memberBenefitClaimStatus") == "transferred"),
                "supportReviews": len(review_records),
                "pendingManualReserveTransfers": sum(
                    1
                    for record in member_records
                    if record.get("memberBenefitClaimStatus") == "pending_manual_reserve_transfer"
                ),
                "remainingCredits": sum(int(record.get("remainingCredits") or 0) for record in credit_records),
            },
            "operatorBoundaries": {
                "noPrivateKeys": True,
                "noSeedPhrases": True,
                "noExchangeApiSecrets": True,
                "noWithdrawalPermission": True,
                "noCustody": True,
                "readOnlyWalletVerification": True,
                "manualReserveTransferOnly": True,
                "recordsManualTransfersOnly": True,
                "recordsServiceRequestsOnly": True,
                "recordsCreditUsageOnly": True,
                "supportReviewContinuityChainLocalOnly": True,
                "supportReviewContinuityChainSigned": False,
                "supportReviewContinuityChainExternallyAnchored": False,
                "supportReviewContinuityChainImmutable": False,
            },
        }
        return summary

    def operator_digest(self) -> dict[str, Any]:
        digest_path = self.store.data_dir / OPERATOR_DIGEST_FILE
        base_payload: dict[str, Any] = {
            "ok": True,
            "service": "gca-member-backend",
            "generatedAt": iso_now(),
            "available": False,
            "status": "missing",
            "packetVersion": OPERATOR_DIGEST_VERSION,
            "digestOk": False,
            "digestFile": OPERATOR_DIGEST_FILE,
            "writesProductionData": False,
            "walletCalls": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTokenTransfer": False,
            "sourceFileStatus": {},
            "dailyOps": {
                "available": False,
                "ok": False,
                "generatedAt": "",
                "includeMemberOps": False,
                "includeHoldingReport": False,
                "steps": [],
                "baseScanPreflight": {
                    "available": False,
                    "readyForBaseScanResubmission": None,
                    "status": "missing",
                    "publicEmailSwitchStatus": "",
                    "filesStillUsingOldEmail": 0,
                    "oldEmailFilePaths": [],
                    "missingTargetEmailFilePaths": [],
                    "snapshotAlignmentStatus": "",
                    "snapshotAlignmentStaleMarkers": 0,
                    "snapshotAlignmentMissingCurrentDate": 0,
                    "missingOrBlockedRequirements": [],
                },
            },
            "memberOps": {
                "available": False,
                "ok": False,
                "recordCount": 0,
                "supportQueue": {},
                "report": {},
                "holdingPeriod": {},
            },
            "supportQueue": {
                "available": False,
                "ok": False,
                "rows": 0,
                "replyReadyRows": 0,
                "statusCounts": {},
            },
            "holdingPeriod": {
                "available": False,
                "ok": False,
                "counts": {},
                "laneCounts": {},
            },
            "nextActions": [
                "Run `.venv/bin/python tools/run_gca_daily_ops.py --build-digest --summary-output .gca_access_data/gca_daily_ops_summary.json --digest-output .gca_access_data/gca_operator_digest.md --digest-json-output .gca_access_data/gca_operator_digest.json` to create the local operator digest."
            ],
            "outputs": {
                "markdownFile": "gca_operator_digest.md",
                "jsonFile": OPERATOR_DIGEST_FILE,
            },
            "boundaries": {
                "localhostOnly": True,
                "localOperatorDigestOnly": True,
                "writesProductionData": False,
                "adminTokenPrinted": False,
                "userEmailsPrinted": False,
                "userRecordsPrinted": False,
                "walletCalls": False,
                "requiresSignature": False,
                "requiresTransaction": False,
                "automaticTokenTransfer": False,
                "memberBenefitTransferAutomatic": False,
            },
        }
        if not digest_path.exists():
            return base_payload
        try:
            raw_payload = json.loads(digest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            base_payload.update({
                "available": False,
                "status": "invalid_json",
                "error": safe_operator_text(exc, 240),
            })
            return base_payload
        if not isinstance(raw_payload, dict):
            base_payload.update({
                "available": False,
                "status": "invalid_shape",
                "error": "operator digest file must contain a JSON object",
            })
            return base_payload

        daily = raw_payload.get("dailyOps") if isinstance(raw_payload.get("dailyOps"), dict) else {}
        member = raw_payload.get("memberOps") if isinstance(raw_payload.get("memberOps"), dict) else {}
        support = raw_payload.get("supportQueue") if isinstance(raw_payload.get("supportQueue"), dict) else {}
        holding = raw_payload.get("holdingPeriod") if isinstance(raw_payload.get("holdingPeriod"), dict) else {}
        source_files = raw_payload.get("sourceFiles") if isinstance(raw_payload.get("sourceFiles"), dict) else {}
        outputs = raw_payload.get("outputs") if isinstance(raw_payload.get("outputs"), dict) else {}
        support_status_counts = support.get("statusCounts") if isinstance(support.get("statusCounts"), dict) else {}
        holding_counts = holding.get("counts") if isinstance(holding.get("counts"), dict) else {}
        holding_lane_counts = holding.get("laneCounts") if isinstance(holding.get("laneCounts"), dict) else {}
        base_scan = daily.get("baseScanPreflight") if isinstance(daily.get("baseScanPreflight"), dict) else {}

        source_file_status = {}
        for key, value in source_files.items():
            if not isinstance(value, dict):
                continue
            source_file_status[safe_operator_text(key, 80)] = {
                "fileName": Path(str(value.get("path") or "")).name,
                "exists": safe_operator_bool(value.get("exists")),
                "ok": safe_operator_bool(value.get("ok")),
                "generatedAt": safe_operator_text(value.get("generatedAt"), 80),
                "packetVersion": safe_operator_text(value.get("packetVersion"), 80),
            }

        steps = []
        for step in daily.get("steps") or []:
            if isinstance(step, dict):
                steps.append({
                    "id": safe_operator_text(step.get("id"), 80),
                    "ok": safe_operator_bool(step.get("ok")),
                    "returnCode": step.get("returnCode", ""),
                })

        safe_payload = dict(base_payload)
        safe_payload.update({
            "available": True,
            "status": "loaded",
            "packetVersion": safe_operator_text(raw_payload.get("packetVersion") or OPERATOR_DIGEST_VERSION, 80),
            "digestOk": safe_operator_bool(raw_payload.get("ok")),
            "digestGeneratedAt": safe_operator_text(raw_payload.get("generatedAt"), 80),
            "sourceFileStatus": source_file_status,
            "dailyOps": {
                "available": safe_operator_bool(daily.get("available")),
                "ok": safe_operator_bool(daily.get("ok")),
                "generatedAt": safe_operator_text(daily.get("generatedAt"), 80),
                "includeMemberOps": safe_operator_bool(daily.get("includeMemberOps")),
                "includeHoldingReport": safe_operator_bool(daily.get("includeHoldingReport")),
                "steps": steps,
                "baseScanPreflight": {
                    "available": safe_operator_bool(base_scan.get("available")),
                    "readyForBaseScanResubmission": (
                        True if base_scan.get("readyForBaseScanResubmission") is True
                        else False if base_scan.get("readyForBaseScanResubmission") is False
                        else None
                    ),
                    "status": safe_operator_text(base_scan.get("status"), 120),
                    "publicEmailSwitchStatus": safe_operator_text(base_scan.get("publicEmailSwitchStatus"), 120),
                    "filesStillUsingOldEmail": safe_operator_int(base_scan.get("filesStillUsingOldEmail")),
                    "oldEmailFilePaths": [
                        safe_operator_text(item, 160)
                        for item in base_scan.get("oldEmailFilePaths", [])
                        if str(item or "").strip()
                    ][:20],
                    "missingTargetEmailFilePaths": [
                        safe_operator_text(item, 160)
                        for item in base_scan.get("missingTargetEmailFilePaths", [])
                        if str(item or "").strip()
                    ][:20],
                    "snapshotAlignmentStatus": safe_operator_text(base_scan.get("snapshotAlignmentStatus"), 120),
                    "snapshotAlignmentStaleMarkers": safe_operator_int(base_scan.get("snapshotAlignmentStaleMarkers")),
                    "snapshotAlignmentMissingCurrentDate": safe_operator_int(base_scan.get("snapshotAlignmentMissingCurrentDate")),
                    "missingOrBlockedRequirements": [
                        safe_operator_text(item, 120)
                        for item in base_scan.get("missingOrBlockedRequirements", [])
                        if str(item or "").strip()
                    ][:20],
                },
            },
            "memberOps": {
                "available": safe_operator_bool(member.get("available")),
                "ok": safe_operator_bool(member.get("ok")),
                "generatedAt": safe_operator_text(member.get("generatedAt"), 80),
                "recordCount": safe_operator_int(member.get("recordCount")),
                "datasetCount": safe_operator_int(member.get("datasetCount")),
                "supportQueue": safe_operator_mapping(member.get("supportQueue"), ("rows", "replyReadyRows", "statusCounts")),
                "report": safe_operator_mapping(
                    member.get("report"),
                    (
                        "accounts",
                        "walletVerifications",
                        "holderBonusEligibleWallets",
                        "gcaMemberEligibleWallets",
                        "creditLedgerRecords",
                        "activeGcaMembers",
                        "queuedGcaMembers",
                        "pendingManualReserveTransfers",
                        "holdingPeriodReviewsNeeded",
                    ),
                ),
                "holdingPeriod": safe_operator_mapping(
                    member.get("holdingPeriod"),
                    (
                        "candidateWallets",
                        "snapshotRecordsAvailable",
                        "observedEligibleFor30Days",
                        "walletsChecked",
                        "snapshotsAdded",
                    ),
                ),
            },
            "supportQueue": {
                "available": safe_operator_bool(support.get("available")),
                "ok": safe_operator_bool(support.get("ok")),
                "generatedAt": safe_operator_text(support.get("generatedAt"), 80),
                "rows": safe_operator_int(support.get("rows")),
                "replyReadyRows": safe_operator_int(support.get("replyReadyRows")),
                "statusCounts": safe_operator_mapping(support_status_counts, tuple(str(key) for key in support_status_counts.keys())),
            },
            "holdingPeriod": {
                "available": safe_operator_bool(holding.get("available")),
                "ok": safe_operator_bool(holding.get("ok")),
                "generatedAt": safe_operator_text(holding.get("generatedAt"), 80),
                "counts": safe_operator_mapping(holding_counts, tuple(str(key) for key in holding_counts.keys())),
                "laneCounts": safe_operator_mapping(holding_lane_counts, tuple(str(key) for key in holding_lane_counts.keys())),
            },
            "nextActions": [
                safe_operator_text(action, 500)
                for action in raw_payload.get("nextActions", [])
                if str(action or "").strip()
            ][:12],
            "outputs": {
                "markdownFile": Path(str(outputs.get("markdown") or "gca_operator_digest.md")).name,
                "jsonFile": Path(str(outputs.get("json") or OPERATOR_DIGEST_FILE)).name,
            },
        })
        if not safe_payload["nextActions"]:
            safe_payload["nextActions"] = ["No immediate operator action from the available summaries."]
        return safe_payload

    def operator_action_plan(self, limit: int = 10) -> dict[str, Any]:
        summary = self.operator_summary(limit=limit)
        digest = self.operator_digest()
        totals = summary.get("totals", {})
        items: list[dict[str, Any]] = []

        def add_item(item_id: str, priority: str, title: str, detail: str, source: str, command: str = "") -> None:
            items.append({
                "id": item_id,
                "priority": priority,
                "title": safe_operator_text(title, 160),
                "detail": safe_operator_text(detail, 500),
                "source": safe_operator_text(source, 120),
                "command": safe_operator_text(command, 500),
                "manualReviewRequired": True,
                "automaticExecution": False,
            })

        if not digest.get("available"):
            add_item(
                "build-operator-digest",
                "high",
                "Build the daily operator digest",
                "No local operator digest is available yet. Run the daily public health check with --build-digest, then reload this console.",
                "operator-digest",
                ".venv/bin/python tools/run_gca_daily_ops.py --build-digest --summary-output .gca_access_data/gca_daily_ops_summary.json --digest-output .gca_access_data/gca_operator_digest.md --digest-json-output .gca_access_data/gca_operator_digest.json",
            )
        elif not digest.get("digestOk"):
            add_item(
                "review-operator-digest",
                "high",
                "Review operator digest attention state",
                "The latest digest is present but not marked ok. Check daily public health and member ops summaries before platform or support follow-up.",
                "operator-digest",
            )

        daily = digest.get("dailyOps") if isinstance(digest.get("dailyOps"), dict) else {}
        if daily.get("available") and not daily.get("ok"):
            failed_steps = [
                str(step.get("id") or "")
                for step in daily.get("steps", [])
                if isinstance(step, dict) and step.get("ok") is not True
            ]
            add_item(
                "fix-public-health",
                "high",
                "Fix public health check failure",
                f"Daily public health has failing step(s): {', '.join(failed_steps) or 'unknown'}. Fix this before sending users or reviewers to public links.",
                "daily-ops",
            )

        base_scan = daily.get("baseScanPreflight") if isinstance(daily.get("baseScanPreflight"), dict) else {}
        if base_scan.get("available") and base_scan.get("readyForBaseScanResubmission") is False:
            blockers = [
                safe_operator_text(item, 120)
                for item in base_scan.get("missingOrBlockedRequirements", [])
                if str(item or "").strip()
            ]
            blocker_ids = {item for item in blockers if item}
            blocker_text = ", ".join(blockers[:5]) if blockers else "see BaseScan preflight summary"
            old_email_files = safe_operator_int(base_scan.get("filesStillUsingOldEmail"))
            old_email_paths = [
                safe_operator_text(item, 160)
                for item in base_scan.get("oldEmailFilePaths", [])
                if str(item or "").strip()
            ][:5]
            missing_target_paths = [
                safe_operator_text(item, 160)
                for item in base_scan.get("missingTargetEmailFilePaths", [])
                if str(item or "").strip()
            ][:5]
            stale_snapshot_files = safe_operator_int(base_scan.get("snapshotAlignmentStaleMarkers"))
            missing_snapshot_files = safe_operator_int(base_scan.get("snapshotAlignmentMissingCurrentDate"))
            suffix_parts = []
            if old_email_files:
                path_suffix = f" Example file(s): {', '.join(old_email_paths)}." if old_email_paths else ""
                suffix_parts.append(f"Public switch still has {old_email_files} old-email file(s).{path_suffix}")
            if missing_target_paths:
                suffix_parts.append(f"Critical file(s) missing target domain email: {', '.join(missing_target_paths)}.")
            if stale_snapshot_files or missing_snapshot_files:
                suffix_parts.append(
                    "DNS snapshot alignment has "
                    f"{stale_snapshot_files} stale marker file(s) and "
                    f"{missing_snapshot_files} missing current-date file(s)."
                )
            suffix = f" {' '.join(suffix_parts)}" if suffix_parts else ""
            add_item(
                "complete-basescan-preflight",
                "medium",
                "Complete BaseScan preflight blockers",
                f"BaseScan token-profile resubmission is still blocked: {blocker_text}.{suffix}",
                "basescan-preflight",
                ".venv/bin/python tools/check_basescan_resubmission_readiness.py --skip-url-checks --json",
            )
            if blocker_ids.intersection({"official-domain-email", "domain-email-evidence-packet", "next-submission-ready-flag"}):
                add_item(
                    "activate-domain-email-evidence",
                    "medium",
                    "Activate domain email evidence",
                    "Create and test the project-domain support mailbox, complete MX/SPF/DKIM/DMARC readiness, and archive provider, inbound, outbound, and support-page evidence before the next BaseScan resubmission.",
                    "domain-email",
                    ".venv/bin/python tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector PROVIDER_SELECTOR --json",
                )
                add_item(
                    "build-domain-email-evidence-packet",
                    "medium",
                    "Build domain email evidence packet",
                    "Run the evidence-directory initializer, then after mailbox DNS and send/receive tests pass, save the five evidence files under launch/domain_email_evidence and build the local packet before any BaseScan resubmission.",
                    "domain-email-evidence-packet",
                    DOMAIN_EMAIL_EVIDENCE_PACKET_COMMAND,
                )
            if (
                old_email_files
                or blocker_ids.intersection({"domain-email-public-switch-check", "domain-email-public-switch-old-email"})
            ):
                add_item(
                    "complete-public-email-switch",
                    "medium",
                    "Complete public email switch",
                    "After the domain mailbox evidence is ready, switch critical public, support, and BaseScan files to the project-domain mailbox and rerun the public switch checker.",
                    "domain-email-public-switch",
                    ".venv/bin/python tools/check_domain_email_public_switch.py --json --require-switched",
                )
            if (
                stale_snapshot_files
                or missing_snapshot_files
                or blocker_ids.intersection({
                    "domain-email-snapshot-alignment",
                    "stale-dns-snapshot-markers",
                    "missing-current-snapshot-date",
                })
            ):
                add_item(
                    "fix-domain-email-snapshot-alignment",
                    "medium",
                    "Fix domain email snapshot alignment",
                    "Update public, launch, and reply artifacts so every domain-email DNS snapshot reference matches the canonical site/domain-email.json snapshot before the next platform reply.",
                    "domain-email-snapshot-alignment",
                    ".venv/bin/python tools/check_domain_email_snapshot_alignment.py --json --require-aligned",
                )

        reply_ready = safe_operator_int(
            (digest.get("supportQueue") or {}).get("replyReadyRows")
            or (digest.get("memberOps") or {}).get("supportQueue", {}).get("replyReadyRows")
        )
        if reply_ready:
            add_item(
                "review-support-replies",
                "high",
                "Review reply-ready support queue",
                f"{reply_ready} support queue row(s) are reply-ready. Review the prepared reply manually before sending anything to a user.",
                "support-queue",
            )

        pending_transfers = safe_operator_int(totals.get("pendingManualReserveTransfers"))
        if pending_transfers:
            add_item(
                "review-pending-reserve-transfers",
                "high",
                "Review pending member benefit transfers",
                f"{pending_transfers} active GCA Member record(s) are waiting for manual reserve-transfer review. Verify 30-day evidence and transfer readiness before any wallet action.",
                "member-ledger",
            )

        queued_members = safe_operator_int(totals.get("queuedMembers"))
        if queued_members:
            add_item(
                "review-queued-members",
                "medium",
                "Review queued GCA Member evidence",
                f"{queued_members} GCA Member record(s) are queued, usually because 30-day holding evidence is missing or incomplete.",
                "member-ledger",
            )

        local_support_reviews = safe_operator_int(totals.get("supportReviews"))
        if local_support_reviews:
            add_item(
                "inspect-local-support-reviews",
                "medium",
                "Inspect local support review records",
                f"{local_support_reviews} local support review record(s) exist. Use the latest review table to confirm next steps and avoid duplicate replies.",
                "local-ledgers",
            )

        if not safe_operator_int(totals.get("emailRegistrations")):
            add_item(
                "sync-email-registrations",
                "medium",
                "Sync Cloudflare email registrations",
                "No local email registration records are loaded. Sync token-protected Worker records before exporting contact CSVs or campaign lists.",
                "email-registrations",
                ".venv/bin/python tools/run_gca_registration_ops.py --limit 100 --data-dir .gca_access_data",
            )

        holding = digest.get("holdingPeriod") if isinstance(digest.get("holdingPeriod"), dict) else {}
        holding_counts = holding.get("counts") if isinstance(holding.get("counts"), dict) else {}
        ready_wallets = safe_operator_int(holding_counts.get("observedEligibleFor30Days"))
        if ready_wallets:
            add_item(
                "review-holding-ready-wallets",
                "medium",
                "Review 30-day holding-ready wallets",
                f"{ready_wallets} wallet(s) have observed 30-day member-threshold evidence. Confirm support approval before any benefit decision.",
                "holding-period",
            )

        if not items:
            add_item(
                "no-immediate-action",
                "low",
                "No immediate operator action",
                "Available summaries do not show urgent public health, support, holding, or transfer work.",
                "operator-summary",
            )

        priority_order = {"high": 0, "medium": 1, "low": 2}
        items = sorted(items, key=lambda item: (priority_order.get(str(item.get("priority")), 9), str(item.get("id"))))

        support_preview = []
        support_latest = summary.get("dataLedgers", {}).get("support_reviews", {}).get("latest", [])
        for record in support_latest[:limit]:
            if not isinstance(record, dict):
                continue
            support_preview.append({
                "lane": safe_operator_text(record.get("lane"), 120),
                "status": safe_operator_text(record.get("status"), 120),
                "walletAddress": safe_operator_text(record.get("walletAddress"), 80),
                "creditLedgerId": safe_operator_text(record.get("creditLedgerId"), 120),
                "memberLedgerId": safe_operator_text(record.get("memberLedgerId"), 120),
                "memberBenefitTransferTx": safe_operator_text(record.get("memberBenefitTransferTx"), 120),
                "nextStep": safe_operator_text(record.get("nextStep"), 500),
                "updatedAt": safe_operator_text(record.get("updatedAt"), 120),
            })

        return {
            "ok": True,
            "service": "gca-member-backend",
            "packetVersion": OPERATOR_ACTION_PLAN_VERSION,
            "generatedAt": iso_now(),
            "itemCount": len(items),
            "items": items,
            "supportReviewPreview": support_preview,
            "sourceStatus": {
                "operatorSummaryAvailable": True,
                "operatorDigestAvailable": bool(digest.get("available")),
                "operatorDigestOk": bool(digest.get("digestOk")),
                "digestGeneratedAt": safe_operator_text(digest.get("digestGeneratedAt"), 80),
            },
            "totals": {
                "emailRegistrations": safe_operator_int(totals.get("emailRegistrations")),
                "supportReviews": safe_operator_int(totals.get("supportReviews")),
                "queuedMembers": queued_members,
                "pendingManualReserveTransfers": pending_transfers,
                "memberBenefitTransfers": safe_operator_int(totals.get("memberBenefitTransfers")),
            },
            "boundaries": {
                "localhostOnly": True,
                "readOnlyOperatorPlan": True,
                "writesProductionData": False,
                "adminTokenPrinted": False,
                "userEmailsPrinted": False,
                "userRecordsPrinted": False,
                "walletCalls": False,
                "requiresSignature": False,
                "requiresTransaction": False,
                "automaticTokenTransfer": False,
                "automaticUserReply": False,
                "memberBenefitTransferAutomatic": False,
            },
        }

    def review_package(self, limit: int = 100, redacted: bool = False) -> dict[str, Any]:
        summary = self.operator_summary(limit=limit)
        support_review_audit = summary.get("supportReviewAudit", {})
        if redacted and support_review_audit.get("ok") is not True:
            raise BackendError(
                "public redacted review package export requires a verified support review chain",
                HTTPStatus.CONFLICT,
            )
        ledgers = summary.get("dataLedgers", {})
        package = {
            "ok": True,
            "packageType": "gca-local-review-package",
            "generatedAt": summary["generatedAt"],
            "intendedUse": "Operator export for GCA support review, platform follow-up, and reviewer evidence handoff.",
            "chainId": CHAIN_ID,
            "contractAddress": CONTRACT_ADDRESS,
            "memberPacketVersion": PACKET_VERSION,
            "contactEmail": CONTACT_EMAIL,
            "publicSelfServiceClaim": False,
            "automaticTokenTransfer": False,
            "localJsonlDataOnly": True,
            "redactedForExternalSharing": False,
            "packageDigestAlgorithm": "",
            "packageDigestSha256": "",
            "recordManifest": {
                "limit": limit,
                "ledgerNames": list(LEDGER_NAMES),
                "ledgerCounts": {
                    name: int(ledgers.get(name, {}).get("count") or 0)
                    for name in LEDGER_NAMES
                },
                "latestRecordCounts": {
                    name: len(ledgers.get(name, {}).get("latest") or [])
                    for name in LEDGER_NAMES
                },
                "supportReviewAudit": support_review_audit,
            },
            "redactionPolicy": {
                "mode": "full-local",
                "availableMode": "redact=public",
                "redactedFields": sorted(REDACTED_EXTERNAL_KEYS),
                "keepsPublicChainEvidence": True,
            },
            "fullLocalExportWarning": {
                "mode": "full-local",
                "internalOnly": True,
                "externalSharingAllowed": False,
                "operatorConfirmationRequired": True,
                "mayContainLocalFields": sorted(REDACTED_EXTERNAL_KEYS),
                "externalSharingAlternative": "GET /gca/review-package?redact=public",
                "warning": "Full-local review packages may include local user email, Telegram handle, reviewer notes, support notes, and evidence notes. Use redacted-public mode for platform or reviewer handoff.",
            },
            "handoffInstructions": {
                "externalSharingMode": "redacted-public",
                "fullLocalMode": "internal-only",
                "offlineRedactedExportCommand": ".venv/bin/python tools/export_gca_review_package.py --redact public --output gca-public-redacted-review-package.json",
                "verifyCommand": ".venv/bin/python tools/verify_gca_review_package.py gca-public-redacted-review-package.json",
                "replyTemplatePage": "https://gcagochina.com/platform-replies.html",
                "replyTemplateJson": "https://gcagochina.com/platform-replies.json",
                "beforeExternalSharing": [
                    "export redacted-public package only",
                    "verify packageDigestSha256 before sending",
                    "confirm no user email, Telegram handle, reviewer note, support note, evidence note, private key, seed phrase, exchange API secret, withdrawal permission, or one-time code is present",
                ],
                "publicClaimBoundary": "support evidence only; not a third-party audit, security-vendor approval, listing approval, or liquidity-depth claim",
            },
            "localEndpoint": "/gca/review-package",
            "operatorSummary": summary,
            "exportBoundaries": {
                "localhostOnly": True,
                "noPrivateKeys": True,
                "noSeedPhrases": True,
                "noExchangeApiSecrets": True,
                "noWithdrawalPermission": True,
                "noCustody": True,
                "readOnlyWalletVerification": True,
                "readOnlyTransferReceiptVerification": True,
                "manualReserveTransferOnly": True,
            },
            "publicReferences": {
                "memberProgram": "https://gcagochina.com/member-program.json",
                "memberLedger": "https://gcagochina.com/member-ledger.json",
                "memberBenefitTransfer": "https://gcagochina.com/member-benefit-transfer.json",
                "accessApi": "https://gcagochina.com/access-api.json",
                "support": "https://gcagochina.com/support.json",
                "technicalReport": "https://gcagochina.com/technical-report.json",
                "reserveStatement": "https://gcagochina.com/reserve-statement.json",
            },
            "reviewChecklist": [
                "Confirm each wallet verification uses Base Mainnet chainId 8453 and the official GCA contract.",
                "Confirm holder credits remain utility credits only and are not cash, income, or trading permission.",
                "Confirm each service request has a serviceRequestId, serviceId, requestedCreditHold, and operator-review status before delivery.",
                "Confirm any credit usage record has a creditUsageId, serviceId, creditAmountUsed, and remainingCreditsAfter value.",
                "Confirm GCA Member records require at least 1,000,000 GCA and 30 consecutive holding days before benefit review.",
                "Confirm any 10,000 GCA member benefit transfer has a successful Base Mainnet GCA Transfer log to the verified member wallet.",
                "Confirm supportReviewAudit is verified before relying on local review history or sharing a redacted review package.",
                "Confirm no user secret, private key, seed phrase, exchange API secret, withdrawal permission, or custody request appears in notes.",
            ],
        }
        if redacted:
            package = redact_for_external_sharing(package)
            package["redactedForExternalSharing"] = True
            package["redactionPolicy"]["mode"] = "redacted-public"
            package["redactionPolicy"]["availableMode"] = "redact=public"
        return add_package_digest(package)


def build_handler(site_dir: Path, backend: GcaMemberBackend) -> type[SimpleHTTPRequestHandler]:
    class GcaMemberRequestHandler(SimpleHTTPRequestHandler):
        server_version = "GcaMemberBackend/1.0"

        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, directory=str(site_dir), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

        def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def read_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 256_000:
                raise BackendError("Request body is too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return read_json_request(self.rfile.read(length))

        def assert_local_api_client(self) -> None:
            client_host = self.client_address[0]
            if client_host not in LOCAL_CLIENTS:
                raise BackendError("GCA local operator API only accepts localhost clients", HTTPStatus.FORBIDDEN)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/gca/health":
                    self.send_json({
                        "ok": True,
                        "service": "gca-member-backend",
                        "chainId": CHAIN_ID,
                        "contractAddress": CONTRACT_ADDRESS,
                        "publicSelfServiceClaim": False,
                    })
                    return
                if parsed.path == "/gca/operator-summary":
                    self.assert_local_api_client()
                    self.send_json(backend.operator_summary())
                    return
                if parsed.path == "/gca/operator-digest":
                    self.assert_local_api_client()
                    self.send_json(backend.operator_digest())
                    return
                if parsed.path == "/gca/operator-action-plan":
                    self.assert_local_api_client()
                    limit_text = query.get("limit", ["10"])[0]
                    try:
                        limit = min(max(int(limit_text), 1), 50)
                    except ValueError as exc:
                        raise BackendError("limit must be an integer") from exc
                    self.send_json(backend.operator_action_plan(limit=limit))
                    return
                if parsed.path == "/gca/review-package":
                    self.assert_local_api_client()
                    limit_text = query.get("limit", ["100"])[0]
                    try:
                        limit = min(max(int(limit_text), 1), 200)
                    except ValueError as exc:
                        raise BackendError("limit must be an integer") from exc
                    redact_text = str(query.get("redact", query.get("redacted", [""]))[0]).strip().lower()
                    redacted = redact_text in {"1", "true", "yes", "public", "external"}
                    self.send_json(backend.review_package(limit=limit, redacted=redacted))
                    return
                ledger_map = {
                    "/gca/email-registrations": "email_registrations",
                    "/gca/pre-registrations": "pre_registrations",
                    "/gca/wallet-verifications": "wallet_verifications",
                    "/gca/credit-ledger": "credit_ledger",
                    "/gca/service-requests": "service_requests",
                    "/gca/credit-usage": "credit_usage",
                    "/gca/member-ledger": "member_ledger",
                    "/gca/member-benefit-transfers": "member_benefit_transfers",
                    "/gca/member-review": "support_reviews",
                }
                if parsed.path in ledger_map:
                    self.assert_local_api_client()
                    records = backend.query(ledger_map[parsed.path], query)
                    self.send_json({"ok": True, "count": len(records), "records": records})
                    return
                super().do_GET()
            except BackendError as exc:
                self.send_json({"ok": False, "error": str(exc)}, exc.status)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                if parsed.path.startswith("/gca/"):
                    self.assert_local_api_client()
                payload = self.read_body()
                if parsed.path == "/gca/email-registrations":
                    self.send_json(backend.submit_email_registration(payload), HTTPStatus.CREATED)
                    return
                if parsed.path == "/gca/pre-registrations":
                    self.send_json(backend.submit_pre_registration(payload), HTTPStatus.CREATED)
                    return
                if parsed.path == "/gca/wallet-verifications":
                    self.send_json({"ok": True, "walletVerification": backend.wallet_verification_from_request(payload)}, HTTPStatus.CREATED)
                    return
                if parsed.path == "/gca/service-requests":
                    self.send_json(backend.record_service_request(payload), HTTPStatus.CREATED)
                    return
                if parsed.path == "/gca/credit-usage":
                    self.send_json(backend.record_credit_usage(payload), HTTPStatus.CREATED)
                    return
                if parsed.path == "/gca/member-benefit-transfers":
                    result = backend.record_member_benefit_transfer(payload)
                    self.send_json({"ok": True, **result}, HTTPStatus.CREATED)
                    return
                if parsed.path == "/gca/member-review":
                    self.send_json(backend.record_support_review_update(payload), HTTPStatus.CREATED)
                    return
                self.send_json({"ok": False, "error": "Unsupported API path"}, HTTPStatus.NOT_FOUND)
            except BackendError as exc:
                self.send_json({"ok": False, "error": str(exc)}, exc.status)

    return GcaMemberRequestHandler


def make_server(host: str, port: int, site_dir: Path, data_dir: Path, rpc_url: str) -> ThreadingHTTPServer:
    store = JsonlLedgerStore(data_dir)
    backend = GcaMemberBackend(store=store, balance_reader=BaseRpcBalanceReader(rpc_url=rpc_url))
    return ThreadingHTTPServer((host, port), build_handler(site_dir, backend))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local-only GCA member backend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--site-dir", type=Path, default=Path("site"))
    parser.add_argument("--data-dir", type=Path, default=Path(".gca_access_data"))
    parser.add_argument("--rpc-url", default=BASE_RPC_URL)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    server = make_server(args.host, args.port, args.site_dir.resolve(), args.data_dir.resolve(), args.rpc_url)
    print(f"GCA member backend running at http://{args.host}:{args.port}/members.html")
    print(f"Local ledgers: {args.data_dir.resolve()}")
    print("Stop with Ctrl-C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping GCA member backend.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
