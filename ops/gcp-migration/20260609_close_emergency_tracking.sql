ALTER TABLE reportes_emergencia
ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

ALTER TABLE reportes_emergencia
ADD COLUMN IF NOT EXISTS closed_by_user_id BIGINT;

ALTER TABLE asignaciones_emergencia
ADD COLUMN IF NOT EXISTS finalized_at TIMESTAMPTZ;
