import json
import tempfile
import unittest
from pathlib import Path

from tools.check_domain_email_snapshot_alignment import (
    SnapshotAlignmentError,
    build_report,
    canonical_snapshot,
    render_markdown,
)


class DomainEmailSnapshotAlignmentTests(unittest.TestCase):
    def write_fixture(self, root: Path, *, checked_at: str = "2026-05-30T08:13:47Z") -> Path:
        site = root / "site"
        site.mkdir(parents=True, exist_ok=True)
        config_path = site / "domain-email.json"
        config_path.write_text(
            json.dumps({
                "liveDnsSnapshot": {
                    "checkedAt": checked_at,
                    "readyForBaseScanEmailEvidence": False,
                    "missingOrBlockedChecks": ["mx", "spf", "dmarc", "dkim"],
                }
            }),
            encoding="utf-8",
        )
        return config_path

    def test_current_repository_snapshot_references_are_aligned(self):
        report = build_report()

        self.assertEqual(report["schema"], "gca-domain-email-snapshot-alignment-v1")
        self.assertEqual(report["canonicalSnapshot"]["checkedAt"], "2026-05-30T16:24:34Z")
        self.assertEqual(report["canonicalSnapshot"]["date"], "2026-05-30")
        self.assertEqual(report["canonicalSnapshot"]["gateSlug"], "blocked-by-dns-snapshot-2026-05-30")
        self.assertTrue(report["canonicalSnapshot"]["readyForBaseScanEmailEvidence"])
        self.assertEqual(report["status"], "aligned")
        self.assertTrue(report["alignedForPublicPlatformPackets"])
        self.assertEqual(report["blockedRequirements"], [])
        self.assertGreaterEqual(report["summary"]["filesChecked"], 20)
        self.assertEqual(report["summary"]["filesWithStaleSnapshotMarkers"], 0)
        self.assertEqual(report["summary"]["filesMissingCurrentSnapshotDate"], 0)
        self.assertEqual(report["summary"]["missingMonitoredFiles"], 0)
        self.assertTrue(report["boundaries"]["readOnly"])
        self.assertFalse(report["boundaries"]["writesPublicFiles"])
        self.assertFalse(report["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(report["boundaries"]["touchesWalletsOrContracts"])

    def test_stale_snapshot_marker_blocks_platform_packet_reuse(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self.write_fixture(root)
            artifact = root / "site" / "domain-email.html"
            artifact.write_text("Latest 2026-05-27 DNS snapshot: MX/SPF/DMARC missing.", encoding="utf-8")

            report = build_report(
                root=root,
                config_path=config_path,
                monitored_files=["site/domain-email.html"],
            )

        self.assertEqual(report["status"], "stale-dns-snapshot-markers")
        self.assertFalse(report["alignedForPublicPlatformPackets"])
        self.assertIn("stale-dns-snapshot-markers", report["blockedRequirements"])
        self.assertEqual(report["records"][0]["staleSnapshotMarkerDates"], ["2026-05-27"])
        self.assertIn("replace stale DNS snapshot markers", report["records"][0]["action"])

    def test_missing_current_snapshot_date_blocks_alignment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self.write_fixture(root)
            artifact = root / "site" / "domain-email.html"
            artifact.write_text("Domain email gate is documented, but the date was omitted.", encoding="utf-8")

            report = build_report(
                root=root,
                config_path=config_path,
                monitored_files=["site/domain-email.html"],
            )

        self.assertEqual(report["status"], "missing-current-snapshot-date")
        self.assertFalse(report["alignedForPublicPlatformPackets"])
        self.assertIn("missing-current-snapshot-date", report["blockedRequirements"])
        self.assertIn("add the canonical DNS snapshot date 2026-05-30", report["records"][0]["action"])

    def test_missing_monitored_file_blocks_alignment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self.write_fixture(root)

            report = build_report(
                root=root,
                config_path=config_path,
                monitored_files=["site/missing.html"],
            )

        self.assertEqual(report["status"], "missing-monitored-files")
        self.assertFalse(report["alignedForPublicPlatformPackets"])
        self.assertIn("missing-monitored-files", report["blockedRequirements"])
        self.assertEqual(report["records"][0]["status"], "missing")

    def test_invalid_canonical_snapshot_is_rejected(self):
        with self.assertRaises(SnapshotAlignmentError):
            canonical_snapshot({"liveDnsSnapshot": {"checkedAt": "2026-05-30"}})

    def test_markdown_report_names_boundaries(self):
        report = build_report(monitored_files=["site/domain-email.json"])
        markdown = render_markdown(report)

        self.assertIn("GCA Domain Email Snapshot Alignment", markdown)
        self.assertIn("Canonical snapshot date: `2026-05-30`", markdown)
        self.assertIn("Aligned for public platform packets: `true`", markdown)
        self.assertIn("does not edit files, send email, write DNS, submit BaseScan requests, or touch wallets/contracts", markdown)


if __name__ == "__main__":
    unittest.main()
