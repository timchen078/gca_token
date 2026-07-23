ALTER TABLE gca_wallet_verifications
  ADD COLUMN holding_period_preview_eligible INTEGER NOT NULL DEFAULT 0;

UPDATE gca_wallet_verifications
SET
  holding_period_preview_eligible = gca_member_holding_period_eligible,
  gca_member_holding_period_eligible = 0;

CREATE TABLE IF NOT EXISTS gca_member_reviews (
  member_review_id TEXT PRIMARY KEY,
  member_ledger_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (
    decision IN ('approved', 'rejected', 'needs_more_information')
  ),
  reason_code TEXT NOT NULL,
  operator_note TEXT,
  reviewer_id TEXT NOT NULL,
  reviewed_at TEXT NOT NULL,
  source TEXT NOT NULL,
  balance_at_review TEXT NOT NULL,
  member_threshold_met INTEGER NOT NULL,
  holding_period_preview_days INTEGER NOT NULL,
  evidence_tx_hash TEXT,
  evidence_tx_hash_format_ok INTEGER NOT NULL,
  previous_member_status TEXT NOT NULL,
  resulting_member_status TEXT NOT NULL,
  previous_claim_status TEXT NOT NULL,
  resulting_claim_status TEXT NOT NULL,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0,
  writes_wallet INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_member_reviews_member_ledger
  ON gca_member_reviews (member_ledger_id);

CREATE INDEX IF NOT EXISTS idx_gca_member_reviews_wallet
  ON gca_member_reviews (wallet_address);

CREATE INDEX IF NOT EXISTS idx_gca_member_reviews_decision
  ON gca_member_reviews (decision);

CREATE INDEX IF NOT EXISTS idx_gca_member_reviews_reviewed_at
  ON gca_member_reviews (reviewed_at DESC);
