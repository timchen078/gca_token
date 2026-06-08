import json
import unittest
from urllib.parse import parse_qs, urlparse

from tools.export_cloudflare_email_registrations import ExportError
from tools.export_cloudflare_member_access import (
    build_admin_url,
    export_datasets,
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


class CloudflareMemberAccessExportTests(unittest.TestCase):
    def test_build_admin_url_supports_wallet_and_email_filters(self):
        url = build_admin_url(
            "https://worker.example/",
            "member-access",
            20,
            email="USER@EXAMPLE.COM",
            wallet_address="0xABCDEFabcdefABCDEFabcdefABCDEFabcdefabcd",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/gca/member-access")
        self.assertEqual(query["limit"], ["20"])
        self.assertEqual(query["email"], ["user@example.com"])
        self.assertEqual(query["walletAddress"], ["0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"])

    def test_build_admin_url_rejects_unsupported_email_filter(self):
        with self.assertRaises(ExportError):
            build_admin_url("https://worker.example", "credit-ledger", 20, email="user@example.com")

    def test_export_all_member_datasets_uses_bearer_token_without_printing_records(self):
        seen = []

        def opener(request, timeout):
            seen.append({
                "path": urlparse(request.full_url).path,
                "authorization": request.headers["Authorization"],
                "user_agent": request.headers["User-agent"],
                "timeout": timeout,
            })
            return FakeResponse({
                "ok": True,
                "count": 1,
                "records": [{
                    "email": "private-user@example.com",
                    "displayName": "Private User",
                    "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
                    "status": "active",
                }],
            })

        payload = export_datasets(
            base_url="https://worker.example",
            token="secret-token",
            dataset="all",
            limit=1,
            redacted=True,
            timeout=7,
            opener=opener,
        )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["datasetCount"], 4)
        self.assertEqual(payload["recordCount"], 4)
        self.assertEqual(
            {item["path"] for item in seen},
            {
                "/gca/member-access",
                "/gca/wallet-verifications",
                "/gca/credit-ledger",
                "/gca/member-ledger",
            },
        )
        self.assertTrue(all(item["authorization"] == "Bearer secret-token" for item in seen))
        self.assertTrue(all(item["user_agent"] == "GCA-Operator-Member-Access-Export/1.0" for item in seen))
        self.assertTrue(all(item["timeout"] == 7 for item in seen))
        serialized = json.dumps(payload)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("private-user@example.com", serialized)
        self.assertNotIn("Private User", serialized)
        self.assertFalse(payload["boundaries"]["writesProductionData"])
        self.assertFalse(payload["boundaries"]["automaticTokenTransfer"])
        self.assertFalse(payload["pendingWorkerRoutesIncluded"])

    def test_export_can_include_pending_service_request_dataset_explicitly(self):
        seen = []

        def opener(request, timeout):
            seen.append({"path": urlparse(request.full_url).path})
            return FakeResponse({"ok": True, "count": 0, "records": []})

        payload = export_datasets(
            base_url="https://worker.example",
            token="secret-token",
            dataset="all",
            limit=1,
            include_pending_routes=True,
            opener=opener,
        )

        self.assertEqual(payload["datasetCount"], 6)
        self.assertIn("/gca/service-requests", {item["path"] for item in seen})
        self.assertIn("/gca/credit-usage", {item["path"] for item in seen})
        self.assertTrue(payload["pendingWorkerRoutesIncluded"])

    def test_redacted_export_removes_email_and_display_name(self):
        record = {
            "email": "User@Example.com",
            "displayName": "User Name",
            "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
        }
        redacted = redact_record(record)
        self.assertEqual(redacted["email"], "")
        self.assertEqual(redacted["displayName"], "")
        self.assertEqual(len(redacted["emailSha256"]), 64)
        self.assertEqual(redacted["walletAddress"], record["walletAddress"])
        self.assertTrue(redacted["walletAddressRetainedForOnchainReview"])
        self.assertTrue(redacted["redactedForExternalSharing"])


if __name__ == "__main__":
    unittest.main()
