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

ficha_payload="$(jq -nc \
  --argjson cliente_id "$cliente_id" \
  --arg vehiculo "Toyota Diagnostico 2021" \
  --arg placa "DG${ts: -6}" \
  --arg marca "Toyota" \
  --arg modelo "Diagnostico" \
  --argjson anio 2021 \
  --arg problema_reportado "Validacion diagnosticos observaciones ${ts}" \
  --arg observaciones "Ficha de validacion tecnica" \
  --argjson assigned_mechanic_id "$mecanico_cliente_id" \
  '{cliente_id:$cliente_id,vehiculo:$vehiculo,placa:$placa,marca:$marca,modelo:$modelo,anio:$anio,problema_reportado:$problema_reportado,observaciones:$observaciones,assigned_mechanic_id:$assigned_mechanic_id}')"

ficha_resp="$(curl -i -s -X POST "${BASE_URL}/api/fichas-recepcion" \
  -H "Authorization: Bearer ${sec_token}" -H 'Content-Type: application/json' -d "$ficha_payload")"
printf '== create ficha recepcion ==\n%s\n\n' "$ficha_resp"

recepcion_id="$(printf '%s' "$ficha_resp" | extract_body | jq -r '.id')"

estado_inicial="$(curl -i -s "${BASE_URL}/api/recepciones/${recepcion_id}/estado" -H "Authorization: Bearer ${mec_token}")"
printf '== estado inicial ==\n%s\n\n' "$estado_inicial"

diag_payload="$(jq -nc \
  --arg diagnostic_text "Diagnostico inicial ${ts}" \
  --arg estimated_work "Revision completa del sistema" \
  --argjson estimated_cost 220 \
  '{diagnostic_text:$diagnostic_text,estimated_work:$estimated_work,estimated_cost:$estimated_cost}')"

diag_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/diagnostico" \
  -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$diag_payload")"
printf '== create diagnostico ==\n%s\n\n' "$diag_resp"

estado_post_diag="$(curl -i -s "${BASE_URL}/api/recepciones/${recepcion_id}/estado" -H "Authorization: Bearer ${mec_token}")"
printf '== estado post diagnostico ==\n%s\n\n' "$estado_post_diag"

diag_duplicate_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/diagnostico" \
  -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$diag_payload")"
printf '== duplicate diagnostico ==\n%s\n\n' "$diag_duplicate_resp"

diag_forbidden_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/diagnostico" \
  -H "Authorization: Bearer ${sec_token}" -H 'Content-Type: application/json' -d "$diag_payload")"
printf '== secretaria forbidden diagnostico ==\n%s\n\n' "$diag_forbidden_resp"

obs_payload_1="$(jq -nc \
  --arg observation_text "Observacion tecnica 1 ${ts}" \
  --arg work_status "en_proceso" \
  '{observation_text:$observation_text,work_status:$work_status}')"
obs_payload_2="$(jq -nc \
  --arg observation_text "Observacion tecnica 2 ${ts}" \
  --arg work_status "pausado" \
  '{observation_text:$observation_text,work_status:$work_status}')"

obs_resp_1="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/observaciones" \
  -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$obs_payload_1")"
printf '== create observacion 1 ==\n%s\n\n' "$obs_resp_1"

obs_resp_2="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/observaciones" \
  -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$obs_payload_2")"
printf '== create observacion 2 ==\n%s\n\n' "$obs_resp_2"

estado_post_obs="$(curl -i -s "${BASE_URL}/api/recepciones/${recepcion_id}/estado" -H "Authorization: Bearer ${mec_token}")"
printf '== estado post observaciones ==\n%s\n\n' "$estado_post_obs"

detalle_resp="$(curl -i -s "${BASE_URL}/api/recepciones/${recepcion_id}" -H "Authorization: Bearer ${mec_token}")"
printf '== recepcion detail ==\n%s\n\n' "$detalle_resp"

printf '== conteos finales ==\n'
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
  "SELECT 'diagnosticos_recepcion' AS tabla, COUNT(*) FROM diagnosticos_recepcion
   UNION ALL
   SELECT 'observaciones_recepcion', COUNT(*) FROM observaciones_recepcion;"
