CREATE TABLE IF NOT EXISTS gca_member_accounts (
  account_id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  email_hash TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  display_name TEXT,
  source TEXT NOT NULL,
  language TEXT NOT NULL,
  program_intent TEXT NOT NULL,
  holding_start_date TEXT,
  evidence_tx_hash TEXT,
  contact_consent_accepted INTEGER NOT NULL,
  security_boundary_accepted INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  user_agent TEXT,
  ip_hash TEXT,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_member_accounts_email_hash
  ON gca_member_accounts (email_hash);

CREATE INDEX IF NOT EXISTS idx_gca_member_accounts_wallet
  ON gca_member_accounts (wallet_address);

CREATE INDEX IF NOT EXISTS idx_gca_member_accounts_updated_at
  ON gca_member_accounts (updated_at DESC);

CREATE TABLE IF NOT EXISTS gca_wallet_verifications (
  wallet_verification_id TEXT PRIMARY KEY,
  account_id TEXT,
  email_hash TEXT,
  wallet_address TEXT NOT NULL,
  chain_id INTEGER NOT NULL,
  contract_address TEXT NOT NULL,
  checked_at TEXT NOT NULL,
  raw_balance TEXT NOT NULL,
  gca_balance TEXT NOT NULL,
  holder_bonus_eligible INTEGER NOT NULL,
  gca_member_eligible INTEGER NOT NULL,
  gca_member_holding_period_eligible INTEGER NOT NULL,
  holding_period_days_verified INTEGER NOT NULL,
  evidence_tx_hash TEXT,
  evidence_tx_hash_format_ok INTEGER NOT NULL,
  verification_provider TEXT NOT NULL,
  status TEXT NOT NULL,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_wallet_verifications_wallet
  ON gca_wallet_verifications (wallet_address);

CREATE INDEX IF NOT EXISTS idx_gca_wallet_verifications_checked_at
  ON gca_wallet_verifications (checked_at DESC);

CREATE TABLE IF NOT EXISTS gca_credit_ledger (
  credit_ledger_id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  email_hash TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  credit_amount INTEGER NOT NULL,
  credit_type TEXT NOT NULL,
  activated_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  remaining_credits INTEGER NOT NULL,
  source TEXT NOT NULL,
  transferable INTEGER NOT NULL DEFAULT 0,
  cash_redeemable INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gca_credit_ledger_wallet
  ON gca_credit_ledger (wallet_address);

CREATE TABLE IF NOT EXISTS gca_member_ledger (
  member_ledger_id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  email_hash TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  tier_name TEXT NOT NULL,
  verified_balance TEXT NOT NULL,
  holding_start_date TEXT,
  holding_period_days_verified INTEGER NOT NULL,
  evidence_tx_hash TEXT,
  evidence_tx_hash_format_ok INTEGER NOT NULL,
  member_benefit_review_evidence_status TEXT NOT NULL,
  member_benefit_amount TEXT NOT NULL,
  member_benefit_claim_status TEXT NOT NULL,
  member_benefit_transfer_tx TEXT,
  activated_at TEXT,
  next_refresh_due_at TEXT,
  requires_manual_reserve_transfer_review INTEGER NOT NULL DEFAULT 1,
  automatic_transfer INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gca_member_ledger_wallet
  ON gca_member_ledger (wallet_address);

CREATE INDEX IF NOT EXISTS idx_gca_member_ledger_status
  ON gca_member_ledger (status);
