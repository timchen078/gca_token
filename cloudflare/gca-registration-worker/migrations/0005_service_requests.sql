CREATE TABLE IF NOT EXISTS gca_service_requests (
  service_request_id TEXT PRIMARY KEY,
  account_id TEXT,
  email TEXT NOT NULL,
  email_hash TEXT NOT NULL,
  wallet_address TEXT,
  credit_ledger_id TEXT,
  service_id TEXT NOT NULL,
  service_name TEXT NOT NULL,
  requested_credit_hold INTEGER NOT NULL,
  remaining_credits_at_request INTEGER,
  request_title TEXT,
  request_summary TEXT,
  market_context TEXT,
  preferred_language TEXT NOT NULL,
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  operator_review_required INTEGER NOT NULL DEFAULT 1,
  does_not_deduct_credits INTEGER NOT NULL DEFAULT 1,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0,
  writes_wallet INTEGER NOT NULL DEFAULT 0,
  creates_trading_permission INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_service_requests_credit_ledger
  ON gca_service_requests (credit_ledger_id);
CREATE INDEX IF NOT EXISTS idx_gca_service_requests_wallet
  ON gca_service_requests (wallet_address);
CREATE INDEX IF NOT EXISTS idx_gca_service_requests_email_hash
  ON gca_service_requests (email_hash);
CREATE INDEX IF NOT EXISTS idx_gca_service_requests_created_at
  ON gca_service_requests (created_at DESC);
