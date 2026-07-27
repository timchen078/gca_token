import json
import stat
import tempfile
import unittest
from pathlib import Path

from tools.approve_cloudflare_account_recovery import (
    AccountRecoveryError,
    build_approval_payload,
    safe_result,
    submit_recovery_approval,
    write_delivery_packet,
)


REQUEST_ID = "gca_recovery_request_" + ("a" * 20)
CREDENTIAL = "gca_recovery_" + ("B" * 43)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class GcaAccountRecoveryOperatorTests(unittest.TestCase):
    def test_approval_requires_registered_email_and_identity_confirmations(self):
        with self.assertRaises(AccountRecoveryError):
            build_approval_payload(
                recovery_request_id=REQUEST_ID,
                registered_email="member@example.com",
                operator_id="gca-operator",
                reason_code="registered_email_verified",
            )

        payload = build_approval_payload(
            recovery_request_id=REQUEST_ID,
            registered_email="MEMBER@example.com",
            operator_id="gca-operator",
            reason_code="registered_email_verified",
            registered_email_verified=True,
            identity_reviewed=True,
        )
        self.assertEqual(
            payload["packetVersion"],
            "gca_account_status_recovery_approval_v1",
        )
        self.assertEqual(payload["registeredEmail"], "member@example.com")
        self.assertTrue(
            payload["acknowledgements"][
                "registeredEmailOwnershipVerified"
            ]
        )
        self.assertTrue(
            payload["acknowledgements"]["manualIdentityReviewCompleted"]
        )
        self.assertTrue(payload["acknowledgements"]["noSecretsRequested"])
        self.assertTrue(payload["acknowledgements"]["noWalletAction"])

    def test_protected_submit_uses_bearer_token_and_validates_response(self):
        captured = {}

        def opener(request, **kwargs):
            captured["url"] = request.full_url
            captured["authorization"] = request.headers["Authorization"]
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = kwargs["timeout"]
            return FakeResponse(
                {
                    "ok": True,
                    "recoveryRequestId": REQUEST_ID,
                    "status": "approved",
                    "approvedAt": "2026-07-27T10:00:00Z",
                    "recoveryCredentialExpiresAt": "2026-07-28T10:00:00Z",
                    "recoveryCredential": CREDENTIAL,
                }
            )

        payload = build_approval_payload(
            recovery_request_id=REQUEST_ID,
            registered_email="member@example.com",
            operator_id="gca-operator",
            reason_code="registered_email_verified",
            registered_email_verified=True,
            identity_reviewed=True,
        )
        result = submit_recovery_approval(
            base_url="https://api.example",
            token="local-admin-token",
            payload=payload,
            opener=opener,
        )
        self.assertEqual(
            captured["url"],
            "https://api.example/gca/account-status/recovery-approvals",
        )
        self.assertEqual(
            captured["authorization"],
            "Bearer local-admin-token",
        )
        self.assertEqual(captured["body"], payload)
        self.assertEqual(result["recoveryCredential"], CREDENTIAL)

    def test_delivery_packet_is_private_and_safe_summary_omits_credential(self):
        result = {
            "ok": True,
            "recoveryRequestId": REQUEST_ID,
            "status": "approved",
            "approvedAt": "2026-07-27T10:00:00Z",
            "recoveryCredentialExpiresAt": "2026-07-28T10:00:00Z",
            "recoveryCredential": CREDENTIAL,
            "reissued": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "delivery.json"
            written = write_delivery_packet(
                output=output,
                registered_email="member@example.com",
                result=result,
            )
            mode = stat.S_IMODE(written.stat().st_mode)
            packet = json.loads(written.read_text(encoding="utf-8"))
            summary = safe_result(result, written)

        self.assertEqual(mode, 0o600)
        self.assertEqual(packet["recoveryCredential"], CREDENTIAL)
        self.assertEqual(packet["registeredEmail"], "member@example.com")
        self.assertNotIn("recoveryCredential", summary)
        self.assertTrue(summary["registeredEmailOnly"])
        self.assertFalse(summary["adminTokenPrinted"])
        self.assertFalse(summary["recoveryCredentialPrinted"])
        self.assertFalse(summary["walletActionRequired"])

    def test_delivery_packet_refuses_to_overwrite_existing_credential(self):
        result = {
            "recoveryRequestId": REQUEST_ID,
            "recoveryCredential": CREDENTIAL,
            "recoveryCredentialExpiresAt": "2026-07-28T10:00:00Z",
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "delivery.json"
            write_delivery_packet(
                output=output,
                registered_email="member@example.com",
                result=result,
            )
            with self.assertRaises(AccountRecoveryError):
                write_delivery_packet(
                    output=output,
                    registered_email="member@example.com",
                    result=result,
                )


if __name__ == "__main__":
    unittest.main()
