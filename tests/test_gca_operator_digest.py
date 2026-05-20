import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.build_gca_operator_digest import build_operator_digest


ROOT = Path(__file__).resolve().parents[1]


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class GcaOperatorDigestTests(unittest.TestCase):
    def test_build_digest_summarizes_counts_without_user_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            daily = root / "daily.json"
            member_ops = root / "member-ops.json"
            support = root / "support.json"
            holding = root / "holding.json"
            markdown = root / "digest.md"
            json_output = root / "digest.json"
            write_json(daily, {
                "ok": True,
                "packetVersion": "gca_daily_ops_summary_v1",
                "generatedAt": "2026-05-20T16:00:00Z",
                "includeMemberOps": False,
                "includeHoldingReport": False,
                "steps": [
                    {"id": "public-site", "ok": True, "returnCode": 0, "stdoutTail": "private-user@example.com"},
                    {"id": "registration-api-public", "ok": True, "returnCode": 0},
                ],
            })
            write_json(member_ops, {
                "ok": True,
                "packetVersion": "gca_member_access_ops_summary_v1",
                "generatedAt": "2026-05-20T16:01:00Z",
                "source": "cloudflare-admin-api:https://worker.example",
                "export": {"datasetCount": 4, "recordCount": 12},
                "report": {
                    "pendingManualReserveTransfers": 1,
                    "holdingPeriodReviewsNeeded": 2,
                    "privateRecord": "private-user@example.com",
                },
                "supportQueue": {"rows": 3, "replyReadyRows": 2, "statusCounts": {"holding_period_review_needed": 2}},
                "holdingReportIncluded": True,
            })
            write_json(support, {
                "ok": True,
                "packetVersion": "gca_member_support_queue_v1",
                "rows": 3,
                "replyReadyRows": 2,
                "statusCounts": {"holding_period_review_needed": 2, "gca_member_active_manual_benefit_review": 1},
            })
            write_json(holding, {
                "ok": True,
                "packetVersion": "gca_holding_period_report_v1",
                "counts": {
                    "candidateWallets": 4,
                    "observedEligibleFor30Days": 1,
                    "snapshotsAdded": 2,
                },
                "laneCounts": {
                    "observed_30_day_holding_ready_for_support_review": 1,
                    "continue_daily_snapshots": 2,
                },
            })

            digest = build_operator_digest(
                daily_summary=daily,
                member_ops_summary=member_ops,
                support_queue_summary=support,
                holding_summary=holding,
                digest_output=markdown,
                json_output=json_output,
                generated_at="2026-05-20T16:02:00Z",
            )

            self.assertTrue(digest["ok"])
            self.assertEqual(digest["dailyOps"]["steps"][0]["id"], "public-site")
            self.assertNotIn("stdoutTail", digest["dailyOps"]["steps"][0])
            self.assertEqual(digest["memberOps"]["recordCount"], 12)
            self.assertEqual(digest["supportQueue"]["replyReadyRows"], 2)
            self.assertEqual(digest["holdingPeriod"]["counts"]["observedEligibleFor30Days"], 1)
            self.assertTrue(any("support queue" in action for action in digest["nextActions"]))
            self.assertTrue(any("pending manual reserve-transfer" in action for action in digest["nextActions"]))
            self.assertTrue(any("observed 30-day" in action for action in digest["nextActions"]))
            self.assertFalse(digest["boundaries"]["writesProductionData"])
            self.assertFalse(digest["boundaries"]["walletCalls"])
            self.assertFalse(digest["boundaries"]["requiresSignature"])
            self.assertFalse(digest["boundaries"]["automaticTokenTransfer"])
            self.assertTrue(markdown.exists())
            self.assertTrue(json_output.exists())
            serialized = json.dumps(digest) + markdown.read_text(encoding="utf-8") + json_output.read_text(encoding="utf-8")
            self.assertNotIn("private-user@example.com", serialized)

    def test_digest_handles_missing_summaries_with_next_actions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            digest = build_operator_digest(
                daily_summary=root / "missing-daily.json",
                member_ops_summary=root / "missing-member.json",
                support_queue_summary=root / "missing-support.json",
                holding_summary=root / "missing-holding.json",
                digest_output=root / "digest.md",
                json_output=root / "digest.json",
                generated_at="2026-05-20T16:02:00Z",
            )

            self.assertFalse(digest["dailyOps"]["available"])
            self.assertFalse(digest["memberOps"]["available"])
            self.assertFalse(digest["supportQueue"]["available"])
            self.assertFalse(digest["holdingPeriod"]["available"])
            self.assertTrue(any("run_gca_daily_ops.py" in action for action in digest["nextActions"]))
            self.assertTrue(any("ADMIN_READ_TOKEN" in action for action in digest["nextActions"]))

    def test_cli_writes_digest_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            daily = root / "daily.json"
            output = root / "digest.md"
            json_output = root / "digest.json"
            write_json(daily, {
                "ok": False,
                "packetVersion": "gca_daily_ops_summary_v1",
                "steps": [{"id": "public-site", "ok": False, "returnCode": 1}],
            })

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/build_gca_operator_digest.py",
                    "--daily-summary",
                    str(daily),
                    "--member-ops-summary",
                    str(root / "missing-member.json"),
                    "--support-queue-summary",
                    str(root / "missing-support.json"),
                    "--holding-summary",
                    str(root / "missing-holding.json"),
                    "--output",
                    str(output),
                    "--json-output",
                    str(json_output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertTrue(any("public daily ops failure" in action for action in result["nextActions"]))
            self.assertTrue(output.exists())
            self.assertTrue(json_output.exists())


if __name__ == "__main__":
    unittest.main()
