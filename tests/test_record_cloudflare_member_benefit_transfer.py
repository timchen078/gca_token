import json
import unittest

from tools.record_cloudflare_member_benefit_transfer import (
    MemberBenefitTransferError,
    build_transfer_payload,
    safe_result,
    submit_transfer_evidence,
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


class RecordCloudflareMemberBenefitTransferTests(unittest.TestCase):
    def test_payload_requires_both_operator_confirmations(self):
        with self.assertRaises(MemberBenefitTransferError):
            build_transfer_payload(
                member_ledger_id="gca_member_11111111111111111111",
                transaction_hash=f"0x{'a' * 64}",
                reviewer_id="gca-operator",
            )

    def test_payload_keeps_manual_transfer_boundaries(self):
        payload = build_transfer_payload(
            member_ledger_id="GCA_MEMBER_11111111111111111111",
            transaction_hash=f"0x{'A' * 64}",
            reviewer_id="GCA-OPERATOR",
            manual_transfer_completed=True,
            public_transaction_evidence=True,
        )

        self.assertEqual(payload["packetVersion"], "gca_member_benefit_transfer_v1")
        self.assertEqual(payload["memberLedgerId"], "gca_member_11111111111111111111")
        self.assertEqual(payload["transactionHash"], f"0x{'a' * 64}")
        self.assertTrue(payload["acknowledgements"]["manualReserveTransferCompleted"])
        self.assertTrue(payload["acknowledgements"]["transactionEvidencePublic"])
        self.assertTrue(payload["acknowledgements"]["noAutomaticTokenTransfer"])

    def test_submit_and_safe_result_do_not_expose_token_or_private_record_data(self):
        seen = {}
        response_payload = {
            "ok": True,
            "alreadyRecorded": False,
            "memberBenefitTransfer": {
                "transferRecordId": "gca_benefit_transfer_22222222222222222222",
                "memberLedgerId": "gca_member_11111111111111111111",
                "transactionHash": f"0x{'a' * 64}",
                "amountGca": "10000",
                "verificationStatus": "verified",
                "safeSnapshotBlockNumber": 123,
                "walletAddress": "0x1111111111111111111111111111111111111111",
            },
            "memberLedger": {
                "memberBenefitClaimStatus": "transferred",
                "email": "private@example.com",
            },
            "boundaries": {
                "automaticTokenTransfer": False,
                "writesWallet": False,
                "authorizesAdditionalTransfer": False,
            },
        }

        def opener(request, **kwargs):
            seen["method"] = request.get_method()
            seen["authorization"] = request.headers.get("Authorization")
            seen["content_type"] = request.headers.get("Content-type")
            seen["payload"] = json.loads(request.data.decode("utf-8"))
            seen["timeout"] = kwargs["timeout"]
            return FakeResponse(response_payload)

        result = submit_transfer_evidence(
            base_url="https://worker.example",
            token="secret-admin-token",
            payload=build_transfer_payload(
                member_ledger_id="gca_member_11111111111111111111",
                transaction_hash=f"0x{'a' * 64}",
                reviewer_id="gca-operator",
                manual_transfer_completed=True,
                public_transaction_evidence=True,
            ),
            timeout=9,
            opener=opener,
        )
        public_result = safe_result(result)
        serialized = json.dumps(public_result)

        self.assertEqual(seen["method"], "POST")
        self.assertEqual(seen["authorization"], "Bearer secret-admin-token")
        self.assertEqual(seen["content_type"], "application/json")
        self.assertEqual(seen["timeout"], 9)
        self.assertEqual(public_result["verificationStatus"], "verified")
        self.assertEqual(public_result["memberBenefitClaimStatus"], "transferred")
        self.assertFalse(public_result["automaticTokenTransfer"])
        self.assertFalse(public_result["writesWallet"])
        self.assertFalse(public_result["authorizesAdditionalTransfer"])
        self.assertNotIn("secret-admin-token", serialized)
        self.assertNotIn("private@example.com", serialized)
        self.assertNotIn("0x1111111111111111111111111111111111111111", serialized)


if __name__ == "__main__":
    unittest.main()
