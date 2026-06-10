ALTER TABLE fichas_recepcion
ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ;

ALTER TABLE fichas_recepcion
ADD COLUMN IF NOT EXISTS delivered_by_user_id BIGINT;

ALTER TABLE fichas_recepcion
DROP CONSTRAINT IF EXISTS fichas_recepcion_delivered_by_user_id_fkey;
