ALTER TABLE mecanicos
ADD COLUMN IF NOT EXISTS cliente_id BIGINT;

UPDATE mecanicos AS m
SET cliente_id = c.id
FROM clientes AS c
WHERE m.cliente_id IS NULL
  AND LOWER(TRIM(m.email)) = LOWER(TRIM(c.email))
  AND LOWER(TRIM(c.role)) = 'mecanico';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'mecanicos_cliente_id_fkey'
    ) AND NOT EXISTS (
        SELECT 1
        FROM mecanicos m
        LEFT JOIN clientes c ON c.id = m.cliente_id
        WHERE m.cliente_id IS NOT NULL
          AND c.id IS NULL
    ) THEN
        ALTER TABLE mecanicos
        ADD CONSTRAINT mecanicos_cliente_id_fkey
        FOREIGN KEY (cliente_id)
        REFERENCES clientes(id)
        ON DELETE SET NULL;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mecanicos_cliente_id_unique
ON mecanicos (cliente_id)
WHERE cliente_id IS NOT NULL;
