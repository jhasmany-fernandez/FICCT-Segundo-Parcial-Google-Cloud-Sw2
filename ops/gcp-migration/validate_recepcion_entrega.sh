#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1}"
DB_CONTAINER="${DB_CONTAINER:-diagramador-db}"
DB_USER="${DB_USER:-diagramador}"
DB_NAME="${DB_NAME:-diagramador}"

login() {
  local email="$1"
  local password="$2"
  local account_type="$3"
  jq -nc --arg email "$email" --arg password "$password" --arg account_type "$account_type" \
    '{email:$email,password:$password,account_type:$account_type}' |
    curl -i -s -X POST "${BASE_URL}/api/auth/login" -H 'Content-Type: application/json' -d @-
}

extract_token() {
  sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p'
}

extract_body() {
  awk 'BEGIN{body=0} body{print} /^\r?$/{body=1}'
}

ts="$(date +%s)"
cliente_id="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT id FROM clientes WHERE LOWER(TRIM(role)) = 'client' ORDER BY id LIMIT 1")"
mecanico_cliente_id="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT id FROM clientes WHERE LOWER(TRIM(email)) = 'mecanico@acb.com' LIMIT 1")"

admin_login="$(login "administrador@acb.com" "123ppp+++" "admin")"
sec_login="$(login "secretaria@acb.com" "secretaria123" "client")"
mec_login="$(login "mecanico@acb.com" "mecanico123" "client")"

printf '== login admin ==\n%s\n\n' "$admin_login"
printf '== login secretaria ==\n%s\n\n' "$sec_login"
printf '== login mecanico ==\n%s\n\n' "$mec_login"

admin_token="$(printf '%s' "$admin_login" | extract_token)"
sec_token="$(printf '%s' "$sec_login" | extract_token)"
mec_token="$(printf '%s' "$mec_login" | extract_token)"

make_ficha() {
  local suffix="$1"
  local assigned_id="$2"
  local token="$3"
  local payload
  payload="$(jq -nc \
    --argjson cliente_id "$cliente_id" \
    --arg vehiculo "Toyota Entrega ${suffix}" \
    --arg placa "EN${suffix: -6}" \
    --arg marca "Toyota" \
    --arg modelo "Entrega" \
    --argjson anio 2021 \
    --arg problema_reportado "Validacion entrega ${suffix}" \
    --arg observaciones "Ficha de validacion de entrega" \
    --argjson assigned_mechanic_id "$assigned_id" \
    '{cliente_id:$cliente_id,vehiculo:$vehiculo,placa:$placa,marca:$marca,modelo:$modelo,anio:$anio,problema_reportado:$problema_reportado,observaciones:$observaciones,assigned_mechanic_id:$assigned_mechanic_id}')"
  curl -i -s -X POST "${BASE_URL}/api/fichas-recepcion" \
    -H "Authorization: Bearer ${token}" -H 'Content-Type: application/json' -d "$payload"
}

diag_payload="$(jq -nc --arg diagnostic_text "Diagnostico entrega ${ts}" --arg estimated_work "Revision cierre" --argjson estimated_cost 200 '{diagnostic_text:$diagnostic_text,estimated_work:$estimated_work,estimated_cost:$estimated_cost}')"
obs_payload="$(jq -nc --arg observation_text "Observacion entrega ${ts}" --arg work_status "completado" '{observation_text:$observation_text,work_status:$work_status}')"

finalize_no_override_payload='{"admin_override":false}'

secretary_ficha_resp="$(make_ficha "${ts}" "${mecanico_cliente_id}" "${sec_token}")"
printf '== create ficha secretaria ==\n%s\n\n' "$secretary_ficha_resp"
secretary_id="$(printf '%s' "$secretary_ficha_resp" | extract_body | jq -r '.id')"
curl -s -X POST "${BASE_URL}/api/recepciones/${secretary_id}/diagnostico" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$diag_payload" >/dev/null
curl -s -X POST "${BASE_URL}/api/recepciones/${secretary_id}/observaciones" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$obs_payload" >/dev/null
curl -s -X POST "${BASE_URL}/api/recepciones/${secretary_id}/finalizar" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$finalize_no_override_payload" >/dev/null

secretary_deliver_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${secretary_id}/entregar" -H "Authorization: Bearer ${sec_token}")"
printf '== entregar como secretaria ==\n%s\n\n' "$secretary_deliver_resp"

secretary_detail_resp="$(curl -i -s "${BASE_URL}/api/recepciones/${secretary_id}" -H "Authorization: Bearer ${sec_token}")"
printf '== detalle luego de entrega secretaria ==\n%s\n\n' "$secretary_detail_resp"

admin_ficha_resp="$(make_ficha "$((ts+1))" "${mecanico_cliente_id}" "${sec_token}")"
printf '== create ficha admin ==\n%s\n\n' "$admin_ficha_resp"
admin_id="$(printf '%s' "$admin_ficha_resp" | extract_body | jq -r '.id')"
curl -s -X POST "${BASE_URL}/api/recepciones/${admin_id}/diagnostico" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$diag_payload" >/dev/null
curl -s -X POST "${BASE_URL}/api/recepciones/${admin_id}/observaciones" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$obs_payload" >/dev/null
curl -s -X POST "${BASE_URL}/api/recepciones/${admin_id}/finalizar" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$finalize_no_override_payload" >/dev/null

admin_deliver_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${admin_id}/entregar" -H "Authorization: Bearer ${admin_token}")"
printf '== entregar como admin ==\n%s\n\n' "$admin_deliver_resp"

mechanic_forbidden_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${admin_id}/entregar" -H "Authorization: Bearer ${mec_token}")"
printf '== entregar como mecanico ==\n%s\n\n' "$mechanic_forbidden_resp"

duplicate_deliver_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${admin_id}/entregar" -H "Authorization: Bearer ${admin_token}")"
printf '== entregar dos veces ==\n%s\n\n' "$duplicate_deliver_resp"

not_finalized_resp="$(make_ficha "$((ts+2))" "${mecanico_cliente_id}" "${sec_token}")"
printf '== create ficha no finalizada ==\n%s\n\n' "$not_finalized_resp"
not_finalized_id="$(printf '%s' "$not_finalized_resp" | extract_body | jq -r '.id')"
not_finalized_deliver_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${not_finalized_id}/entregar" -H "Authorization: Bearer ${sec_token}")"
printf '== entregar no finalizada ==\n%s\n\n' "$not_finalized_deliver_resp"
