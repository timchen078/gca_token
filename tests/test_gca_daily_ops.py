import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.run_gca_daily_ops import run_daily_ops


class GcaDailyOpsTests(unittest.TestCase):
    def test_daily_ops_public_only_runs_site_and_api_checks(self):
        seen = []

        def runner(command, cwd, timeout):
            seen.append({"command": list(command), "cwd": cwd, "timeout": timeout})
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                site_base_url="https://example.com/",
                api_base_url="https://api.example.com",
                timeout=5,
                summary_output=Path(temp) / "summary.json",
                runner=runner,
            )

        self.assertTrue(summary["ok"])
        self.assertFalse(summary["includeMemberOps"])
        self.assertEqual([step["id"] for step in summary["steps"]], ["public-site", "registration-api-public"])
        self.assertTrue(summary["boundaries"]["publicOnlyByDefault"])
        self.assertFalse(summary["boundaries"]["writesProductionData"])
        self.assertFalse(summary["boundaries"]["automaticTokenTransfer"])
        commands = [" ".join(item["command"]) for item in seen]
        self.assertTrue(any("tools/check_public_site.py" in command for command in commands))
        self.assertTrue(any("tools/check_gca_registration_api.py" in command and "--public-only" in command for command in commands))

    def test_daily_ops_can_include_member_ops_explicitly(self):
        def runner(command, cwd, timeout):
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                include_member_ops=True,
                member_ops_redact="public",
                summary_output=Path(temp) / "summary.json",
                runner=runner,
            )

        self.assertTrue(summary["ok"])
        self.assertTrue(summary["includeMemberOps"])
        self.assertEqual(summary["steps"][-1]["id"], "member-access-ops")
        self.assertIn("tools/run_gca_member_access_ops.py", summary["steps"][-1]["command"])
        self.assertIn("--redact public", summary["steps"][-1]["command"])

    def test_daily_ops_marks_failure_without_printing_tokens(self):
        def runner(command, cwd, timeout):
            if any("check_public_site.py" in part for part in command):
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="site failed")
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary_output = Path(temp) / "summary.json"
            summary = run_daily_ops(summary_output=summary_output, runner=runner)

            self.assertFalse(summary["ok"])
            self.assertFalse(summary["steps"][0]["ok"])
            self.assertEqual(summary["steps"][0]["stderrTail"], "site failed")
            self.assertTrue(summary_output.exists())
            serialized = json.dumps(summary)
            self.assertNotIn("ADMIN_READ_TOKEN", serialized)
            self.assertNotIn("secret-token", serialized)


if __name__ == "__main__":
    unittest.main()
