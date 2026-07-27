CREATE TABLE IF NOT EXISTS gca_member_benefit_transfers (
  transfer_record_id TEXT PRIMARY KEY,
  packet_version TEXT NOT NULL,
  member_ledger_id TEXT NOT NULL UNIQUE,
  account_id TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  source_wallet TEXT NOT NULL,
  recipient_wallet TEXT NOT NULL,
  chain_id INTEGER NOT NULL,
  contract_address TEXT NOT NULL,
  transaction_hash TEXT NOT NULL UNIQUE,
  receipt_block_number INTEGER NOT NULL,
  receipt_block_hash TEXT NOT NULL,
  safe_snapshot_block_number INTEGER NOT NULL,
  safe_snapshot_block_hash TEXT NOT NULL,
  transfer_log_index INTEGER NOT NULL,
  amount_raw TEXT NOT NULL,
  amount_gca TEXT NOT NULL,
  verification_provider TEXT NOT NULL,
  verification_status TEXT NOT NULL,
  verified_at TEXT NOT NULL,
  reviewer_id TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  operator_note TEXT,
  source TEXT NOT NULL,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0,
  writes_wallet INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_member_benefit_transfers_wallet
  ON gca_member_benefit_transfers (wallet_address);

CREATE INDEX IF NOT EXISTS idx_gca_member_benefit_transfers_verified_at
  ON gca_member_benefit_transfers (verified_at DESC);

ALTER TABLE gca_member_ledger
  ADD COLUMN member_benefit_transfer_record_id TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_member_ledger
  ADD COLUMN member_benefit_transfer_verified_at TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_member_ledger
  ADD COLUMN member_benefit_transfer_verification_status TEXT NOT NULL DEFAULT '';
