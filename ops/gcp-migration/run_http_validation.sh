#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1}"

admin_payload="$(jq -nc \
  --arg email "administrador@acb.com" \
  --arg password "123ppp+++" \
  --arg account_type "admin" \
  '{email:$email,password:$password,account_type:$account_type}')"

admin_login="$(curl -i -s -X POST "${BASE_URL}/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "${admin_payload}")"

admin_token="$(printf '%s' "${admin_login}" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')"

printf '== GET /api/fichas-recepcion ==\n'
curl -i -s "${BASE_URL}/api/fichas-recepcion" -H "Authorization: Bearer ${admin_token}"
printf '\n\n== GET /api/recepciones ==\n'
curl -i -s "${BASE_URL}/api/recepciones" -H "Authorization: Bearer ${admin_token}"
printf '\n\n== GET /api/emergencias ==\n'
curl -i -s "${BASE_URL}/api/emergencias" -H "Authorization: Bearer ${admin_token}"
printf '\n'
