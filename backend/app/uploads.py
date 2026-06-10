import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.constants import (
    ALLOWED_AUDIO_SUFFIXES,
    ALLOWED_PHOTO_SUFFIXES,
    EMERGENCY_AUDIO_DIR,
    EMERGENCY_PHOTOS_DIR,
    MAX_EMERGENCY_AUDIO_BYTES,
    MAX_EMERGENCY_PHOTO_BYTES,
    UPLOADS_ROOT,
    VEHICLE_UPLOADS_DIR,
)
from app.schemas import EmergencyReportResponse


# -------------------------------------------------------------------
# LOGICA:
# Este modulo maneja la validacion, guardado y limpieza de archivos
# que llegan al backend desde formularios y reportes.
# La logica aqui define como aceptar o rechazar archivos, donde
# guardarlos y como eliminarlos si una operacion falla.
# -------------------------------------------------------------------
def build_public_upload_url(relative_path: str) -> str:
    # Traduce la ruta interna del archivo a la URL publica que expone FastAPI.
    return f"/uploads/{relative_path}"


def remove_file_if_exists(path: Path) -> None:
    if path.is_file():
        path.unlink()


def save_upload_with_limit(
    upload: UploadFile,
    *,
    destination_dir: Path,
    relative_dir: str,
    allowed_suffixes: set[str],
    max_bytes: int | None,
    invalid_type_detail: str,
    too_large_detail: str | None = None,
) -> tuple[str, str]:
    # Valida extension y genera un nombre unico para evitar colisiones entre archivos subidos.
    suffix = Path(upload.filename or "").suffix.lower()

    if suffix not in allowed_suffixes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=invalid_type_detail)

    filename = f"{uuid4().hex}{suffix}"
    relative_path = f"{relative_dir}/{filename}"
    absolute_path = destination_dir / filename
    bytes_written = 0

    # Escribe el archivo por bloques para no cargarlo completo en memoria y poder cortar si excede el limite.
    with absolute_path.open("wb") as buffer:
        while chunk := upload.file.read(1024 * 1024):
            bytes_written += len(chunk)
            if max_bytes is not None and bytes_written > max_bytes:
                buffer.close()
                remove_file_if_exists(absolute_path)
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=too_large_detail)
            buffer.write(chunk)

    return relative_path, build_public_upload_url(relative_path)


def cleanup_uploaded_files(*relative_paths: str | None) -> None:
    for relative_path in relative_paths:
        remove_uploaded_file(relative_path)


def save_vehicle_photo(photo: UploadFile | None) -> tuple[str | None, str | None]:
    if photo is None or not photo.filename:
        return None, None

    # CONEXION CON EL MOVIL: este punto recibe la foto del vehiculo enviada desde el telefono.
    # Esto significa que el archivo sale de la camara o galeria del movil,
    # llega al backend dentro de una peticion HTTP y aqui comienza su guardado.
    # Punto donde se recibe la foto del vehiculo enviada desde el movil y se deriva al guardado fisico.
    # Recibe la foto enviada desde formulario multipart, tipicamente desde camara o galeria del movil.
    return save_upload_with_limit(
        photo,
        destination_dir=VEHICLE_UPLOADS_DIR,
        relative_dir="vehicles",
        allowed_suffixes=ALLOWED_PHOTO_SUFFIXES,
        max_bytes=None,
        invalid_type_detail="La foto debe ser JPG, JPEG, PNG o WEBP",
    )


def save_emergency_photo(photo: UploadFile) -> tuple[str, str]:
    # CONEXION CON EL MOVIL: este punto recibe cada foto adjunta en el reporte enviado desde el telefono.
    # En este lugar el backend toma la imagen que mando la app movil y la prepara para almacenarla.
    # Punto donde se recibe cada foto de la emergencia enviada desde la app movil.
    # Guarda cada imagen de evidencia que la app movil adjunta al reporte de emergencia.
    return save_upload_with_limit(
        photo,
        destination_dir=EMERGENCY_PHOTOS_DIR,
        relative_dir="emergencias/photos",
        allowed_suffixes=ALLOWED_PHOTO_SUFFIXES,
        max_bytes=MAX_EMERGENCY_PHOTO_BYTES,
        invalid_type_detail="Cada foto debe ser JPG, JPEG, PNG o WEBP",
        too_large_detail="Archivo demasiado grande: cada foto puede pesar como máximo 5 MB.",
    )


