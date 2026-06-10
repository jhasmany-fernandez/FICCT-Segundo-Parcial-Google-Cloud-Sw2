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
    --arg vehiculo "Toyota Finalizacion ${suffix}" \
    --arg placa "FN${suffix: -6}" \
    --arg marca "Toyota" \
    --arg modelo "Finalizacion" \
    --argjson anio 2021 \
    --arg problema_reportado "Validacion finalizacion ${suffix}" \
    --arg observaciones "Ficha de validacion de finalizacion" \
    --argjson assigned_mechanic_id "$assigned_id" \
    '{cliente_id:$cliente_id,vehiculo:$vehiculo,placa:$placa,marca:$marca,modelo:$modelo,anio:$anio,problema_reportado:$problema_reportado,observaciones:$observaciones,assigned_mechanic_id:$assigned_mechanic_id}')"
  curl -i -s -X POST "${BASE_URL}/api/fichas-recepcion" \
    -H "Authorization: Bearer ${token}" -H 'Content-Type: application/json' -d "$payload"
}

diag_payload="$(jq -nc --arg diagnostic_text "Diagnostico finalizacion ${ts}" --arg estimated_work "Revision cierre" --argjson estimated_cost 200 '{diagnostic_text:$diagnostic_text,estimated_work:$estimated_work,estimated_cost:$estimated_cost}')"
obs_payload="$(jq -nc --arg observation_text "Observacion finalizacion ${ts}" --arg work_status "completado" '{observation_text:$observation_text,work_status:$work_status}')"
finalize_no_override_payload='{"admin_override":false}'
finalize_override_payload='{"admin_override":true}'

# Caso valido
valid_ficha_resp="$(make_ficha "${ts}" "${mecanico_cliente_id}" "${sec_token}")"
printf '== create ficha valida ==\n%s\n\n' "$valid_ficha_resp"
valid_id="$(printf '%s' "$valid_ficha_resp" | extract_body | jq -r '.id')"
curl -s -X POST "${BASE_URL}/api/recepciones/${valid_id}/diagnostico" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$diag_payload" >/dev/null
curl -s -X POST "${BASE_URL}/api/recepciones/${valid_id}/observaciones" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$obs_payload" >/dev/null
valid_finalize_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${valid_id}/finalizar" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$finalize_no_override_payload")"
printf '== finalizar valida ==\n%s\n\n' "$valid_finalize_resp"
valid_estado_resp="$(curl -i -s "${BASE_URL}/api/recepciones/${valid_id}/estado" -H "Authorization: Bearer ${mec_token}")"
printf '== estado final valido ==\n%s\n\n' "$valid_estado_resp"

# Sin diagnostico
no_diag_resp="$(make_ficha "$((ts+1))" "${mecanico_cliente_id}" "${sec_token}")"
no_diag_id="$(printf '%s' "$no_diag_resp" | extract_body | jq -r '.id')"
printf '== create ficha sin diagnostico ==\n%s\n\n' "$no_diag_resp"
finalize_no_diag_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${no_diag_id}/finalizar" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$finalize_no_override_payload")"
printf '== finalizar sin diagnostico ==\n%s\n\n' "$finalize_no_diag_resp"

# Sin observacion
no_obs_resp="$(make_ficha "$((ts+2))" "${mecanico_cliente_id}" "${sec_token}")"
no_obs_id="$(printf '%s' "$no_obs_resp" | extract_body | jq -r '.id')"
printf '== create ficha sin observacion ==\n%s\n\n' "$no_obs_resp"
curl -s -X POST "${BASE_URL}/api/recepciones/${no_obs_id}/diagnostico" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$diag_payload" >/dev/null
finalize_no_obs_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${no_obs_id}/finalizar" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$finalize_no_override_payload")"
printf '== finalizar sin observacion ==\n%s\n\n' "$finalize_no_obs_resp"

# Secretaria prohibida
sec_forbidden_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${valid_id}/finalizar" -H "Authorization: Bearer ${sec_token}" -H 'Content-Type: application/json' -d "$finalize_no_override_payload")"
printf '== finalizar como secretaria ==\n%s\n\n' "$sec_forbidden_resp"

# Finalizar dos veces
duplicate_finalize_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${valid_id}/finalizar" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$finalize_no_override_payload")"
printf '== finalizar dos veces ==\n%s\n\n' "$duplicate_finalize_resp"

# Override admin
admin_override_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${no_obs_id}/finalizar" -H "Authorization: Bearer ${admin_token}" -H 'Content-Type: application/json' -d "$finalize_override_payload")"
printf '== finalizar admin override ==\n%s\n\n' "$admin_override_resp"

printf '== conteos finales ==\n'
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
  "SELECT 'diagnosticos_recepcion' AS tabla, COUNT(*) FROM diagnosticos_recepcion
   UNION ALL
   SELECT 'observaciones_recepcion', COUNT(*) FROM observaciones_recepcion;"
