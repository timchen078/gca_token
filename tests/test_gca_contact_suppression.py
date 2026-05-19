import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.suppress_gca_contact import build_suppression_record


ROOT = Path(__file__).resolve().parents[1]


class GcaContactSuppressionTests(unittest.TestCase):
    def test_build_suppression_record_normalizes_email(self):
        record = build_suppression_record(
            email="USER@EXAMPLE.COM",
            reason="unsubscribe request",
            source="support",
            created_at="2026-05-19T15:00:00Z",
        )
        self.assertEqual(record["email"], "user@example.com")
        self.assertEqual(record["reason"], "unsubscribe request")
        self.assertEqual(record["source"], "support")
        self.assertTrue(record["contactSuppressed"])
        self.assertEqual(len(record["emailSha256"]), 64)

    def test_cli_appends_suppression_record(self):
        with tempfile.TemporaryDirectory() as temp:
            suppression_file = Path(temp) / "suppressions.jsonl"
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/suppress_gca_contact.py",
                    "--email",
                    "USER@EXAMPLE.COM",
                    "--reason",
                    "unsubscribe request",
                    "--source",
                    "support",
                    "--suppression-file",
                    str(suppression_file),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["email"], "user@example.com")
            lines = suppression_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["email"], "user@example.com")
            self.assertEqual(record["reason"], "unsubscribe request")


if __name__ == "__main__":
    unittest.main()
