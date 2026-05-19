import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.export_gca_email_contacts import build_contact_rows, email_sha256
from tools.gca_member_backend import JsonlLedgerStore


ROOT = Path(__file__).resolve().parents[1]


def email_record(email="user@example.com", **overrides):
    record = {
        "emailRegistrationId": "gca_email_test123",
        "createdAt": "2026-05-19T13:00:00Z",
        "updatedAt": "2026-05-19T13:00:00Z",
        "source": "register.html",
        "status": "received",
        "email": email,
        "displayName": "User",
        "language": "zh-CN",
        "interests": ["gca_updates", "member_access"],
        "contactConsentAccepted": True,
        "securityBoundaryAccepted": True,
        "importedFromCloudflare": True,
    }
    record.update(overrides)
    return record


class GcaEmailContactsExportTests(unittest.TestCase):
    def test_build_contact_rows_exports_latest_consented_record_per_email(self):
        rows, skipped = build_contact_rows([
            email_record("User@Example.com", displayName="Old", updatedAt="2026-05-19T13:00:00Z"),
            email_record("user@example.com", displayName="New", updatedAt="2026-05-19T14:00:00Z"),
            email_record("no-consent@example.com", contactConsentAccepted=False),
        ], redacted=False)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["email"], "user@example.com")
        self.assertEqual(rows[0]["displayName"], "New")
        self.assertEqual(rows[0]["interests"], "gca_updates;member_access")
        self.assertEqual(rows[0]["importedFromCloudflare"], "true")
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["reason"], "contact_consent_missing")

    def test_redacted_rows_remove_email_and_display_name(self):
        rows, skipped = build_contact_rows([email_record()], redacted=True)
        self.assertEqual(skipped, [])
        self.assertNotIn("email", rows[0])
        self.assertNotIn("displayName", rows[0])
        self.assertEqual(rows[0]["emailSha256"], email_sha256("user@example.com"))

    def test_cli_writes_csv_from_local_ledger(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp) / "data"
            output = Path(temp) / "contacts.csv"
            store = JsonlLedgerStore(data_dir)
            store.append("email_registrations", email_record())
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/export_gca_email_contacts.py",
                    "--data-dir",
                    str(data_dir),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["contactsExported"], 1)
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["email"], "user@example.com")
            self.assertEqual(rows[0]["displayName"], "User")


if __name__ == "__main__":
    unittest.main()
