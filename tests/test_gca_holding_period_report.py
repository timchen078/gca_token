import csv
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from tests.test_gca_member_access_report import member_access_export_payload
from tools.build_gca_holding_period_report import build_holding_period_report, build_snapshot
from tools.gca_member_backend import MEMBER_THRESHOLD_UNITS


ROOT = Path(__file__).resolve().parents[1]
WALLET_ONE = "0x18d0007bc6be029f8ccd7cb13e324aa21891092d"
WALLET_TWO = "0x28d0007bc6be029f8ccd7cb13e324aa21891092d"


class FakeBalanceReader:
    def __init__(self, balances):
        self.balances = {key.lower(): value for key, value in balances.items()}
        self.calls = []

    def get_balance_units(self, wallet):
        self.calls.append(wallet)
        return self.balances.get(wallet.lower(), 0)


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")


class GcaHoldingPeriodReportTests(unittest.TestCase):
    def test_build_report_records_snapshot_and_finds_30_day_streak(self):
        now = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
        first_day = date(2026, 4, 21)
        prior_snapshots = [
            build_snapshot(
                WALLET_ONE,
                MEMBER_THRESHOLD_UNITS,
                datetime.combine(first_day + timedelta(days=offset), datetime.min.time(), tzinfo=UTC),
            )
            for offset in range(29)
        ]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot_output = root / "snapshots.jsonl"
            report_output = root / "holding.csv"
            summary_output = root / "summary.json"
            write_jsonl(snapshot_output, prior_snapshots)
            reader = FakeBalanceReader({
                WALLET_ONE: MEMBER_THRESHOLD_UNITS,
                WALLET_TWO: MEMBER_THRESHOLD_UNITS - 1,
            })

            summary = build_holding_period_report(
                export_payload=member_access_export_payload(),
                snapshot_output=snapshot_output,
                report_output=report_output,
                summary_output=summary_output,
                balance_reader=reader,
                now=now,
            )

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["counts"]["candidateWallets"], 2)
            self.assertEqual(summary["counts"]["walletsChecked"], 2)
            self.assertEqual(summary["counts"]["snapshotsAdded"], 2)
            self.assertEqual(summary["counts"]["observedEligibleFor30Days"], 1)
            self.assertEqual(summary["laneCounts"]["observed_30_day_holding_ready_for_support_review"], 1)
            self.assertEqual(summary["laneCounts"]["below_member_threshold"], 1)
            self.assertFalse(summary["boundaries"]["writesProductionData"])
            self.assertFalse(summary["boundaries"]["requiresSignature"])
            self.assertFalse(summary["boundaries"]["automaticTokenTransfer"])
            self.assertFalse(summary["boundaries"]["userEmailsPrinted"])

            with report_output.open(newline="", encoding="utf-8") as handle:
                rows = {row["walletAddress"]: row for row in csv.DictReader(handle)}
            self.assertEqual(rows[WALLET_ONE.lower()]["observedQualifiedStreakDays"], "30")
            self.assertEqual(rows[WALLET_ONE.lower()]["observedEligibleFor30Days"], "true")
            self.assertEqual(
                rows[WALLET_ONE.lower()]["recommendedLane"],
                "observed_30_day_holding_ready_for_support_review",
            )
            self.assertEqual(rows[WALLET_TWO.lower()]["recommendedLane"], "below_member_threshold")
            self.assertNotIn("user@example.com", report_output.read_text(encoding="utf-8"))
            self.assertEqual(len(snapshot_output.read_text(encoding="utf-8").splitlines()), 31)
            self.assertEqual({wallet.lower() for wallet in reader.calls}, {WALLET_ONE.lower(), WALLET_TWO.lower()})

    def test_same_day_snapshot_is_reused_without_extra_rpc_read(self):
        now = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
        snapshots = [
            build_snapshot(WALLET_ONE, MEMBER_THRESHOLD_UNITS, now),
            build_snapshot(WALLET_TWO, MEMBER_THRESHOLD_UNITS, now),
        ]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot_output = root / "snapshots.jsonl"
            write_jsonl(snapshot_output, snapshots)
            reader = FakeBalanceReader({WALLET_ONE: 0, WALLET_TWO: 0})

            summary = build_holding_period_report(
                export_payload=member_access_export_payload(),
                snapshot_output=snapshot_output,
                report_output=root / "holding.csv",
                summary_output=root / "summary.json",
                balance_reader=reader,
                now=now,
            )

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["counts"]["walletsChecked"], 0)
            self.assertEqual(summary["counts"]["sameDaySnapshotsReused"], 2)
            self.assertEqual(reader.calls, [])

    def test_cli_can_build_offline_report_from_existing_snapshots(self):
        now = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path = root / "export.json"
            snapshot_output = root / "snapshots.jsonl"
            report_output = root / "holding.csv"
            summary_output = root / "summary.json"
            input_path.write_text(json.dumps(member_access_export_payload()), encoding="utf-8")
            write_jsonl(snapshot_output, [build_snapshot(WALLET_ONE, MEMBER_THRESHOLD_UNITS, now)])

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/build_gca_holding_period_report.py",
                    "--input",
                    str(input_path),
                    "--snapshot-output",
                    str(snapshot_output),
                    "--report-output",
                    str(report_output),
                    "--summary-output",
                    str(summary_output),
                    "--no-live-read",
                    "--now",
                    now.isoformat().replace("+00:00", "Z"),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["counts"]["walletsSkippedNoLiveRead"], 1)
            self.assertTrue(report_output.exists())
            self.assertTrue(summary_output.exists())


if __name__ == "__main__":
    unittest.main()
