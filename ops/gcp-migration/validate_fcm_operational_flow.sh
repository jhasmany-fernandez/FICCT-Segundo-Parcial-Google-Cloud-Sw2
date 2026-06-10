#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://34.122.37.25}"
DB_CONTAINER="${DB_CONTAINER:-diagramador-db}"
DB_USER="${DB_USER:-diagramador}"
DB_NAME="${DB_NAME:-diagramador}"

login() {
  local email="$1"
  local password="$2"
  local account_type="$3"
  local payload
  payload="$(jq -nc --arg email "$email" --arg password "$password" --arg account_type "$account_type" \
    '{email:$email,password:$password,account_type:$account_type}')"
  curl -i -s -X POST "${BASE_URL}/api/auth/login" -H 'Content-Type: application/json' -d "$payload"
}

extract_token() {
  sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p'
}

extract_body() {
  awk 'BEGIN{body=0} body{print} /^\r?$/{body=1}'
}

assert_contains_type() {
  local json="$1"
  local expected="$2"
  if ! printf '%s' "$json" | jq -e --arg expected "$expected" 'map(select(.tipo == $expected)) | length > 0' >/dev/null; then
    echo "No se encontro notificacion tipo ${expected}" >&2
    exit 1
  fi
}

ts="$(date +%s)"
client_email="fcm.client.${ts}@example.com"
client_password="FcmFlow2026!"
client_phone="755${ts: -6}"
client_identity="FCM${ts}"
client_payload="$(jq -nc \
  --arg identityCard "$client_identity" \
  --arg fullName "Cliente FCM ${ts}" \
  --arg email "$client_email" \
  --arg phone "$client_phone" \
  --arg password "$client_password" \
  '{identityCard:$identityCard,fullName:$fullName,email:$email,phone:$phone,password:$password,confirmPassword:$password,acceptedTerms:true,role:"client"}')"

admin_login="$(login "administrador@acb.com" "123ppp+++" "admin")"
sec_login="$(login "secretaria@acb.com" "secretaria123" "client")"
client_create_resp="$(curl -i -s -X POST "${BASE_URL}/api/clientes" -H 'Content-Type: application/json' -d "$client_payload")"
client_login="$(login "$client_email" "$client_password" "client")"

printf '== login admin ==\n%s\n\n' "$admin_login"
printf '== login secretaria ==\n%s\n\n' "$sec_login"
printf '== create client ==\n%s\n\n' "$client_create_resp"
printf '== login client ==\n%s\n\n' "$client_login"

admin_token="$(printf '%s' "$admin_login" | extract_token)"
sec_token="$(printf '%s' "$sec_login" | extract_token)"
client_token="$(printf '%s' "$client_login" | extract_token)"
client_id="$(printf '%s' "$client_login" | extract_body | jq -r '.id')"

dummy_token="dummy-fcm-token-${ts}-ABCDEFGHIJKLMN"
device_payload="$(jq -nc --argjson user_id "$client_id" --arg fcm_token "$dummy_token" '{user_id:$user_id,fcm_token:$fcm_token,platform:"android"}')"
device_resp="$(curl -i -s -X POST "${BASE_URL}/api/devices/fcm-token" \
  -H "Authorization: Bearer ${client_token}" \
  -H 'Content-Type: application/json' \
  -d "$device_payload")"
printf '== register dummy device token ==\n%s\n\n' "$device_resp"

vehicle_resp="$(curl -i -s -X POST "${BASE_URL}/api/vehiculos" \
  -H "Authorization: Bearer ${client_token}" \
  -F "brand=Toyota" \
  -F "model=Corolla FCM" \
  -F "year=2020" \
  -F "plate=FCM${ts: -6}" \
  -F "color=Blanco" \
  -F "is_primary=true")"
printf '== create vehicle ==\n%s\n\n' "$vehicle_resp"
vehicle_id="$(printf '%s' "$vehicle_resp" | extract_body | jq -r '.id')"

