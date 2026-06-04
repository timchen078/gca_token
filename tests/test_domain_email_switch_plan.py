import json
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
        self.assertEqual(plan["currentEmail"], TARGET_EMAIL)
        self.assertEqual(plan["legacyEmail"], CURRENT_EMAIL)
        self.assertEqual(plan["targetDomainEmail"], TARGET_EMAIL)
        self.assertEqual(plan["status"], "public-email-switch-complete")
        self.assertEqual(plan["summary"]["filesRequiringSwitchAfterActivation"], 0)
        self.assertIn("public page", plan["summary"]["categories"])
        self.assertIn("public structured data", plan["summary"]["categories"])
        self.assertIn("owner launch package", plan["summary"]["categories"])
        self.assertEqual(plan["patchPreview"]["command"], "python3 tools/build_domain_email_switch_plan.py --patch")
        self.assertIn("launch/domain_email_switch_preview.patch", plan["patchPreview"]["ownerArtifactCommand"])
        self.assertEqual(plan["patchPreview"]["replacementOccurrences"], 0)
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
        self.assertFalse(records["site/support.html"]["switchRequiredAfterActivation"])
        self.assertIn("site/domain-email.html", records)
        self.assertGreater(records["site/domain-email.html"]["targetEmailOccurrences"], 0)
        self.assertIn("launch/basescan_resubmission_package.md", records)
        self.assertIn("tools/gca_member_backend.py", records)
        self.assertFalse(any(path.startswith("launch/domain_email_evidence/") for path in records))

    def test_markdown_is_copyable_and_output_is_explicit(self):
        plan = build_plan()
        markdown = render_markdown(plan)

        self.assertIn("# GCA Domain Email Public Switch Plan", markdown)
        self.assertIn("Current public email: `support@gcagochina.com`", markdown)
        self.assertIn("Legacy email scanned: `GCAgochina@outlook.com`", markdown)
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
        self.assertEqual(preview["summary"]["filesWithExactReplacement"], 0)
        self.assertEqual(preview["summary"]["replacementOccurrences"], 0)
        self.assertEqual(patch, "")
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
            self.assertEqual(patch_path.read_text(), "")

    def test_committed_owner_artifacts_are_available_and_preview_only(self):
        json_path = ROOT / "launch" / "domain_email_switch_plan.json"
        md_path = ROOT / "launch" / "domain_email_switch_plan.md"
        patch_path = ROOT / "launch" / "domain_email_switch_preview.patch"

        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())
        self.assertTrue(patch_path.exists())

        plan = json.loads(json_path.read_text(encoding="utf-8"))
        markdown = md_path.read_text(encoding="utf-8")
        patch = patch_path.read_text(encoding="utf-8")

        self.assertEqual(plan["schema"], "gca-domain-email-switch-plan-v1")
        self.assertEqual(plan["status"], "public-email-switch-complete")
        self.assertEqual(plan["currentEmail"], TARGET_EMAIL)
        self.assertEqual(plan["legacyEmail"], CURRENT_EMAIL)
        self.assertEqual(plan["targetDomainEmail"], TARGET_EMAIL)
        self.assertFalse(plan["boundaries"]["writesPublicFiles"])
        self.assertFalse(plan["patchPreview"]["appliesChanges"])
        self.assertEqual(plan["summary"]["filesRequiringSwitchAfterActivation"], 0)
        self.assertIn("support@gcagochina.com receives external email", plan["requiredPreconditions"])
        self.assertIn("GCA Domain Email Public Switch Plan", markdown)
        self.assertIn("This plan does not change public files by itself.", markdown)
        self.assertEqual(patch, "")

    def test_cli_can_print_patch_preview(self):
        completed = subprocess.run(
            [sys.executable, "tools/build_domain_email_switch_plan.py", "--patch"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
