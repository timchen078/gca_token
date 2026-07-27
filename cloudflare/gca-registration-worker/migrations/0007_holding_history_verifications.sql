CREATE TABLE IF NOT EXISTS gca_holding_verifications (
  holding_verification_id TEXT PRIMARY KEY,
  member_ledger_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  chain_id INTEGER NOT NULL,
  contract_address TEXT NOT NULL,
  checked_at TEXT NOT NULL,
  window_start_at TEXT NOT NULL,
  window_end_at TEXT NOT NULL,
  snapshot_block_number INTEGER NOT NULL,
  snapshot_block_hash TEXT NOT NULL,
  current_raw_balance TEXT NOT NULL,
  current_gca_balance TEXT NOT NULL,
  window_start_raw_balance TEXT NOT NULL,
  window_start_gca_balance TEXT NOT NULL,
  minimum_raw_balance TEXT NOT NULL,
  minimum_gca_balance TEXT NOT NULL,
  threshold_raw_balance TEXT NOT NULL,
  threshold_gca_balance TEXT NOT NULL,
  observed_continuous_eligible INTEGER NOT NULL,
  history_complete INTEGER NOT NULL,
  reconstruction_consistent INTEGER NOT NULL,
  event_count INTEGER NOT NULL,
  blockscout_event_count INTEGER NOT NULL,
  rpc_event_count INTEGER NOT NULL,
  history_provider TEXT NOT NULL,
  status TEXT NOT NULL,
  failure_reason TEXT,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0,
  writes_wallet INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_holding_verifications_member_ledger
  ON gca_holding_verifications (member_ledger_id);

CREATE INDEX IF NOT EXISTS idx_gca_holding_verifications_wallet
  ON gca_holding_verifications (wallet_address);

CREATE INDEX IF NOT EXISTS idx_gca_holding_verifications_checked_at
  ON gca_holding_verifications (checked_at DESC);

ALTER TABLE gca_member_ledger
  ADD COLUMN latest_holding_verification_id TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_member_ledger
  ADD COLUMN onchain_holding_verified INTEGER NOT NULL DEFAULT 0;

ALTER TABLE gca_member_ledger
  ADD COLUMN onchain_holding_verified_at TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_member_reviews
  ADD COLUMN holding_verification_id TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_member_reviews
  ADD COLUMN onchain_holding_eligible INTEGER NOT NULL DEFAULT 0;

ALTER TABLE gca_member_reviews
  ADD COLUMN onchain_history_complete INTEGER NOT NULL DEFAULT 0;

ALTER TABLE gca_member_reviews
  ADD COLUMN onchain_minimum_balance TEXT NOT NULL DEFAULT '';
