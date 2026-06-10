#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-diagramador-db}"
POSTGRES_USER="${POSTGRES_USER:-diagramador}"
TARGET_DB="${TARGET_DB:-diagramador_restore_check}"

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 /ruta/al/dump.{sql,dump,backup}"
  echo "Restaura en la base temporal ${TARGET_DB} sin tocar la base activa."
  exit 1
fi

DUMP_PATH="$1"

if [[ ! -f "$DUMP_PATH" ]]; then
  echo "No existe el archivo: $DUMP_PATH" >&2
  exit 1
fi

echo "Creando base temporal ${TARGET_DB} en ${CONTAINER_NAME}..."
if docker exec "${CONTAINER_NAME}" psql -U "${POSTGRES_USER}" -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname = '${TARGET_DB}'" | grep -q 1; then
  echo "La base temporal ${TARGET_DB} ya existe; se reutilizara para esta validacion."
else
  docker exec "${CONTAINER_NAME}" createdb -U "${POSTGRES_USER}" "${TARGET_DB}"
fi

case "${DUMP_PATH}" in
  *.sql)
    echo "Restaurando dump SQL plano en ${TARGET_DB}..."
    docker exec -i "${CONTAINER_NAME}" psql -U "${POSTGRES_USER}" -d "${TARGET_DB}" -v ON_ERROR_STOP=1 < "${DUMP_PATH}"
    ;;
  *.dump|*.backup)
    echo "Restaurando dump custom en ${TARGET_DB}..."
    docker exec -i "${CONTAINER_NAME}" pg_restore -U "${POSTGRES_USER}" -d "${TARGET_DB}" --no-owner --no-privileges < "${DUMP_PATH}"
    ;;
  *)
    echo "Formato no reconocido. Usa .sql, .dump o .backup" >&2
    exit 1
    ;;
esac

echo
echo "Restauracion completada en ${TARGET_DB}. Resumen de tablas clave:"
docker exec "${CONTAINER_NAME}" psql -U "${POSTGRES_USER}" -d "${TARGET_DB}" -c \
  "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('clientes','vehiculos','reportes_emergencia','fichas_recepcion','diagnosticos_recepcion','observaciones_recepcion','mecanicos','sucursales','secretarias') ORDER BY table_name;"
