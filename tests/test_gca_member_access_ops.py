import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from tests.test_gca_member_access_report import member_access_export_payload
from tools.run_gca_member_access_ops import run_member_access_ops


ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class GcaMemberAccessOpsTests(unittest.TestCase):
    def test_pipeline_fetches_export_and_builds_reports_without_printing_secrets(self):
        seen = []

        def opener(request, timeout):
            seen.append({
                "path": urlparse(request.full_url).path,
                "authorization": request.headers["Authorization"],
                "timeout": timeout,
            })
            return FakeResponse({
                "ok": True,
                "count": 1,
                "records": [{
                    "email": "private-user@example.com",
                    "displayName": "Private User",
                    "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
                    "status": "active",
                }],
            })

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary = run_member_access_ops(
                base_url="https://worker.example",
                token="secret-token",
                limit=1,
                timeout=7,
                export_output=root / "export.json",
                report_dir=root / "report",
                report_summary_output=root / "report-summary.json",
                support_queue_output=root / "support.csv",
                support_queue_summary_output=root / "support-summary.json",
                pipeline_summary_output=root / "ops-summary.json",
                opener=opener,
            )

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["export"]["datasetCount"], 4)
            self.assertEqual(summary["export"]["recordCount"], 4)
            self.assertTrue((root / "export.json").exists())
            self.assertTrue((root / "report" / "gca_member_accounts.csv").exists())
            self.assertTrue((root / "support.csv").exists())
            self.assertTrue((root / "support-summary.json").exists())
            self.assertTrue((root / "ops-summary.json").exists())
            self.assertIn("supportQueue", summary)
            self.assertEqual(summary["supportQueue"]["rows"], 1)
            self.assertEqual(
                {item["path"] for item in seen},
                {"/gca/member-access", "/gca/wallet-verifications", "/gca/credit-ledger", "/gca/member-ledger"},
            )
            self.assertTrue(all(item["authorization"] == "Bearer secret-token" for item in seen))
            self.assertTrue(all(item["timeout"] == 7 for item in seen))
            serialized = json.dumps(summary)
            self.assertNotIn("secret-token", serialized)
            self.assertNotIn("private-user@example.com", serialized)
            self.assertFalse(summary["boundaries"]["writesProductionData"])
            self.assertFalse(summary["boundaries"]["automaticTokenTransfer"])
            self.assertFalse(summary["holdingReportIncluded"])
            self.assertFalse(summary["boundaries"]["walletCalls"])

    def test_pipeline_can_use_existing_export_file_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path = root / "input-export.json"
            input_path.write_text(json.dumps(member_access_export_payload()), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/run_gca_member_access_ops.py",
                    "--input",
                    str(input_path),
                    "--export-output",
                    str(root / "export-copy.json"),
                    "--report-dir",
                    str(root / "report"),
                    "--report-summary-output",
                    str(root / "report-summary.json"),
                    "--support-queue-output",
                    str(root / "support.csv"),
                    "--support-queue-summary-output",
                    str(root / "support-summary.json"),
                    "--summary-output",
                    str(root / "ops-summary.json"),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["source"], f"input-file:{input_path}")
            self.assertEqual(result["report"]["memberBenefitReviewQueueRows"], 2)
            self.assertEqual(result["supportQueue"]["rows"], 1)
            self.assertTrue((root / "export-copy.json").exists())
            self.assertTrue((root / "report" / "gca_member_benefit_review_queue.csv").exists())
            self.assertTrue((root / "support.csv").exists())
            self.assertTrue((root / "support-summary.json").exists())
            self.assertTrue((root / "ops-summary.json").exists())

    def test_pipeline_can_include_holding_report_without_live_reads(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary = run_member_access_ops(
                export_payload=member_access_export_payload(),
                export_output=root / "export-copy.json",
                report_dir=root / "report",
                report_summary_output=root / "report-summary.json",
                support_queue_output=root / "support.csv",
                support_queue_summary_output=root / "support-summary.json",
                include_holding_report=True,
                holding_live_read=False,
                holding_snapshot_output=root / "holding-snapshots.jsonl",
                holding_report_output=root / "holding.csv",
                holding_summary_output=root / "holding-summary.json",
                pipeline_summary_output=root / "ops-summary.json",
            )

            self.assertTrue(summary["ok"])
            self.assertTrue(summary["holdingReportIncluded"])
            self.assertEqual(summary["holdingPeriod"]["candidateWallets"], 2)
            self.assertEqual(summary["holdingPeriod"]["walletsSkippedNoLiveRead"], 2)
            self.assertEqual(summary["holdingPeriodLaneCounts"]["needs_first_snapshot"], 2)
            self.assertFalse(summary["boundaries"]["walletCalls"])
            self.assertFalse(summary["boundaries"]["requiresSignature"])
            self.assertFalse(summary["boundaries"]["automaticTokenTransfer"])
            self.assertTrue((root / "holding.csv").exists())
            self.assertTrue((root / "holding-summary.json").exists())


if __name__ == "__main__":
    unittest.main()
