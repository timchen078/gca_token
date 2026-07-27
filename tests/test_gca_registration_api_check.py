import json
import unittest
from urllib.parse import urlparse

from tools.check_gca_registration_api import ApiCheckError, run_checks


HEALTH_PAYLOAD = {
    "ok": True,
    "service": "gca-registration-api",
    "workerRelease": "gca-registration-worker-2026-07-27-account-status-recovery-v1",
    "contactEmail": "support@gcagochina.com",
    "packetVersion": "gca_email_registration_v1",
    "contactSuppressionVersion": "gca_contact_suppression_v1",
    "memberAccessVersion": "gca_member_access_v2",
    "legacyMemberAccessVersion": "gca_member_access_v1",
    "accountStatusVersion": "gca_account_status_v1",
    "accountStatusRotationVersion": "gca_account_status_rotation_v1",
    "accountStatusRecoveryRequestVersion": "gca_account_status_recovery_request_v1",
    "accountStatusRecoveryApprovalVersion": "gca_account_status_recovery_approval_v1",
    "accountStatusRecoveryVersion": "gca_account_status_recovery_v1",
    "creditUsageVersion": "gca_credit_usage_v1",
    "serviceRequestVersion": "gca_service_request_v1",
    "memberReviewVersion": "gca_member_review_v1",
    "holdingVerificationVersion": "gca_holding_verification_v1",
    "memberBenefitTransferVersion": "gca_member_benefit_transfer_v1",
    "memberBenefitSourceWallet": "0x5e8f84748612b913aacc937492ac25dc5630e246",
    "chainId": 8453,
    "contractAddress": "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6",
    "storage": "cloudflare-d1",
    "antiSpam": {
        "honeypotFields": ["website", "company", "homepage"],
        "rejectsFilledHoneypotFields": True,
        "rateLimitsStillRequired": True,
    },
}

