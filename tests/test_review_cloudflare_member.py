import json
import unittest

from tools.review_cloudflare_member import (
    MemberReviewError,
    build_review_payload,
    safe_result,
    submit_member_review,
)


class FakeResponse:
    def __init__(self, payload, status=201):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ReviewCloudflareMemberTests(unittest.TestCase):
    def test_member_ledger_id_must_match_production_shape(self):
        with self.assertRaises(MemberReviewError):
            build_review_payload(
                member_ledger_id="gca_member_not-a-production-id",
                decision="needs_more_information",
                reason_code="missing_public_evidence",
                reviewer_id="gca-operator",
            )

    def test_approved_review_requires_explicit_evidence_confirmation(self):
        with self.assertRaises(MemberReviewError):
            build_review_payload(
                member_ledger_id="gca_member_11111111111111111111",
                decision="approved",
                reason_code="holding_evidence_reviewed",
                reviewer_id="gca-operator",
            )

    def test_build_review_payload_keeps_manual_boundaries(self):
        payload = build_review_payload(
            member_ledger_id="GCA_MEMBER_11111111111111111111",
            decision="approved",
            reason_code="HOLDING_EVIDENCE_REVIEWED",
            reviewer_id="GCA-OPERATOR",
            operator_note="Reviewed against public evidence.",
            evidence_reviewed=True,
        )

        self.assertEqual(payload["packetVersion"], "gca_member_review_v1")
        self.assertEqual(payload["memberLedgerId"], "gca_member_11111111111111111111")
        self.assertEqual(payload["decision"], "approved")
        self.assertTrue(payload["acknowledgements"]["manualEvidenceReviewCompleted"])
        self.assertTrue(payload["acknowledgements"]["noAutomaticTokenTransfer"])

    def test_submit_and_safe_result_do_not_expose_sensitive_values(self):
        seen = {}
        response_payload = {
            "ok": True,
            "memberReview": {
                "memberReviewId": "gca_member_review_22222222222222222222",
                "memberLedgerId": "gca_member_11111111111111111111",
                "decision": "approved",
                "resultingMemberStatus": "active",
                "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
            },
            "memberLedger": {
                "memberBenefitClaimStatus": "pending_manual_reserve_transfer",
                "email": "private@example.com",
            },
            "boundaries": {
                "automaticTokenTransfer": False,
                "authorizesMemberBenefitTransfer": False,
            },
        }

        def opener(request, **kwargs):
            seen["method"] = request.get_method()
            seen["authorization"] = request.headers.get("Authorization")
            seen["content_type"] = request.headers.get("Content-type")
            seen["payload"] = json.loads(request.data.decode("utf-8"))
            seen["timeout"] = kwargs["timeout"]
            return FakeResponse(response_payload)

        result = submit_member_review(
            base_url="https://worker.example",
            token="secret-admin-token",
            payload=build_review_payload(
                member_ledger_id="gca_member_11111111111111111111",
                decision="approved",
                reason_code="holding_evidence_reviewed",
                reviewer_id="gca-operator",
                evidence_reviewed=True,
            ),
            timeout=7,
            opener=opener,
        )
        public_result = safe_result(result)
        serialized = json.dumps(public_result)

        self.assertEqual(seen["method"], "POST")
        self.assertEqual(seen["authorization"], "Bearer secret-admin-token")
        self.assertEqual(seen["content_type"], "application/json")
        self.assertEqual(seen["timeout"], 7)
        self.assertEqual(seen["payload"]["decision"], "approved")
        self.assertEqual(public_result["resultingMemberStatus"], "active")
        self.assertFalse(public_result["automaticTokenTransfer"])
        self.assertFalse(public_result["authorizesMemberBenefitTransfer"])
        self.assertNotIn("secret-admin-token", serialized)
        self.assertNotIn("private@example.com", serialized)
        self.assertNotIn("0x18d0007bc6be029f8ccd7cb13e324aa21891092d", serialized)


if __name__ == "__main__":
    unittest.main()
