CREATE TABLE IF NOT EXISTS gca_email_registrations (
  email_registration_id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  email_hash TEXT NOT NULL,
  display_name TEXT,
  source TEXT NOT NULL,
  language TEXT NOT NULL,
  interests_json TEXT NOT NULL,
  contact_consent_accepted INTEGER NOT NULL,
  security_boundary_accepted INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  user_agent TEXT,
  ip_hash TEXT,
  wallet_required INTEGER NOT NULL DEFAULT 0,
  requires_signature INTEGER NOT NULL DEFAULT 0,
  requires_transaction INTEGER NOT NULL DEFAULT 0,
  automatic_token_transfer INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gca_email_registrations_created_at
  ON gca_email_registrations (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_gca_email_registrations_email_hash
  ON gca_email_registrations (email_hash);
