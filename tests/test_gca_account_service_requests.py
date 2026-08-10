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
SERVICE_REQUEST_REVIEW_MIGRATION = (
    ROOT
    / "cloudflare"
    / "gca-registration-worker"
    / "migrations"
    / "0012_service_request_reviews.sql"
)
SERVICE_DELIVERY_RECEIPT_MIGRATION = (
    ROOT
    / "cloudflare"
    / "gca-registration-worker"
    / "migrations"
    / "0013_service_delivery_receipts.sql"
)
SERVICE_REQUEST_CANCELLATION_MIGRATION = (
    ROOT
    / "cloudflare"
    / "gca-registration-worker"
    / "migrations"
    / "0014_service_request_cancellations.sql"
)
CREDIT_USAGE_MIGRATION = (
    ROOT
    / "cloudflare"
    / "gca-registration-worker"
    / "migrations"
    / "0004_credit_usage_ledger.sql"
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

    def test_review_migration_links_requests_reviews_and_credit_usage(self):
        database = sqlite3.connect(":memory:")
        try:
            database.executescript(
                CREDIT_USAGE_MIGRATION.read_text(encoding="utf-8")
            )
            database.executescript(
                SERVICE_REQUEST_MIGRATION.read_text(encoding="utf-8")
            )
            database.executescript(
                SERVICE_REQUEST_REVIEW_MIGRATION.read_text(
                    encoding="utf-8"
                )
            )
            request_columns = {
                row[1]
                for row in database.execute(
                    "PRAGMA table_info(gca_service_requests)"
                ).fetchall()
            }
            usage_columns = {
                row[1]
                for row in database.execute(
                    "PRAGMA table_info(gca_credit_usage)"
                ).fetchall()
            }
            review_columns = {
                row[1]
                for row in database.execute(
                    "PRAGMA table_info(gca_service_request_reviews)"
                ).fetchall()
            }
            self.assertIn("latest_review_id", request_columns)
            self.assertIn("credit_usage_id", request_columns)
            self.assertIn("service_request_id", usage_columns)
            self.assertIn("decision", review_columns)
            self.assertIn("credits_deducted", review_columns)
            self.assertNotIn("status_access_token", review_columns)
            self.assertNotIn("device_key", review_columns)

            indexes = database.execute(
                "PRAGMA index_list(gca_credit_usage)"
            ).fetchall()
            service_index = next(
                row for row in indexes
                if row[1] == "idx_gca_credit_usage_service_request"
            )
            self.assertEqual(service_index[2], 1)
        finally:
            database.close()

    def test_worker_exposes_admin_review_and_idempotent_delivery(self):
        source = WORKER_SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            '"gca_service_request_review_v1"',
            source,
        )
        self.assertIn(
            'url.pathname === "/gca/service-request-reviews"',
            source,
        )
        self.assertIn(
            "approvedBeforeDeliveryRequired: true",
            source,
        )
        self.assertIn(
            "creditsDeductedAtMostOncePerRequest: true",
            source,
        )
        self.assertIn(
            "serverCatalogCreditUnitRequired: true",
            source,
        )
        self.assertIn(
            "service request credit settlement is already recorded",
            source,
        )
        self.assertIn(
            "deliveryReference is required when delivery is recorded",
            source,
        )
        self.assertIn(
            "review.delivery_reference AS review_delivery_reference",
            source,
        )
        self.assertIn(
            "nonSensitiveDeliveryReferenceReturnedAfterDelivered: true",
            source,
        )
        self.assertIn(
            "serviceReviewTransitionAllowed",
            source,
        )
        self.assertIn(
            "serviceRequestRow.service_id",
            source,
        )
        self.assertIn(
            "WHERE service_request_id = ?1",
            source,
        )
        self.assertNotIn("eth_sendTransaction", source)
        self.assertNotIn("personal_sign", source)

    def test_delivery_receipt_migration_adds_single_use_account_marker(self):
        database = sqlite3.connect(":memory:")
        try:
            database.executescript(
                CREDIT_USAGE_MIGRATION.read_text(encoding="utf-8")
            )
            database.executescript(
                SERVICE_REQUEST_MIGRATION.read_text(encoding="utf-8")
            )
            database.executescript(
                SERVICE_REQUEST_REVIEW_MIGRATION.read_text(
                    encoding="utf-8"
                )
            )
            database.executescript(
                SERVICE_DELIVERY_RECEIPT_MIGRATION.read_text(
                    encoding="utf-8"
                )
            )
            columns = {
                row[1]
                for row in database.execute(
                    "PRAGMA table_info(gca_service_requests)"
                ).fetchall()
            }
            self.assertIn("delivery_receipt_id", columns)
            self.assertIn("delivery_acknowledged_at", columns)
            self.assertIn("delivery_acknowledgement_version", columns)
            self.assertIn("delivery_acknowledgement_source", columns)
            indexes = database.execute(
                "PRAGMA index_list(gca_service_requests)"
            ).fetchall()
            receipt_index = next(
                row
                for row in indexes
                if row[1] == "idx_gca_service_requests_delivery_receipt"
            )
            self.assertEqual(receipt_index[2], 1)
        finally:
            database.close()

    def test_worker_exposes_device_key_delivery_receipt_without_wallet_effect(self):
        source = WORKER_SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            '"gca_account_service_delivery_receipt_v1"',
            source,
        )
        self.assertIn(
            '"/gca/account-service-requests/delivery-receipts"',
            source,
        )
        self.assertIn(
            "submitAccountServiceDeliveryReceipt",
            source,
        )
        self.assertIn(
            "delivery can only be acknowledged after completed delivery",
            source,
        )
        self.assertIn(
            "service_request_id = ?1\n        AND account_id = ?2",
            source,
        )
        self.assertIn(
            "AND delivery_receipt_id = ''",
            source,
        )
        self.assertIn(
            "review.service_request_review_id =\n"
            "            gca_service_requests.latest_review_id\n"
            "            AND review.delivery_completed = 1",
            source,
        )
        self.assertIn(
            "deliveryAcknowledgementChangesCredits: false",
            source,
        )
        self.assertIn(
            "deliveryAcknowledgementWritesWallet: false",
            source,
        )
        self.assertNotIn("eth_sendTransaction", source)
        self.assertNotIn("personal_sign", source)

    def test_cancellation_migration_adds_single_use_account_marker(self):
        database = sqlite3.connect(":memory:")
        try:
            database.executescript(
                CREDIT_USAGE_MIGRATION.read_text(encoding="utf-8")
            )
            database.executescript(
                SERVICE_REQUEST_MIGRATION.read_text(encoding="utf-8")
            )
            database.executescript(
                SERVICE_REQUEST_REVIEW_MIGRATION.read_text(encoding="utf-8")
            )
            database.executescript(
                SERVICE_DELIVERY_RECEIPT_MIGRATION.read_text(encoding="utf-8")
            )
            database.executescript(
                SERVICE_REQUEST_CANCELLATION_MIGRATION.read_text(
                    encoding="utf-8"
                )
            )
            columns = {
                row[1]
                for row in database.execute(
                    "PRAGMA table_info(gca_service_requests)"
                ).fetchall()
            }
            self.assertIn("cancellation_id", columns)
            self.assertIn("cancelled_at", columns)
            self.assertIn("cancellation_version", columns)
            self.assertIn("cancellation_source", columns)
            indexes = database.execute(
                "PRAGMA index_list(gca_service_requests)"
            ).fetchall()
            cancellation_index = next(
                row
                for row in indexes
                if row[1] == "idx_gca_service_requests_cancellation"
            )
            self.assertEqual(cancellation_index[2], 1)
        finally:
            database.close()

    def test_worker_exposes_account_scoped_queued_request_cancellation(self):
        source = WORKER_SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            '"gca_account_service_request_cancellation_v1"',
            source,
        )
        self.assertIn(
            '"/gca/account-service-requests/cancellations"',
            source,
        )
        self.assertIn("submitAccountServiceRequestCancellation", source)
        self.assertIn(
            "service request can only be cancelled before manual review",
            source,
        )
        self.assertIn("SERVICE_REQUEST_QUEUED_STATUSES", source)
        self.assertIn("AND latest_review_id = ''", source)
        self.assertIn("AND credit_usage_id = ''", source)
        self.assertIn("AND delivery_receipt_id = ''", source)
        self.assertIn("cancellationChangesCredits: false", source)
        self.assertIn("cancellationWritesWallet: false", source)
        self.assertNotIn("eth_sendTransaction", source)
        self.assertNotIn("personal_sign", source)

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
        self.assertTrue(history["returnsDeliveryReferenceAfterDelivered"])
        self.assertTrue(history["returnsDeliveryAcknowledgement"])

        receipt = public_endpoints[
            "/gca/account-service-requests/delivery-receipts"
        ]
        self.assertEqual(
            receipt["packetVersion"],
            "gca_account_service_delivery_receipt_v1",
        )
        self.assertTrue(receipt["requiresDeviceStatusKey"])
        self.assertTrue(receipt["accountScoped"])
        self.assertTrue(receipt["requiresCompletedDelivery"])
        self.assertTrue(receipt["idempotent"])
        self.assertFalse(receipt["changesCredits"])
        self.assertFalse(receipt["writesWallet"])
        self.assertFalse(receipt["automaticTokenTransfer"])
        self.assertFalse(receipt["createsTradingPermission"])

        cancellation = public_endpoints[
            "/gca/account-service-requests/cancellations"
        ]
        self.assertEqual(
            cancellation["packetVersion"],
            "gca_account_service_request_cancellation_v1",
        )
        self.assertTrue(cancellation["requiresDeviceStatusKey"])
        self.assertTrue(cancellation["accountScoped"])
        self.assertTrue(cancellation["queuedOnly"])
        self.assertTrue(cancellation["idempotent"])
        self.assertFalse(cancellation["changesCredits"])
        self.assertFalse(cancellation["writesWallet"])
        self.assertFalse(cancellation["automaticTokenTransfer"])
        self.assertFalse(cancellation["createsTradingPermission"])

        review = next(
            endpoint
            for endpoint in access_api["endpoints"]
            if endpoint["path"] == "/gca/service-request-reviews"
        )
        self.assertIn(
            "deliveryReference is required when delivered is recorded",
            review["serverChecks"],
        )

        state = access_api["currentState"]
        self.assertTrue(state["accountServiceRequestProductionLive"])
        self.assertTrue(state["accountServiceRequestDeviceKeyProtected"])
        self.assertFalse(state["accountServiceRequestCreditsReserved"])
        self.assertFalse(state["accountServiceRequestCreditsDeductedOnRequest"])
        self.assertFalse(state["accountServiceRequestCreatesTradingPermission"])
        self.assertTrue(state["accountServiceDeliveryReceiptProductionLive"])
        self.assertTrue(state["accountServiceRequestCancellationProductionLive"])
        self.assertTrue(state["accountServiceRequestCancellationQueuedOnly"])
        self.assertTrue(state["accountServiceRequestCancellationIdempotent"])
        self.assertFalse(state["accountServiceRequestCancellationChangesCredits"])
        self.assertFalse(state["accountServiceRequestCancellationWritesWallet"])
        self.assertTrue(
            state["accountServiceDeliveryReceiptRequiresCompletedDelivery"]
        )
        self.assertTrue(state["accountServiceDeliveryReceiptIdempotent"])
        self.assertFalse(state["accountServiceDeliveryReceiptChangesCredits"])
        self.assertFalse(state["accountServiceDeliveryReceiptWritesWallet"])

        receipt_contract = next(
            endpoint
            for endpoint in access_api["endpoints"]
            if endpoint["path"]
            == "/gca/account-service-requests/delivery-receipts"
        )
        self.assertIn(
            "the service request must belong to the matched account",
            receipt_contract["serverChecks"],
        )
        self.assertIn(
            "the request status and latest operator review must both show completed delivery",
            receipt_contract["serverChecks"],
        )

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
        self.assertIn(
            '"/gca/account-service-requests/delivery-receipts"',
            page,
        )
        self.assertIn('"gca_account_service_request_v1"', page)
        self.assertIn('"gca_account_service_request_status_v1"', page)
        self.assertIn(
            '"gca_account_service_delivery_receipt_v1"',
            page,
        )
        self.assertIn(
            '"gca_account_service_request_cancellation_v1"',
            page,
        )
        self.assertIn("newServiceClientRequestId", page)
        self.assertIn("pendingServiceDraftSignature", page)
        self.assertIn("Submission does not reserve or deduct credits", page)
        self.assertIn(
            "does not return email, device keys, wallet secrets, operator notes, or the full request body",
            page,
        )
        self.assertIn("approved_operator_review", page)
        self.assertIn("needs_more_information", page)
        self.assertIn("rejected_operator_review", page)
        self.assertIn("Delivered / 已交付", page)
        self.assertIn("creditAmountUsed", page)
        self.assertIn("latestReview.deliveryReference", page)
        self.assertIn("Delivery reference / 交付引用", page)
        self.assertIn("delivery.textContent", page)
        self.assertIn("accountServiceDeliveryReceiptPayload", page)
        self.assertIn("deliveryAcknowledged", page)
        self.assertIn("Confirm Delivery Received / 确认已收到", page)
        self.assertIn("Cancel Request / 取消申请", page)
        self.assertIn("cancelQueuedRequest", page)
        self.assertIn("noCreditOrWalletEffect", page)
        self.assertIn("receiptButton.isConnected", page)
        self.assertIn("cancelButton.isConnected", page)
        submit_start = page.index(
            'submitServiceRequest.addEventListener("click", async () => {'
        )
        submit_end = page.index(
            'refreshServiceRequests.addEventListener("click", async () => {',
            submit_start,
        )
        self.assertNotIn("receiptButton", page[submit_start:submit_end])
        self.assertNotIn("cancelButton", page[submit_start:submit_end])
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