def save_emergency_audio(audio: UploadFile | None) -> tuple[str | None, str | None]:
    if audio is None or not audio.filename:
        return None, None

    # CONEXION CON EL MOVIL: este punto recibe el audio grabado desde el telefono.
    # Aqui entra al backend el archivo de audio capturado por el usuario desde la app del celular.
    # Punto donde se recibe el audio grabado en el movil antes de guardarlo en disco.
    # Guarda el audio grabado desde el movil como evidencia adicional del incidente.
    return save_upload_with_limit(
        audio,
        destination_dir=EMERGENCY_AUDIO_DIR,
        relative_dir="emergencias/audio",
        allowed_suffixes=ALLOWED_AUDIO_SUFFIXES,
        max_bytes=MAX_EMERGENCY_AUDIO_BYTES,
        invalid_type_detail="El audio debe ser AAC, M4A, MP3, WAV, OGG o WEBM",
        too_large_detail="Archivo demasiado grande: el audio puede pesar como máximo 15 MB.",
    )


def remove_vehicle_photo(photo_path: str | None) -> None:
    remove_uploaded_file(photo_path)


def remove_uploaded_file(relative_path: str | None) -> None:
    if not relative_path:
        return

    # Verifica que la ruta a borrar siga dentro del directorio de uploads para evitar borrar fuera del proyecto.
    candidate = (UPLOADS_ROOT / relative_path).resolve()

    try:
        candidate.relative_to(UPLOADS_ROOT.resolve())
    except ValueError:
        return

    remove_file_if_exists(candidate)


def parse_json_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]

    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []

        if isinstance(decoded, list):
            return [str(item) for item in decoded]

    return []


def normalize_emergency_assignment_fields(row: dict[str, object]) -> dict[str, object]:
    # Canonical emergency assignment fields for new clients.
    if row.get("assigned_mecanico_id") is None:
        row["assigned_mecanico_id"] = row.get("assigned_mechanic_id") or row.get("assigned_technician_id")
    if row.get("assigned_mecanico_name") is None:
        row["assigned_mecanico_name"] = row.get("assigned_mechanic_name") or row.get("assigned_technician_name")
    if row.get("assigned_mecanico_phone") is None:
        row["assigned_mecanico_phone"] = row.get("assigned_mechanic_phone") or row.get("assigned_technician_phone")
    if row.get("assigned_mecanico_email") is None:
        row["assigned_mecanico_email"] = row.get("assigned_mechanic_email") or row.get("assigned_technician_email")
    if row.get("assigned_mecanico_specialty") is None:
        row["assigned_mecanico_specialty"] = (
            row.get("assigned_mechanic_specialty") or row.get("assigned_technician_specialty")
        )
    # Deprecated legacy aliases kept temporarily for backwards compatibility.
    row["assigned_mechanic_id"] = row.get("assigned_mecanico_id")
    row["assigned_mechanic_name"] = row.get("assigned_mecanico_name")
    row["assigned_mechanic_phone"] = row.get("assigned_mecanico_phone")
    row["assigned_mechanic_email"] = row.get("assigned_mecanico_email")
    row["assigned_mechanic_specialty"] = row.get("assigned_mecanico_specialty")
    row["assigned_technician_id"] = row.get("assigned_mecanico_id")
    row["assigned_technician_name"] = row.get("assigned_mecanico_name")
    row["assigned_technician_phone"] = row.get("assigned_mecanico_phone")
    row["assigned_technician_email"] = row.get("assigned_mecanico_email")
    row["assigned_technician_specialty"] = row.get("assigned_mecanico_specialty")
    return row


def serialize_emergency_report(row: dict[str, object]) -> EmergencyReportResponse:
    # Convierte los JSON guardados en texto a listas reales antes de devolver la respuesta al cliente.
    row["photo_paths"] = parse_json_string_list(row.get("photo_paths"))
    row["photo_urls"] = parse_json_string_list(row.get("photo_urls"))
    normalize_emergency_assignment_fields(row)
    return EmergencyReportResponse.model_validate(row)
