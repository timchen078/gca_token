#!/usr/bin/env python3
"""Build local CSV reports from a GCA Cloudflare member-access export.

This is an offline operator helper. It reads the JSON produced by
``tools/export_cloudflare_member_access.py`` and writes local CSV/summary
files for account review, wallet verification review, credit review, GCA
credit usage review, Member review, and manual member-benefit follow-up. It
never calls Cloudflare, wallets, or RPC endpoints.
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
DEFAULT_INPUT = ROOT / ".gca_access_data" / "cloudflare_member_access_export.json"
DEFAULT_OUTPUT_DIR = ROOT / ".gca_access_data" / "member_access_report"
DEFAULT_SUMMARY_OUTPUT = DEFAULT_OUTPUT_DIR / "gca_member_access_report_summary.json"


class ReportError(RuntimeError):
    """Raised for expected operator-facing report failures."""


ACCOUNT_FIELDS = [
    "accountId",
    "status",
    "createdAt",
    "updatedAt",
    "email",
    "emailSha256",
    "displayName",
    "walletAddress",
    "programIntent",
    "holdingStartDate",
    "evidenceTxHash",
    "source",
    "language",
]

WALLET_FIELDS = [
    "walletVerificationId",
    "accountId",
    "walletAddress",
    "chainId",
    "contractAddress",
    "checkedAt",
    "gcaBalance",
    "holderBonusEligible",
    "gcaMemberEligible",
    "gcaMemberHoldingPeriodEligible",
    "holdingPeriodDaysVerified",
    "evidenceTxHash",
    "evidenceTxHashFormatOk",
    "status",
]

CREDIT_FIELDS = [
    "creditLedgerId",
    "accountId",
    "walletAddress",
    "creditAmount",
    "creditType",
    "activatedAt",
    "expiresAt",
    "remainingCredits",
    "source",
    "transferable",
    "cashRedeemable",
    "status",
]

CREDIT_USAGE_FIELDS = [
    "creditUsageId",
    "creditLedgerId",
    "accountId",
    "walletAddress",
    "serviceId",
    "serviceName",
    "creditAmountUsed",
    "remainingCreditsBefore",
    "remainingCreditsAfter",
    "usedAt",
    "source",
    "operatorNote",
    "status",
]

MEMBER_FIELDS = [
    "memberLedgerId",
    "accountId",
    "walletAddress",
    "tierName",
    "verifiedBalance",
    "holdingStartDate",
    "holdingPeriodDaysVerified",
    "evidenceTxHash",
    "evidenceTxHashFormatOk",
    "memberBenefitReviewEvidenceStatus",
    "memberBenefitAmount",
    "memberBenefitClaimStatus",
    "memberBenefitTransferTx",
    "activatedAt",
    "nextRefreshDueAt",
    "requiresManualReserveTransferReview",
    "automaticTransfer",
    "status",
    "updatedAt",
]

BENEFIT_QUEUE_FIELDS = [
    "reviewLane",
    "memberLedgerId",
    "accountId",
    "walletAddress",
    "tierName",
    "verifiedBalance",
    "holdingStartDate",
    "holdingPeriodDaysVerified",
    "evidenceTxHash",
    "evidenceTxHashFormatOk",
    "memberBenefitReviewEvidenceStatus",
    "memberBenefitAmount",
    "memberBenefitClaimStatus",
    "memberBenefitTransferTx",
    "activatedAt",
    "nextRefreshDueAt",
    "status",
    "updatedAt",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_export(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReportError(f"input export not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReportError(f"input export is not valid JSON: {path}") from exc

    if payload.get("ok") is not True:
        raise ReportError("input export must have ok=true")
    if payload.get("packetVersion") != "gca_cloudflare_member_access_export_v1":
        raise ReportError("input export has the wrong packetVersion")
    if not isinstance(payload.get("datasets"), dict):
        raise ReportError("input export is missing datasets{}")
    return payload


def dataset_records(payload: dict[str, Any], dataset: str) -> list[dict[str, Any]]:
    data = payload.get("datasets", {}).get(dataset, {})
    records = data.get("records", [])
    if not isinstance(records, list):
        raise ReportError(f"{dataset} dataset is missing records[]")
    return [record for record in records if isinstance(record, dict)]


def stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def select_row(record: dict[str, Any], fields: list[str]) -> dict[str, str]:
    return {field: stringify(record.get(field, "")) for field in fields}


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def member_benefit_review_lane(record: dict[str, Any]) -> str:
    claim_status = str(record.get("memberBenefitClaimStatus") or "")
    evidence_status = str(record.get("memberBenefitReviewEvidenceStatus") or "")
    status = str(record.get("status") or "")
    if claim_status == "pending_manual_reserve_transfer" and status == "active":
        return "pending_manual_reserve_transfer"
    if claim_status == "needs_holding_period_review" or evidence_status == "needs_more_information":
        return "holding_period_review"
    if record.get("requiresManualReserveTransferReview") is True and claim_status not in {"transferred", "closed"}:
        return "manual_review"
    return ""


def build_benefit_queue(member_records: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in member_records:
        lane = member_benefit_review_lane(record)
        if not lane:
            continue
        row = select_row(record, BENEFIT_QUEUE_FIELDS)
        row["reviewLane"] = lane
        rows.append(row)
    return rows


def count_records(records: list[dict[str, Any]], field: str, value: Any) -> int:
    return sum(1 for record in records if record.get(field) == value)


def count_any(records: list[dict[str, Any]], field: str, values: set[Any]) -> int:
    return sum(1 for record in records if record.get(field) in values)


def build_report(payload: dict[str, Any], output_dir: Path, summary_output: Path) -> dict[str, Any]:
    accounts = dataset_records(payload, "member-access")
    wallet_verifications = dataset_records(payload, "wallet-verifications")
    credits = dataset_records(payload, "credit-ledger")
    credit_usage = dataset_records(payload, "credit-usage")
    members = dataset_records(payload, "member-ledger")

    account_rows = [select_row(record, ACCOUNT_FIELDS) for record in accounts]
    wallet_rows = [select_row(record, WALLET_FIELDS) for record in wallet_verifications]
    credit_rows = [select_row(record, CREDIT_FIELDS) for record in credits]
    credit_usage_rows = [select_row(record, CREDIT_USAGE_FIELDS) for record in credit_usage]
    member_rows = [select_row(record, MEMBER_FIELDS) for record in members]
    benefit_queue_rows = build_benefit_queue(members)

    outputs = {
        "accountsCsv": output_dir / "gca_member_accounts.csv",
        "walletVerificationsCsv": output_dir / "gca_wallet_verifications.csv",
        "creditLedgerCsv": output_dir / "gca_credit_ledger.csv",
        "creditUsageCsv": output_dir / "gca_credit_usage.csv",
        "memberLedgerCsv": output_dir / "gca_member_ledger.csv",
        "memberBenefitReviewQueueCsv": output_dir / "gca_member_benefit_review_queue.csv",
    }

    write_csv(outputs["accountsCsv"], account_rows, ACCOUNT_FIELDS)
    write_csv(outputs["walletVerificationsCsv"], wallet_rows, WALLET_FIELDS)
    write_csv(outputs["creditLedgerCsv"], credit_rows, CREDIT_FIELDS)
    write_csv(outputs["creditUsageCsv"], credit_usage_rows, CREDIT_USAGE_FIELDS)
    write_csv(outputs["memberLedgerCsv"], member_rows, MEMBER_FIELDS)
    write_csv(outputs["memberBenefitReviewQueueCsv"], benefit_queue_rows, BENEFIT_QUEUE_FIELDS)

    summary = {
        "ok": True,
        "packetVersion": "gca_member_access_report_v1",
        "generatedAt": utc_now(),
        "sourceExportedAt": payload.get("exportedAt", ""),
        "sourceRedactedForExternalSharing": bool(payload.get("redactedForExternalSharing")),
        "counts": {
            "accounts": len(accounts),
            "walletVerifications": len(wallet_verifications),
            "holderBonusEligibleWallets": count_records(wallet_verifications, "holderBonusEligible", True),
            "gcaMemberEligibleWallets": count_records(wallet_verifications, "gcaMemberEligible", True),
            "creditLedgerRecords": len(credits),
            "creditLedgerRecorded": count_records(credits, "status", "ledger_recorded"),
            "creditUsageRecords": len(credit_usage),
            "creditUsageRecorded": count_any(credit_usage, "status", {"usage_recorded", "exhausted"}),
            "creditsConsumed": sum(int(record.get("creditAmountUsed") or 0) for record in credit_usage),
            "memberLedgerRecords": len(members),
            "activeGcaMembers": count_records(members, "status", "active"),
            "queuedGcaMembers": count_records(members, "status", "queued"),
            "pendingManualReserveTransfers": count_records(members, "memberBenefitClaimStatus", "pending_manual_reserve_transfer"),
            "holdingPeriodReviewsNeeded": count_records(members, "memberBenefitClaimStatus", "needs_holding_period_review"),
            "memberBenefitReviewQueueRows": len(benefit_queue_rows),
        },
        "outputs": {key: str(value) for key, value in outputs.items()},
        "summaryOutput": str(summary_output),
        "boundaries": {
            "offlineReportOnly": True,
            "writesProductionData": False,
            "adminTokenPrinted": False,
            "walletCalls": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTokenTransfer": False,
            "memberBenefitTransferAutomatic": False,
        },
    }
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build local CSV reports from a GCA Cloudflare member access export.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input export JSON path.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory for CSV reports.")
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT, help="Output summary JSON path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = load_export(args.input)
        summary = build_report(payload, args.output_dir, args.summary_output)
    except ReportError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
