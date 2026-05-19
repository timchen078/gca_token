import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.gca_member_backend import JsonlLedgerStore
from tools.run_gca_registration_ops import run_registration_ops


ROOT = Path(__file__).resolve().parents[1]


def cloudflare_record(email="user@example.com", **overrides):
    record = {
        "emailRegistrationId": "gca_email_test123",
        "packetVersion": "gca_email_registration_v1",
        "status": "received",
        "createdAt": "2026-05-19T13:33:41Z",
        "updatedAt": "2026-05-19T13:33:41Z",
        "email": email,
        "displayName": "User",
        "source": "register.html",
        "language": "zh-CN",
        "interests": ["gca_updates", "member_access"],
        "walletRequired": False,
        "requiresSignature": False,
        "requiresTransaction": False,
        "automaticTokenTransfer": False,
    }
    record.update(overrides)
    return record


class GcaRegistrationOpsTests(unittest.TestCase):
    def test_run_registration_ops_syncs_ledger_and_exports_csvs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "data"
            contact_output = root / "contacts.csv"
            redacted_output = root / "contacts-public.csv"
            summary_output = root / "summary.json"
            summary = run_registration_ops(
                payload={"ok": True, "records": [cloudflare_record("USER@EXAMPLE.COM")]},
                data_dir=data_dir,
                contact_output=contact_output,
                redacted_contact_output=redacted_output,
                summary_output=summary_output,
                source="unit-test",
                imported_at="2026-05-19T14:00:00Z",
            )

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["sync"]["created"], 1)
            self.assertEqual(summary["contactExports"]["contactsExported"], 1)
            self.assertFalse(summary["boundaries"]["adminTokenPrinted"])
            self.assertFalse(summary["boundaries"]["walletCalls"])
            records = JsonlLedgerStore(data_dir).read_all("email_registrations")
            self.assertEqual(records[0]["email"], "user@example.com")
            with contact_output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["email"], "user@example.com")
            with redacted_output.open(encoding="utf-8") as handle:
                redacted_text = handle.read()
            self.assertNotIn("user@example.com", redacted_text)
            self.assertTrue(summary_output.exists())

    def test_cli_runs_from_full_export_file_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            export_path = root / "cloudflare-export.json"
            data_dir = root / "data"
            contact_output = root / "contacts.csv"
            redacted_output = root / "contacts-public.csv"
            summary_output = root / "summary.json"
            export_path.write_text(
                json.dumps({
                    "ok": True,
                    "redactedForExternalSharing": False,
                    "records": [cloudflare_record()],
                }),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/run_gca_registration_ops.py",
                    "--input",
                    str(export_path),
                    "--data-dir",
                    str(data_dir),
                    "--contact-output",
                    str(contact_output),
                    "--public-redacted-contact-output",
                    str(redacted_output),
                    "--summary-output",
                    str(summary_output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["sync"]["created"], 1)
            self.assertEqual(result["contactExports"]["contactsExported"], 1)
            self.assertTrue(contact_output.exists())
            self.assertTrue(redacted_output.exists())
            self.assertTrue(summary_output.exists())


if __name__ == "__main__":
    unittest.main()
