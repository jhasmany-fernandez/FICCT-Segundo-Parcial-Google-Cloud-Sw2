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

ts="$(date +%s)"

admin_login="$(login "administrador@acb.com" "123ppp+++" "admin")"
sec_login="$(login "secretaria@acb.com" "secretaria123" "client")"

printf '== login admin ==\n%s\n\n' "$admin_login"
printf '== login secretaria ==\n%s\n\n' "$sec_login"

admin_token="$(printf '%s' "$admin_login" | extract_token)"
sec_token="$(printf '%s' "$sec_login" | extract_token)"

if [[ -z "$admin_token" || -z "$sec_token" ]]; then
  echo "No se pudieron obtener los tokens base de admin/secretaria." >&2
  exit 1
fi

client_vehicle_row="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At -F '|' -c \
  "SELECT c.id, v.id, v.plate
   FROM clientes c
   JOIN vehiculos v ON v.cliente_id = c.id
   WHERE LOWER(TRIM(c.role)) = 'client'
     AND LOWER(TRIM(c.status)) = 'active'
   ORDER BY v.id
   LIMIT 1")"
IFS='|' read -r client_id vehicle_id vehicle_plate <<< "$client_vehicle_row"

sucursal_id="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At -F '|' -c \
  "SELECT id
   FROM sucursales
   WHERE estado = 'ACTIVO'
   ORDER BY id
   LIMIT 1")"

workshop_id="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At -F '|' -c \
  "SELECT id
   FROM registros_taller
   ORDER BY id
   LIMIT 1")"

if [[ -z "${workshop_id:-}" ]]; then
  workshop_id="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At -F '|' -c \
    "INSERT INTO registros_taller (nombre_taller, contact_name, phone, email, zone, specialty, approval_status, password_hash, latitude, longitude)
     VALUES ('Taller Validacion Tracking', 'Operaciones Tracking', '70010000', 'tracking-validacion@example.com', 'Norte', 'Motor', 'aprobado', 'fixture', -17.7833, -63.1821)
     RETURNING id")"
fi

if [[ -z "${client_id:-}" || -z "${vehicle_id:-}" || -z "${sucursal_id:-}" || -z "${workshop_id:-}" ]]; then
  echo "No se pudo resolver cliente/vehiculo/sucursal/taller base para la validacion." >&2
  exit 1
fi

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c \
  "UPDATE sucursales
      SET latitud = COALESCE(latitud, -17.7833),
          longitud = COALESCE(longitud, -63.1821)
    WHERE id = ${sucursal_id};" >/dev/null

problem_type="Bateria descargada"
description="Validacion tracking cierre E2E ${ts}"
address="Validacion GCP ${ts}"
zone="Norte"
latitude="-17.7833"
longitude="-63.1821"

mechanic_email="tracking.mec.${ts}@example.com"
mechanic_password="TrackPass2026!"
mechanic_payload="$(jq -nc \
  --arg full_name "Mecanico Tracking ${ts}" \
  --arg phone "7999${ts: -6}" \
  --arg email "$mechanic_email" \
  --arg specialty "Motor" \
  --arg status "disponible" \
  --arg password "$mechanic_password" \
  --arg identity_card "TRK${ts}" \
  --argjson workshop_id "$workshop_id" \
  --argjson sucursal_id "$sucursal_id" \
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

if [[ -z "${mecanico_id:-}" || -z "${mecanico_cliente_id:-}" || -z "${mec_token:-}" ]]; then
  echo "No se pudo crear o autenticar el mecánico fixture." >&2
  exit 1
fi

create_emergency_resp="$(curl -i -s -X POST "${BASE_URL}/api/emergencias" \
  -H "Authorization: Bearer ${admin_token}" \
  -F "client_id=${client_id}" \
  -F "vehicle_id=${vehicle_id}" \
  -F "problem_type=Motor" \
  -F "description=${description}" \
  -F "latitude=${latitude}" \
  -F "longitude=${longitude}" \
  -F "address=${address}" \
  -F "zone=${zone}" \
  -F "nearest_workshop_id=${workshop_id}")"
printf '== create emergency ==\n%s\n\n' "$create_emergency_resp"
emergency_id="$(printf '%s' "$create_emergency_resp" | extract_body | jq -r '.id')"

accept_resp="$(curl -i -s -X PUT "${BASE_URL}/api/emergencias/${emergency_id}/status?workshop_id=${workshop_id}" \
  -H "Authorization: Bearer ${admin_token}" \
  -H 'Content-Type: application/json' \
  -d '{"emergency_status":"activo"}')"
printf '== accept emergency ==\n%s\n\n' "$accept_resp"

