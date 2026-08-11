import json
import tempfile
import unittest
from pathlib import Path

from tools.sync_basescan_final_package_references import (
    FinalPackageReferenceSyncError,
    canonical_reference,
    synchronize_references,
)


OLD_TIMESTAMP = "2026-08-10T15:51:53Z"
NEW_TIMESTAMP = "2026-08-12T02:00:00Z"
DAILY_TIMESTAMP = "2026-08-11T17:22:15Z"


class BaseScanFinalPackageReferenceSyncTests(unittest.TestCase):
    def write_fixture(self, root: Path) -> tuple[Path, Path]:
        launch = root / "launch"
        launch.mkdir(parents=True, exist_ok=True)
        package_path = launch / "basescan_final_submission_package.json"
        values_path = launch / "basescan_resubmission_values.json"
        package_path.write_text(
            json.dumps({
                "schema": "gca-basescan-submission-package-v1",
                "generatedAt": NEW_TIMESTAMP,
                "status": "ready-for-owner-submission",
                "readyForOwnerSubmission": True,
                "copyPasteBlocks": {"baseScanReviewerComment": "ready"},
                "preflightSummary": {"status": "ready-for-owner-resubmission"},
                "dailyStatusReferenceGuard": {
                    "status": "aligned",
                    "aligned": True,
                    "canonicalReference": {
                        "dailyStatusGeneratedAt": DAILY_TIMESTAMP,
                    },
                },
            }),
            encoding="utf-8",
        )
        values_path.write_text(
            json.dumps({
                "baseScanFinalSubmissionPackageGeneratedAt": OLD_TIMESTAMP,
            }),
            encoding="utf-8",
        )
        return package_path, values_path

    def test_sync_updates_json_text_and_handoff_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package_path, values_path = self.write_fixture(root)
            site = root / "site"
            site.mkdir(parents=True, exist_ok=True)
            handoff_path = site / "basescan-handoff.json"
            preflight_path = site / "basescan-preflight.json"
            html_path = site / "status.html"
            handoff_path.write_text(
                json.dumps({
                    "finalSubmissionPackage": {
                        "generatedAt": OLD_TIMESTAMP,
                        "copyPasteContent": {},
                    },
                }),
                encoding="utf-8",
            )
            preflight_path.write_text(
                json.dumps({
                    "preflightRefresh": {
                        "refreshedAt": "2026-08-10",
                        "finalSubmissionPackageGeneratedAt": OLD_TIMESTAMP,
                    },
                }),
                encoding="utf-8",
            )
            html_path.write_text(
                f"Final package refreshed {OLD_TIMESTAMP.split('T', 1)[0]}; generated {OLD_TIMESTAMP}",
                encoding="utf-8",
            )

            report = synchronize_references(
                root=root,
                package_path=package_path,
                values_path=values_path,
                target_files=[
                    "launch/basescan_final_submission_package.json",
                    "launch/basescan_resubmission_values.json",
                    "site/basescan-handoff.json",
                    "site/basescan-preflight.json",
                    "site/status.html",
                ],
            )

            values = json.loads(values_path.read_text(encoding="utf-8"))
            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
            html = html_path.read_text(encoding="utf-8")

        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "updated")
        self.assertEqual(values["baseScanFinalSubmissionPackageGeneratedAt"], NEW_TIMESTAMP)
        self.assertEqual(
            handoff["finalSubmissionPackage"]["dailyStatusReferenceGuard"]["status"],
            "aligned",
        )
        self.assertEqual(
            handoff["finalSubmissionPackage"]["copyPasteContent"]["baseScanReviewerComment"],
            "ready",
        )
        self.assertEqual(handoff["lastUpdated"], "2026-08-12")
        self.assertEqual(
            handoff["finalSubmissionPackage"]["referenceSynchronization"]["status"],
            "aligned-after-canonical-build",
        )
        self.assertEqual(preflight["preflightRefresh"]["refreshedAt"], "2026-08-12")
        self.assertEqual(
            preflight["preflightRefresh"]["finalPackageReferenceAlignment"]["status"],
            "aligned-after-canonical-build",
        )
        self.assertIn(NEW_TIMESTAMP, html)
        self.assertIn("Final package refreshed 2026-08-12", html)

    def test_check_mode_reports_drift_without_writing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package_path, values_path = self.write_fixture(root)
            artifact = root / "artifact.md"
            artifact.write_text(f"Final package: {OLD_TIMESTAMP}", encoding="utf-8")

            report = synchronize_references(
                root=root,
                package_path=package_path,
                values_path=values_path,
                target_files=["artifact.md"],
                write=False,
            )

            current = artifact.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "updated")
        self.assertEqual(report["summary"]["filesChanged"], 1)
        self.assertFalse(report["writeMode"])
        self.assertEqual(current, f"Final package: {OLD_TIMESTAMP}")

    def test_missing_target_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package_path, values_path = self.write_fixture(root)
            report = synchronize_references(
                root=root,
                package_path=package_path,
                values_path=values_path,
                target_files=["missing.md"],
            )

        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "missing-target-files")

    def test_failed_write_preflight_does_not_partially_update_valid_targets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package_path, values_path = self.write_fixture(root)
            artifact = root / "artifact.md"
            artifact.write_text(f"Final package: {OLD_TIMESTAMP}", encoding="utf-8")

            report = synchronize_references(
                root=root,
                package_path=package_path,
                values_path=values_path,
                target_files=["artifact.md", "missing.md"],
            )

            current = artifact.read_text(encoding="utf-8")

        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "missing-target-files")
        self.assertEqual(current, f"Final package: {OLD_TIMESTAMP}")

    def test_missing_canonical_reference_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package_path, values_path = self.write_fixture(root)
            artifact = root / "artifact.md"
            artifact.write_text("No package timestamp here.", encoding="utf-8")
            report = synchronize_references(
                root=root,
                package_path=package_path,
                values_path=values_path,
                target_files=["artifact.md"],
            )

        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "missing-canonical-references")

    def test_unready_or_unguarded_package_is_rejected(self):
        with self.assertRaises(FinalPackageReferenceSyncError):
            canonical_reference({
                "schema": "gca-basescan-submission-package-v1",
                "generatedAt": NEW_TIMESTAMP,
                "readyForOwnerSubmission": False,
            })

        with self.assertRaises(FinalPackageReferenceSyncError):
            canonical_reference({
                "schema": "gca-basescan-submission-package-v1",
                "generatedAt": NEW_TIMESTAMP,
                "readyForOwnerSubmission": True,
                "dailyStatusReferenceGuard": {"aligned": False},
            })


if __name__ == "__main__":
    unittest.main()
