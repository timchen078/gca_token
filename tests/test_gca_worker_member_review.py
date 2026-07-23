import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER_SOURCE = ROOT / "cloudflare" / "gca-registration-worker" / "src" / "worker.mjs"
MEMBER_LEDGER_MIGRATION = (
    ROOT
    / "cloudflare"
    / "gca-registration-worker"
    / "migrations"
    / "0003_member_access_ledgers.sql"
)
MEMBER_REVIEW_MIGRATION = (
    ROOT
    / "cloudflare"
    / "gca-registration-worker"
    / "migrations"
    / "0006_member_reviews.sql"
)


class GcaWorkerMemberReviewTests(unittest.TestCase):
    def test_migration_preserves_preview_and_clears_unreviewed_eligibility(self):
        database = sqlite3.connect(":memory:")
        try:
            database.executescript(MEMBER_LEDGER_MIGRATION.read_text(encoding="utf-8"))
            database.execute(
                """
                INSERT INTO gca_wallet_verifications (
                  wallet_verification_id,
                  account_id,
                  email_hash,
                  wallet_address,
                  chain_id,
                  contract_address,
                  checked_at,
                  raw_balance,
                  gca_balance,
                  holder_bonus_eligible,
                  gca_member_eligible,
                  gca_member_holding_period_eligible,
                  holding_period_days_verified,
                  evidence_tx_hash,
                  evidence_tx_hash_format_ok,
                  verification_provider,
                  status,
                  requires_signature,
                  requires_transaction
                ) VALUES (
                  'gca_wallet_test',
                  'gca_account_test',
                  'email_hash',
                  '0x18d0007bc6be029f8ccd7cb13e324aa21891092d',
                  8453,
                  '0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6',
                  '2026-07-24T00:00:00Z',
                  '1000000000000000000000000',
                  '1000000',
                  1,
                  1,
                  1,
                  30,
                  '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                  1,
                  'test',
                  'verified',
                  0,
                  0
                )
                """
            )

            database.executescript(MEMBER_REVIEW_MIGRATION.read_text(encoding="utf-8"))

            eligibility = database.execute(
                """
                SELECT
                  gca_member_holding_period_eligible,
                  holding_period_preview_eligible
                FROM gca_wallet_verifications
                WHERE wallet_verification_id = 'gca_wallet_test'
                """
            ).fetchone()
            self.assertEqual(eligibility, (0, 1))
            review_columns = {
                row[1]
                for row in database.execute("PRAGMA table_info(gca_member_reviews)").fetchall()
            }
            self.assertIn("member_review_id", review_columns)
            self.assertIn("decision", review_columns)
            self.assertIn("automatic_token_transfer", review_columns)
            self.assertIn("writes_wallet", review_columns)
        finally:
            database.close()

    def test_worker_requires_manual_review_before_member_activation(self):
        source = WORKER_SOURCE.read_text(encoding="utf-8")

        self.assertIn('const MEMBER_REVIEW_VERSION = "gca_member_review_v1";', source)
        self.assertIn(
            'const WORKER_RELEASE = "gca-registration-worker-2026-07-24-member-review-v1";',
            source,
        )
        self.assertIn("gcaMemberHoldingPeriodEligible: false", source)
        self.assertIn('const status = "queued";', source)
        self.assertIn('"pending_manual_review"', source)
        self.assertIn('if (!isAdminAuthorized(request, env))', source)
        self.assertIn("acknowledgements.manualEvidenceReviewCompleted === true", source)
        self.assertIn("acknowledgements.noAutomaticTokenTransfer === true", source)
        self.assertIn('url.pathname === "/gca/member-reviews"', source)
        self.assertIn("await db.batch([insertReview, updateMemberLedger, updateMemberAccount]);", source)
        self.assertIn("rawBalance >= MEMBER_THRESHOLD_UNITS", source)
        self.assertIn("holdingPeriodPreviewDays < MEMBER_HOLD_DAYS", source)
        self.assertIn("!evidenceTxHashFormatOk", source)
        self.assertIn("automaticTokenTransfer: false", source)
        self.assertIn("authorizesMemberBenefitTransfer: false", source)
        self.assertIn("createsTradingPermission: false", source)

    def test_member_review_migration_has_append_only_review_rows(self):
        migration = MEMBER_REVIEW_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE IF NOT EXISTS gca_member_reviews", migration)
        self.assertNotIn("UNIQUE (member_ledger_id)", migration)
        self.assertIn("previous_member_status TEXT NOT NULL", migration)
        self.assertIn("resulting_member_status TEXT NOT NULL", migration)
        self.assertIn("requires_signature INTEGER NOT NULL DEFAULT 0", migration)
        self.assertIn("requires_transaction INTEGER NOT NULL DEFAULT 0", migration)
        self.assertIn("automatic_token_transfer INTEGER NOT NULL DEFAULT 0", migration)
        self.assertIn("writes_wallet INTEGER NOT NULL DEFAULT 0", migration)


if __name__ == "__main__":
    unittest.main()
