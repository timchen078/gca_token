#!/usr/bin/env python3
"""Build a local GCA Member 30-day holding-period evidence report.

The report reads a GCA member-access export, optionally records one read-only
Base Mainnet balance snapshot per wallet for the current day, and writes local
operator CSV/JSON output. It does not write production data, request wallet
signatures, send transactions, or transfer tokens.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_gca_member_access_report import DEFAULT_INPUT, ReportError, dataset_records, load_export  # noqa: E402
from tools.gca_member_backend import (  # noqa: E402
    CHAIN_ID,
    CONTRACT_ADDRESS,
    MEMBER_HOLD_DAYS,
    MEMBER_THRESHOLD_UNITS,
    BaseRpcBalanceReader,
    is_tx_hash,
    normalize_wallet,
    stable_id,
    units_to_gca,
)


SNAPSHOT_VERSION = "gca_holding_snapshot_v1"
SUMMARY_VERSION = "gca_holding_period_report_v1"
DEFAULT_SNAPSHOT_OUTPUT = ROOT / ".gca_access_data" / "gca_holding_snapshots.jsonl"
DEFAULT_REPORT_OUTPUT = ROOT / ".gca_access_data" / "member_access_report" / "gca_holding_period_report.csv"
DEFAULT_SUMMARY_OUTPUT = ROOT / ".gca_access_data" / "member_access_report" / "gca_holding_period_summary.json"

REPORT_FIELDS = [
    "walletAddress",
    "accountIds",
    "memberLedgerIds",
    "latestSnapshotDate",
    "latestCheckedAt",
    "latestGcaBalance",
    "currentMemberThresholdQualified",
    "observedQualifiedStreakDays",
    "observedQualifiedStartDate",
    "observedEligibleFor30Days",
    "missingSnapshotDaysInWindow",
    "selfReportedHoldingStartDate",
    "selfReportedHoldingDaysPreview",
    "evidenceTxHash",
    "evidenceTxHashFormatOk",
    "recommendedLane",
]


class HoldingReportError(RuntimeError):
    """Raised for expected operator-facing holding report failures."""


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso_now(now: datetime | None = None) -> str:
    value = now or utc_now()
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc_datetime(value: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        return utc_now()
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HoldingReportError("--now must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def days_since(value: str, today: date) -> int:
    start = parse_date(value)
    if not start or start > today:
        return 0
    return (today - start).days


def stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([{field: stringify(row.get(field, "")) for field in REPORT_FIELDS} for row in rows])


def load_snapshots(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise HoldingReportError(f"snapshot file has invalid JSON on line {line_number}: {path}") from exc
        if isinstance(record, dict):
            records.append(record)
    return records


def append_snapshot(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def merge_list(existing: list[str], value: Any) -> list[str]:
    text = str(value or "").strip()
    if text and text not in existing:
        existing.append(text)
    return existing


def extract_candidates(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}

    def candidate(wallet_value: Any) -> dict[str, Any] | None:
        wallet = str(wallet_value or "").strip()
        if not wallet:
            return None
        try:
            wallet = normalize_wallet(wallet)
        except Exception:
            return None
        return candidates.setdefault(
            wallet,
            {
                "walletAddress": wallet,
                "accountIds": [],
                "memberLedgerIds": [],
                "walletVerificationIds": [],
                "selfReportedHoldingStartDate": "",
                "evidenceTxHash": "",
                "evidenceTxHashFormatOk": False,
            },
        )

    for record in dataset_records(payload, "member-access"):
        item = candidate(record.get("walletAddress"))
        if not item:
            continue
        merge_list(item["accountIds"], record.get("accountId") or record.get("registrationId"))
        if not item["selfReportedHoldingStartDate"]:
            item["selfReportedHoldingStartDate"] = str(record.get("holdingStartDate") or "")[:10]
        if not item["evidenceTxHash"]:
            item["evidenceTxHash"] = str(record.get("evidenceTxHash") or "").strip().lower()
            item["evidenceTxHashFormatOk"] = is_tx_hash(item["evidenceTxHash"])

    for record in dataset_records(payload, "wallet-verifications"):
        item = candidate(record.get("walletAddress"))
        if not item:
            continue
        merge_list(item["accountIds"], record.get("accountId") or record.get("registrationId"))
        merge_list(item["walletVerificationIds"], record.get("walletVerificationId"))
        if not item["evidenceTxHash"]:
            item["evidenceTxHash"] = str(record.get("evidenceTxHash") or "").strip().lower()
            item["evidenceTxHashFormatOk"] = is_tx_hash(item["evidenceTxHash"])

    for record in dataset_records(payload, "member-ledger"):
        item = candidate(record.get("walletAddress"))
        if not item:
            continue
        merge_list(item["accountIds"], record.get("accountId") or record.get("registrationId"))
        merge_list(item["memberLedgerIds"], record.get("memberLedgerId"))
        if not item["selfReportedHoldingStartDate"]:
            item["selfReportedHoldingStartDate"] = str(record.get("holdingStartDate") or "")[:10]
        if not item["evidenceTxHash"]:
            item["evidenceTxHash"] = str(record.get("evidenceTxHash") or "").strip().lower()
            item["evidenceTxHashFormatOk"] = is_tx_hash(item["evidenceTxHash"])

    return candidates


def latest_snapshot_for_day(snapshots: list[dict[str, Any]], wallet: str, snapshot_date: date) -> dict[str, Any] | None:
    wallet = wallet.lower()
    day = snapshot_date.isoformat()
    matches = [
        record
        for record in snapshots
        if str(record.get("walletAddress") or "").lower() == wallet and str(record.get("snapshotDate") or "") == day
    ]
    return matches[-1] if matches else None


def build_snapshot(wallet: str, balance_units: int, now: datetime) -> dict[str, Any]:
    checked_at = iso_now(now)
    snapshot_day = now.astimezone(UTC).date().isoformat()
    return {
        "packetVersion": SNAPSHOT_VERSION,
        "snapshotId": stable_id("gca_hold", wallet, snapshot_day),
        "walletAddress": wallet.lower(),
        "chainId": CHAIN_ID,
        "contractAddress": CONTRACT_ADDRESS,
        "checkedAt": checked_at,
        "snapshotDate": snapshot_day,
        "rawBalance": str(balance_units),
        "gcaBalance": units_to_gca(balance_units),
        "memberThresholdGca": "1000000",
        "meetsMemberThreshold": balance_units >= MEMBER_THRESHOLD_UNITS,
        "source": "read-only-base-mainnet-balanceOf",
        "requiresSignature": False,
        "requiresTransaction": False,
        "automaticTokenTransfer": False,
    }


def snapshots_by_wallet(snapshots: list[dict[str, Any]], wallet: str) -> dict[date, dict[str, Any]]:
    wallet = wallet.lower()
    by_day: dict[date, dict[str, Any]] = {}
    for record in snapshots:
        if str(record.get("walletAddress") or "").lower() != wallet:
            continue
        day = parse_date(record.get("snapshotDate"))
        if not day:
            continue
        by_day[day] = record
    return by_day


def observed_streak(by_day: dict[date, dict[str, Any]], latest_day: date | None) -> tuple[int, str]:
    if latest_day is None:
        return 0, ""
    cursor = latest_day
    count = 0
    while True:
        record = by_day.get(cursor)
        if not record or record.get("meetsMemberThreshold") is not True:
            break
        count += 1
        cursor = cursor - timedelta(days=1)
    start = (latest_day - timedelta(days=count - 1)).isoformat() if count else ""
    return count, start


def missing_days_in_window(by_day: dict[date, dict[str, Any]], latest_day: date | None, window_days: int) -> int:
    if latest_day is None:
        return window_days
    start = latest_day - timedelta(days=window_days - 1)
    return sum(1 for offset in range(window_days) if (start + timedelta(days=offset)) not in by_day)


def build_candidate_row(candidate: dict[str, Any], snapshots: list[dict[str, Any]], today: date) -> dict[str, Any]:
    wallet = candidate["walletAddress"]
    by_day = snapshots_by_wallet(snapshots, wallet)
    latest_day = max(by_day) if by_day else None
    latest = by_day.get(latest_day) if latest_day else {}
    streak, streak_start = observed_streak(by_day, latest_day)
    current_ok = bool(latest and latest.get("meetsMemberThreshold") is True)
    observed_ready = streak >= MEMBER_HOLD_DAYS
    if not latest:
        lane = "needs_first_snapshot"
    elif not current_ok:
        lane = "below_member_threshold"
    elif observed_ready:
        lane = "observed_30_day_holding_ready_for_support_review"
    else:
        lane = "continue_daily_snapshots"

    holding_start = str(candidate.get("selfReportedHoldingStartDate") or "")
    return {
        "walletAddress": wallet,
        "accountIds": ",".join(candidate.get("accountIds", [])),
        "memberLedgerIds": ",".join(candidate.get("memberLedgerIds", [])),
        "latestSnapshotDate": latest_day.isoformat() if latest_day else "",
        "latestCheckedAt": latest.get("checkedAt", "") if latest else "",
        "latestGcaBalance": latest.get("gcaBalance", "") if latest else "",
        "currentMemberThresholdQualified": current_ok,
        "observedQualifiedStreakDays": streak,
        "observedQualifiedStartDate": streak_start,
        "observedEligibleFor30Days": observed_ready,
        "missingSnapshotDaysInWindow": missing_days_in_window(by_day, latest_day, MEMBER_HOLD_DAYS),
        "selfReportedHoldingStartDate": holding_start,
        "selfReportedHoldingDaysPreview": days_since(holding_start, today),
        "evidenceTxHash": candidate.get("evidenceTxHash", ""),
        "evidenceTxHashFormatOk": bool(candidate.get("evidenceTxHashFormatOk")),
        "recommendedLane": lane,
    }


def refresh_snapshots(
    *,
    candidates: dict[str, dict[str, Any]],
    snapshots: list[dict[str, Any]],
    snapshot_output: Path,
    balance_reader: Any,
    now: datetime,
    live_read: bool,
    force_same_day: bool,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    counts = {"walletsChecked": 0, "snapshotsAdded": 0, "sameDaySnapshotsReused": 0, "walletsSkippedNoLiveRead": 0}
    today = now.astimezone(UTC).date()
    all_snapshots = list(snapshots)
    for wallet in sorted(candidates):
        existing = latest_snapshot_for_day(all_snapshots, wallet, today)
        if existing and not force_same_day:
            counts["sameDaySnapshotsReused"] += 1
            continue
        if not live_read:
            counts["walletsSkippedNoLiveRead"] += 1
            continue
        balance_units = int(balance_reader.get_balance_units(wallet))
        counts["walletsChecked"] += 1
        snapshot = build_snapshot(wallet, balance_units, now)
        append_snapshot(snapshot_output, snapshot)
        all_snapshots.append(snapshot)
        counts["snapshotsAdded"] += 1
    return all_snapshots, counts


def build_holding_period_report(
    *,
    export_payload: dict[str, Any],
    snapshot_output: Path = DEFAULT_SNAPSHOT_OUTPUT,
    report_output: Path = DEFAULT_REPORT_OUTPUT,
    summary_output: Path = DEFAULT_SUMMARY_OUTPUT,
    balance_reader: Any | None = None,
    now: datetime | None = None,
    live_read: bool = True,
    force_same_day: bool = False,
) -> dict[str, Any]:
    now = now or utc_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    candidates = extract_candidates(export_payload)
    existing_snapshots = load_snapshots(snapshot_output)
    reader = balance_reader or BaseRpcBalanceReader()
    all_snapshots, refresh_counts = refresh_snapshots(
        candidates=candidates,
        snapshots=existing_snapshots,
        snapshot_output=snapshot_output,
        balance_reader=reader,
        now=now,
        live_read=live_read,
        force_same_day=force_same_day,
    )
    rows = [
        build_candidate_row(candidate, all_snapshots, today=now.astimezone(UTC).date())
        for candidate in sorted(candidates.values(), key=lambda item: item["walletAddress"])
    ]
    write_csv(report_output, rows)

    lane_counts: dict[str, int] = {}
    for row in rows:
        lane = str(row.get("recommendedLane") or "unknown")
        lane_counts[lane] = lane_counts.get(lane, 0) + 1

    summary = {
        "ok": True,
        "packetVersion": SUMMARY_VERSION,
        "generatedAt": iso_now(now),
        "sourceExportedAt": export_payload.get("exportedAt", ""),
        "redactedForExternalSharing": bool(export_payload.get("redactedForExternalSharing")),
        "snapshotOutput": str(snapshot_output),
        "reportOutput": str(report_output),
        "summaryOutput": str(summary_output),
        "counts": {
            "candidateWallets": len(candidates),
            "snapshotRecordsAvailable": len(all_snapshots),
            "observedEligibleFor30Days": sum(1 for row in rows if row.get("observedEligibleFor30Days") is True),
            **refresh_counts,
        },
        "laneCounts": lane_counts,
        "boundaries": {
            "localOperatorReportOnly": True,
            "writesProductionData": False,
            "writesLocalSnapshotOnly": True,
            "readOnlyPublicChainBalanceCheck": bool(live_read),
            "adminTokenPrinted": False,
            "userEmailsPrinted": False,
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTokenTransfer": False,
            "memberBenefitTransferAutomatic": False,
            "doesNotApproveMemberBenefitByItself": True,
        },
    }
    write_json(summary_output, summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local GCA Member 30-day holding-period evidence report.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Member access export JSON.")
    parser.add_argument("--snapshot-output", type=Path, default=DEFAULT_SNAPSHOT_OUTPUT, help="Append-only snapshot JSONL path.")
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUTPUT, help="Holding report CSV output.")
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT, help="Holding report summary JSON output.")
    parser.add_argument("--no-live-read", action="store_true", help="Build report from existing snapshots without RPC reads.")
    parser.add_argument("--force-same-day", action="store_true", help="Append a new same-day snapshot instead of reusing one.")
    parser.add_argument("--rpc-url", default="", help="Optional Base RPC URL for read-only balance snapshots.")
    parser.add_argument("--timeout", type=float, default=20, help="Read-only RPC timeout in seconds. Default: 20.")
    parser.add_argument("--now", default="", help="Optional ISO-8601 UTC time for deterministic local/offline reports.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        export_payload = load_export(args.input)
        reader = BaseRpcBalanceReader(rpc_url=args.rpc_url, timeout=args.timeout) if args.rpc_url else BaseRpcBalanceReader(timeout=args.timeout)
        summary = build_holding_period_report(
            export_payload=export_payload,
            snapshot_output=args.snapshot_output,
            report_output=args.report_output,
            summary_output=args.summary_output,
            balance_reader=reader,
            now=parse_utc_datetime(args.now) if args.now else None,
            live_read=not args.no_live_read,
            force_same_day=args.force_same_day,
        )
    except (ReportError, HoldingReportError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
