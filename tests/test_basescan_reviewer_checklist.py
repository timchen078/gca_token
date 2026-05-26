import tempfile
import unittest
from pathlib import Path

import tools.build_basescan_reviewer_checklist as module


class BaseScanReviewerChecklistTests(unittest.TestCase):
    def test_checklist_maps_return_reasons_to_evidence_and_blocks_email(self):
        report = module.build_checklist()

        self.assertEqual(report["schema"], "gca-basescan-reviewer-checklist-v1")
        self.assertEqual(report["status"], "blocked-before-basescan-resubmission")
        self.assertFalse(report["readyForCleanResubmission"])
        self.assertEqual(report["latestReturnNoticeDate"], "2026-05-23")
        self.assertEqual(report["targetDomainEmail"], "support@gcagochina.com")
        self.assertIn("sender-domain-email", report["blockedItems"])

        items = {item["key"]: item for item in report["checklist"]}
        self.assertEqual(items["website-accessible"]["status"], "implemented")
        self.assertEqual(items["clear-project-information"]["status"], "implemented")
        self.assertEqual(items["placeholder-and-link-review"]["status"], "implemented-with-automated-check")
        self.assertEqual(items["founder-team-transparency"]["status"], "implemented-official-domain-equivalent")
        self.assertEqual(items["sender-domain-email"]["status"], "blocked-owner-action-required")
        self.assertEqual(items["source-and-contract"]["status"], "implemented")
        self.assertEqual(items["brand-logo-whitepaper"]["status"], "implemented")
        self.assertEqual(items["social-and-market-links"]["status"], "implemented")
        self.assertIn("https://gcagochina.com/tim-chen.html", items["founder-team-transparency"]["links"])
        self.assertIn("https://gcagochina.com/domain-email.html#worksheetTitle", items["sender-domain-email"]["links"])
        self.assertIn("https://gcagochina.com/assets/gca-logo.svg", items["brand-logo-whitepaper"]["links"])
        self.assertIn("https://www.geckoterminal.com/base/pools/", " ".join(items["social-and-market-links"]["links"]))

        self.assertIn("python3 tools/check_basescan_resubmission_readiness.py --json --require-ready", report["preflightCommands"])
        self.assertFalse(report["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(report["boundaries"]["sendsEmail"])
        self.assertFalse(report["boundaries"]["writesDns"])
        self.assertFalse(report["boundaries"]["signsWalletMessage"])
        self.assertFalse(report["boundaries"]["touchesWalletsOrContracts"])

    def test_markdown_and_optional_outputs_are_copyable(self):
        report = module.build_checklist()
        markdown = module.render_markdown(report)
        self.assertIn("# GCA BaseScan Reviewer Checklist", markdown)
        self.assertIn("Ready for clean resubmission: `false`", markdown)
        self.assertIn("Sender email matches project domain", markdown)
        self.assertIn("does not submit BaseScan requests", markdown)

        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = Path(temp_dir) / "basescan-checklist.json"
            md_path = Path(temp_dir) / "basescan-checklist.md"
            json_path.write_text(module.json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            md_path.write_text(markdown, encoding="utf-8")
            self.assertIn("gca-basescan-reviewer-checklist-v1", json_path.read_text())
            self.assertIn("GCA BaseScan Reviewer Checklist", md_path.read_text())


if __name__ == "__main__":
    unittest.main()
