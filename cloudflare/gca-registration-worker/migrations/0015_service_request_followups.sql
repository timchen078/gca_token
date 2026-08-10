ALTER TABLE gca_service_request_reviews
  ADD COLUMN member_prompt TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS gca_service_request_followups (
  service_request_followup_id TEXT PRIMARY KEY,
  service_request_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  client_followup_id TEXT NOT NULL,
  packet_version TEXT NOT NULL,
  response_text TEXT NOT NULL,
  submitted_at TEXT NOT NULL,
  source TEXT NOT NULL,
  no_secrets_no_custody INTEGER NOT NULL DEFAULT 1,
  manual_review_only INTEGER NOT NULL DEFAULT 1,
  changes_credits INTEGER NOT NULL DEFAULT 0,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0,
  writes_wallet INTEGER NOT NULL DEFAULT 0,
  creates_trading_permission INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_gca_service_request_followups_client
  ON gca_service_request_followups (service_request_id, client_followup_id);

CREATE INDEX IF NOT EXISTS idx_gca_service_request_followups_request
  ON gca_service_request_followups (service_request_id, submitted_at DESC);

CREATE INDEX IF NOT EXISTS idx_gca_service_request_followups_account
  ON gca_service_request_followups (account_id, submitted_at DESC);
