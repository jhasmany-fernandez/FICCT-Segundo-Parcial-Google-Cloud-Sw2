#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1}"
CONTAINER_NAME="${CONTAINER_NAME:-diagramador-db}"
POSTGRES_USER="${POSTGRES_USER:-diagramador}"
POSTGRES_DB="${POSTGRES_DB:-diagramador}"
ADMIN_EMAIL="${ADMIN_EMAIL:-administrador@acb.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-123ppp+++}"
SECRETARIA_EMAIL="${SECRETARIA_EMAIL:-secretaria@acb.com}"
SECRETARIA_PASSWORD="${SECRETARIA_PASSWORD:-secretaria123}"
MECANICO_EMAIL="${MECANICO_EMAIL:-mecanico@acb.com}"
MECANICO_PASSWORD="${MECANICO_PASSWORD:-mecanico123}"

extract_token() {
  sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p'
}

echo "== Docker =="
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
echo
docker compose ps
echo

echo "== Health =="
curl -i -s "${BASE_URL}/api/health"
echo
echo

echo "== Login admin =="
ADMIN_LOGIN="$(curl -i -s -X POST "${BASE_URL}/api/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\",\"account_type\":\"admin\"}")"
printf '%s\n' "${ADMIN_LOGIN}"
echo

echo "== Login secretaria =="
curl -i -s -X POST "${BASE_URL}/api/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"${SECRETARIA_EMAIL}\",\"password\":\"${SECRETARIA_PASSWORD}\",\"account_type\":\"client\"}"
echo
echo

echo "== Login mecanico =="
curl -i -s -X POST "${BASE_URL}/api/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"${MECANICO_EMAIL}\",\"password\":\"${MECANICO_PASSWORD}\",\"account_type\":\"client\"}"
echo
echo

ADMIN_TOKEN="$(printf '%s' "${ADMIN_LOGIN}" | extract_token)"
if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "No se pudo extraer el token admin." >&2
  exit 1
fi

echo "== GET /api/fichas-recepcion =="
curl -i -s "${BASE_URL}/api/fichas-recepcion" -H "Authorization: Bearer ${ADMIN_TOKEN}"
echo
echo

echo "== GET /api/recepciones =="
curl -i -s "${BASE_URL}/api/recepciones" -H "Authorization: Bearer ${ADMIN_TOKEN}"
echo
echo

echo "== GET /api/mecanicos =="
curl -i -s "${BASE_URL}/api/mecanicos" -H "Authorization: Bearer ${ADMIN_TOKEN}"
echo
echo

echo "== Tablas clave =="
docker exec "${CONTAINER_NAME}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c \
  "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('clientes','vehiculos','reportes_emergencia','fichas_recepcion','diagnosticos_recepcion','observaciones_recepcion','mecanicos','sucursales','secretarias') ORDER BY table_name;"
echo

echo "== Conteos =="
docker exec "${CONTAINER_NAME}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c \
  "SELECT 'clientes' AS tabla, COUNT(*) FROM clientes
   UNION ALL SELECT 'vehiculos', COUNT(*) FROM vehiculos
   UNION ALL SELECT 'reportes_emergencia', COUNT(*) FROM reportes_emergencia
   UNION ALL SELECT 'fichas_recepcion', COUNT(*) FROM fichas_recepcion
   UNION ALL SELECT 'diagnosticos_recepcion', COUNT(*) FROM diagnosticos_recepcion
   UNION ALL SELECT 'observaciones_recepcion', COUNT(*) FROM observaciones_recepcion
   UNION ALL SELECT 'mecanicos', COUNT(*) FROM mecanicos
   UNION ALL SELECT 'sucursales', COUNT(*) FROM sucursales
   UNION ALL SELECT 'secretarias', COUNT(*) FROM secretarias;"
