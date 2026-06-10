#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1}"
DB_CONTAINER="${DB_CONTAINER:-diagramador-db}"
DB_USER="${DB_USER:-diagramador}"
DB_NAME="${DB_NAME:-diagramador}"

ts="$(date +%s)"
admin_email="mechanic.admin.${ts}@example.com"
sec_email="mechanic.sec.${ts}@example.com"
default_password="MecanicoTemp2026!"

login() {
  local email="$1"
  local password="$2"
  local account_type="$3"
  jq -nc --arg email "$email" --arg password "$password" --arg account_type "$account_type" \
    '{email:$email,password:$password,account_type:$account_type}' |
    curl -i -s -X POST "${BASE_URL}/api/auth/login" -H 'Content-Type: application/json' -d @-
}

extract_json_body() {
  awk 'BEGIN{body=0} body{print} /^\r?$/{body=1}'
}

extract_token() {
  sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p'
}

extract_status() {
  sed -n '1s/.* \([0-9][0-9][0-9]\) .*/\1/p'
}

admin_login="$(login "administrador@acb.com" "123ppp+++" "admin")"
sec_login="$(login "secretaria@acb.com" "secretaria123" "client")"
mec_login="$(login "mecanico@acb.com" "mecanico123" "client")"

printf '== login admin ==\n%s\n\n' "$admin_login"
printf '== login secretaria ==\n%s\n\n' "$sec_login"
printf '== login mecanico ==\n%s\n\n' "$mec_login"

admin_token="$(printf '%s' "$admin_login" | extract_token)"
sec_token="$(printf '%s' "$sec_login" | extract_token)"
mec_token="$(printf '%s' "$mec_login" | extract_token)"

if [[ -z "$admin_token" || -z "$sec_token" || -z "$mec_token" ]]; then
  echo "No se pudieron obtener los tokens base." >&2
  exit 1
fi

sucursal_id="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT id FROM sucursales WHERE estado = 'ACTIVO' ORDER BY id LIMIT 1")"
mecanico_cliente_id="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT id FROM clientes WHERE LOWER(TRIM(email)) = 'mecanico@acb.com' LIMIT 1")"
cliente_operativo_id="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT id FROM clientes WHERE LOWER(TRIM(role)) = 'client' ORDER BY id LIMIT 1")"

admin_create_payload="$(jq -nc \
  --arg full_name "Mecanico Admin ${ts}" \
  --arg phone "7991${ts: -6}" \
  --arg email "$admin_email" \
  --arg specialty "Motor" \
  --arg status "disponible" \
  --arg password "$default_password" \
  --arg identity_card "MECA${ts}" \
  --argjson sucursal_id "$sucursal_id" \
  '{full_name:$full_name,phone:$phone,email:$email,specialty:$specialty,status:$status,password:$password,identity_card:$identity_card,sucursal_id:$sucursal_id}')"
admin_create_resp="$(curl -i -s -X POST "${BASE_URL}/api/mecanicos" -H "Authorization: Bearer ${admin_token}" -H 'Content-Type: application/json' -d "$admin_create_payload")"
printf '== admin create mecanico ==\n%s\n\n' "$admin_create_resp"
admin_mecanico_id="$(printf '%s' "$admin_create_resp" | extract_json_body | jq -r '.id')"

admin_update_payload="$(jq -nc \
  --arg full_name "Mecanico Admin Editado ${ts}" \
  --arg phone "7992${ts: -6}" \
  --arg email "$admin_email" \
  --arg specialty "Sistema eléctrico" \
  --arg status "ocupado" \
  --arg identity_card "MECA${ts}" \
  --argjson sucursal_id "$sucursal_id" \
  '{full_name:$full_name,phone:$phone,email:$email,specialty:$specialty,status:$status,identity_card:$identity_card,sucursal_id:$sucursal_id}')"
admin_update_resp="$(curl -i -s -X PUT "${BASE_URL}/api/mecanicos/${admin_mecanico_id}" -H "Authorization: Bearer ${admin_token}" -H 'Content-Type: application/json' -d "$admin_update_payload")"
printf '== admin update mecanico ==\n%s\n\n' "$admin_update_resp"

admin_list_resp="$(curl -i -s "${BASE_URL}/api/mecanicos" -H "Authorization: Bearer ${admin_token}")"
printf '== admin list mecanicos ==\n%s\n\n' "$admin_list_resp"

