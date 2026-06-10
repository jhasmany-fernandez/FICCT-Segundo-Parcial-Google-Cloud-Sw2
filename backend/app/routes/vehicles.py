from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import settings
from app.db import create_vehicle, delete_vehicle, get_vehicle_by_id, list_vehicles, update_vehicle
from app.schemas import VehicleResponse
from app.security import ensure_client_exists, normalize_plate
from app.uploads import remove_vehicle_photo, save_vehicle_photo


# ================================================================
# ARCHIVO: vehicles.py
# TIPO: Controlador de vehiculos
# ESTE ARCHIVO SI TIENE METODOS
#
# QUE HACE ESTE ARCHIVO:
# Administra los vehiculos de los clientes, incluyendo registro,
# listado, actualizacion, eliminacion y manejo de fotos.
# Actua como controlador porque recibe peticiones, arma el flujo del
# modulo y devuelve respuestas listas para la app o frontend.
#
# CONTROLADORES / METODOS QUE TIENE:
# - register_vehicle:
#   Registra un vehiculo nuevo.
# - get_vehicles:
#   Lista los vehiculos de un cliente.
# - edit_vehicle:
#   Actualiza los datos de un vehiculo y opcionalmente su foto.
# - remove_vehicle:
#   Elimina un vehiculo y limpia su foto asociada.
# Los metodos de este archivo cubren el ciclo completo de vida de un vehiculo.
# ================================================================
router = APIRouter(prefix=settings.api_prefix, tags=["vehicles"])


# -------------------------------------------------------------------
# LOGICA:
# Aqui se maneja el ciclo de vida de los vehiculos del cliente,
# incluyendo validacion del propietario y reemplazo de fotos.
# En este modulo, "logica" significa validar el dueño, decidir si se
# conserva o reemplaza una foto y mantener coherencia entre base y disco.
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# CONEXION CON EL MOVIL:
# Estos endpoints son usados por la app movil para administrar los
# vehiculos del cliente. Desde el movil se puede:
# - registrar un vehiculo
# - listar vehiculos
# - editar datos y foto
# - eliminar un vehiculo
# Aqui "conexion con el movil" significa que el backend recibe datos
# enviados desde formularios del telefono y responde con informacion
# que luego la app muestra al usuario.
# -------------------------------------------------------------------
# ================================================================
# CONTROLADOR: REGISTRO DE VEHICULO
# Atiende la creacion de vehiculos para un cliente.
# ================================================================
@router.post(
    "/vehiculos",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_vehicle(
    client_id: int = Form(ge=1),
    brand: str = Form(min_length=1, max_length=120),
    model: str = Form(min_length=1, max_length=120),
    year: int = Form(ge=1900, le=2100),
    plate: str = Form(min_length=3, max_length=40),
    color: str = Form(min_length=2, max_length=80),
    is_primary: bool = Form(default=False),
    photo: UploadFile | None = File(default=None),
) -> VehicleResponse:
    # Recibe desde el movil un formulario multipart con datos del vehiculo y una foto opcional.
    # LOGICA: primero se valida el cliente y luego se prepara el payload limpio para guardar.
    # Esto asegura que no existan vehiculos sin un propietario valido.
    # Antes de crear el vehiculo, valida que el cliente propietario exista.
    # ================================================================
    # VALIDACION: CLIENTE PROPIETARIO
    # AQUI SE HACE ESTA VALIDACION DE EXISTENCIA DEL CLIENTE PROPIETARIO DEL VEHICULO.
    # ================================================================
    ensure_client_exists(client_id)
    # Si el movil manda una imagen, aqui se guarda y se genera la URL publica.
    photo_path, photo_url = save_vehicle_photo(photo)

    # ================================================================
    # METODO: ARMADO DEL PAYLOAD DEL VEHICULO
    # Prepara los datos finales antes de insertarlos.
    # ================================================================
    vehicle_payload = {
        # Campos enviados desde el formulario del movil.
        "client_id": client_id,
        "brand": brand.strip(),
        "model": model.strip(),
        "year": year,
        "plate": normalize_plate(plate),
        "color": color.strip(),
        "is_primary": is_primary,
        "photo_path": photo_path,
        "photo_url": photo_url,
    }

    try:
        # La insercion puede fallar por conexion o por placa duplicada.
        created = create_vehicle(vehicle_payload)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un vehiculo con esa placa",
        ) from exc

    # ================================================================
    # METODO: RESPUESTA DE REGISTRO
    # Devuelve el vehiculo creado con el esquema esperado por la API.
    # ================================================================
    return VehicleResponse.model_validate(created)


