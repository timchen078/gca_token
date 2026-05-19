import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.gca_member_backend import JsonlLedgerStore
from tools.sync_cloudflare_email_registrations import (
    SyncError,
    cloudflare_record_to_local,
    load_export_file,
    sync_records,
)


ROOT = Path(__file__).resolve().parents[1]


def cloudflare_record(email="user@example.com"):
    return {
        "emailRegistrationId": "gca_email_test123",
        "packetVersion": "gca_email_registration_v1",
        "status": "received",
        "createdAt": "2026-05-19T13:33:41Z",
        "updatedAt": "2026-05-19T13:33:41Z",
        "email": email,
        "displayName": "User",
        "source": "register.html",
        "language": "zh-CN",
        "interests": ["gca_updates"],
        "walletRequired": False,
        "requiresSignature": False,
        "requiresTransaction": False,
        "automaticTokenTransfer": False,
    }


class CloudflareEmailSyncTests(unittest.TestCase):
    def test_cloudflare_record_to_local_preserves_safe_registration_fields(self):
        local = cloudflare_record_to_local(cloudflare_record("USER@EXAMPLE.COM"), "2026-05-19T14:00:00Z")
        self.assertEqual(local["email"], "user@example.com")
        self.assertEqual(local["emailRegistrationId"], "gca_email_test123")
        self.assertTrue(local["contactConsentAccepted"])
        self.assertTrue(local["securityBoundaryAccepted"])
        self.assertFalse(local["walletRequired"])
        self.assertFalse(local["requiresSignature"])
        self.assertFalse(local["requiresTransaction"])
        self.assertTrue(local["importedFromCloudflare"])

    def test_sync_records_is_idempotent_by_email_registration_id(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlLedgerStore(Path(temp))
            first = sync_records(store, [cloudflare_record()], "2026-05-19T14:00:00Z")
            second = sync_records(store, [cloudflare_record()], "2026-05-19T14:01:00Z")
            self.assertEqual(first["created"], 1)
            self.assertEqual(first["skipped"], 0)
            self.assertEqual(second["created"], 0)
            self.assertEqual(second["skipped"], 1)
            self.assertEqual(len(store.read_all("email_registrations")), 1)

    def test_redacted_export_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            export_path = Path(temp) / "redacted.json"
            export_path.write_text(json.dumps({"redactedForExternalSharing": True, "records": []}), encoding="utf-8")
            with self.assertRaises(SyncError):
                load_export_file(export_path)

    def test_cli_syncs_full_export_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            export_path = root / "cloudflare-export.json"
            data_dir = root / "data"
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
                    "tools/sync_cloudflare_email_registrations.py",
                    "--input",
                    str(export_path),
                    "--data-dir",
                    str(data_dir),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["created"], 1)
            records = JsonlLedgerStore(data_dir).read_all("email_registrations")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["email"], "user@example.com")


if __name__ == "__main__":
    unittest.main()
