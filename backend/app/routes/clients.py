from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db import create_client, delete_client, list_clients, update_client, update_client_status
from app.schemas import (
    ClientRegistrationCreate,
    ClientRegistrationResponse,
    ClientStatusUpdate,
    ClientUpdate,
)
from app.security import hash_password, is_protected_admin_email, is_protected_admin_role, normalize_email


# ================================================================
# ARCHIVO: clients.py
# TIPO: Controlador de clientes
# ESTE ARCHIVO SI TIENE METODOS
#
# QUE HACE ESTE ARCHIVO:
# Administra el registro, listado, edicion, cambio de estado y
# eliminacion de clientes del sistema.
# Aqui "controlador" indica que este archivo expone rutas HTTP del
# modulo de clientes y coordina validaciones, operaciones y respuestas.
#
# CONTROLADORES / METODOS QUE TIENE:
# - register_client:
#   Registra un cliente nuevo.
# - get_clients:
#   Lista todos los clientes registrados.
# - edit_client_status:
#   Cambia el estado de una cuenta de cliente.
# - edit_client:
#   Actualiza los datos de un cliente.
# - remove_client:
#   Elimina un cliente y sus recursos asociados.
# En este archivo, cada metodo representa una accion del CRUD o de
# administracion sobre clientes.
# ================================================================
router = APIRouter(prefix=settings.api_prefix, tags=["clients"])


