import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

from tools.build_domain_email_switch_plan import (
    CURRENT_EMAIL,
    TARGET_EMAIL,
    build_patch_preview,
    build_plan,
    render_markdown,
    render_patch_preview,
)


ROOT = Path(__file__).resolve().parents[1]


class DomainEmailSwitchPlanTests(unittest.TestCase):
    def test_plan_finds_public_files_and_keeps_boundaries(self):
        plan = build_plan()

        self.assertEqual(plan["schema"], "gca-domain-email-switch-plan-v1")
        self.assertEqual(plan["currentEmail"], CURRENT_EMAIL)
        self.assertEqual(plan["targetDomainEmail"], TARGET_EMAIL)
        self.assertEqual(plan["status"], "blocked-until-domain-email-evidence-ready")
        self.assertGreater(plan["summary"]["filesRequiringSwitchAfterActivation"], 10)
        self.assertIn("public page", plan["summary"]["categories"])
        self.assertIn("public structured data", plan["summary"]["categories"])
        self.assertIn("owner launch package", plan["summary"]["categories"])
        self.assertEqual(plan["patchPreview"]["command"], "python3 tools/build_domain_email_switch_plan.py --patch")
        self.assertIn("launch/domain_email_switch_preview.patch", plan["patchPreview"]["ownerArtifactCommand"])
        self.assertGreater(plan["patchPreview"]["replacementOccurrences"], 10)
        self.assertFalse(plan["patchPreview"]["appliesChanges"])
        self.assertIn(
            "launch/domain_email_evidence_packet.json reports readyForBaseScanResubmission true",
            plan["requiredPreconditions"],
        )
        self.assertIn(
            "tools/check_basescan_resubmission_readiness.py reports readyForBaseScanResubmission true",
            plan["requiredPreconditions"],
        )
        self.assertFalse(plan["boundaries"]["writesPublicFiles"])
        self.assertFalse(plan["boundaries"]["sendsEmail"])
        self.assertFalse(plan["boundaries"]["writesDns"])
        self.assertFalse(plan["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(plan["boundaries"]["touchesWalletsOrContracts"])

        records = {record["path"]: record for record in plan["records"]}
        self.assertIn("site/support.html", records)
        self.assertTrue(records["site/support.html"]["switchRequiredAfterActivation"])
        self.assertIn("site/domain-email.html", records)
        self.assertGreater(records["site/domain-email.html"]["targetEmailOccurrences"], 0)
        self.assertIn("launch/basescan_resubmission_package.md", records)
        self.assertIn("tools/gca_member_backend.py", records)

    def test_markdown_is_copyable_and_output_is_explicit(self):
        plan = build_plan()
        markdown = render_markdown(plan)

        self.assertIn("# GCA Domain Email Public Switch Plan", markdown)
        self.assertIn("Current email: `GCAgochina@outlook.com`", markdown)
        self.assertIn("Target domain email: `support@gcagochina.com`", markdown)
        self.assertIn("## Required Preconditions", markdown)
        self.assertIn("## Patch Preview", markdown)
        self.assertIn("tools/build_domain_email_switch_plan.py --patch", markdown)
        self.assertIn("launch/domain_email_switch_preview.patch", markdown)
        self.assertIn("## File Records", markdown)
        self.assertIn("This plan does not change public files by itself.", markdown)
        self.assertIn("patch preview is a generated diff only", markdown)
        self.assertIn("does not send email, write DNS, submit BaseScan requests, or touch wallets/contracts", markdown)

    def test_patch_preview_is_unified_diff_and_does_not_write_public_files(self):
        plan = build_plan()
        preview = build_patch_preview(plan)
        patch = render_patch_preview(plan)

        self.assertEqual(preview["schema"], "gca-domain-email-switch-patch-preview-v1")
        self.assertEqual(preview["status"], "preview-only-not-applied")
        self.assertGreater(preview["summary"]["filesWithExactReplacement"], 10)
        self.assertGreater(preview["summary"]["replacementOccurrences"], 10)
        self.assertIn("--- a/site/support.html", patch)
        self.assertIn("+++ b/site/support.html", patch)
        self.assertIn(CURRENT_EMAIL, patch)
        self.assertIn(TARGET_EMAIL, patch)
        self.assertFalse(preview["boundaries"]["writesPublicFiles"])
        self.assertFalse(preview["boundaries"]["submitsBaseScanRequest"])

    def test_output_files_are_optional_owner_artifacts(self):
        import tools.build_domain_email_switch_plan as module

        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = Path(temp_dir) / "switch-plan.json"
            md_path = Path(temp_dir) / "switch-plan.md"
            patch_path = Path(temp_dir) / "switch-preview.patch"
            plan = module.build_plan()
            json_path.write_text(module.json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            md_path.write_text(module.render_markdown(plan), encoding="utf-8")
            patch_path.write_text(module.render_patch_preview(plan), encoding="utf-8")

            self.assertIn("gca-domain-email-switch-plan-v1", json_path.read_text())
            self.assertIn("GCA Domain Email Public Switch Plan", md_path.read_text())
            self.assertIn("--- a/site/support.html", patch_path.read_text())

    def test_cli_can_print_patch_preview(self):
        completed = subprocess.run(
            [sys.executable, "tools/build_domain_email_switch_plan.py", "--patch"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--- a/site/support.html", completed.stdout)
        self.assertIn("+++ b/site/support.html", completed.stdout)
        self.assertIn(TARGET_EMAIL, completed.stdout)


if __name__ == "__main__":
    unittest.main()
