import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.sync_cloudflare_contact_suppressions import (
    SuppressionSyncError,
    build_admin_url,
    cloudflare_suppression_to_local,
    fetch_admin_suppressions,
    load_suppression_export_file,
    sync_suppressions,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def suppression_record(email="user@example.com", **overrides):
    record = {
        "suppressionId": "gca_suppression_test123",
        "packetVersion": "gca_contact_suppression_v1",
        "status": "suppressed",
        "createdAt": "2026-05-19T14:22:01Z",
        "updatedAt": "2026-05-19T14:22:01Z",
        "email": email,
        "emailSha256": "0" * 64,
        "reason": "unsubscribe_request",
        "source": "unsubscribe.html",
        "contactSuppressed": True,
        "requiresSignature": False,
        "requiresTransaction": False,
        "automaticTokenTransfer": False,
    }
    record.update(overrides)
    return record


class CloudflareContactSuppressionSyncTests(unittest.TestCase):
    def test_build_admin_url_normalizes_contact_suppression_query(self):
        url = build_admin_url("https://worker.example/", 20, "USER@EXAMPLE.COM")
        self.assertEqual(url, "https://worker.example/gca/contact-suppressions?limit=20&email=user%40example.com")

    def test_fetch_admin_suppressions_uses_bearer_token_without_printing_it(self):
        seen = {}

        def opener(request, timeout):
            seen["url"] = request.full_url
            seen["authorization"] = request.headers["Authorization"]
            seen["user_agent"] = request.headers["User-agent"]
            seen["timeout"] = timeout
            return FakeResponse({"ok": True, "count": 1, "records": [suppression_record()]})

        payload = fetch_admin_suppressions(
            base_url="https://worker.example",
            token="secret-token",
            limit=1,
            timeout=7,
            opener=opener,
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(seen["authorization"], "Bearer secret-token")
        self.assertEqual(seen["user_agent"], "GCA-Operator-Contact-Suppression-Sync/1.0")
        self.assertEqual(seen["timeout"], 7)
        self.assertIn("/gca/contact-suppressions?limit=1", seen["url"])

    def test_cloudflare_suppression_to_local_normalizes_safe_fields(self):
        local = cloudflare_suppression_to_local(suppression_record("USER@EXAMPLE.COM"), "2026-05-19T15:00:00Z")
        self.assertEqual(local["email"], "user@example.com")
        self.assertEqual(local["suppressionId"], "gca_suppression_test123")
        self.assertTrue(local["contactSuppressed"])
        self.assertTrue(local["importedFromCloudflare"])
        self.assertEqual(local["reason"], "unsubscribe_request")
        self.assertEqual(local["source"], "unsubscribe.html")

    def test_sync_suppressions_is_idempotent_by_id_and_email(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "suppressions.jsonl"
            first = sync_suppressions(path, [suppression_record()], "2026-05-19T15:00:00Z")
            second = sync_suppressions(path, [suppression_record()], "2026-05-19T15:01:00Z")
            third = sync_suppressions(
                path,
                [suppression_record("USER@EXAMPLE.COM", suppressionId="gca_suppression_other")],
                "2026-05-19T15:02:00Z",
            )
            self.assertEqual(first["created"], 1)
            self.assertEqual(second["created"], 0)
            self.assertEqual(second["skipped"], 1)
            self.assertEqual(third["created"], 0)
            self.assertEqual(third["skipped"], 1)
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)

    def test_redacted_or_malformed_export_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            export_path = Path(temp) / "bad.json"
            export_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
            with self.assertRaises(SuppressionSyncError):
                load_suppression_export_file(export_path)

    def test_cli_syncs_contact_suppression_export_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            export_path = root / "contact-suppressions.json"
            suppression_file = root / "suppressions.jsonl"
            export_path.write_text(
                json.dumps({"ok": True, "records": [suppression_record("USER@EXAMPLE.COM")]}),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/sync_cloudflare_contact_suppressions.py",
                    "--input",
                    str(export_path),
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
            self.assertEqual(result["created"], 1)
            record = json.loads(suppression_file.read_text(encoding="utf-8"))
            self.assertEqual(record["email"], "user@example.com")
            self.assertTrue(record["contactSuppressed"])


if __name__ == "__main__":
    unittest.main()