emergency_resp="$(curl -i -s -X POST "${BASE_URL}/api/emergencias" \
  -H "Authorization: Bearer ${client_token}" \
  -F "vehicle_id=${vehicle_id}" \
  -F "problem_type=Motor" \
  -F "description=Flujo FCM operativo ${ts}" \
  -F "latitude=-17.7833" \
  -F "longitude=-63.1821" \
  -F "address=Validacion FCM ${ts}" \
  -F "zone=Norte" \
  -F "nearest_workshop_id=1")"
printf '== create emergency ==\n%s\n\n' "$emergency_resp"
emergency_id="$(printf '%s' "$emergency_resp" | extract_body | jq -r '.id')"

accept_resp="$(curl -i -s -X PUT "${BASE_URL}/api/emergencias/${emergency_id}/status?workshop_id=1" \
  -H "Authorization: Bearer ${admin_token}" \
  -H 'Content-Type: application/json' \
  -d '{"emergency_status":"activo"}')"
printf '== accept emergency ==\n%s\n\n' "$accept_resp"

mechanic_email="operational.fcm.${ts}@example.com"
mechanic_password="FcmMec2026!"
mechanic_payload="$(jq -nc \
  --arg full_name "Mecanico FCM ${ts}" \
  --arg phone "766${ts: -6}" \
  --arg email "$mechanic_email" \
  --arg specialty "Motor" \
  --arg status "disponible" \
  --arg password "$mechanic_password" \
  --arg identity_card "FCMMEC${ts}" \
  --argjson workshop_id 1 \
  --argjson sucursal_id 1 \
  '{full_name:$full_name,phone:$phone,email:$email,specialty:$specialty,status:$status,password:$password,identity_card:$identity_card,workshop_id:$workshop_id,sucursal_id:$sucursal_id}')"
mechanic_create_resp="$(curl -i -s -X POST "${BASE_URL}/api/mecanicos" \
  -H "Authorization: Bearer ${admin_token}" \
  -H 'Content-Type: application/json' \
  -d "$mechanic_payload")"
printf '== create mechanic fixture ==\n%s\n\n' "$mechanic_create_resp"

mecanico_id="$(printf '%s' "$mechanic_create_resp" | extract_body | jq -r '.id')"
mecanico_cliente_id="$(printf '%s' "$mechanic_create_resp" | extract_body | jq -r '.cliente_id')"

mec_login="$(login "$mechanic_email" "$mechanic_password" "client")"
printf '== login mechanic fixture ==\n%s\n\n' "$mec_login"
mec_token="$(printf '%s' "$mec_login" | extract_token)"

if [[ -z "${mecanico_id}" || "${mecanico_id}" == "null" || -z "${mecanico_cliente_id}" || "${mecanico_cliente_id}" == "null" || -z "${mec_token}" ]]; then
  echo "No se pudo crear o autenticar el mecanico fixture para validar el flujo E2E" >&2
  exit 1
fi

assign_payload="$(jq -nc --argjson mecanico_id "$mecanico_id" '{mecanico_id:$mecanico_id}')"
assign_resp="$(curl -i -s -X PUT "${BASE_URL}/api/emergencias/${emergency_id}/mechanic-assignment?workshop_id=1" \
  -H "Authorization: Bearer ${admin_token}" \
  -H 'Content-Type: application/json' \
  -d "$assign_payload")"
printf '== assign mechanic ==\n%s\n\n' "$assign_resp"

tracking_resp="$(curl -i -s -X POST "${BASE_URL}/api/mobile/emergencias/${emergency_id}/tracking/events" \
  -H "Authorization: Bearer ${mec_token}" \
  -H 'Content-Type: application/json' \
  -d '{"latitud":-17.7829,"longitud":-63.1814,"heading":88.0,"speed":22.5,"event_type":"moving"}')"
printf '== create tracking event ==\n%s\n\n' "$tracking_resp"

