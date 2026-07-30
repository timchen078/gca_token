ALTER TABLE gca_service_requests
  ADD COLUMN latest_review_id TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_service_requests
  ADD COLUMN reviewed_at TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_service_requests
  ADD COLUMN completed_at TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_service_requests
  ADD COLUMN updated_at TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_service_requests
  ADD COLUMN credit_usage_id TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_credit_usage
  ADD COLUMN service_request_id TEXT NOT NULL DEFAULT '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_gca_credit_usage_service_request
  ON gca_credit_usage (service_request_id)
  WHERE service_request_id <> '';

CREATE TABLE IF NOT EXISTS gca_service_request_reviews (
  service_request_review_id TEXT PRIMARY KEY,
  service_request_id TEXT NOT NULL,
  packet_version TEXT NOT NULL,
  decision TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  reviewer_id TEXT NOT NULL,
  operator_note TEXT,
  delivery_reference TEXT,
  credit_usage_id TEXT,
  credit_amount_used INTEGER NOT NULL DEFAULT 0,
  remaining_credits_before INTEGER,
  remaining_credits_after INTEGER,
  reviewed_at TEXT NOT NULL,
  source TEXT NOT NULL,
  manual_review_completed INTEGER NOT NULL DEFAULT 1,
  delivery_completed INTEGER NOT NULL DEFAULT 0,
  credits_deducted INTEGER NOT NULL DEFAULT 0,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0,
  writes_wallet INTEGER NOT NULL DEFAULT 0,
  creates_trading_permission INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_service_request_reviews_request
  ON gca_service_request_reviews (service_request_id, reviewed_at DESC);

CREATE INDEX IF NOT EXISTS idx_gca_service_request_reviews_reviewed_at
  ON gca_service_request_reviews (reviewed_at DESC);
