import json
import shutil
import sqlite3
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER_DIR = ROOT / "cloudflare" / "gca-registration-worker"
WORKER_SOURCE = WORKER_DIR / "src" / "worker.mjs"
STATUS_MODULE = WORKER_DIR / "src" / "account-status.mjs"
MEMBER_ACCESS_PAGE = ROOT / "site" / "gca" / "member-access" / "index.html"
MIGRATIONS = [
    WORKER_DIR / "migrations" / "0003_member_access_ledgers.sql",
    WORKER_DIR / "migrations" / "0006_member_reviews.sql",
    WORKER_DIR / "migrations" / "0007_holding_history_verifications.sql",
    WORKER_DIR / "migrations" / "0008_member_benefit_transfer_evidence.sql",
    WORKER_DIR / "migrations" / "0009_account_status_access.sql",
    WORKER_DIR / "migrations" / "0010_account_status_rotation.sql",
    WORKER_DIR / "migrations" / "0011_account_status_recovery.sql",
]
BUNDLED_NODE = (
    Path.home()
    / ".cache"
    / "codex-runtimes"
    / "codex-primary-runtime"
    / "dependencies"
    / "node"
    / "bin"
    / "node"
)


class GcaAccountStatusTests(unittest.TestCase):
    def test_migration_stores_only_status_token_hash_and_read_only_boundaries(self):
        database = sqlite3.connect(":memory:")
        try:
            for migration in MIGRATIONS:
                database.executescript(migration.read_text(encoding="utf-8"))

            columns = {
                row[1]
                for row in database.execute(
                    "PRAGMA table_info(gca_account_status_access)"
                ).fetchall()
            }
            indexes = {
                row[1]: bool(row[2])
                for row in database.execute(
                    "PRAGMA index_list(gca_account_status_access)"
                ).fetchall()
            }

            self.assertIn("token_hash", columns)
            self.assertNotIn("status_access_token", columns)
            self.assertNotIn("email", columns)
            self.assertIn("read_only", columns)
            self.assertIn("returns_email", columns)
            self.assertIn("returns_token", columns)
            self.assertIn("requires_signature", columns)
            self.assertIn("requires_transaction", columns)
            self.assertIn("automatic_token_transfer", columns)
            self.assertIn("previous_token_hash", columns)
            self.assertIn("previous_token_expires_at", columns)
            self.assertIn("rotated_at", columns)
            self.assertIn("recovered_at", columns)
            self.assertIn("recovery_request_id", columns)
            self.assertTrue(any(indexes.values()))
            migration_source = MIGRATIONS[-1].read_text(encoding="utf-8")
            self.assertNotIn("currentStatusAccessToken", migration_source)
            self.assertNotIn("newStatusAccessToken", migration_source)
            self.assertNotIn("recoveryCredential TEXT", migration_source)
            recovery_columns = {
                row[1]
                for row in database.execute(
                    "PRAGMA table_info(gca_account_status_recovery_requests)"
                ).fetchall()
            }
            self.assertIn("new_token_hash", recovery_columns)
            self.assertIn("recovery_credential_hash", recovery_columns)
            self.assertNotIn("new_status_access_token", recovery_columns)
            self.assertNotIn("recovery_credential", recovery_columns)
            self.assertNotIn("email", recovery_columns)
            self.assertIn("registered_email_verified", recovery_columns)
            self.assertIn("manual_identity_review_completed", recovery_columns)
            self.assertIn("changes_account_or_ledgers", recovery_columns)
        finally:
            database.close()

    def test_public_status_builder_redacts_identity_and_access_key(self):
        node = shutil.which("node") or (str(BUNDLED_NODE) if BUNDLED_NODE.exists() else "")
        if not node:
            self.skipTest("Node.js is not available")
        script = r"""
import { pathToFileURL } from "node:url";
const status = await import(pathToFileURL(process.argv[1]).href);
const token = `gca_status_${"A".repeat(43)}`;
const payload = status.buildPublicAccountStatus({
  account: {
    accountId: "gca_account_0123456789abcdef0123",
    email: "private@example.com",
    emailSha256: "secret-email-hash",
    walletAddress: "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
    status: "member_active",
    createdAt: "2026-07-01T00:00:00Z",
    updatedAt: "2026-07-27T00:00:00Z"
  },
  walletVerification: {
    walletVerificationId: "gca_wallet_0123456789abcdef0123",
    emailSha256: "secret-email-hash",
    walletAddress: "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
    checkedAt: "2026-07-27T00:00:00Z",
    gcaBalance: "1000000",
    holderBonusEligible: true,
    gcaMemberEligible: true,
    holdingPeriodDaysVerified: 30,
    status: "verified"
  },
  creditLedger: {
    creditLedgerId: "gca_credit_0123456789abcdef0123",
    creditAmount: 100,
    remainingCredits: 80,
    activatedAt: "2026-07-01T00:00:00Z",
    expiresAt: "2026-12-28T00:00:00Z",
    status: "ledger_recorded"
  },
  memberLedger: {
    memberLedgerId: "gca_member_0123456789abcdef0123",
    tierName: "GCA Member",
    verifiedBalance: "1000000",
    holdingPeriodDaysVerified: 30,
    memberBenefitReviewEvidenceStatus: "approved",
    memberBenefitAmount: "10000 GCA",
    memberBenefitClaimStatus: "pending_manual_reserve_transfer",
    memberBenefitTransferTx: "",
    memberBenefitTransferVerifiedAt: "",
    memberBenefitTransferVerificationStatus: "",
    activatedAt: "2026-07-27T00:00:00Z",
    nextRefreshDueAt: "2026-08-26T00:00:00Z",
    onchainHoldingVerified: true,
    onchainHoldingVerifiedAt: "2026-07-27T00:00:00Z",
    status: "active",
    updatedAt: "2026-07-27T00:00:00Z"
  },
  checkedAt: "2026-07-27T00:00:00Z",
  nextStep: "Manual reserve-wallet processing remains pending."
});
console.log(JSON.stringify({
  validToken: status.isStatusAccessToken(token),
  invalidToken: status.isStatusAccessToken("gca_status_short"),
  payload
}));
"""
        completed = subprocess.run(
            [node, "--input-type=module", "-e", script, str(STATUS_MODULE)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        serialized = json.dumps(result["payload"])

        self.assertTrue(result["validToken"])
        self.assertFalse(result["invalidToken"])
        self.assertEqual(
            result["payload"]["account"]["walletAddressMasked"],
            "0x18d000...092d",
        )
        self.assertNotIn("private@example.com", serialized)
        self.assertNotIn("secret-email-hash", serialized)
        self.assertNotIn("gca_status_", serialized)
        self.assertNotIn(
            "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
            serialized,
        )
        self.assertFalse(result["payload"]["boundaries"]["emailReturned"])
        self.assertFalse(result["payload"]["boundaries"]["accessTokenReturned"])
        self.assertTrue(result["payload"]["boundaries"]["readOnlyStatusLookup"])

    def test_worker_status_route_is_read_only_and_device_key_protected(self):
        source = WORKER_SOURCE.read_text(encoding="utf-8")

        self.assertIn('const MEMBER_ACCESS_VERSION = "gca_member_access_v2";', source)
        self.assertIn('const ACCOUNT_STATUS_VERSION = "gca_account_status_v1";', source)
        self.assertIn(
            'const ACCOUNT_STATUS_ROTATION_VERSION = "gca_account_status_rotation_v1";',
            source,
        )
        self.assertIn(
            'const WORKER_RELEASE =\n  "gca-registration-worker-2026-07-30-service-request-delivery-v1";',
            source,
        )
        self.assertIn('url.pathname === "/gca/account-status"', source)
        self.assertIn('url.pathname === "/gca/account-status/rotate"', source)
        self.assertIn("device status access key is invalid or expired", source)
        self.assertIn(
            "device status access key is already assigned to another account",
            source,
        )
        self.assertLess(
            source.index("device status access key is already assigned to another account"),
            source.index("INSERT INTO gca_member_accounts"),
        )
        self.assertIn("buildPublicAccountStatus", source)
        self.assertIn("accountStatusTokenStoredAsSha256: true", source)
        self.assertIn("accountStatusReturnsEmail: false", source)
        self.assertIn("accountStatusReturnsAccessToken: false", source)
        self.assertIn("accountStatusKeyRotationEnabled: true", source)
        self.assertIn("accountStatusRotationReturnsAccessToken: false", source)
        self.assertIn("accountStatusRotationChangesAccountOrLedgers: false", source)
        self.assertIn("previous_token_hash = token_hash", source)
        self.assertIn("previous_token_expires_at > ?2", source)
        self.assertIn("the previous device key can only retry its completed rotation", source)
        self.assertIn("currentTokenReturned: false", source)
        self.assertIn("newTokenReturned: false", source)
        self.assertIn(
            'url.pathname === "/gca/account-status/recovery-requests"',
            source,
        )
        self.assertIn(
            'url.pathname === "/gca/account-status/recovery-approvals"',
            source,
        )
        self.assertIn(
            'url.pathname === "/gca/account-status/recover"',
            source,
        )
        self.assertIn(
            "accountStatusRecoveryMode: \"registered-email-manual-review\"",
            source,
        )
        self.assertIn("accountStatusRecoveryReturnsAccountMatch: false", source)
        self.assertIn(
            "accountStatusRecoveryStoresCredentialAsSha256: true",
            source,
        )
        self.assertIn("oldDeviceKeyInvalidated: true", source)
        self.assertIn("previousKeyRetryAllowed: false", source)
        self.assertIn("recoveryCredentialConsumed: true", source)
        self.assertIn("previous_token_hash = ''", source)
        self.assertIn("manualIdentityReviewRequired: true", source)
        self.assertNotIn("eth_sendTransaction", source)
        self.assertNotIn("personal_sign", source)

    def test_member_page_supports_recoverable_device_key_rotation(self):
        page = MEMBER_ACCESS_PAGE.read_text(encoding="utf-8")

        self.assertIn('id="rotateStatusKey"', page)
        self.assertIn('"/gca/account-status/rotate"', page)
        self.assertIn('"gca_account_status_rotation_v1"', page)
        self.assertIn("pendingRotation", page)
        self.assertIn("pendingStatusAccessRotation", page)
        self.assertIn("PENDING_STATUS_ACCESS_MAX_AGE_MS", page)
        self.assertIn("promotePendingStatusAccess", page)
        self.assertIn("readAccountStatusWithRecovery", page)
        self.assertIn("currentStatusAccessToken: statusAccess.token", page)
        self.assertIn(
            "newStatusAccessToken: pendingRotation.newToken",
            page,
        )
        self.assertIn(
            "The key is not included in review packets or API responses.",
            page,
        )
        self.assertIn('id="openRecovery"', page)
        self.assertIn('id="recoveryBlock"', page)
        self.assertIn('id="recoveryCredential"', page)
        self.assertIn('"/gca/account-status/recovery-requests"', page)
        self.assertIn('"/gca/account-status/recover"', page)
        self.assertIn('"gca_account_status_recovery_request_v1"', page)
        self.assertIn('"gca_account_status_recovery_v1"', page)
        self.assertIn("RECOVERY_DRAFT_KEY", page)
        self.assertIn("newToken: newStatusAccessToken()", page)
        self.assertIn("recoveryCredential: credential", page)
        self.assertIn("removeRecoveryDraft()", page)
        self.assertIn(
            "The public response does not confirm whether an account exists.",
            page,
        )
        self.assertNotIn(
            "reviewPacket.value = JSON.stringify(sessionStatusAccess",
            page,
        )
        self.assertNotIn(
            "reviewPacket.value = JSON.stringify(loadRecoveryDraft",
            page,
        )


if __name__ == "__main__":
    unittest.main()
