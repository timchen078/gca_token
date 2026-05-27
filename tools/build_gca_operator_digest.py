#!/usr/bin/env python3
"""Build a local GCA operator digest from existing summary files.

The digest is intentionally redacted-by-design: it reads only summary JSON
files, emits counts/statuses/next actions, and never includes user records,
emails, admin tokens, wallet signatures, transactions, or transfer automation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DAILY_SUMMARY = ROOT / ".gca_access_data" / "gca_daily_ops_summary.json"
DEFAULT_MEMBER_OPS_SUMMARY = ROOT / ".gca_access_data" / "gca_member_access_ops_summary.json"
DEFAULT_SUPPORT_QUEUE_SUMMARY = ROOT / ".gca_access_data" / "member_access_report" / "gca_member_support_queue_summary.json"
DEFAULT_HOLDING_SUMMARY = ROOT / ".gca_access_data" / "member_access_report" / "gca_holding_period_summary.json"
DEFAULT_DIGEST_OUTPUT = ROOT / ".gca_access_data" / "gca_operator_digest.md"
DEFAULT_JSON_OUTPUT = ROOT / ".gca_access_data" / "gca_operator_digest.json"
DIGEST_VERSION = "gca_operator_digest_v1"


class DigestError(RuntimeError):
    """Raised for operator-facing digest failures."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DigestError(f"summary file is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise DigestError(f"summary file must contain a JSON object: {path}")
    return payload


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_bool(value: Any) -> bool:
    return value is True


def file_status(path: Path, payload: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": payload is not None,
        "ok": bool(payload.get("ok")) if payload else False,
        "generatedAt": str(payload.get("generatedAt") or payload.get("checkedAt") or "") if payload else "",
        "packetVersion": str(payload.get("packetVersion") or "") if payload else "",
    }


