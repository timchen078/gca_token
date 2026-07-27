ALTER TABLE gca_account_status_access
  ADD COLUMN recovered_at TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_account_status_access
  ADD COLUMN recovery_request_id TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS gca_account_status_recovery_requests (
  recovery_request_id TEXT PRIMARY KEY,
  packet_version TEXT NOT NULL,
  account_id TEXT NOT NULL,
  email_hash TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  new_token_hash TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  requested_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  recovery_credential_hash TEXT NOT NULL DEFAULT '',
  recovery_credential_expires_at TEXT NOT NULL DEFAULT '',
  approved_at TEXT NOT NULL DEFAULT '',
  consumed_at TEXT NOT NULL DEFAULT '',
  cancelled_at TEXT NOT NULL DEFAULT '',
  operator_id TEXT NOT NULL DEFAULT '',
  reason_code TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL,
  user_agent TEXT NOT NULL DEFAULT '',
  ip_hash TEXT,
  registered_email_verified INTEGER NOT NULL DEFAULT 0,
  manual_identity_review_completed INTEGER NOT NULL DEFAULT 0,
  no_secrets_requested INTEGER NOT NULL DEFAULT 1,
  changes_account_or_ledgers INTEGER NOT NULL DEFAULT 0,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_account_status_recovery_account_id
  ON gca_account_status_recovery_requests (account_id);

CREATE INDEX IF NOT EXISTS idx_gca_account_status_recovery_status
  ON gca_account_status_recovery_requests (status, requested_at);

CREATE INDEX IF NOT EXISTS idx_gca_account_status_recovery_expires_at
  ON gca_account_status_recovery_requests (expires_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_gca_account_status_recovery_credential_hash
  ON gca_account_status_recovery_requests (recovery_credential_hash)
  WHERE recovery_credential_hash <> '';

CREATE INDEX IF NOT EXISTS idx_gca_account_status_access_recovered_at
  ON gca_account_status_access (recovered_at);
