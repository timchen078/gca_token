import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_gca_member_access_report import member_access_export_payload
from tools.build_gca_member_support_queue import build_queue_rows, build_support_queue


ROOT = Path(__file__).resolve().parents[1]


def support_payload_with_account(*, account_overrides=None, wallet=None, credit=None, member=None):
    account = {
        "accountId": "gca_account_1",
        "status": "active",
        "email": "user@example.com",
        "emailSha256": "0" * 64,
        "displayName": "User",
        "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
    }
    if account_overrides:
        account.update(account_overrides)
    return {
        "ok": True,
        "packetVersion": "gca_cloudflare_member_access_export_v1",
        "exportedAt": "2026-05-20T15:00:00Z",
        "redactedForExternalSharing": False,
        "datasets": {
            "member-access": {"records": [account]},
            "wallet-verifications": {"records": [wallet] if wallet else []},
            "credit-ledger": {"records": [credit] if credit else []},
            "member-ledger": {"records": [member] if member else []},
        },
    }


class GcaMemberSupportQueueTests(unittest.TestCase):
    def test_build_queue_classifies_active_member_manual_benefit_review(self):
        payload = member_access_export_payload()
        rows = build_queue_rows(payload)
        statuses = {row["supportStatus"] for row in rows}
        self.assertIn("gca_member_active_manual_benefit_review", statuses)
        row = next(item for item in rows if item["supportStatus"] == "gca_member_active_manual_benefit_review")
        self.assertEqual(row["replyReady"], "true")
        self.assertIn("manual benefit review", row["subject"])
        self.assertIn("not automatic", row["body"])
        self.assertIn("do not promise timing", row["nextStep"])

    def test_build_queue_classifies_below_threshold_wallet(self):
        payload = support_payload_with_account(
            wallet={
                "accountId": "gca_account_1",
                "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
                "gcaBalance": "9000",
                "holderBonusEligible": False,
                "gcaMemberEligible": False,
                "status": "below_threshold",
            },
        )
        rows = build_queue_rows(payload)
        self.assertEqual(rows[0]["supportStatus"], "below_10000_gca_threshold")
        self.assertIn("below the 10,000 GCA", rows[0]["body"])

    def test_build_queue_handles_redacted_email_as_not_reply_ready(self):
        payload = support_payload_with_account(account_overrides={"email": "", "displayName": ""})
        rows = build_queue_rows(payload)
        self.assertEqual(rows[0]["replyReady"], "false")
        self.assertEqual(rows[0]["supportStatus"], "wallet_verification_pending")

    def test_build_support_queue_writes_csv_and_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "support.csv"
            summary_output = root / "support-summary.json"
            summary = build_support_queue(member_access_export_payload(), output, summary_output)

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["rows"], 1)
            self.assertEqual(summary["replyReadyRows"], 1)
            self.assertFalse(summary["boundaries"]["writesProductionData"])
            self.assertFalse(summary["boundaries"]["automaticTokenTransfer"])
            self.assertTrue(summary["boundaries"]["operatorReviewRequiredBeforeSending"])
            self.assertTrue(output.exists())
            self.assertTrue(summary_output.exists())
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["email"], "user@example.com")
            self.assertIn("GCA Member status active", rows[0]["subject"])

    def test_cli_builds_support_queue_from_export_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path = root / "export.json"
            output = root / "support.csv"
            summary_output = root / "support-summary.json"
            input_path.write_text(json.dumps(member_access_export_payload()), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/build_gca_member_support_queue.py",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output),
                    "--summary-output",
                    str(summary_output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertTrue(output.exists())
            self.assertTrue(summary_output.exists())


if __name__ == "__main__":
    unittest.main()
