import json
import tempfile
import unittest
from pathlib import Path

from tools.export_cloudflare_email_registrations import (
    ExportError,
    build_admin_url,
    build_export_payload,
    fetch_admin_records,
    load_admin_token,
    redact_record,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class CloudflareEmailExportTests(unittest.TestCase):
    def test_build_admin_url_normalizes_query(self):
        url = build_admin_url("https://worker.example/", 20, "USER@EXAMPLE.COM")
        self.assertEqual(url, "https://worker.example/gca/email-registrations?limit=20&email=user%40example.com")

    def test_load_admin_token_from_ignored_env_file(self):
        with tempfile.TemporaryDirectory() as temp:
            token_file = Path(temp) / ".env.admin.local"
            token_file.write_text("ADMIN_READ_TOKEN=secret-token\nPRIVACY_HASH_SALT=unused\n", encoding="utf-8")
            self.assertEqual(load_admin_token(token_file), "secret-token")

    def test_fetch_admin_records_uses_bearer_token_without_printing_it(self):
        seen = {}

        def opener(request, timeout):
            seen["url"] = request.full_url
            seen["authorization"] = request.headers["Authorization"]
            seen["user_agent"] = request.headers["User-agent"]
            seen["timeout"] = timeout
            return FakeResponse({"ok": True, "count": 1, "records": [{"email": "user@example.com"}]})

        payload = fetch_admin_records(
            base_url="https://worker.example",
            token="secret-token",
            limit=1,
            timeout=7,
            opener=opener,
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(seen["authorization"], "Bearer secret-token")
        self.assertEqual(seen["user_agent"], "GCA-Operator-Registration-Export/1.0")
        self.assertEqual(seen["timeout"], 7)
        self.assertIn("/gca/email-registrations?limit=1", seen["url"])

    def test_fetch_admin_records_rejects_malformed_success(self):
        def opener(request, timeout):
            return FakeResponse({"ok": True})

        with self.assertRaises(ExportError):
            fetch_admin_records(base_url="https://worker.example", token="secret-token", limit=1, opener=opener)

    def test_redacted_export_removes_personal_email_and_display_name(self):
        record = {"email": "User@Example.com", "displayName": "User Name", "status": "received"}
        redacted = redact_record(record)
        self.assertEqual(redacted["email"], "")
        self.assertEqual(redacted["displayName"], "")
        self.assertEqual(len(redacted["emailSha256"]), 64)
        self.assertTrue(redacted["redactedForExternalSharing"])

        payload = build_export_payload(
            response_payload={"ok": True, "count": 1, "records": [record]},
            source_url="https://worker.example/gca/email-registrations?limit=1",
            redacted=True,
        )
        exported = json.dumps(payload)
        self.assertNotIn("User@Example.com", exported)
        self.assertNotIn("User Name", exported)
        self.assertTrue(payload["boundaries"]["localOperatorExportOnly"])
        self.assertFalse(payload["boundaries"]["adminTokenPrinted"])


if __name__ == "__main__":
    unittest.main()
