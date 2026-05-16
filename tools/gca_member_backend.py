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
BALANCE_OF_SELECTOR = "0x70a08231"
TOKEN_DECIMALS = 18
TOKEN_UNIT = 10**TOKEN_DECIMALS
HOLDER_THRESHOLD_UNITS = 10_000 * TOKEN_UNIT
MEMBER_THRESHOLD_UNITS = 1_000_000 * TOKEN_UNIT
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


@dataclass
class BaseRpcBalanceReader:
    rpc_url: str = BASE_RPC_URL
    timeout: float = 20.0

    def get_balance_units(self, wallet: str) -> int:
        request_payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "eth_call",
            "params": [{"to": CONTRACT_ADDRESS, "data": balance_of_calldata(wallet)}, "latest"],
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
            raise BackendError(f"Base RPC balance read failed: {exc}", HTTPStatus.BAD_GATEWAY) from exc
        if "error" in payload:
            raise BackendError(f"Base RPC error: {payload['error']}", HTTPStatus.BAD_GATEWAY)
        result = str(payload.get("result") or "0x0")
        return int(result, 16)


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

    def query(self, ledger: str, query: dict[str, list[str]]) -> list[dict[str, Any]]:
        filters: dict[str, str] = {}
        for key in ("walletAddress", "email", "registrationId", "creditLedgerId", "memberLedgerId"):
            value = query.get(key, [""])[0]
            if value:
                filters[key] = value.lower() if key == "walletAddress" else value
        return self.store.find(ledger, **filters)


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
                ledger_map = {
                    "/gca/pre-registrations": "pre_registrations",
                    "/gca/wallet-verifications": "wallet_verifications",
                    "/gca/credit-ledger": "credit_ledger",
                    "/gca/member-ledger": "member_ledger",
                    "/gca/member-review": "support_reviews",
                }
                if parsed.path in ledger_map:
                    records = backend.query(ledger_map[parsed.path], query)
                    self.send_json({"ok": True, "count": len(records), "records": records})
                    return
                super().do_GET()
            except BackendError as exc:
                self.send_json({"ok": False, "error": str(exc)}, exc.status)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                payload = self.read_body()
                if parsed.path == "/gca/pre-registrations":
                    self.send_json(backend.submit_pre_registration(payload), HTTPStatus.CREATED)
                    return
                if parsed.path == "/gca/wallet-verifications":
                    self.send_json({"ok": True, "walletVerification": backend.wallet_verification_from_request(payload)}, HTTPStatus.CREATED)
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
