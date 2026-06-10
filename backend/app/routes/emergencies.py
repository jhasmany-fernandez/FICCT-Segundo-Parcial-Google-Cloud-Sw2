import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.constants import MAX_EMERGENCY_PHOTOS
from app.db import create_emergency_report
from app.schemas import EmergencyReportResponse
from app.security import ensure_client_exists, normalize_optional_text, normalize_plate
from app.uploads import (
    cleanup_uploaded_files,
    save_emergency_audio,
    save_emergency_photo,
    serialize_emergency_report,
)


# ================================================================
# ARCHIVO: emergencies.py
# TIPO: Controlador de emergencias
# ESTE ARCHIVO SI TIENE METODOS
#
# QUE HACE ESTE ARCHIVO:
# Recibe y procesa reportes de emergencia enviados por el usuario,
# incluyendo texto, ubicacion, fotos y audio.
# Este archivo funciona como controlador porque recibe la solicitud,
# valida lo que manda el usuario y coordina guardado de archivos y base.
#
# CONTROLADORES / METODOS QUE TIENE:
# - register_emergency:
#   Registra una emergencia, guarda multimedia y persiste el reporte.
# El metodo principal de este modulo centraliza todo el flujo del
# reporte de emergencia.
# ================================================================
router = APIRouter(prefix=settings.api_prefix, tags=["emergencies"])


# -------------------------------------------------------------------
# LOGICA:
# Aqui se concentra la logica de recepcion, validacion y persistencia
# de reportes de emergencia con multimedia.
# Aqui "logica" significa las decisiones para validar cliente, limitar
# fotos, guardar archivos y limpiar residuos si algo falla.
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# CONEXION CON EL MOVIL:
# Este endpoint es consumido directamente por la app movil cuando el
# usuario reporta una emergencia. Desde aqui llegan:
# - datos del vehiculo
# - tipo de problema
# - descripcion
# - ubicacion GPS
# - fotos tomadas desde el celular
# - audio grabado desde el celular
# En otras palabras, este bloque marca el punto exacto donde el backend
# recibe lo que la app movil captura en el telefono y lo transforma en
# un reporte que luego se guarda en la base de datos.
# -------------------------------------------------------------------
# ================================================================
# CONTROLADOR: REGISTRO DE EMERGENCIA
# Procesa el reporte completo de una emergencia.
# ================================================================
@router.post(
    "/emergencias",
    response_model=EmergencyReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_emergency(
    client_id: int | None = Form(default=None, ge=1),
    vehicle_name: str = Form(min_length=1, max_length=160),
    vehicle_plate: str = Form(min_length=3, max_length=40),
    problem_type: str = Form(min_length=2, max_length=120),
    description: str | None = Form(default=None, min_length=3, max_length=4000),
    latitude: float | None = Form(default=None, ge=-90, le=90),
    longitude: float | None = Form(default=None, ge=-180, le=180),
    address: str | None = Form(default=None, max_length=255),
    zone: str | None = Form(default=None, max_length=120),
    audio_duration_seconds: float | None = Form(default=None, ge=0),
    photos: list[UploadFile] = File(default=[]),
    audio: UploadFile | None = File(default=None),
) -> EmergencyReportResponse:
    # Este endpoint recibe desde el movil un multipart/form-data con texto, ubicacion, fotos y audio.
    # LOGICA: el reporte puede existir con o sin cliente, pero si llega client_id debe ser valido.
    # Esto permite reportes anonimos sin perder control cuando si hay usuario identificado.
    if client_id is not None:
        # El reporte puede ser anonimo, pero si trae client_id se valida que pertenezca a un cliente real.
        ensure_client_exists(client_id)

    # ================================================================
    # VALIDACION: ARCHIVOS RECIBIDOS
    # AQUI SE HACE ESTA VALIDACION DE FOTOS NO VACIAS Y LIMITE MAXIMO DE ADJUNTOS.
    # ================================================================
    # Filtra archivos vacios que algunos clientes moviles pueden enviar al adjuntar multimedia.
    valid_photos = [photo for photo in photos if photo.filename]

    if len(valid_photos) > MAX_EMERGENCY_PHOTOS:
        # LOGICA: se limita la cantidad de fotos para controlar peso y volumen del reporte.
        # La restriccion protege almacenamiento y rendimiento.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Se permiten como maximo {MAX_EMERGENCY_PHOTOS} fotos por emergencia",
        )

    # Estas variables almacenan temporalmente los archivos recibidos desde el movil.
    photo_paths: list[str] = []
    photo_urls: list[str] = []
    audio_path: str | None = None

    try:
        # ================================================================
        # METODO: GUARDADO DE MULTIMEDIA
        # Guarda fotos y audio antes de registrar la emergencia.
        # ================================================================
        # LOGICA: primero se guardan archivos y luego se persiste el reporte en base de datos.
        # Se hace en este orden porque la base necesita conocer las rutas finales de los archivos.
        # Guarda cada evidencia fotografica subida desde el movil y conserva sus rutas para luego persistirlas en la base.
        for photo in valid_photos:
            relative_path, public_url = save_emergency_photo(photo)
            photo_paths.append(relative_path)
            photo_urls.append(public_url)

        # Procesa el audio grabado en el movil y genera su ruta publica si fue adjuntado.
        audio_path, audio_url = save_emergency_audio(audio)

        # ================================================================
        # METODO: ARMADO DEL PAYLOAD DE EMERGENCIA
        # Construye el objeto final que se persiste en base de datos.
        # ================================================================
        # Arma el payload final que representa exactamente lo que la app movil reporto al backend.
        payload = {
            # Datos de identificacion del reporte enviados desde el movil.
            "client_id": client_id,
            "vehicle_name": vehicle_name.strip(),
            "vehicle_plate": normalize_plate(vehicle_plate),
            "problem_type": problem_type.strip(),
            "description": normalize_optional_text(description),
            # Datos de ubicacion capturados por GPS o ingresados manualmente.
            "latitude": latitude,
            "longitude": longitude,
            "address": normalize_optional_text(address),
            "zone": normalize_optional_text(zone),
            # Evidencia multimedia adjuntada por el usuario desde su telefono.
            "audio_duration_seconds": audio_duration_seconds,
            "photo_paths": json.dumps(photo_paths),
            "photo_urls": json.dumps(photo_urls),
            "audio_path": audio_path,
            "audio_url": audio_url,
        }

        created = create_emergency_report(payload)
    except HTTPException:
        # LOGICA: si algo falla a mitad de proceso, se revierte manualmente la parte de archivos.
        # Esto evita dejar fotos o audios huerfanos en disco.
        # Si falla una validacion o un guardado intermedio, elimina archivos ya subidos para no dejar residuos.
        cleanup_uploaded_files(*photo_paths, audio_path)
        raise
    except OperationalError as exc:
        # Si la base falla luego de recibir contenido del movil, limpia archivos para evitar basura.
        cleanup_uploaded_files(*photo_paths, audio_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    # ================================================================
    # METODO: RESPUESTA DEL REPORTE
    # Devuelve la emergencia registrada con el esquema de salida.
    # ================================================================
    return serialize_emergency_report(created)
