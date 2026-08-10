ALTER TABLE gca_service_requests
  ADD COLUMN cancellation_id TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_service_requests
  ADD COLUMN cancelled_at TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_service_requests
  ADD COLUMN cancellation_version TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_service_requests
  ADD COLUMN cancellation_source TEXT NOT NULL DEFAULT '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_gca_service_requests_cancellation
  ON gca_service_requests (cancellation_id)
  WHERE cancellation_id <> '';
