import json
import unittest
from urllib.parse import urlparse

from tools.check_gca_registration_api import ApiCheckError, run_checks


class FakeResponse:
    def __init__(self, payload=None, *, status=200, headers=None):
        self.payload = payload
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        if self.payload is None:
            return b""
        return json.dumps(self.payload).encode("utf-8")


class GcaRegistrationApiCheckTests(unittest.TestCase):
    def test_run_checks_is_read_only_and_does_not_print_sensitive_values(self):
        seen = []

        def opener(request, **kwargs):
            parsed = urlparse(request.full_url)
            method = request.get_method()
            seen.append({
                "method": method,
                "path": parsed.path,
                "query": parsed.query,
                "authorization": request.headers.get("Authorization", ""),
                "user_agent": request.headers.get("User-agent", ""),
                "timeout": kwargs.get("timeout"),
            })

            if parsed.path == "/health":
                return FakeResponse({
                    "ok": True,
                    "service": "gca-registration-api",
                    "packetVersion": "gca_email_registration_v1",
                    "contactSuppressionVersion": "gca_contact_suppression_v1",
                    "storage": "cloudflare-d1",
                })
            if method == "OPTIONS":
                return FakeResponse(
                    None,
                    status=204,
                    headers={
                        "access-control-allow-origin": "https://gcagochina.com",
                        "access-control-allow-methods": "GET,POST,OPTIONS",
                    },
                )
            if parsed.path in {"/gca/email-registrations", "/gca/contact-suppressions"}:
                if not request.headers.get("Authorization"):
                    return FakeResponse({"ok": False, "error": "admin authorization is required"}, status=401)
                if parsed.path == "/gca/email-registrations":
                    return FakeResponse({
                        "ok": True,
                        "count": 1,
                        "records": [{"email": "private-user@example.com", "status": "received"}],
                    })
                return FakeResponse({
                    "ok": True,
                    "count": 1,
                    "records": [{"email": "suppressed-user@example.com", "status": "suppressed"}],
                })
            return FakeResponse({"ok": False}, status=404)

        result = run_checks(
            base_url="https://worker.example",
            token="secret-token",
            limit=1,
            timeout=7,
            opener=opener,
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["boundaries"]["readOnlySmokeCheck"])
        self.assertFalse(result["boundaries"]["writesProductionData"])
        self.assertFalse(result["boundaries"]["submitsRegistration"])
        self.assertFalse(result["boundaries"]["submitsContactSuppression"])
        self.assertFalse(result["boundaries"]["adminTokenPrinted"])
        self.assertFalse(result["boundaries"]["userEmailsPrinted"])
        self.assertFalse(result["boundaries"]["publicOnly"])
        self.assertTrue(result["boundaries"]["adminReadTokenRequired"])
        self.assertTrue(result["boundaries"]["tokenProtectedAdminReadChecked"])
        self.assertEqual({item["method"] for item in seen}, {"GET", "OPTIONS"})
        self.assertEqual(len(result["checks"]), 7)
        self.assertTrue(any(item["id"] == "admin-email-registrations-read" for item in result["checks"]))
        serialized = json.dumps(result)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("private-user@example.com", serialized)
        self.assertNotIn("suppressed-user@example.com", serialized)
        self.assertTrue(all(item["timeout"] == 7 for item in seen))
        self.assertTrue(all(item["user_agent"] == "GCA-Operator-Registration-API-Check/1.0" for item in seen))

    def test_public_only_mode_skips_token_protected_reads(self):
        seen = []

        def opener(request, **kwargs):
            parsed = urlparse(request.full_url)
            method = request.get_method()
            seen.append({
                "method": method,
                "path": parsed.path,
                "authorization": request.headers.get("Authorization", ""),
            })
            if parsed.path == "/health":
                return FakeResponse({
                    "ok": True,
                    "service": "gca-registration-api",
                    "packetVersion": "gca_email_registration_v1",
                    "contactSuppressionVersion": "gca_contact_suppression_v1",
                    "storage": "cloudflare-d1",
                })
            if method == "OPTIONS":
                return FakeResponse(
                    None,
                    status=204,
                    headers={
                        "access-control-allow-origin": "https://gcagochina.com",
                        "access-control-allow-methods": "GET,POST,OPTIONS",
                    },
                )
            return FakeResponse({"ok": False, "error": "admin authorization is required"}, status=401)

        result = run_checks(base_url="https://worker.example", public_only=True, opener=opener)
        self.assertTrue(result["ok"])
        self.assertTrue(result["boundaries"]["publicOnly"])
        self.assertFalse(result["boundaries"]["adminReadTokenRequired"])
        self.assertFalse(result["boundaries"]["tokenProtectedAdminReadChecked"])
        self.assertEqual(len(result["checks"]), 5)
        self.assertNotIn("admin-email-registrations-read", {item["id"] for item in result["checks"]})
        self.assertTrue(all(item["authorization"] == "" for item in seen))

    def test_admin_mode_requires_token(self):
        with self.assertRaises(ApiCheckError):
            run_checks(base_url="https://worker.example", token="", opener=lambda request, **kwargs: None)

    def test_run_checks_rejects_bad_health_payload(self):
        def opener(request, **kwargs):
            return FakeResponse({"ok": True, "service": "wrong-service", "storage": "cloudflare-d1"})

        with self.assertRaises(ApiCheckError):
            run_checks(base_url="https://worker.example", token="secret-token", opener=opener)

    def test_run_checks_rejects_invalid_limit(self):
        with self.assertRaises(ApiCheckError):
            run_checks(base_url="https://worker.example", token="secret-token", limit=0, opener=lambda request, **kwargs: None)


if __name__ == "__main__":
    unittest.main()
