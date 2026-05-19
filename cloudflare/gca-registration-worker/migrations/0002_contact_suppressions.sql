CREATE TABLE IF NOT EXISTS gca_contact_suppressions (
  suppression_id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  email_hash TEXT NOT NULL,
  reason TEXT NOT NULL,
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  contact_suppressed INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  user_agent TEXT,
  ip_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_gca_contact_suppressions_created_at
  ON gca_contact_suppressions (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_gca_contact_suppressions_email_hash
  ON gca_contact_suppressions (email_hash);
