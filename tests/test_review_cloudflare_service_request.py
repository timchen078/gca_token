import json
import unittest

from tools.review_cloudflare_service_request import (
    ServiceRequestReviewError,
    build_client_review_id,
    build_review_payload,
    safe_result,
    submit_service_request_review,
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


class ReviewCloudflareServiceRequestTests(unittest.TestCase):
    def test_service_request_id_must_match_production_shape(self):
        with self.assertRaises(ServiceRequestReviewError):
            build_review_payload(
                service_request_id="gca_service_req_not-valid",
                decision="approved",
                reason_code="scope_reviewed",
                reviewer_id="gca-operator",
                manual_review_confirmed=True,
                no_secrets_no_custody_confirmed=True,
                no_trading_permission_confirmed=True,
            )

    def test_review_requires_all_manual_safety_confirmations(self):
        with self.assertRaises(ServiceRequestReviewError):
            build_review_payload(
                service_request_id=(
                    "gca_service_req_11111111111111111111"
                ),
                decision="approved",
                reason_code="scope_reviewed",
                reviewer_id="gca-operator",
            )

    def test_delivered_requires_delivery_credit_and_reference(self):
        common = {
            "service_request_id": (
                "gca_service_req_11111111111111111111"
            ),
            "decision": "delivered",
            "reason_code": "delivery_reviewed",
            "reviewer_id": "gca-operator",
            "manual_review_confirmed": True,
            "no_secrets_no_custody_confirmed": True,
            "no_trading_permission_confirmed": True,
        }
        with self.assertRaises(ServiceRequestReviewError):
            build_review_payload(**common)
        with self.assertRaises(ServiceRequestReviewError):
            build_review_payload(
                **common,
                delivery_completed=True,
            )
        with self.assertRaises(ServiceRequestReviewError):
            build_review_payload(
                **common,
                delivery_completed=True,
                credit_settlement_accepted=True,
            )

    def test_more_information_requires_public_member_prompt(self):
        common = {
            "service_request_id": (
                "gca_service_req_11111111111111111111"
            ),
            "decision": "needs_more_information",
            "reason_code": "missing_context",
            "reviewer_id": "gca-operator",
            "manual_review_confirmed": True,
            "no_secrets_no_custody_confirmed": True,
            "no_trading_permission_confirmed": True,
        }
        with self.assertRaises(ServiceRequestReviewError):
            build_review_payload(**common)

        payload = build_review_payload(
            **common,
            member_prompt=(
                "Please provide the non-sensitive market and timeframe context."
            ),
        )
        self.assertEqual(
            payload["memberPrompt"],
            "Please provide the non-sensitive market and timeframe context.",
        )

        with self.assertRaises(ServiceRequestReviewError):
            build_review_payload(
                service_request_id=common["service_request_id"],
                decision="approved",
                reason_code="scope_reviewed",
                reviewer_id="gca-operator",
                member_prompt="This prompt must not be accepted.",
                manual_review_confirmed=True,
                no_secrets_no_custody_confirmed=True,
                no_trading_permission_confirmed=True,
            )

    def test_payload_uses_deterministic_idempotency_and_boundaries(self):
        kwargs = {
            "service_request_id": (
                "gca_service_req_11111111111111111111"
            ),
            "decision": "delivered",
            "reason_code": "delivery_reviewed",
            "reviewer_id": "gca-operator",
            "delivery_reference": "support-ticket-42",
            "manual_review_confirmed": True,
            "no_secrets_no_custody_confirmed": True,
            "no_trading_permission_confirmed": True,
            "delivery_completed": True,
            "credit_settlement_accepted": True,
        }
        first = build_review_payload(**kwargs)
        second = build_review_payload(**kwargs)

        self.assertEqual(
            first["packetVersion"],
            "gca_service_request_review_v1",
        )
        self.assertEqual(
            first["clientReviewId"],
            second["clientReviewId"],
        )
        self.assertEqual(
            first["clientReviewId"],
            build_client_review_id(
                service_request_id=kwargs["service_request_id"],
                decision=kwargs["decision"],
                reason_code=kwargs["reason_code"],
                delivery_reference=kwargs[
                    "delivery_reference"
                ],
            ),
        )
        self.assertTrue(
            first["acknowledgements"][
                "manualReviewCompleted"
            ]
        )
        self.assertTrue(
            first["acknowledgements"][
                "noSecretsNoCustody"
            ]
        )
        self.assertTrue(
            first["acknowledgements"][
                "noTradingPermission"
            ]
        )
        self.assertTrue(
            first["acknowledgements"]["deliveryCompleted"]
        )
        self.assertTrue(
            first["acknowledgements"][
                "creditSettlementAccepted"
            ]
        )

    def test_submit_and_safe_result_redact_sensitive_values(self):
        seen = {}
        response_payload = {
            "ok": True,
            "idempotentReplay": False,
            "serviceRequestReview": {
                "serviceRequestReviewId": (
                    "gca_service_review_22222222222222222222"
                ),
                "serviceRequestId": (
                    "gca_service_req_11111111111111111111"
                ),
                "decision": "delivered",
                "operatorNote": "private note",
                "memberPrompt": "public prompt not printed by safe result",
            },
            "serviceRequest": {
                "status": "delivered",
                "email": "private@example.com",
                "walletAddress": (
                    "0x18d0007bc6be029f8ccd7cb13e324aa21891092d"
                ),
            },
            "creditUsage": {
                "creditUsageId": (
                    "gca_credit_use_33333333333333333333"
                ),
                "creditAmountUsed": 15,
            },
            "creditLedger": {
                "remainingCredits": 85,
                "emailSha256": "private-hash",
            },
            "boundaries": {
                "requiresSignature": False,
                "requiresTransaction": False,
                "automaticTokenTransfer": False,
                "createsTradingPermission": False,
            },
        }

        def opener(request, **kwargs):
            seen["method"] = request.get_method()
            seen["authorization"] = request.headers.get(
                "Authorization"
            )
            seen["payload"] = json.loads(
                request.data.decode("utf-8")
            )
            seen["timeout"] = kwargs["timeout"]
            return FakeResponse(response_payload)

        result = submit_service_request_review(
            base_url="https://worker.example",
            token="secret-admin-token",
            payload=build_review_payload(
                service_request_id=(
                    "gca_service_req_11111111111111111111"
                ),
                decision="delivered",
                reason_code="delivery_reviewed",
                reviewer_id="gca-operator",
                delivery_reference="support-ticket-42",
                manual_review_confirmed=True,
                no_secrets_no_custody_confirmed=True,
                no_trading_permission_confirmed=True,
                delivery_completed=True,
                credit_settlement_accepted=True,
            ),
            timeout=7,
            opener=opener,
        )
        public_result = safe_result(result)
        serialized = json.dumps(public_result)

        self.assertEqual(seen["method"], "POST")
        self.assertEqual(
            seen["authorization"],
            "Bearer secret-admin-token",
        )
        self.assertEqual(seen["timeout"], 7)
        self.assertEqual(
            seen["payload"]["decision"],
            "delivered",
        )
        self.assertEqual(
            public_result["requestStatus"],
            "delivered",
        )
        self.assertEqual(
            public_result["creditAmountUsed"],
            15,
        )
        self.assertEqual(public_result["remainingCredits"], 85)
        self.assertFalse(
            public_result["automaticTokenTransfer"]
        )
        self.assertFalse(
            public_result["createsTradingPermission"]
        )
        self.assertTrue(public_result["memberPromptPublished"])
        self.assertNotIn("secret-admin-token", serialized)
        self.assertNotIn("private@example.com", serialized)
        self.assertNotIn("private note", serialized)
        self.assertNotIn("public prompt not printed", serialized)
        self.assertNotIn(
            "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
            serialized,
        )


if __name__ == "__main__":
    unittest.main()