ficha_payload="$(jq -nc \
  --argjson emergencia_id "$emergency_id" \
  --argjson assigned_mechanic_id "$mecanico_cliente_id" \
  --arg vehiculo "Recepcion FCM ${ts}" \
  --arg placa "FCM${ts: -6}" \
  --arg marca "Toyota" \
  --arg modelo "FCM" \
  --argjson anio 2020 \
  --arg problema_reportado "Flujo FCM operativo ${ts}" \
  --arg observaciones "Validacion flujo FCM" \
  '{emergencia_id:$emergencia_id,vehiculo:$vehiculo,placa:$placa,marca:$marca,modelo:$modelo,anio:$anio,problema_reportado:$problema_reportado,observaciones:$observaciones,assigned_mechanic_id:$assigned_mechanic_id}')"
ficha_resp="$(curl -i -s -X POST "${BASE_URL}/api/fichas-recepcion" \
  -H "Authorization: Bearer ${sec_token}" \
  -H 'Content-Type: application/json' \
  -d "$ficha_payload")"
printf '== create ficha recepcion ==\n%s\n\n' "$ficha_resp"
recepcion_id="$(printf '%s' "$ficha_resp" | extract_body | jq -r '.id')"

diagnostico_payload="$(jq -nc --arg diagnostic_text "Diagnostico FCM ${ts}" --arg estimated_work "Cierre operativo FCM" --argjson estimated_cost 300 '{diagnostic_text:$diagnostic_text,estimated_work:$estimated_work,estimated_cost:$estimated_cost}')"
diagnostico_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/diagnostico" \
  -H "Authorization: Bearer ${mec_token}" \
  -H 'Content-Type: application/json' \
  -d "$diagnostico_payload")"
printf '== create diagnostico ==\n%s\n\n' "$diagnostico_resp"

observacion_payload="$(jq -nc --arg observation_text "Observacion FCM ${ts}" --arg work_status "completado" '{observation_text:$observation_text,work_status:$work_status}')"
observacion_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/observaciones" \
  -H "Authorization: Bearer ${mec_token}" \
  -H 'Content-Type: application/json' \
  -d "$observacion_payload")"
printf '== create observacion ==\n%s\n\n' "$observacion_resp"

finalize_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/finalizar" \
  -H "Authorization: Bearer ${mec_token}" \
  -H 'Content-Type: application/json' \
  -d '{"admin_override":false}')"
printf '== finalize recepcion ==\n%s\n\n' "$finalize_resp"

deliver_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/entregar" \
  -H "Authorization: Bearer ${sec_token}")"
printf '== deliver recepcion ==\n%s\n\n' "$deliver_resp"

unread_before_resp="$(curl -i -s "${BASE_URL}/api/mobile/notificaciones/unread-count" \
  -H "Authorization: Bearer ${client_token}")"
notifications_resp="$(curl -i -s "${BASE_URL}/api/mobile/notificaciones" \
  -H "Authorization: Bearer ${client_token}")"

printf '== unread count before ==\n%s\n\n' "$unread_before_resp"
printf '== notifications list ==\n%s\n\n' "$notifications_resp"

notifications_body="$(printf '%s' "$notifications_resp" | extract_body)"
assert_contains_type "$notifications_body" "tracking_started"
assert_contains_type "$notifications_body" "recepcion_finalizada"
assert_contains_type "$notifications_body" "vehiculo_entregado"
assert_contains_type "$notifications_body" "emergencia_cerrada"

tracking_notification_id="$(printf '%s' "$notifications_body" | jq -r '[.[] | select(.tipo == "tracking_started")][0].id')"
mark_read_resp="$(curl -i -s -X PATCH "${BASE_URL}/api/mobile/notificaciones/${tracking_notification_id}/leida" \
  -H "Authorization: Bearer ${client_token}")"
unread_after_resp="$(curl -i -s "${BASE_URL}/api/mobile/notificaciones/unread-count" \
  -H "Authorization: Bearer ${client_token}")"

printf '== mark tracking_started read ==\n%s\n\n' "$mark_read_resp"
printf '== unread count after ==\n%s\n\n' "$unread_after_resp"

printf '== notification rows in DB ==\n'
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
  "SELECT id, tipo, emergencia_id, leida, created_at
     FROM notificaciones_cliente
    WHERE cliente_id = ${client_id}
    ORDER BY id;"