sec_create_payload="$(jq -nc \
  --arg full_name "Mecanico Secretaria ${ts}" \
  --arg phone "7993${ts: -6}" \
  --arg email "$sec_email" \
  --arg specialty "Motor" \
  --arg status "disponible" \
  --arg password "$default_password" \
  --arg identity_card "MECS${ts}" \
  --argjson sucursal_id "$sucursal_id" \
  '{full_name:$full_name,phone:$phone,email:$email,specialty:$specialty,status:$status,password:$password,identity_card:$identity_card,sucursal_id:$sucursal_id}')"
sec_create_resp="$(curl -i -s -X POST "${BASE_URL}/api/mecanicos" -H "Authorization: Bearer ${sec_token}" -H 'Content-Type: application/json' -d "$sec_create_payload")"
printf '== secretaria create mecanico ==\n%s\n\n' "$sec_create_resp"
sec_mecanico_id="$(printf '%s' "$sec_create_resp" | extract_json_body | jq -r '.id')"

sec_update_payload="$(jq -nc \
  --arg full_name "Mecanico Secretaria Editado ${ts}" \
  --arg phone "7994${ts: -6}" \
  --arg email "$sec_email" \
  --arg specialty "Motor" \
  --arg status "disponible" \
  --arg identity_card "MECS${ts}" \
  --argjson sucursal_id "$sucursal_id" \
  '{full_name:$full_name,phone:$phone,email:$email,specialty:$specialty,status:$status,identity_card:$identity_card,sucursal_id:$sucursal_id}')"
sec_update_resp="$(curl -i -s -X PUT "${BASE_URL}/api/mecanicos/${sec_mecanico_id}" -H "Authorization: Bearer ${sec_token}" -H 'Content-Type: application/json' -d "$sec_update_payload")"
printf '== secretaria update mecanico ==\n%s\n\n' "$sec_update_resp"

sec_list_resp="$(curl -i -s "${BASE_URL}/api/mecanicos" -H "Authorization: Bearer ${sec_token}")"
printf '== secretaria list mecanicos ==\n%s\n\n' "$sec_list_resp"

assignables_resp="$(curl -i -s "${BASE_URL}/api/recepciones/mecanicos-asignables" -H "Authorization: Bearer ${sec_token}")"
printf '== recepciones mecanicos asignables ==\n%s\n\n' "$assignables_resp"

ficha_payload="$(jq -nc \
  --argjson cliente_id "$cliente_operativo_id" \
  --arg vehiculo "Chevrolet Tracker 2020" \
  --arg placa "VAL${ts: -6}" \
  --arg marca "Chevrolet" \
  --arg modelo "Tracker" \
  --argjson anio 2020 \
  --arg problema_reportado "Validacion modulo mecanicos ${ts}" \
  --arg observaciones "Creada para validar diagnostico y observacion" \
  --argjson assigned_mechanic_id "$mecanico_cliente_id" \
  '{cliente_id:$cliente_id,vehiculo:$vehiculo,placa:$placa,marca:$marca,modelo:$modelo,anio:$anio,problema_reportado:$problema_reportado,observaciones:$observaciones,assigned_mechanic_id:$assigned_mechanic_id}')"
ficha_resp="$(curl -i -s -X POST "${BASE_URL}/api/fichas-recepcion" -H "Authorization: Bearer ${sec_token}" -H 'Content-Type: application/json' -d "$ficha_payload")"
printf '== create ficha recepcion ==\n%s\n\n' "$ficha_resp"
recepcion_id="$(printf '%s' "$ficha_resp" | extract_json_body | jq -r '.id')"

diagnostico_payload="$(jq -nc --arg diagnostic_text "Diagnostico operativo ${ts}" --arg estimated_work "Revision integral" --argjson estimated_cost 180 '{diagnostic_text:$diagnostic_text,estimated_work:$estimated_work,estimated_cost:$estimated_cost}')"
diagnostico_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/diagnostico" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$diagnostico_payload")"
printf '== mecanico create diagnostico ==\n%s\n\n' "$diagnostico_resp"

observacion_payload="$(jq -nc --arg observation_text "Observacion operativa ${ts}" --arg work_status "en_proceso" '{observation_text:$observation_text,work_status:$work_status}')"
observacion_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/observaciones" -H "Authorization: Bearer ${mec_token}" -H 'Content-Type: application/json' -d "$observacion_payload")"
printf '== mecanico create observacion ==\n%s\n\n' "$observacion_resp"

printf '== conteos bd ==\n'
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
  "SELECT 'sucursales' AS tabla, COUNT(*) FROM sucursales
   UNION ALL SELECT 'secretarias', COUNT(*) FROM secretarias
   UNION ALL SELECT 'mecanicos', COUNT(*) FROM mecanicos
   UNION ALL SELECT 'clientes_mecanico', COUNT(*) FROM clientes WHERE LOWER(TRIM(role)) = 'mecanico';"
