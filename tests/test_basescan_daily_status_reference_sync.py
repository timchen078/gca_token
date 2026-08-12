import json
import tempfile
import unittest
from pathlib import Path

from tools.sync_basescan_daily_status_references import (
    DailyStatusReferenceSyncError,
    PUBLIC_SITE_TARGET_FILES,
    canonical_reference,
    parse_args,
    synchronize_references,
)


OLD_TIMESTAMP = "2026-07-23T16:08:40Z"
NEW_TIMESTAMP = "2026-08-11T17:22:15Z"
OLD_DATE = "2026-07-23"
NEW_DATE = "2026-08-11"


class BaseScanDailyStatusReferenceSyncTests(unittest.TestCase):
    def write_fixture(self, root: Path) -> tuple[Path, Path]:
        site = root / "site"
        launch = root / "launch"
        site.mkdir(parents=True, exist_ok=True)
        launch.mkdir(parents=True, exist_ok=True)
        daily_status_path = site / "daily-status.json"
        values_path = launch / "basescan_resubmission_values.json"
        daily_status_path.write_text(
            json.dumps({
                "snapshotGeneratedAt": NEW_TIMESTAMP,
                "baseScanPublicProfile": {"checkedAt": NEW_TIMESTAMP},
            }),
            encoding="utf-8",
        )
        values_path.write_text(
            json.dumps({
                "dailyStatusGeneratedAt": OLD_TIMESTAMP,
                "lastCheckedDate": OLD_DATE,
            }),
            encoding="utf-8",
        )
        return daily_status_path, values_path

    def test_sync_updates_json_and_text_without_changing_historical_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            daily_status_path, values_path = self.write_fixture(root)
            json_path = root / "site" / "packet.json"
            html_path = root / "site" / "packet.html"
            python_path = root / "tools" / "validator.py"
            python_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps({
                    "lastCheckedDate": OLD_DATE,
                    "dailyStatusGeneratedAt": OLD_TIMESTAMP,
                    "evidence": (
                        f"Read-only public BaseScan check on {OLD_DATE}; "
                        f"daily status {OLD_TIMESTAMP}."
                    ),
                    "historicalDeploymentDate": OLD_DATE,
                }),
                encoding="utf-8",
            )
            html_path.write_text(
                f"""<span class="label">Preflight Refresh</span>
<span class="value">{OLD_DATE}</span>
<p>A read-only public-page check on {OLD_DATE} still shows pending.</p>
<p>Daily status {OLD_TIMESTAMP}</p>
<p>Initial migration passed on {OLD_DATE} UTC.</p>""",
                encoding="utf-8",
            )
            python_path.write_text(
                f'EXPECTED_DATE = "{OLD_DATE}"\nEXPECTED_TIMESTAMP = "{OLD_TIMESTAMP}"\n'
                f'HISTORICAL = "passed-{OLD_DATE}"\n',
                encoding="utf-8",
            )

            report = synchronize_references(
                root=root,
                daily_status_path=daily_status_path,
                values_path=values_path,
                target_files=["site/packet.json", "site/packet.html", "tools/validator.py"],
            )

            updated_json = json.loads(json_path.read_text(encoding="utf-8"))
            updated_html = html_path.read_text(encoding="utf-8")
            updated_python = python_path.read_text(encoding="utf-8")

        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "updated")
        self.assertEqual(report["summary"]["filesChanged"], 3)
        self.assertEqual(updated_json["lastCheckedDate"], NEW_DATE)
        self.assertEqual(updated_json["dailyStatusGeneratedAt"], NEW_TIMESTAMP)
        self.assertIn(f"Read-only public BaseScan check on {NEW_DATE}", updated_json["evidence"])
        self.assertEqual(updated_json["historicalDeploymentDate"], OLD_DATE)
        self.assertIn(f'<span class="value">{NEW_DATE}</span>', updated_html)
        self.assertIn(f"public-page check on {NEW_DATE}", updated_html)
        self.assertIn(f"Daily status {NEW_TIMESTAMP}", updated_html)
        self.assertIn(f"Initial migration passed on {OLD_DATE} UTC", updated_html)
        self.assertIn(f'EXPECTED_DATE = "{NEW_DATE}"', updated_python)
        self.assertIn(f'EXPECTED_TIMESTAMP = "{NEW_TIMESTAMP}"', updated_python)
        self.assertIn(f'HISTORICAL = "passed-{OLD_DATE}"', updated_python)

    def test_check_mode_reports_drift_without_writing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            daily_status_path, values_path = self.write_fixture(root)
            artifact = root / "site" / "artifact.html"
            original = f"daily status {OLD_TIMESTAMP}"
            artifact.write_text(original, encoding="utf-8")

            report = synchronize_references(
                root=root,
                daily_status_path=daily_status_path,
                values_path=values_path,
                target_files=["site/artifact.html"],
                write=False,
            )

            current = artifact.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "updated")
        self.assertEqual(report["summary"]["filesChanged"], 1)
        self.assertFalse(report["writeMode"])
        self.assertEqual(current, original)

    def test_missing_target_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            daily_status_path, values_path = self.write_fixture(root)

            report = synchronize_references(
                root=root,
                daily_status_path=daily_status_path,
                values_path=values_path,
                target_files=["site/missing.html"],
            )

        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "missing-target-files")
        self.assertEqual(report["missingFilePaths"], ["site/missing.html"])

    def test_missing_canonical_reference_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            daily_status_path, values_path = self.write_fixture(root)
            artifact = root / "site" / "artifact.html"
            artifact.write_text("BaseScan evidence exists, but the snapshot marker is absent.", encoding="utf-8")

            report = synchronize_references(
                root=root,
                daily_status_path=daily_status_path,
                values_path=values_path,
                target_files=["site/artifact.html"],
            )

        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "missing-canonical-references")
        self.assertEqual(report["missingCanonicalReferencePaths"], ["site/artifact.html"])

    def test_invalid_canonical_timestamp_is_rejected(self):
        with self.assertRaises(DailyStatusReferenceSyncError):
            canonical_reference({
                "snapshotGeneratedAt": "2026-08-11",
                "baseScanPublicProfile": {"checkedAt": NEW_TIMESTAMP},
            })

    def test_site_only_cli_selects_public_targets(self):
        args = parse_args(["--site-only", "--check"])

        self.assertTrue(args.site_only)
        self.assertTrue(args.check)
        self.assertTrue(PUBLIC_SITE_TARGET_FILES)
        self.assertTrue(all(path.startswith("site/") for path in PUBLIC_SITE_TARGET_FILES))


if __name__ == "__main__":
    unittest.main()
