ALTER TABLE gca_account_status_access
  ADD COLUMN previous_token_hash TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_account_status_access
  ADD COLUMN previous_token_expires_at TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_account_status_access
  ADD COLUMN rotated_at TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_gca_account_status_access_previous_token_hash
  ON gca_account_status_access (previous_token_hash);

CREATE INDEX IF NOT EXISTS idx_gca_account_status_access_rotated_at
  ON gca_account_status_access (rotated_at);
