#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-diagramador-db}"
POSTGRES_USER="${POSTGRES_USER:-diagramador}"
POSTGRES_DB="${POSTGRES_DB:-diagramador}"

docker exec -i "${CONTAINER_NAME}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  < ops/gcp-migration/20260608_link_mecanicos_clientes.sql

docker exec -i "${CONTAINER_NAME}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  < ops/gcp-migration/seed_minimum_operational_mecanicos.sql
