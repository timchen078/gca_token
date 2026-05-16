#!/usr/bin/env python3
"""Local-only GCA member access backend.

This server is intentionally small and conservative:
- serves the static site from ``site/``
- accepts local member pre-registration packets on localhost
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
PACKET_VERSION = "gca_member_preregistration_v2"
CONTACT_EMAIL = "GCAgochina@outlook.com"
ALLOWED_PROGRAM_INTENTS = {"holder_bonus", "gca_member", "general_waitlist"}
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
TX_HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
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
    "pre_registrations",
    "wallet_verifications",
    "credit_ledger",
    "member_ledger",
    "member_benefit_transfers",
    "support_reviews",
)
LOCAL_CLIENTS = {"127.0.0.1", "::1", "localhost"}
REDACTED_EXTERNAL_VALUE = "[redacted-for-external-sharing]"
REDACTED_EXTERNAL_KEYS = {"email", "telegram", "reviewerNote", "supportNote", "evidenceNote"}


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
    email = str(packet.get("email") or user.get("email") or "").strip().lower()
    telegram = str(packet.get("telegram") or user.get("telegram") or "").strip()
    wallet = normalize_wallet(str(packet.get("walletAddress") or user.get("walletAddress") or ""))
    if not email or "@" not in email:
        raise BackendError("email is required")
    return {"email": email, "telegram": telegram, "walletAddress": wallet}


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

    def path(self, name: str) -> Path:
        return self.data_dir / f"{name}.jsonl"

    def append(self, name: str, record: dict[str, Any]) -> dict[str, Any]:
        path = self.path(name)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        return record

    def read_all(self, name: str) -> list[dict[str, Any]]:
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

    def submit_pre_registration(self, packet: dict[str, Any]) -> dict[str, Any]:
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
            "creditType": "Web3 Radar utility credits",
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

    def query(self, ledger: str, query: dict[str, list[str]]) -> list[dict[str, Any]]:
        filters: dict[str, str] = {}
        for key in (
            "walletAddress",
            "email",
            "registrationId",
            "creditLedgerId",
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
        member_records = latest_records_by(ledgers["member_ledger"], "memberLedgerId")
        transfer_records = latest_records_by(ledgers["member_benefit_transfers"], "transferRecordId")
        review_records = ledgers["support_reviews"]
        summary = {
            "ok": True,
            "service": "gca-member-backend",
            "generatedAt": iso_now(),
            "chainId": CHAIN_ID,
            "contractAddress": CONTRACT_ADDRESS,
            "publicSelfServiceClaim": False,
            "automaticTokenTransfer": False,
            "localJsonlDataOnly": True,
            "dataLedgers": {
                name: {
                    "count": len(records),
                    "latest": records[-limit:][::-1],
                }
                for name, records in ledgers.items()
            },
            "totals": {
                "preRegistrations": len(ledgers["pre_registrations"]),
                "walletVerifications": len(ledgers["wallet_verifications"]),
                "creditLedgerRecords": len(credit_records),
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
            },
        }
        return summary

    def review_package(self, limit: int = 100, redacted: bool = False) -> dict[str, Any]:
        summary = self.operator_summary(limit=limit)
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
            "redactionPolicy": {
                "mode": "full-local",
                "availableMode": "redact=public",
                "redactedFields": sorted(REDACTED_EXTERNAL_KEYS),
                "keepsPublicChainEvidence": True,
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
                "Confirm GCA Member records require at least 1,000,000 GCA and 30 consecutive holding days before benefit review.",
                "Confirm any 10,000 GCA member benefit transfer has a successful Base Mainnet GCA Transfer log to the verified member wallet.",
                "Confirm no user secret, private key, seed phrase, exchange API secret, withdrawal permission, or custody request appears in notes.",
            ],
        }
        if redacted:
            package = redact_for_external_sharing(package)
            package["redactedForExternalSharing"] = True
            package["redactionPolicy"]["mode"] = "redacted-public"
            package["redactionPolicy"]["availableMode"] = "redact=public"
        return package


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
                    "/gca/pre-registrations": "pre_registrations",
                    "/gca/wallet-verifications": "wallet_verifications",
                    "/gca/credit-ledger": "credit_ledger",
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
                if parsed.path == "/gca/pre-registrations":
                    self.send_json(backend.submit_pre_registration(payload), HTTPStatus.CREATED)
                    return
                if parsed.path == "/gca/wallet-verifications":
                    self.send_json({"ok": True, "walletVerification": backend.wallet_verification_from_request(payload)}, HTTPStatus.CREATED)
                    return
                if parsed.path == "/gca/member-benefit-transfers":
                    result = backend.record_member_benefit_transfer(payload)
                    self.send_json({"ok": True, **result}, HTTPStatus.CREATED)
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
