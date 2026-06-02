#!/usr/bin/env python3
"""Build a local support reply queue from a GCA member-access export.

The queue is for operator review before any user reply is sent. It reads the
JSON produced by ``tools/export_cloudflare_member_access.py`` and writes a CSV
with status, subject, body, and next step. It never calls Cloudflare, wallets,
or RPC endpoints, and it does not transfer tokens.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_gca_member_access_report import DEFAULT_INPUT, ReportError, dataset_records, load_export  # noqa: E402


DEFAULT_OUTPUT = ROOT / ".gca_access_data" / "member_access_report" / "gca_member_support_queue.csv"
DEFAULT_SUMMARY_OUTPUT = ROOT / ".gca_access_data" / "member_access_report" / "gca_member_support_queue_summary.json"

SUPPORT_FIELDS = [
    "replyReady",
    "supportStatus",
    "email",
    "emailSha256",
    "displayName",
    "accountId",
    "walletAddress",
    "gcaBalance",
    "creditLedgerStatus",
    "memberLedgerStatus",
    "memberBenefitClaimStatus",
    "subject",
    "body",
    "nextStep",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def key_values(record: dict[str, Any]) -> tuple[str, str]:
    return str(record.get("accountId") or ""), str(record.get("walletAddress") or "").lower()


def index_records(records: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_account: dict[str, dict[str, Any]] = {}
    by_wallet: dict[str, dict[str, Any]] = {}
    for record in records:
        account_id, wallet = key_values(record)
        if account_id and account_id not in by_account:
            by_account[account_id] = record
        if wallet and wallet not in by_wallet:
            by_wallet[wallet] = record
    return by_account, by_wallet


def lookup_related(
    account: dict[str, Any],
    by_account: dict[str, dict[str, Any]],
    by_wallet: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    account_id, wallet = key_values(account)
    return by_account.get(account_id) or by_wallet.get(wallet) or {}


def safe_name(account: dict[str, Any]) -> str:
    display = str(account.get("displayName") or "").strip()
    return display or "GCA member"


def classify_support_status(
    account: dict[str, Any],
    wallet: dict[str, Any],
    credit: dict[str, Any],
    member: dict[str, Any],
) -> str:
    if not wallet:
        return "wallet_verification_pending"
    if wallet.get("holderBonusEligible") is not True:
        return "below_10000_gca_threshold"
    if credit.get("status") == "ledger_recorded" and not member:
        return "credits_recorded_member_not_eligible"
    if member.get("memberBenefitClaimStatus") == "pending_manual_reserve_transfer" and member.get("status") == "active":
        return "gca_member_active_manual_benefit_review"
    if member.get("memberBenefitClaimStatus") == "needs_holding_period_review" or member.get("status") == "queued":
        return "holding_period_review_needed"
    if credit.get("status") == "ledger_recorded":
        return "credits_recorded"
    return str(account.get("status") or "received")


def build_reply(
    *,
    account: dict[str, Any],
    wallet: dict[str, Any],
    credit: dict[str, Any],
    member: dict[str, Any],
    support_status: str,
) -> tuple[str, str, str]:
    name = safe_name(account)
    wallet_address = str(account.get("walletAddress") or wallet.get("walletAddress") or "")
    balance = str(wallet.get("gcaBalance") or member.get("verifiedBalance") or "")
    if support_status == "wallet_verification_pending":
        subject = "GCA account received - wallet verification pending"
        body = (
            f"Hello {name},\n\n"
            "Your GCA account record has been received. The next step is read-only Base Mainnet GCA balance verification. "
            "GCA support will never ask for your private key, seed phrase, wallet password, exchange API secret, or withdrawal permission.\n\n"
            "Please use the official member access page if you need to resubmit your Base wallet address: https://gcagochina.com/gca/member-access/"
        )
        return subject, body, "Run read-only wallet verification or ask the user to resubmit wallet details through /gca/member-access/."

    if support_status == "below_10000_gca_threshold":
        subject = "GCA wallet verification update"
        body = (
            f"Hello {name},\n\n"
            f"We checked the submitted Base wallet {wallet_address}. The verified GCA balance is currently below the 10,000 GCA holder-credit threshold. "
            "No 100 Web3 Radar utility credits ledger record has been activated for this wallet at this time.\n\n"
            "You may request another read-only check after your wallet balance changes. This status does not involve wallet signatures, custody, or token transfers."
        )
        return subject, body, "Mark below-threshold or invite the user to request a later read-only recheck."

    if support_status == "credits_recorded_member_not_eligible":
        subject = "GCA 100 utility credits recorded"
        body = (
            f"Hello {name},\n\n"
            f"Your submitted Base wallet {wallet_address} has passed the 10,000 GCA holder-credit check. "
            "A one-time 100 Web3 Radar utility credits ledger record has been recorded for account-level service access.\n\n"
            "GCA Member status still requires at least 1,000,000 GCA and the separate 30-day holding-period review. Credits are not cash, income, reimbursement, or trading permission."
        )
        return subject, body, "Confirm credit-ledger record and explain GCA Member threshold if asked."

    if support_status == "gca_member_active_manual_benefit_review":
        subject = "GCA Member status active - manual benefit review pending"
        body = (
            f"Hello {name},\n\n"
            f"Your submitted Base wallet {wallet_address} has passed the GCA Member balance and holding-period checks. Verified balance: {balance} GCA. "
            "Your GCA Member ledger status is active, and the one-time 10,000 GCA member benefit is now in manual reserve-wallet transfer review.\n\n"
            "The member benefit is not automatic, not newly minted, and not a cash or income claim. Support will update you after manual review and any public transfer hash is available."
        )
        return subject, body, "Review reserve-wallet transfer readiness manually; do not promise timing."

    if support_status == "holding_period_review_needed":
        subject = "GCA Member holding-period review needed"
        body = (
            f"Hello {name},\n\n"
            f"Your submitted Base wallet {wallet_address} appears to meet or approach the 1,000,000 GCA member balance path, but the 30-day holding-period evidence is not complete yet. "
            "Please provide a public Base transaction hash and holding start date showing the wallet has bought and continuously held at least 1,000,000 GCA for 30 consecutive days.\n\n"
            "Do not send private keys, seed phrases, passwords, exchange API secrets, or one-time codes. Public transaction hashes and wallet addresses are enough for review."
        )
        return subject, body, "Ask for public holding-period evidence or wait until 30 days are complete."

    subject = "GCA account status update"
    body = (
        f"Hello {name},\n\n"
        "Your GCA account record is in review. Please use official links only and keep sensitive wallet or exchange information private. "
        "GCA support cannot promise token price, liquidity, listings, audit approval, or trading results."
    )
    return subject, body, "Review the account manually."


def stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def build_queue_rows(payload: dict[str, Any]) -> list[dict[str, str]]:
    source_redacted = bool(payload.get("redactedForExternalSharing"))
    accounts = dataset_records(payload, "member-access")
    wallet_by_account, wallet_by_wallet = index_records(dataset_records(payload, "wallet-verifications"))
    credit_by_account, credit_by_wallet = index_records(dataset_records(payload, "credit-ledger"))
    member_by_account, member_by_wallet = index_records(dataset_records(payload, "member-ledger"))

    rows: list[dict[str, str]] = []
    for account in accounts:
        wallet = lookup_related(account, wallet_by_account, wallet_by_wallet)
        credit = lookup_related(account, credit_by_account, credit_by_wallet)
        member = lookup_related(account, member_by_account, member_by_wallet)
        support_status = classify_support_status(account, wallet, credit, member)
        subject, body, next_step = build_reply(
            account=account,
            wallet=wallet,
            credit=credit,
            member=member,
            support_status=support_status,
        )
        visible_email = "" if source_redacted else stringify(account.get("email", ""))
        visible_display_name = "" if source_redacted else stringify(account.get("displayName", ""))
        reply_ready = bool(visible_email.strip())
        if source_redacted:
            subject = "GCA support queue blocked - redacted export"
            body = (
                "This row was generated from a public-redacted GCA member-access export. "
                "Do not send it as a user reply and do not treat it as a contactable support queue. "
                "Run the operator pipeline with a full internal export before contacting the account."
            )
            next_step = "Use a non-redacted internal export before sending support replies."
        rows.append({
            "replyReady": "true" if reply_ready else "false",
            "supportStatus": support_status,
            "email": visible_email,
            "emailSha256": stringify(account.get("emailSha256", "")),
            "displayName": visible_display_name,
            "accountId": stringify(account.get("accountId", "")),
            "walletAddress": stringify(account.get("walletAddress") or wallet.get("walletAddress") or ""),
            "gcaBalance": stringify(wallet.get("gcaBalance") or member.get("verifiedBalance") or ""),
            "creditLedgerStatus": stringify(credit.get("status", "")),
            "memberLedgerStatus": stringify(member.get("status", "")),
            "memberBenefitClaimStatus": stringify(member.get("memberBenefitClaimStatus", "")),
            "subject": subject,
            "body": body,
            "nextStep": next_step,
        })
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUPPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_support_queue(payload: dict[str, Any], output: Path, summary_output: Path) -> dict[str, Any]:
    source_redacted = bool(payload.get("redactedForExternalSharing"))
    rows = build_queue_rows(payload)
    write_csv(output, rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["supportStatus"]] = counts.get(row["supportStatus"], 0) + 1
    summary = {
        "ok": True,
        "packetVersion": "gca_member_support_queue_v1",
        "generatedAt": utc_now(),
        "sourceExportedAt": payload.get("exportedAt", ""),
        "sourceRedactedForExternalSharing": source_redacted,
        "output": str(output),
        "summaryOutput": str(summary_output),
        "rows": len(rows),
        "replyReadyRows": sum(1 for row in rows if row["replyReady"] == "true"),
        "replySuppressedRows": len(rows) if source_redacted else 0,
        "statusCounts": counts,
        "boundaries": {
            "operatorReviewRequiredBeforeSending": True,
            "redactedExportBlocksUserReplies": True,
            "offlineQueueOnly": True,
            "writesProductionData": False,
            "adminTokenPrinted": False,
            "walletCalls": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTokenTransfer": False,
            "memberBenefitTransferAutomatic": False,
            "noPriceLiquidityListingAuditPromises": True,
        },
    }
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local GCA member support reply queue from a member access export.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input member access export JSON path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output support queue CSV path.")
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT, help="Output summary JSON path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = load_export(args.input)
        summary = build_support_queue(payload, args.output, args.summary_output)
    except ReportError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
