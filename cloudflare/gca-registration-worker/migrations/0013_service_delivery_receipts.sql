ALTER TABLE gca_service_requests
  ADD COLUMN delivery_receipt_id TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_service_requests
  ADD COLUMN delivery_acknowledged_at TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_service_requests
  ADD COLUMN delivery_acknowledgement_version TEXT NOT NULL DEFAULT '';

ALTER TABLE gca_service_requests
  ADD COLUMN delivery_acknowledgement_source TEXT NOT NULL DEFAULT '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_gca_service_requests_delivery_receipt
  ON gca_service_requests (delivery_receipt_id)
  WHERE delivery_receipt_id <> '';