ACCESS_CONFIG_PAYLOAD = {
    "ok": True,
    "service": "gca-registration-api",
    "workerRelease": "gca-registration-worker-2026-07-27-account-status-recovery-v1",
    "contactEmail": "support@gcagochina.com",
    "memberAccessVersion": "gca_member_access_v2",
    "legacyMemberAccessVersion": "gca_member_access_v1",
    "accountStatusVersion": "gca_account_status_v1",
    "accountStatusRotationVersion": "gca_account_status_rotation_v1",
    "accountStatusRecoveryRequestVersion": "gca_account_status_recovery_request_v1",
    "accountStatusRecoveryApprovalVersion": "gca_account_status_recovery_approval_v1",
    "accountStatusRecoveryVersion": "gca_account_status_recovery_v1",
    "creditUsageVersion": "gca_credit_usage_v1",
    "serviceRequestVersion": "gca_service_request_v1",
    "memberReviewVersion": "gca_member_review_v1",
    "holdingVerificationVersion": "gca_holding_verification_v1",
    "memberBenefitTransferVersion": "gca_member_benefit_transfer_v1",
    "endpoints": {
        "accountStatus": "/gca/account-status",
        "accountStatusRotation": "/gca/account-status/rotate",
        "accountStatusRecoveryRequests": "/gca/account-status/recovery-requests",
        "accountStatusRecoveryApprovals": "/gca/account-status/recovery-approvals",
        "accountStatusRecovery": "/gca/account-status/recover",
        "memberReviewsAdmin": "/gca/member-reviews",
        "holdingVerificationsAdmin": "/gca/holding-verifications",
        "memberBenefitTransfersAdmin": "/gca/member-benefit-transfers",
    },
    "thresholds": {
        "holderBonusMinimumGca": "10000",
        "gcaMemberMinimumGca": "1000000",
        "memberBenefitSourceWallet": "0x5e8f84748612b913aacc937492ac25dc5630e246",
    },
    "boundaries": {
        "readOnlyWalletVerification": True,
        "readOnlyAccountStatus": True,
        "accountStatusTokenStoredAsSha256": True,
        "accountStatusReturnsEmail": False,
        "accountStatusReturnsAccessToken": False,
        "accountStatusKeyRotationEnabled": True,
        "accountStatusRotationGraceMinutes": 15,
        "accountStatusRotationReturnsAccessToken": False,
        "accountStatusRotationChangesAccountOrLedgers": False,
        "accountStatusRecoveryEnabled": True,
        "accountStatusRecoveryMode": "registered-email-manual-review",
        "accountStatusRecoveryStoresCredentialAsSha256": True,
        "accountStatusRecoveryReturnsAccountMatch": False,
        "accountStatusRecoveryInvalidatesOldDeviceKey": True,
        "accountStatusRecoveryChangesAccountOrLedgers": False,
        "automaticTokenTransfer": False,
        "automaticMemberActivationFromSubmittedDate": False,
        "onchainHoldingHistoryRequiredForApproval": True,
        "memberBenefitExactTransferRequired": True,
        "memberBenefitSafeBlockRequired": True,
    },
    "antiSpam": {
        "honeypotFields": ["website", "company", "homepage"],
        "rejectsFilledHoneypotFields": True,
        "rateLimitsStillRequired": True,
    },
}


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
                return FakeResponse(HEALTH_PAYLOAD)
            if parsed.path == "/gca/access-config":
                return FakeResponse(ACCESS_CONFIG_PAYLOAD)
            if method == "OPTIONS":
                return FakeResponse(
                    None,
                    status=204,
                    headers={
                        "access-control-allow-origin": "https://gcagochina.com",
                        "access-control-allow-methods": "GET,POST,OPTIONS",
                    },
                )
            if parsed.path in {
                "/gca/account-status",
                "/gca/account-status/rotate",
                "/gca/account-status/recovery-approvals",
                "/gca/account-status/recover",
            }:
                return FakeResponse({"ok": False, "error": "method not allowed"}, status=405)
            if parsed.path in {
                "/gca/email-registrations",
                "/gca/contact-suppressions",
                "/gca/wallet-verifications",
                "/gca/member-access",
                "/gca/credit-ledger",
                "/gca/service-requests",
                "/gca/credit-usage",
                "/gca/member-ledger",
                "/gca/member-reviews",
                "/gca/holding-verifications",
                "/gca/member-benefit-transfers",
                "/gca/account-status/recovery-requests",
            }:
                if not request.headers.get("Authorization"):
                    return FakeResponse({"ok": False, "error": "admin authorization is required"}, status=401)
                if parsed.path == "/gca/email-registrations":
                    return FakeResponse({
                        "ok": True,
                        "count": 1,
                        "records": [{"email": "private-user@example.com", "status": "received"}],
                    })
                if parsed.path == "/gca/contact-suppressions":
                    return FakeResponse({
                        "ok": True,
                        "count": 1,
                        "records": [{"email": "suppressed-user@example.com", "status": "suppressed"}],
                    })
                return FakeResponse({
                    "ok": True,
                    "count": 1,
                    "records": [{"walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d", "status": "verified"}],
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
        self.assertFalse(result["boundaries"]["submitsWalletVerification"])
        self.assertFalse(result["boundaries"]["submitsMemberAccess"])
        self.assertFalse(result["boundaries"]["submitsAccountStatus"])
        self.assertFalse(result["boundaries"]["submitsAccountStatusRotation"])
        self.assertFalse(result["boundaries"]["submitsAccountStatusRecoveryRequest"])
        self.assertFalse(result["boundaries"]["submitsAccountStatusRecoveryApproval"])
        self.assertFalse(result["boundaries"]["submitsAccountStatusRecoveryCompletion"])
        self.assertFalse(result["boundaries"]["submitsServiceRequest"])
        self.assertFalse(result["boundaries"]["submitsMemberReview"])
        self.assertFalse(result["boundaries"]["submitsHoldingVerification"])
        self.assertFalse(result["boundaries"]["submitsMemberBenefitTransfer"])
        self.assertFalse(result["boundaries"]["automaticTokenTransfer"])
        self.assertFalse(result["boundaries"]["adminTokenPrinted"])
        self.assertFalse(result["boundaries"]["userEmailsPrinted"])
        self.assertFalse(result["boundaries"]["publicOnly"])
        self.assertTrue(result["boundaries"]["adminReadTokenRequired"])
        self.assertTrue(result["boundaries"]["tokenProtectedAdminReadChecked"])
        self.assertEqual({item["method"] for item in seen}, {"GET", "OPTIONS"})
        self.assertEqual(len(result["checks"]), 37)
        self.assertTrue(any(item["id"] == "admin-email-registrations-read" for item in result["checks"]))
        self.assertTrue(any(item["id"] == "admin-member-ledger-read" for item in result["checks"]))
        self.assertTrue(any(item["id"] == "admin-member-reviews-read" for item in result["checks"]))
        self.assertTrue(any(item["id"] == "admin-holding-verifications-read" for item in result["checks"]))
        self.assertTrue(any(item["id"] == "admin-member-benefit-transfers-read" for item in result["checks"]))
        self.assertTrue(any(item["id"] == "admin-account-status-recovery-requests-read" for item in result["checks"]))
        self.assertFalse(any(item["id"] == "admin-credit-usage-read" for item in result["checks"]))
        self.assertTrue(any(item.get("antiSpamHoneypotFields") == ["website", "company", "homepage"] for item in result["checks"]))
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
                return FakeResponse(HEALTH_PAYLOAD)
            if parsed.path == "/gca/access-config":
                return FakeResponse(ACCESS_CONFIG_PAYLOAD)
            if method == "OPTIONS":
                return FakeResponse(
                    None,
                    status=204,
                    headers={
                        "access-control-allow-origin": "https://gcagochina.com",
                        "access-control-allow-methods": "GET,POST,OPTIONS",
                    },
                )
            if parsed.path in {
                "/gca/account-status",
                "/gca/account-status/rotate",
                "/gca/account-status/recovery-approvals",
                "/gca/account-status/recover",
            }:
                return FakeResponse({"ok": False, "error": "method not allowed"}, status=405)
            return FakeResponse({"ok": False, "error": "admin authorization is required"}, status=401)

        result = run_checks(base_url="https://worker.example", public_only=True, opener=opener)
        self.assertTrue(result["ok"])
        self.assertTrue(result["boundaries"]["publicOnly"])
        self.assertFalse(result["boundaries"]["adminReadTokenRequired"])
        self.assertFalse(result["boundaries"]["tokenProtectedAdminReadChecked"])
        self.assertEqual(len(result["checks"]), 27)
        self.assertNotIn("admin-email-registrations-read", {item["id"] for item in result["checks"]})
        self.assertTrue(all(item["authorization"] == "" for item in seen))

    def test_pending_service_request_route_can_be_checked_explicitly(self):
        seen = []

        def opener(request, **kwargs):
            parsed = urlparse(request.full_url)
            method = request.get_method()
            seen.append({"method": method, "path": parsed.path})
            if parsed.path == "/health":
                return FakeResponse(HEALTH_PAYLOAD)
            if parsed.path == "/gca/access-config":
                return FakeResponse(ACCESS_CONFIG_PAYLOAD)
            if method == "OPTIONS":
                return FakeResponse(
                    None,
                    status=204,
                    headers={
                        "access-control-allow-origin": "https://gcagochina.com",
                        "access-control-allow-methods": "GET,POST,OPTIONS",
                    },
                )
            if parsed.path in {
                "/gca/account-status",
                "/gca/account-status/rotate",
                "/gca/account-status/recovery-approvals",
                "/gca/account-status/recover",
            }:
                return FakeResponse({"ok": False, "error": "method not allowed"}, status=405)
            if not request.headers.get("Authorization"):
                return FakeResponse({"ok": False, "error": "admin authorization is required"}, status=401)
            return FakeResponse({"ok": True, "count": 0, "records": []})

        result = run_checks(
            base_url="https://worker.example",
            token="secret-token",
            limit=1,
            include_pending_routes=True,
            opener=opener,
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["boundaries"]["pendingWorkerRoutesIncluded"])
        health = next(item for item in result["checks"] if item["id"] == "health")
        self.assertEqual(health["workerRelease"], "gca-registration-worker-2026-07-27-account-status-recovery-v1")
        self.assertEqual(health["contactEmail"], "support@gcagochina.com")
        self.assertEqual(len(result["checks"]), 43)
        self.assertTrue(any(item["id"] == "admin-service-requests-read" for item in result["checks"]))
        self.assertTrue(any(item["id"] == "admin-credit-usage-read" for item in result["checks"]))
        self.assertIn(("GET", "/gca/service-requests"), {(item["method"], item["path"]) for item in seen})

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
