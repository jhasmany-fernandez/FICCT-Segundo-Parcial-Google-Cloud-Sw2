#!/usr/bin/env bash
set -euo pipefail

BASE_URL_VM3="${BASE_URL_VM3:-http://34.122.37.25:8010}"
TMP_DIR="$(mktemp -d /tmp/vm3-academic-XXXXXX)"
EMERGENCIA_ID="${EMERGENCIA_ID:-vm2-vm3-$(date +%s)}"

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

TEXT_FILE="${TMP_DIR}/evidencia.txt"
IMAGE_FILE="${TMP_DIR}/vision.jpg"

cat > "${TEXT_FILE}" <<EOF
Validacion academica VM2 -> VM3
Emergencia: ${EMERGENCIA_ID}
Origen: Google Cloud / VM2
EOF

# Archivo binario minimo para el endpoint simulado de vision.
printf '\377\330\377\340VM3JPEG\377\331' > "${IMAGE_FILE}"

curl_json() {
  local method="$1"
  local url="$2"
  local data="$3"
  local response_file="$4"
  local status

  status="$(curl -sS -o "${response_file}" -w '%{http_code}' -X "${method}" "${url}" \
    -H 'Content-Type: application/json' \
    -d "${data}")"
  printf '%s' "${status}"
}

curl_form() {
  local url="$1"
  shift
  local response_file="$1"
  shift
  local status

  status="$(curl -sS -o "${response_file}" -w '%{http_code}' -X POST "${url}" "$@")"
  printf '%s' "${status}"
}

print_section() {
  local title="$1"
  echo "== ${title} =="
}

print_response() {
  local status="$1"
  local response_file="$2"
  echo "HTTP ${status}"
  cat "${response_file}"
  echo
  echo
}

ensure_status() {
  local actual="$1"
  local expected="$2"
  local label="$3"

  if [[ "${actual}" != "${expected}" ]]; then
    echo "Fallo en ${label}: se esperaba HTTP ${expected} y se obtuvo ${actual}." >&2
    exit 1
  fi
}

ensure_json_key() {
  local response_file="$1"
  local jq_expr="$2"
  local label="$3"

  if ! jq -e "${jq_expr}" "${response_file}" >/dev/null; then
    echo "Respuesta invalida en ${label}: no cumple ${jq_expr}." >&2
    exit 1
  fi
}

health_response="${TMP_DIR}/health.json"
s3_response="${TMP_DIR}/s3.json"
dynamo_response="${TMP_DIR}/dynamo.json"
blockchain_response="${TMP_DIR}/blockchain.json"
vision_response="${TMP_DIR}/vision.json"
n8n_response="${TMP_DIR}/n8n.json"

print_section "1. health VM3"
health_status="$(curl -sS -o "${health_response}" -w '%{http_code}' "${BASE_URL_VM3}/health")"
print_response "${health_status}" "${health_response}"
ensure_status "${health_status}" "200" "health VM3"
ensure_json_key "${health_response}" '.status == "ok"' "health VM3"

print_section "2. upload S3 simulado"
s3_status="$(curl_form "${BASE_URL_VM3}/aws-s3/upload-evidencia" "${s3_response}" \
  -F "emergencia_id=${EMERGENCIA_ID}" \
  -F "archivo=@${TEXT_FILE};type=text/plain")"
print_response "${s3_status}" "${s3_response}"
ensure_status "${s3_status}" "200" "upload S3"
ensure_json_key "${s3_response}" '.bucket and .key and .url_simulada and (.size_bytes >= 1)' "upload S3"

s3_bucket="$(jq -r '.bucket' "${s3_response}")"
s3_key="$(jq -r '.key' "${s3_response}")"
s3_url="$(jq -r '.url_simulada' "${s3_response}")"
text_size="$(wc -c < "${TEXT_FILE}")"

print_section "3. registro DynamoDB simulado"
dynamo_payload="$(jq -nc \
  --arg emergencia_id "${EMERGENCIA_ID}" \
  --arg bucket "${s3_bucket}" \
  --arg key "${s3_key}" \
  --arg tipo "texto" \
  --arg url_simulada "${s3_url}" \
  --arg content_type "text/plain" \
  --argjson size_bytes "${text_size}" \
  '{emergencia_id:$emergencia_id,bucket:$bucket,key:$key,tipo:$tipo,url_simulada:$url_simulada,size_bytes:$size_bytes,content_type:$content_type}')"
dynamo_status="$(curl_json "POST" "${BASE_URL_VM3}/dynamodb/evidencia" "${dynamo_payload}" "${dynamo_response}")"
print_response "${dynamo_status}" "${dynamo_response}"
ensure_status "${dynamo_status}" "200" "registro DynamoDB"
ensure_json_key "${dynamo_response}" '.emergencia_id == "'"${EMERGENCIA_ID}"'"' "registro DynamoDB"

print_section "4. registro Blockchain simulado"
blockchain_payload="$(jq -nc \
  --arg emergencia_id "${EMERGENCIA_ID}" \
  --arg evento "Validacion academica VM2->VM3" \
  --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{emergencia_id:$emergencia_id,evento:$evento,timestamp:$timestamp}')"
blockchain_status="$(curl_json "POST" "${BASE_URL_VM3}/blockchain/registrar" "${blockchain_payload}" "${blockchain_response}")"
print_response "${blockchain_status}" "${blockchain_response}"
ensure_status "${blockchain_status}" "200" "registro Blockchain"
ensure_json_key "${blockchain_response}" '.hash and .emergencia_id == "'"${EMERGENCIA_ID}"'"' "registro Blockchain"

print_section "5. Deep Learning simulado"
vision_status="$(curl_form "${BASE_URL_VM3}/ai/deep-learning/vision" "${vision_response}" \
  -F "emergencia_id=${EMERGENCIA_ID}" \
  -F "imagen=@${IMAGE_FILE};type=image/jpeg")"
print_response "${vision_status}" "${vision_response}"
ensure_status "${vision_status}" "200" "deep learning"
ensure_json_key "${vision_response}" '.modelo and .deteccion and (.confidence >= 0)' "deep learning"

print_section "6. n8n webhook simulado"
n8n_payload="$(jq -nc \
  --arg emergencia_id "${EMERGENCIA_ID}" \
  --arg descripcion "Validacion academica VM2->VM3 desde Google Cloud" \
  '{emergencia_id:$emergencia_id,descripcion:$descripcion}')"
n8n_status="$(curl_json "POST" "${BASE_URL_VM3}/automation/n8n/webhook" "${n8n_payload}" "${n8n_response}")"
print_response "${n8n_status}" "${n8n_response}"
ensure_status "${n8n_status}" "200" "n8n webhook"
ensure_json_key "${n8n_response}" '.emergencia_id == "'"${EMERGENCIA_ID}"'" and .flujo' "n8n webhook"

echo "VALIDACION_VM3_ACADEMIC_SERVICES=OK"
