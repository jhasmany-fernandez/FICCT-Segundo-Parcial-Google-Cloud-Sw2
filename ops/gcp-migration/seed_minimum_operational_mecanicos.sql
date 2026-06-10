DO $$
DECLARE
    v_sucursal_id BIGINT;
    v_secretaria_cliente_id BIGINT;
    v_mecanico_cliente_id BIGINT;
    v_mecanico_profile_id BIGINT;
BEGIN
    SELECT id
    INTO v_sucursal_id
    FROM sucursales
    WHERE estado = 'ACTIVO'
    ORDER BY id
    LIMIT 1;

    IF v_sucursal_id IS NULL THEN
        INSERT INTO sucursales (
            nombre,
            direccion,
            zona,
            telefono,
            email,
            responsable,
            estado
        )
        VALUES (
            'Sucursal Central GCP',
            'Av. Principal Google Cloud 100',
            'Centro',
            '70001000',
            'sucursal.central.gcp@acb.com',
            'Coordinacion Operativa',
            'ACTIVO'
        )
        RETURNING id INTO v_sucursal_id;
    END IF;

    SELECT id
    INTO v_secretaria_cliente_id
    FROM clientes
    WHERE LOWER(TRIM(email)) = 'secretaria@acb.com'
    LIMIT 1;

    IF v_secretaria_cliente_id IS NULL THEN
        RAISE EXCEPTION 'No existe el cliente secretaria@acb.com';
    END IF;

    UPDATE clientes
    SET
        role = 'secretaria',
        status = 'active',
        full_name = COALESCE(NULLIF(TRIM(full_name), ''), 'Secretaria Recepcion'),
        phone = COALESCE(NULLIF(TRIM(phone), ''), '70000001'),
        updated_at = NOW()
    WHERE id = v_secretaria_cliente_id;

    INSERT INTO secretarias (cliente_id, sucursal_id, status)
    VALUES (v_secretaria_cliente_id, v_sucursal_id, 'activo')
    ON CONFLICT (cliente_id) DO UPDATE
    SET
        sucursal_id = EXCLUDED.sucursal_id,
        status = 'activo',
        updated_at = NOW();

    SELECT id
    INTO v_mecanico_cliente_id
    FROM clientes
    WHERE LOWER(TRIM(email)) = 'mecanico@acb.com'
    LIMIT 1;

    IF v_mecanico_cliente_id IS NULL THEN
        RAISE EXCEPTION 'No existe el cliente mecanico@acb.com';
    END IF;

    UPDATE clientes
    SET
        role = 'mecanico',
        status = 'active',
        full_name = COALESCE(NULLIF(TRIM(full_name), ''), 'Mecanico Taller'),
        phone = COALESCE(NULLIF(TRIM(phone), ''), '70000002'),
        updated_at = NOW()
    WHERE id = v_mecanico_cliente_id;

    SELECT id
    INTO v_mecanico_profile_id
    FROM mecanicos
    WHERE cliente_id = v_mecanico_cliente_id
    LIMIT 1;

    IF v_mecanico_profile_id IS NULL THEN
        SELECT id
        INTO v_mecanico_profile_id
        FROM mecanicos
        WHERE cliente_id IS NULL
          AND LOWER(TRIM(email)) = 'mecanico@acb.com'
        LIMIT 1;
    END IF;

    IF v_mecanico_profile_id IS NULL THEN
        INSERT INTO mecanicos (
            taller_id,
            cliente_id,
            sucursal_id,
            full_name,
            phone,
            email,
            specialty,
            status
        )
        VALUES (
            NULL,
            v_mecanico_cliente_id,
            v_sucursal_id,
            'Mecanico Taller',
            '70000002',
            'mecanico@acb.com',
            'Motor',
            'disponible'
        );
    ELSE
        UPDATE mecanicos
        SET
            cliente_id = v_mecanico_cliente_id,
            sucursal_id = v_sucursal_id,
            full_name = 'Mecanico Taller',
            phone = '70000002',
            email = 'mecanico@acb.com',
            specialty = 'Motor',
            status = 'disponible',
            updated_at = NOW()
        WHERE id = v_mecanico_profile_id;
    END IF;
END $$;
