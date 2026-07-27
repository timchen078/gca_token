CREATE TABLE IF NOT EXISTS gca_account_status_access (
  status_access_id TEXT PRIMARY KEY,
  packet_version TEXT NOT NULL,
  account_id TEXT NOT NULL UNIQUE,
  token_hash TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL,
  read_only INTEGER NOT NULL DEFAULT 1,
  returns_email INTEGER NOT NULL DEFAULT 0,
  returns_token INTEGER NOT NULL DEFAULT 0,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_account_status_access_expires_at
  ON gca_account_status_access (expires_at);

CREATE INDEX IF NOT EXISTS idx_gca_account_status_access_account_id
  ON gca_account_status_access (account_id);