def summarize_daily(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {
            "available": False,
            "ok": False,
            "generatedAt": "",
            "includeMemberOps": False,
            "includeHoldingReport": False,
            "steps": [],
            "baseScanPreflight": {"available": False, "readyForBaseScanResubmission": None, "status": "missing"},
        }
    steps = []
    for step in payload.get("steps") or []:
        if not isinstance(step, dict):
            continue
        steps.append({
            "id": str(step.get("id") or ""),
            "ok": bool(step.get("ok")),
            "returnCode": step.get("returnCode", ""),
        })
    preflight = payload.get("baseScanPreflight") if isinstance(payload.get("baseScanPreflight"), dict) else {}
    return {
        "available": True,
        "ok": bool(payload.get("ok")),
        "generatedAt": str(payload.get("generatedAt") or ""),
        "includeMemberOps": bool(payload.get("includeMemberOps")),
        "includeHoldingReport": bool(payload.get("includeHoldingReport")),
        "steps": steps,
        "baseScanPreflight": {
            "available": bool(preflight.get("available")),
            "readyForBaseScanResubmission": preflight.get("readyForBaseScanResubmission"),
            "status": str(preflight.get("status") or ""),
            "publicEmailSwitchStatus": str(preflight.get("publicEmailSwitchStatus") or ""),
            "filesStillUsingOldEmail": as_int(preflight.get("filesStillUsingOldEmail")),
            "missingOrBlockedRequirements": [
                str(item) for item in preflight.get("missingOrBlockedRequirements", []) if str(item)
            ],
        },
    }


def summarize_member_ops(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {
            "available": False,
            "ok": False,
            "generatedAt": "",
            "recordCount": 0,
            "report": {},
            "supportQueue": {},
            "holdingPeriod": {},
            "holdingPeriodLaneCounts": {},
        }
    export = payload.get("export") if isinstance(payload.get("export"), dict) else {}
    report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
    support = payload.get("supportQueue") if isinstance(payload.get("supportQueue"), dict) else {}
    holding = payload.get("holdingPeriod") if isinstance(payload.get("holdingPeriod"), dict) else {}
    allowed_report_keys = (
        "accounts",
        "walletVerifications",
        "holderBonusEligibleWallets",
        "gcaMemberEligibleWallets",
        "creditLedgerRecords",
        "creditLedgerRecorded",
        "memberLedgerRecords",
        "activeGcaMembers",
        "queuedGcaMembers",
        "pendingManualReserveTransfers",
        "holdingPeriodReviewsNeeded",
        "memberBenefitReviewQueueRows",
    )
    allowed_holding_keys = (
        "candidateWallets",
        "snapshotRecordsAvailable",
        "observedEligibleFor30Days",
        "walletsChecked",
        "snapshotsAdded",
        "sameDaySnapshotsReused",
        "walletsSkippedNoLiveRead",
    )
    return {
        "available": True,
        "ok": bool(payload.get("ok")),
        "generatedAt": str(payload.get("generatedAt") or ""),
        "source": str(payload.get("source") or ""),
        "recordCount": as_int(export.get("recordCount")),
        "datasetCount": as_int(export.get("datasetCount")),
        "report": {key: as_int(report.get(key)) for key in allowed_report_keys if key in report},
        "supportQueue": {
            "rows": as_int(support.get("rows")),
            "replyReadyRows": as_int(support.get("replyReadyRows")),
            "statusCounts": support.get("statusCounts") if isinstance(support.get("statusCounts"), dict) else {},
        },
        "holdingReportIncluded": bool(payload.get("holdingReportIncluded")),
        "holdingPeriod": {key: as_int(holding.get(key)) for key in allowed_holding_keys if key in holding},
        "holdingPeriodLaneCounts": payload.get("holdingPeriodLaneCounts") if isinstance(payload.get("holdingPeriodLaneCounts"), dict) else {},
    }


def summarize_support_queue(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {"available": False, "ok": False, "rows": 0, "replyReadyRows": 0, "statusCounts": {}}
    return {
        "available": True,
        "ok": bool(payload.get("ok")),
        "generatedAt": str(payload.get("generatedAt") or ""),
        "rows": as_int(payload.get("rows")),
        "replyReadyRows": as_int(payload.get("replyReadyRows")),
        "statusCounts": payload.get("statusCounts") if isinstance(payload.get("statusCounts"), dict) else {},
    }


def summarize_holding(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {"available": False, "ok": False, "counts": {}, "laneCounts": {}}
    return {
        "available": True,
        "ok": bool(payload.get("ok")),
        "generatedAt": str(payload.get("generatedAt") or ""),
        "counts": payload.get("counts") if isinstance(payload.get("counts"), dict) else {},
        "laneCounts": payload.get("laneCounts") if isinstance(payload.get("laneCounts"), dict) else {},
    }


def build_next_actions(daily: dict[str, Any], member_ops: dict[str, Any], support: dict[str, Any], holding: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    if not daily["available"]:
        actions.append("Run `python3 tools/run_gca_daily_ops.py --summary-output .gca_access_data/gca_daily_ops_summary.json` to create the public health baseline.")
    elif not daily["ok"]:
        failed = [step["id"] for step in daily["steps"] if not step.get("ok")]
        suffix = f" Failed step(s): {', '.join(failed)}." if failed else ""
        actions.append(f"Investigate the latest public daily ops failure.{suffix}")

    base_scan = daily.get("baseScanPreflight", {})
    if daily["available"] and isinstance(base_scan, dict):
        if not base_scan.get("available"):
            actions.append("Refresh the non-blocking BaseScan preflight status in the next daily ops run.")
        elif base_scan.get("readyForBaseScanResubmission") is False:
            blocked = base_scan.get("missingOrBlockedRequirements") if isinstance(base_scan.get("missingOrBlockedRequirements"), list) else []
            blocked_text = ", ".join(str(item) for item in blocked[:5]) if blocked else "see BaseScan preflight summary"
            actions.append(f"Do not resubmit the BaseScan token profile yet; complete blocked item(s): {blocked_text}.")

    if not member_ops["available"]:
        actions.append("When `ADMIN_READ_TOKEN` is available locally, run member ops to refresh account, ledger, support, and optional holding reports.")
    elif not member_ops["ok"]:
        actions.append("Investigate the latest member-access ops failure before using support or benefit queues.")

    reply_ready = as_int(support.get("replyReadyRows")) or as_int(member_ops.get("supportQueue", {}).get("replyReadyRows"))
    if reply_ready:
        actions.append(f"Review {reply_ready} support queue row(s) manually before sending any user reply.")

    report_counts = member_ops.get("report", {})
    pending_transfers = as_int(report_counts.get("pendingManualReserveTransfers"))
    holding_reviews = as_int(report_counts.get("holdingPeriodReviewsNeeded"))
    if pending_transfers:
        actions.append(f"Review {pending_transfers} pending manual reserve-transfer case(s); verify evidence before any transfer.")
    if holding_reviews:
        actions.append(f"Review {holding_reviews} GCA Member holding-period case(s) that need more evidence or more time.")

    holding_counts = holding.get("counts", {})
    if not holding["available"] and member_ops.get("holdingReportIncluded") is False:
        actions.append("For GCA Member evidence, run member ops with `--include-holding-report` on operator hardware.")
    observed_ready = as_int(holding_counts.get("observedEligibleFor30Days"))
    if observed_ready:
        actions.append(f"Review {observed_ready} wallet(s) with observed 30-day member-threshold streak before any member benefit decision.")
    lane_counts = holding.get("laneCounts", {})
    needs_first_snapshot = as_int(lane_counts.get("needs_first_snapshot"))
    continue_snapshots = as_int(lane_counts.get("continue_daily_snapshots"))
    if needs_first_snapshot or continue_snapshots:
        actions.append("Keep daily holding snapshots running until every candidate has enough consecutive evidence.")

    if not actions:
        actions.append("No immediate operator action from the available summaries.")
    return actions


def render_status(value: bool, available: bool = True) -> str:
    if not available:
        return "missing"
    return "ok" if value else "attention"


def render_markdown(digest: dict[str, Any]) -> str:
    daily = digest["dailyOps"]
    member = digest["memberOps"]
    support = digest["supportQueue"]
    holding = digest["holdingPeriod"]
    lines = [
        "# GCA Operator Digest",
        "",
        f"Generated: `{digest['generatedAt']}`",
        "",
        "## Public Health",
        "",
        f"- Daily ops: `{render_status(daily['ok'], daily['available'])}`",
        f"- Generated at: `{daily.get('generatedAt') or 'not available'}`",
        f"- Member ops included: `{str(daily.get('includeMemberOps')).lower()}`",
        f"- Holding report included: `{str(daily.get('includeHoldingReport')).lower()}`",
        "",
        "## BaseScan Preflight",
        "",
        f"- Status: `{daily.get('baseScanPreflight', {}).get('status') or 'not available'}`",
        f"- Ready for resubmission: `{str(daily.get('baseScanPreflight', {}).get('readyForBaseScanResubmission')).lower()}`",
        f"- Public email switch: `{daily.get('baseScanPreflight', {}).get('publicEmailSwitchStatus') or 'not available'}`",
        f"- Blocked requirements: `{len(daily.get('baseScanPreflight', {}).get('missingOrBlockedRequirements') or [])}`",
        "",
        "## Member Operations",
        "",
        f"- Member ops: `{render_status(member['ok'], member['available'])}`",
        f"- Export records: `{member.get('recordCount', 0)}`",
        f"- Support queue rows: `{member.get('supportQueue', {}).get('rows', support.get('rows', 0))}`",
        f"- Reply-ready rows: `{member.get('supportQueue', {}).get('replyReadyRows', support.get('replyReadyRows', 0))}`",
        f"- Pending manual reserve transfers: `{member.get('report', {}).get('pendingManualReserveTransfers', 0)}`",
        "",
        "## Holding Evidence",
        "",
        f"- Holding report: `{render_status(holding['ok'], holding['available'])}`",
        f"- Candidate wallets: `{holding.get('counts', {}).get('candidateWallets', 0)}`",
        f"- Observed 30-day eligible wallets: `{holding.get('counts', {}).get('observedEligibleFor30Days', 0)}`",
        f"- Snapshots added: `{holding.get('counts', {}).get('snapshotsAdded', 0)}`",
        "",
        "## Next Actions",
        "",
    ]
    lines.extend(f"{index}. {action}" for index, action in enumerate(digest["nextActions"], start=1))
    lines.extend([
        "",
        "## Boundaries",
        "",
        "- Local operator summary only.",
        "- Does not print admin tokens or user records.",
        "- Does not request signatures, transactions, custody, or automatic GCA transfers.",
        "- Does not approve the 10,000 GCA member benefit by itself.",
        "",
    ])
    return "\n".join(lines)


def build_operator_digest(
    *,
    daily_summary: Path = DEFAULT_DAILY_SUMMARY,
    member_ops_summary: Path = DEFAULT_MEMBER_OPS_SUMMARY,
    support_queue_summary: Path = DEFAULT_SUPPORT_QUEUE_SUMMARY,
    holding_summary: Path = DEFAULT_HOLDING_SUMMARY,
    digest_output: Path = DEFAULT_DIGEST_OUTPUT,
    json_output: Path = DEFAULT_JSON_OUTPUT,
    generated_at: str | None = None,
) -> dict[str, Any]:
    daily_payload = load_json(daily_summary)
    member_payload = load_json(member_ops_summary)
    support_payload = load_json(support_queue_summary)
    holding_payload = load_json(holding_summary)
    daily = summarize_daily(daily_payload)
    member = summarize_member_ops(member_payload)
    support = summarize_support_queue(support_payload)
    holding = summarize_holding(holding_payload)
    digest = {
        "ok": True,
        "packetVersion": DIGEST_VERSION,
        "generatedAt": generated_at or utc_now(),
        "sourceFiles": {
            "dailyOps": file_status(daily_summary, daily_payload),
            "memberOps": file_status(member_ops_summary, member_payload),
            "supportQueue": file_status(support_queue_summary, support_payload),
            "holdingPeriod": file_status(holding_summary, holding_payload),
        },
        "dailyOps": daily,
        "memberOps": member,
        "supportQueue": support,
        "holdingPeriod": holding,
        "nextActions": build_next_actions(daily, member, support, holding),
        "outputs": {
            "markdown": str(digest_output),
            "json": str(json_output),
        },
        "boundaries": {
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
            "doesNotApproveMemberBenefitByItself": True,
        },
    }
    markdown = render_markdown(digest)
    digest_output.parent.mkdir(parents=True, exist_ok=True)
    digest_output.write_text(markdown, encoding="utf-8")
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(digest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return digest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a redacted local GCA operator digest from summary JSON files.")
    parser.add_argument("--daily-summary", type=Path, default=DEFAULT_DAILY_SUMMARY, help="Daily ops summary JSON path.")
    parser.add_argument("--member-ops-summary", type=Path, default=DEFAULT_MEMBER_OPS_SUMMARY, help="Member ops summary JSON path.")
    parser.add_argument("--support-queue-summary", type=Path, default=DEFAULT_SUPPORT_QUEUE_SUMMARY, help="Support queue summary JSON path.")
    parser.add_argument("--holding-summary", type=Path, default=DEFAULT_HOLDING_SUMMARY, help="Holding-period summary JSON path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_DIGEST_OUTPUT, help="Markdown digest output path.")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT, help="JSON digest output path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        digest = build_operator_digest(
            daily_summary=args.daily_summary,
            member_ops_summary=args.member_ops_summary,
            support_queue_summary=args.support_queue_summary,
            holding_summary=args.holding_summary,
            digest_output=args.output,
            json_output=args.json_output,
        )
    except DigestError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(digest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