assign_resp="$(curl -i -s -X PUT "${BASE_URL}/api/emergencias/${emergency_id}/mechanic-assignment?workshop_id=${workshop_id}" \
  -H "Authorization: Bearer ${admin_token}" \
  -H 'Content-Type: application/json' \
  -d "{\"mecanico_id\":${mecanico_id}}")"
printf '== assign mechanic ==\n%s\n\n' "$assign_resp"

accept_assignment_resp="$(curl -i -s -X POST "${BASE_URL}/api/emergencias/${emergency_id}/aceptar" \
  -H "Authorization: Bearer ${mec_token}")"
printf '== accept mechanic assignment ==\n%s\n\n' "$accept_assignment_resp"

tracking_get_resp="$(curl -i -s "${BASE_URL}/api/emergencias/${emergency_id}/tracking" \
  -H "Authorization: Bearer ${admin_token}")"
printf '== get operational tracking ==\n%s\n\n' "$tracking_get_resp"

tracking_event_resp="$(curl -i -s -X POST "${BASE_URL}/api/mobile/emergencias/${emergency_id}/tracking/events" \
  -H "Authorization: Bearer ${mec_token}" \
  -H 'Content-Type: application/json' \
  -d '{"latitud":-17.7829,"longitud":-63.1814,"heading":88.0,"speed":22.5,"event_type":"moving"}')"
printf '== create tracking event ==\n%s\n\n' "$tracking_event_resp"

ficha_payload="$(jq -nc \
  --argjson emergencia_id "$emergency_id" \
  --argjson assigned_mechanic_id "$mecanico_cliente_id" \
  --arg vehiculo "Recepcion E2E ${ts}" \
  --arg placa "$vehicle_plate" \
  --arg marca "Validacion" \
  --arg modelo "Tracking" \
  --argjson anio 2026 \
  --arg problema_reportado "Recepcion desde emergencia ${ts}" \
  --arg observaciones "Flujo E2E tracking-cierre" \
  '{emergencia_id:$emergencia_id,vehiculo:$vehiculo,placa:$placa,marca:$marca,modelo:$modelo,anio:$anio,problema_reportado:$problema_reportado,observaciones:$observaciones,assigned_mechanic_id:$assigned_mechanic_id}')"
ficha_resp="$(curl -i -s -X POST "${BASE_URL}/api/fichas-recepcion" \
  -H "Authorization: Bearer ${sec_token}" \
  -H 'Content-Type: application/json' \
  -d "$ficha_payload")"
printf '== create ficha recepcion ==\n%s\n\n' "$ficha_resp"
recepcion_id="$(printf '%s' "$ficha_resp" | extract_body | jq -r '.id')"

diagnostico_payload="$(jq -nc --arg diagnostic_text "Diagnostico tracking cierre ${ts}" --arg estimated_work "Cierre operativo" --argjson estimated_cost 250 '{diagnostic_text:$diagnostic_text,estimated_work:$estimated_work,estimated_cost:$estimated_cost}')"
diagnostico_resp="$(curl -i -s -X POST "${BASE_URL}/api/recepciones/${recepcion_id}/diagnostico" \
  -H "Authorization: Bearer ${mec_token}" \
  -H 'Content-Type: application/json' \
  -d "$diagnostico_payload")"
printf '== create diagnostico ==\n%s\n\n' "$diagnostico_resp"

observacion_payload="$(jq -nc --arg observation_text "Observacion tracking cierre ${ts}" --arg work_status "completado" '{observation_text:$observation_text,work_status:$work_status}')"
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

cerrada_resp="$(curl -i -s "${BASE_URL}/api/emergencias?emergency_status=cerrada" \
  -H "Authorization: Bearer ${admin_token}")"
printf '== list closed emergencies ==\n%s\n\n' "$cerrada_resp"

printf '== final db state ==\n'
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
  "SELECT id, estado_emergencia, closed_at, closed_by_user_id
     FROM reportes_emergencia
    WHERE id = ${emergency_id};
   SELECT reporte_emergencia_id, estado_asignacion, finalized_at, mecanico_id
     FROM asignaciones_emergencia
    WHERE reporte_emergencia_id = ${emergency_id};
   SELECT id, status
     FROM mecanicos
    WHERE id = ${mecanico_id};
   SELECT id, emergencia_id, status, finalized_at, delivered_at, delivered_by_user_id
     FROM fichas_recepcion
    WHERE id = ${recepcion_id};
   SELECT COUNT(*) AS tracking_events
     FROM seguimiento_emergencia_tracking
    WHERE emergencia_id = ${emergency_id};"