# ================================================================
# CONTROLADOR: LISTADO DE VEHICULOS
# Lista los vehiculos asociados a un cliente.
# ================================================================
@router.get(
    "/vehiculos",
    response_model=list[VehicleResponse],
)
def get_vehicles(client_id: int = Query(ge=1)) -> list[VehicleResponse]:
    # LOGICA: solo se listan vehiculos del cliente solicitado.
    # Asi cada consulta se mantiene ligada a un propietario concreto.
    # La app movil consulta aqui los vehiculos registrados del cliente autenticado.
    ensure_client_exists(client_id)
    try:
        rows = list_vehicles(client_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    # ================================================================
    # METODO: RESPUESTA DE LISTADO
    # Convierte la consulta al formato de salida de la API.
    # ================================================================
    return [VehicleResponse.model_validate(row) for row in rows]


# ================================================================
# CONTROLADOR: EDICION DE VEHICULO
# Actualiza un vehiculo existente y su foto si corresponde.
# ================================================================
@router.put(
    "/vehiculos/{vehicle_id}",
    response_model=VehicleResponse,
)
def edit_vehicle(
    vehicle_id: int,
    client_id: int = Form(ge=1),
    brand: str = Form(min_length=1, max_length=120),
    model: str = Form(min_length=1, max_length=120),
    year: int = Form(ge=1900, le=2100),
    plate: str = Form(min_length=3, max_length=40),
    color: str = Form(min_length=2, max_length=80),
    is_primary: bool = Form(default=False),
    photo: UploadFile | None = File(default=None),
) -> VehicleResponse:
    # Recibe desde el movil la actualizacion del vehiculo, con opcion de reemplazar la foto actual.
    # LOGICA: si no llega foto nueva, la anterior debe mantenerse.
    # Esto evita perder la imagen existente por una edicion parcial.
    ensure_client_exists(client_id)
    try:
        # ================================================================
        # VALIDACION: VEHICULO EXISTENTE
        # AQUI SE HACE ESTA VALIDACION DE EXISTENCIA DEL VEHICULO PARA CONSERVAR O REEMPLAZAR FOTO.
        # ================================================================
        # Carga el vehiculo actual para mantener la foto previa si el usuario no sube una nueva.
        current_vehicle = get_vehicle_by_id(vehicle_id, client_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not current_vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")

    new_photo_path, new_photo_url = save_vehicle_photo(photo)
    # ================================================================
    # METODO: DECISION SOBRE LA FOTO
    # Decide si conservar la foto actual o reemplazarla por una nueva.
    # ================================================================
    # Si hay una foto nueva se reemplazan las rutas; si no, se conservan las existentes.
    photo_path = new_photo_path if new_photo_path is not None else current_vehicle.get("photo_path")
    photo_url = new_photo_url if new_photo_url is not None else current_vehicle.get("photo_url")

    vehicle_payload = {
        # Nuevo estado del vehiculo segun lo que envio la app movil en la edicion.
        "client_id": client_id,
        "brand": brand.strip(),
        "model": model.strip(),
        "year": year,
        "plate": normalize_plate(plate),
        "color": color.strip(),
        "is_primary": is_primary,
        "photo_path": photo_path,
        "photo_url": photo_url,
    }

    try:
        updated = update_vehicle(vehicle_id, vehicle_payload)
    except OperationalError as exc:
        # Si la base falla despues de subir una nueva imagen, se limpia el archivo para no dejar basura.
        if new_photo_path is not None:
            remove_vehicle_photo(new_photo_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    except IntegrityError as exc:
        if new_photo_path is not None:
            remove_vehicle_photo(new_photo_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un vehiculo con esa placa",
        ) from exc

    # ================================================================
    # VALIDACION: RESULTADO DE ACTUALIZACION
    # AQUI SE HACE ESTA VALIDACION DE ACTUALIZACION EXITOSA SOBRE UN VEHICULO EXISTENTE.
    # ================================================================
    if not updated:
        if new_photo_path is not None:
            remove_vehicle_photo(new_photo_path)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")

    if new_photo_path is not None:
        # Una vez confirmada la actualizacion en base de datos, se elimina la foto anterior del disco.
        remove_vehicle_photo(str(current_vehicle.get("photo_path")) if current_vehicle.get("photo_path") else None)

    # ================================================================
    # METODO: RESPUESTA DE EDICION
    # Devuelve el vehiculo actualizado.
    # ================================================================
    return VehicleResponse.model_validate(updated)


# ================================================================
# CONTROLADOR: ELIMINACION DE VEHICULO
# Elimina un vehiculo y limpia su imagen asociada.
# ================================================================
@router.delete(
    "/vehiculos/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_vehicle(vehicle_id: int, client_id: int = Query(ge=1)) -> None:
    # LOGICA: al borrar el registro, tambien se limpia la imagen asociada en disco.
    # Asi no quedan archivos huérfanos ocupando espacio.
    # Permite que el movil solicite eliminar un vehiculo puntual del cliente.
    ensure_client_exists(client_id)
    try:
        deleted = delete_vehicle(vehicle_id, client_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")

    # Despues del borrado logico en base, elimina la imagen fisica asociada si existia.
    remove_vehicle_photo(str(deleted.get("photo_path")) if deleted.get("photo_path") else None)
