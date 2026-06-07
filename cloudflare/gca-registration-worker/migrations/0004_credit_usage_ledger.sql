CREATE TABLE IF NOT EXISTS gca_credit_usage (
  credit_usage_id TEXT PRIMARY KEY,
  credit_ledger_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  email_hash TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  service_id TEXT NOT NULL,
  service_name TEXT NOT NULL,
  credit_amount_used INTEGER NOT NULL,
  remaining_credits_before INTEGER NOT NULL,
  remaining_credits_after INTEGER NOT NULL,
  used_at TEXT NOT NULL,
  source TEXT NOT NULL,
  operator_note TEXT,
  status TEXT NOT NULL,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0,
  writes_wallet INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_credit_usage_credit_ledger
  ON gca_credit_usage (credit_ledger_id);

CREATE INDEX IF NOT EXISTS idx_gca_credit_usage_wallet
  ON gca_credit_usage (wallet_address);

CREATE INDEX IF NOT EXISTS idx_gca_credit_usage_used_at
  ON gca_credit_usage (used_at DESC);
