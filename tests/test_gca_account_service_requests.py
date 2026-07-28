import json
import re
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER_SOURCE = (
    ROOT / "cloudflare" / "gca-registration-worker" / "src" / "worker.mjs"
)
SERVICE_REQUEST_MIGRATION = (
    ROOT
    / "cloudflare"
    / "gca-registration-worker"
    / "migrations"
    / "0005_service_requests.sql"
)
MEMBER_ACCESS_PAGE = ROOT / "site" / "gca" / "member-access" / "index.html"
CREDITS_JSON = ROOT / "site" / "credits.json"
ACCESS_API_JSON = ROOT / "site" / "access-api.json"
API_STATUS_JSON = ROOT / "site" / "api-status.json"
SERVICE_PLAYBOOK_JSON = ROOT / "site" / "service-delivery-playbook.json"


class GcaAccountServiceRequestTests(unittest.TestCase):
    def test_existing_service_request_table_keeps_no_device_key_or_wallet_write(self):
        database = sqlite3.connect(":memory:")
        try:
            database.executescript(
                SERVICE_REQUEST_MIGRATION.read_text(encoding="utf-8")
            )
            columns = {
                row[1]
                for row in database.execute(
                    "PRAGMA table_info(gca_service_requests)"
                ).fetchall()
            }
            self.assertIn("account_id", columns)
            self.assertIn("requested_credit_hold", columns)
            self.assertIn("does_not_deduct_credits", columns)
            self.assertIn("creates_trading_permission", columns)
            self.assertNotIn("status_access_token", columns)
            self.assertNotIn("device_key", columns)
            self.assertNotIn("private_key", columns)
        finally:
            database.close()

    def test_worker_exposes_device_key_protected_account_request_routes(self):
        source = WORKER_SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            'const ACCOUNT_SERVICE_REQUEST_VERSION = "gca_account_service_request_v1";',
            source,
        )
        self.assertIn(
            '"gca_account_service_request_status_v1"',
            source,
        )
        self.assertIn(
            'url.pathname === "/gca/account-service-requests"',
            source,
        )
        self.assertIn(
            'url.pathname === "/gca/account-service-requests/status"',
            source,
        )
        self.assertIn("authenticateAccountStatusAccess", source)
        self.assertIn("requestedCreditHold: service.creditUnit", source)
        self.assertIn("ACCOUNT_SERVICE_REQUEST_DAILY_LIMIT = 5", source)
        self.assertIn("clientRequestId is already assigned", source)
        self.assertIn("INSERT OR IGNORE INTO gca_service_requests", source)
        self.assertIn("creditsDeductedOnRequest: false", source)
        self.assertIn("accountServiceRequestReturnsEmail: false", source)
        self.assertIn("accountServiceRequestCreatesTradingPermission: false", source)
        self.assertIn("creditsReserved: false", source)
        self.assertIn("createsTradingPermission: false", source)
        self.assertNotIn("eth_sendTransaction", source)
        self.assertNotIn("personal_sign", source)

        auth_position = source.index("authenticateAccountStatusAccess(\n    db,")
        insert_position = source.index(
            "INSERT OR IGNORE INTO gca_service_requests",
            auth_position,
        )
        self.assertLess(auth_position, insert_position)

    def test_worker_catalog_matches_public_credits_catalog(self):
        source = WORKER_SOURCE.read_text(encoding="utf-8")
        credits = json.loads(CREDITS_JSON.read_text(encoding="utf-8"))
        public_services = {
            item["id"]: int(item["creditUnit"])
            for item in credits["serviceCatalog"]
        }

        worker_catalog_match = re.search(
            r"const CREDIT_SERVICE_CATALOG = \{(?P<body>.*?)\n\};",
            source,
            re.DOTALL,
        )
        self.assertIsNotNone(worker_catalog_match)
        worker_services = {
            service_id: int(unit)
            for service_id, unit in re.findall(
                r'"([a-z0-9-]+)": \{ name: "[^"]+", creditUnit: (\d+) \}',
                worker_catalog_match.group("body"),
            )
        }
        self.assertEqual(worker_services, public_services)

        playbook = json.loads(SERVICE_PLAYBOOK_JSON.read_text(encoding="utf-8"))
        playbook_services = {
            item["id"]: int(item["defaultCreditUnit"])
            for item in playbook["serviceCatalog"]
        }
        self.assertEqual(playbook_services, public_services)

    def test_public_api_contracts_publish_request_boundaries(self):
        access_api = json.loads(ACCESS_API_JSON.read_text(encoding="utf-8"))
        api_status = json.loads(API_STATUS_JSON.read_text(encoding="utf-8"))
        public_endpoints = {
            endpoint["path"]: endpoint for endpoint in api_status["publicEndpoints"]
        }

        create = public_endpoints["/gca/account-service-requests"]
        self.assertTrue(create["requiresDeviceStatusKey"])
        self.assertTrue(create["serverCatalogUnitRequired"])
        self.assertEqual(create["dailyRequestLimit"], 5)
        self.assertFalse(create["creditsReserved"])
        self.assertFalse(create["creditsDeductedOnSubmission"])
        self.assertFalse(create["returnsEmail"])
        self.assertFalse(create["createsTradingPermission"])

        history = public_endpoints["/gca/account-service-requests/status"]
        self.assertTrue(history["requiresDeviceStatusKey"])
        self.assertTrue(history["accountScoped"])
        self.assertEqual(history["historyLimit"], 25)
        self.assertFalse(history["returnsEmail"])
        self.assertFalse(history["returnsFullWalletAddress"])
        self.assertFalse(history["returnsFullRequestBody"])

        state = access_api["currentState"]
        self.assertTrue(state["accountServiceRequestProductionLive"])
        self.assertTrue(state["accountServiceRequestDeviceKeyProtected"])
        self.assertFalse(state["accountServiceRequestCreditsReserved"])
        self.assertFalse(state["accountServiceRequestCreditsDeductedOnRequest"])
        self.assertFalse(state["accountServiceRequestCreatesTradingPermission"])

    def test_member_access_page_submits_and_reads_redacted_request_history(self):
        page = MEMBER_ACCESS_PAGE.read_text(encoding="utf-8")

        for element_id in (
            "accountServiceRequests",
            "accountServiceId",
            "accountServiceTitle",
            "accountServiceSummary",
            "accountServiceBoundary",
            "submitServiceRequest",
            "refreshServiceRequests",
            "serviceRequestList",
        ):
            self.assertIn(f'id="{element_id}"', page)
        self.assertIn('"/gca/account-service-requests"', page)
        self.assertIn('"/gca/account-service-requests/status"', page)
        self.assertIn('"gca_account_service_request_v1"', page)
        self.assertIn('"gca_account_service_request_status_v1"', page)
        self.assertIn("newServiceClientRequestId", page)
        self.assertIn("pendingServiceDraftSignature", page)
        self.assertIn("Submission does not reserve or deduct credits", page)
        self.assertIn("does not return email or the full request body", page)
        self.assertNotIn(
            "serviceRequestList.textContent = statusAccess.token",
            page,
        )
        self.assertNotIn(
            "requestSummary: statusAccess.token",
            page,
        )


if __name__ == "__main__":
    unittest.main()
