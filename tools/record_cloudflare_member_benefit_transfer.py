#!/usr/bin/env python3
"""Record verified evidence for an already-completed GCA member benefit transfer.

This operator command never connects a wallet, signs, sends a transaction, or
transfers GCA. The production Worker verifies the supplied public transaction
receipt against the official reserve wallet, member wallet, exact 10,000 GCA
amount, and a Base safe-block snapshot before writing D1 evidence.
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


PACKET_VERSION = "gca_member_benefit_transfer_v1"
MEMBER_LEDGER_ID_RE = re.compile(r"^gca_member_[a-f0-9]{20}$")
TX_HASH_RE = re.compile(r"^0x[a-f0-9]{64}$")
OPERATOR_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
REASON_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


class MemberBenefitTransferError(RuntimeError):
    """Raised for expected operator-facing transfer evidence failures."""


def build_transfer_payload(
    *,
    member_ledger_id: str,
    transaction_hash: str,
    reviewer_id: str,
    reason_code: str = "manual_reserve_transfer_verified",
    operator_note: str = "",
    manual_transfer_completed: bool = False,
    public_transaction_evidence: bool = False,
) -> dict[str, Any]:
    clean_ledger_id = member_ledger_id.strip().lower()
    clean_tx_hash = transaction_hash.strip().lower()
    clean_reviewer = reviewer_id.strip().lower()
    clean_reason = reason_code.strip().lower()
    if not MEMBER_LEDGER_ID_RE.fullmatch(clean_ledger_id):
        raise MemberBenefitTransferError(
            "member ledger id must match gca_member_ plus 20 lowercase hex characters"
        )
    if not TX_HASH_RE.fullmatch(clean_tx_hash):
        raise MemberBenefitTransferError("transaction hash must be 0x plus 64 hexadecimal characters")
    if not OPERATOR_ID_RE.fullmatch(clean_reviewer):
        raise MemberBenefitTransferError("reviewer id must be a short lowercase identifier")
    if not REASON_CODE_RE.fullmatch(clean_reason):
        raise MemberBenefitTransferError("reason code must be a short lowercase identifier")
    if not manual_transfer_completed:
        raise MemberBenefitTransferError("--confirm-manual-transfer-completed is required")
    if not public_transaction_evidence:
        raise MemberBenefitTransferError("--confirm-public-transaction-evidence is required")
    return {
        "packetVersion": PACKET_VERSION,
        "memberLedgerId": clean_ledger_id,
        "transactionHash": clean_tx_hash,
        "reviewerId": clean_reviewer,
        "reasonCode": clean_reason,
        "operatorNote": operator_note.strip()[:500],
        "source": "gca-member-benefit-transfer-operator-cli",
        "acknowledgements": {
            "manualReserveTransferCompleted": True,
            "transactionEvidencePublic": True,
            "noAutomaticTokenTransfer": True,
        },
    }


def submit_transfer_evidence(
    *,
    base_url: str,
    token: str,
    payload: dict[str, Any],
    timeout: float = 30,
    cafile: str = "",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    request = Request(
        f"{base_url.rstrip('/')}/gca/member-benefit-transfers",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "user-agent": "GCA-Operator-Member-Benefit-Evidence/1.0",
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
        raise MemberBenefitTransferError(
            f"member benefit transfer API rejected the evidence: {detail}"
        ) from exc
    except URLError as exc:
        raise MemberBenefitTransferError(
            f"member benefit transfer API request failed: {exc.reason}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise MemberBenefitTransferError(
            "member benefit transfer API returned invalid JSON"
        ) from exc
    if result.get("ok") is not True:
        raise MemberBenefitTransferError(
            "member benefit transfer API did not return ok=true"
        )
    if not isinstance(result.get("memberBenefitTransfer"), dict):
        raise MemberBenefitTransferError(
            "member benefit transfer API response is missing the evidence record"
        )
    return result


def safe_result(payload: dict[str, Any]) -> dict[str, Any]:
    transfer = payload.get("memberBenefitTransfer", {})
    ledger = payload.get("memberLedger", {})
    boundaries = payload.get("boundaries", {})
    return {
        "ok": True,
        "alreadyRecorded": bool(payload.get("alreadyRecorded", False)),
        "transferRecordId": transfer.get("transferRecordId", ""),
        "memberLedgerId": transfer.get("memberLedgerId", ""),
        "transactionHash": transfer.get("transactionHash", ""),
        "amountGca": transfer.get("amountGca", ""),
        "verificationStatus": transfer.get("verificationStatus", ""),
        "safeSnapshotBlockNumber": transfer.get("safeSnapshotBlockNumber", 0),
        "memberBenefitClaimStatus": ledger.get("memberBenefitClaimStatus", ""),
        "automaticTokenTransfer": bool(boundaries.get("automaticTokenTransfer", False)),
        "writesWallet": bool(boundaries.get("writesWallet", False)),
        "authorizesAdditionalTransfer": bool(boundaries.get("authorizesAdditionalTransfer", False)),
        "adminTokenPrinted": False,
        "walletPrinted": False,
        "emailPrinted": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record read-only production evidence for an already-completed manual 10,000 GCA member benefit transfer.",
    )
    parser.add_argument("--member-ledger-id", required=True, help="Target gca_member_* ledger id.")
    parser.add_argument("--transaction-hash", required=True, help="Public Base Mainnet transaction hash.")
    parser.add_argument("--reviewer-id", default="gca-operator", help="Short operator identifier.")
    parser.add_argument(
        "--reason-code",
        default="manual_reserve_transfer_verified",
        help="Short lowercase evidence reason.",
    )
    parser.add_argument("--note", default="", help="Optional operator note, maximum 500 characters.")
    parser.add_argument(
        "--confirm-manual-transfer-completed",
        action="store_true",
        help="Confirm the operator already completed the transfer outside this tool.",
    )
    parser.add_argument(
        "--confirm-public-transaction-evidence",
        action="store_true",
        help="Confirm the transaction hash is intended as public evidence.",
    )
    parser.add_argument(
        "--confirm-production-write",
        action="store_true",
        help="Required because this command writes an evidence record to production D1.",
    )
    parser.add_argument("--base-url", default=DEFAULT_API_BASE, help=f"Worker API base URL. Default: {DEFAULT_API_BASE}")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE, help="Path to ignored local admin env file.")
    parser.add_argument("--timeout", type=float, default=30, help="HTTP timeout in seconds. Default: 30.")
    parser.add_argument("--cafile", default="", help=f"Optional CA bundle path. Default fallback: {DEFAULT_CA_FILE}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if not args.confirm_production_write:
            raise MemberBenefitTransferError("--confirm-production-write is required")
        payload = build_transfer_payload(
            member_ledger_id=args.member_ledger_id,
            transaction_hash=args.transaction_hash,
            reviewer_id=args.reviewer_id,
            reason_code=args.reason_code,
            operator_note=args.note,
            manual_transfer_completed=args.confirm_manual_transfer_completed,
            public_transaction_evidence=args.confirm_public_transaction_evidence,
        )
        token = load_admin_token(args.token_file)
        result = submit_transfer_evidence(
            base_url=args.base_url,
            token=token,
            payload=payload,
            timeout=args.timeout,
            cafile=args.cafile,
        )
    except (ExportError, MemberBenefitTransferError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(safe_result(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
