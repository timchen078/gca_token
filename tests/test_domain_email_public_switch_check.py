import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_domain_email_public_switch import (
    DEFAULT_CURRENT_EMAIL,
    DEFAULT_TARGET_EMAIL,
    build_report,
    render_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_domain_email_public_switch.py"


def write_fixture(root: Path, files: dict[str, str]) -> Path:
    site = root / "site"
    site.mkdir(parents=True, exist_ok=True)
    config = {
        "currentPublicEmail": DEFAULT_CURRENT_EMAIL,
        "targetDomainEmail": DEFAULT_TARGET_EMAIL,
        "filesToUpdateAfterActivation": sorted(files),
    }
    config_path = site / "domain-email.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return config_path


class DomainEmailPublicSwitchCheckTests(unittest.TestCase):
    def test_current_repo_reports_public_switch_pending(self):
        report = build_report()

        self.assertEqual(report["schema"], "gca-domain-email-public-switch-check-v1")
        self.assertEqual(report["currentEmail"], "GCAgochina@outlook.com")
        self.assertEqual(report["targetDomainEmail"], "support@gcagochina.com")
        self.assertEqual(report["status"], "public-email-switch-complete")
        self.assertTrue(report["readyForBaseScanPublicEmailAlignment"])
        self.assertEqual(report["blockedRequirements"], [])
        self.assertEqual(report["summary"]["filesStillUsingCurrentEmail"], 0)
        self.assertFalse(report["boundaries"]["writesPublicFiles"])
        self.assertFalse(report["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(report["boundaries"]["touchesWalletsOrContracts"])

    def test_ready_fixture_passes_when_all_critical_files_use_target_email(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = write_fixture(
                root,
                {
                    "site/support.html": f"Contact {DEFAULT_TARGET_EMAIL}",
                    "site/project.json": f'{{"email":"{DEFAULT_TARGET_EMAIL}"}}',
                    "launch/basescan_resubmission_values.json": f'{{"officialEmail":"{DEFAULT_TARGET_EMAIL}"}}',
                },
            )

            report = build_report(root=root, config_path=config_path)

        self.assertEqual(report["status"], "public-email-switch-complete")
        self.assertTrue(report["readyForBaseScanPublicEmailAlignment"])
        self.assertEqual(report["blockedRequirements"], [])
        self.assertEqual(report["summary"]["filesStillUsingCurrentEmail"], 0)
        self.assertEqual(report["summary"]["targetEmailOccurrences"], 3)

    def test_missing_and_targetless_critical_files_block_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / "site"
            site.mkdir(parents=True, exist_ok=True)
            config_path = site / "domain-email.json"
            config_path.write_text(
                json.dumps(
                    {
                        "currentPublicEmail": DEFAULT_CURRENT_EMAIL,
                        "targetDomainEmail": DEFAULT_TARGET_EMAIL,
                        "filesToUpdateAfterActivation": ["site/support.html", "site/project.json"],
                    }
                ),
                encoding="utf-8",
            )
            (site / "support.html").write_text("Contact page without the target address", encoding="utf-8")

            report = build_report(root=root, config_path=config_path)

        self.assertEqual(report["status"], "missing-critical-files")
        self.assertFalse(report["readyForBaseScanPublicEmailAlignment"])
        self.assertIn("missing-critical-files", report["blockedRequirements"])
        self.assertIn("target-domain-email-missing", report["blockedRequirements"])

    def test_markdown_is_copyable_and_explicit(self):
        report = build_report()
        markdown = render_markdown(report)

        self.assertIn("# GCA Domain Email Public Switch Check", markdown)
        self.assertIn("Ready for BaseScan public email alignment: `true`", markdown)
        self.assertIn("Critical File Records", markdown)
        self.assertIn("site/support.html", markdown)
        self.assertIn("This check is read-only.", markdown)
        self.assertIn("does not edit files, send email, write DNS, submit BaseScan requests, or touch wallets/contracts", markdown)

    def test_cli_require_switched_blocks_until_public_files_are_aligned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = write_fixture(root, {"site/support.html": f"Contact {DEFAULT_CURRENT_EMAIL}"})
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--root",
                    str(root),
                    "--config",
                    str(config_path),
                    "--json",
                    "--require-switched",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "public-email-switch-pending")


if __name__ == "__main__":
    unittest.main()