# -------------------------------------------------------------------
# LOGICA:
# Aqui se controla el alta, actualizacion, suspension y eliminacion
# de clientes, aplicando restricciones de correo, rol y duplicados.
# "Logica" aqui significa las reglas que definen si un cliente puede
# registrarse, actualizarse, suspenderse o eliminarse.
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# CONEXION CON EL MOVIL:
# La aplicacion movil usa este endpoint para registrar clientes nuevos
# y tambien para enviar cambios del perfil del usuario.
# Aqui "conexion con el movil" indica que estos metodos reciben la
# informacion escrita por el usuario en pantallas del telefono, como
# formularios de registro, edicion de perfil o actualizacion de datos.
# -------------------------------------------------------------------
# ================================================================
# CONTROLADOR: REGISTRO DE CLIENTE
# Atiende la creacion de clientes nuevos.
# ================================================================
@router.post(
    "/clientes",
    response_model=ClientRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_client(payload: ClientRegistrationCreate) -> ClientRegistrationResponse:
    # Recibe el formulario de registro que completa el usuario desde la aplicacion movil.
    # LOGICA: se normaliza el correo y se bloquean casos reservados para administracion.
    # Esto evita conflictos con cuentas especiales del sistema.
    normalized_email = normalize_email(payload.email)

    # ================================================================
    # VALIDACION: RESTRICCIONES DE REGISTRO
    # AQUI SE HACE ESTA VALIDACION DE BLOQUEO DE CORREO Y ROL RESERVADOS EN EL REGISTRO.
    # ================================================================
    # Protege el correo reservado del administrador para que no pueda registrarse como cliente normal.
    if is_protected_admin_email(normalized_email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ese correo está reservado para el administrador del sistema",
        )

    if is_protected_admin_role(payload.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se permite registrar clientes con rol administrador",
        )

    # ================================================================
    # METODO: ARMADO DEL PAYLOAD
    # Construye la informacion final que se enviara a la base de datos.
    # ================================================================
    client_payload = {
        "identity_card": payload.identity_card,
        "full_name": payload.full_name,
        "email": normalized_email,
        "phone": payload.phone,
        # Nunca se guarda la contraseña en texto plano; siempre se persiste su hash.
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "status": "active",
        "accepted_terms": payload.accepted_terms,
    }

    try:
        # La insercion puede fallar por restricciones unicas en carnet o correo.
        created = create_client(client_payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese carnet o correo",
        ) from exc

    # ================================================================
    # METODO: RESPUESTA DE REGISTRO
    # Convierte el cliente creado al esquema de salida esperado.
    # ================================================================
    return ClientRegistrationResponse.model_validate(created)


# ================================================================
# CONTROLADOR: LISTADO DE CLIENTES
# Devuelve el listado completo de clientes.
# ================================================================
@router.get(
    "/clientes",
    response_model=list[ClientRegistrationResponse],
)
def get_clients() -> list[ClientRegistrationResponse]:
    # Devuelve el listado de clientes para paneles administrativos o vistas de gestion.
    rows = list_clients()
    # ================================================================
    # METODO: RESPUESTA DE LISTADO
    # Transforma las filas al esquema de salida de la API.
    # ================================================================
    return [ClientRegistrationResponse.model_validate(row) for row in rows]


# ================================================================
# CONTROLADOR: CAMBIO DE ESTADO DE CLIENTE
# Permite suspender o reactivar una cuenta.
# ================================================================
@router.put(
    "/clientes/{client_id}/status",
    response_model=ClientRegistrationResponse,
)
def edit_client_status(client_id: int, payload: ClientStatusUpdate) -> ClientRegistrationResponse:
    # LOGICA: este flujo solo altera el estado de la cuenta, sin tocar el resto del perfil.
    # Sirve para suspender o reactivar sin reescribir otros datos.
    # Permite bloquear o reactivar cuentas sin modificar el resto del perfil.
    updated = update_client_status(client_id, payload.status)

    # ================================================================
    # VALIDACION: CLIENTE EXISTENTE
    # AQUI SE HACE ESTA VALIDACION DE EXISTENCIA DEL CLIENTE A ACTUALIZAR.
    # ================================================================
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    # ================================================================
    # METODO: RESPUESTA DE CAMBIO DE ESTADO
    # Devuelve el cliente con el nuevo estado aplicado.
    # ================================================================
    return ClientRegistrationResponse.model_validate(updated)


# ================================================================
# CONTROLADOR: EDICION DE CLIENTE
# Actualiza los datos principales de un cliente existente.
# ================================================================
@router.put(
    "/clientes/{client_id}",
    response_model=ClientRegistrationResponse,
)
def edit_client(client_id: int, payload: ClientUpdate) -> ClientRegistrationResponse:
    # CONEXION CON EL MOVIL: aqui llega la edicion del perfil del cliente desde la app.
    # Recibe cambios del perfil del cliente enviados desde una pantalla de edicion.
    # LOGICA: si no mandan contraseña nueva, se conserva la contraseña anterior.
    # Asi no se obliga al usuario a reingresar su clave en cada actualizacion.
    normalized_email = normalize_email(payload.email)

    # ================================================================
    # VALIDACION: RESTRICCIONES DE EDICION
    # AQUI SE HACE ESTA VALIDACION DE BLOQUEO DE CORREO Y ROL RESERVADOS EN LA EDICION.
    # ================================================================
    if is_protected_admin_email(normalized_email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ese correo está reservado para el administrador del sistema",
        )

    if is_protected_admin_role(payload.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se permite asignar el rol administrador desde este módulo",
        )

    # ================================================================
    # METODO: PAYLOAD DE ACTUALIZACION
    # Prepara la informacion final para actualizar al cliente.
    # ================================================================
    client_payload = {
        "identity_card": payload.identity_card,
        "full_name": payload.full_name,
        "email": normalized_email,
        "phone": payload.phone,
        # Si no llega una nueva contraseña, la consulta SQL conserva el hash actual con COALESCE.
        "password_hash": hash_password(payload.password) if payload.password else None,
        "role": payload.role,
        "status": payload.status,
        "accepted_terms": payload.accepted_terms,
    }

    # ================================================================
    # VALIDACION: DATOS UNICOS Y CLIENTE EXISTENTE
    # AQUI SE HACE ESTA VALIDACION DE CONFLICTOS DE UNICIDAD Y EXISTENCIA DEL CLIENTE.
    # ================================================================
    try:
        updated = update_client(client_id, client_payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese carnet o correo",
        ) from exc

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    # ================================================================
    # METODO: RESPUESTA DE EDICION
    # Devuelve el cliente ya actualizado.
    # ================================================================
    return ClientRegistrationResponse.model_validate(updated)


# ================================================================
# CONTROLADOR: ELIMINACION DE CLIENTE
# Elimina un cliente y sus recursos asociados.
# ================================================================
@router.delete(
    "/clientes/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_client(client_id: int) -> None:
    # LOGICA: al eliminar un cliente, tambien deben desaparecer sus recursos asociados.
    # Esto mantiene consistente la informacion relacionada del sistema.
    # El borrado tambien elimina sus vehiculos asociados desde la capa de base de datos.
    deleted = delete_client(client_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
