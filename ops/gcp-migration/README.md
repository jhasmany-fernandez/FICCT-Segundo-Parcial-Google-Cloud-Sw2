# Migracion Azure -> Google Cloud

Kit operativo para preparar y validar la migracion del backend `diagramador-backend` y PostgreSQL en Google Cloud sin eliminar la base activa.

## Estado esperado del host

- `diagramador-backend` expuesto internamente en `backend:8000`
- `diagramador-gateway` publicado en `80` y proxy hacia `/api/*`
- `diagramador-db` publicado en `5454` hacia `5432`

## DATABASE_URL

Interna al contenedor backend:

`postgresql+psycopg://diagramador:diagramador@db:5432/diagramador`

Host para acceso externo o utilidades locales:

`postgresql://diagramador:diagramador@34.122.37.25:5454/diagramador`

## Restaurar dump sin tocar la base activa

1. Copiar el dump de Azure al host.
2. Restaurar en una base temporal:

```bash
chmod +x ops/gcp-migration/restore_dump.sh
./ops/gcp-migration/restore_dump.sh /ruta/al/dump.sql
```

Por defecto restaura en `diagramador_restore_check`. Si hace falta cambiar el destino:

```bash
TARGET_DB=diagramador_azure_import ./ops/gcp-migration/restore_dump.sh /ruta/al/dump.backup
```

## Validacion funcional

```bash
chmod +x ops/gcp-migration/validate_migration.sh
./ops/gcp-migration/validate_migration.sh
```

Esto valida:

- `GET /api/health`
- login admin
- login secretaria
- login mecanico
- `GET /api/fichas-recepcion`
- `GET /api/recepciones`
- `GET /api/mecanicos`
- existencia y conteo de tablas clave

Para el cierre administrativo de recepciones:

```bash
chmod +x ops/gcp-migration/validate_recepcion_entrega.sh
./ops/gcp-migration/validate_recepcion_entrega.sh
```

Esto valida:

- `POST /api/recepciones/{id}/entregar`
- entrega como `secretaria`
- entrega como `admin`
- rechazo para `mecanico`
- rechazo de entrega duplicada
- rechazo si la recepción no está `finalizada`

## Nota sobre login

Aunque la respuesta de negocio devuelve roles `secretaria` y `mecanico`, el contrato actual de `/api/auth/login` acepta `account_type=client` para ambos casos. `admin` sigue usando `account_type=admin`.
