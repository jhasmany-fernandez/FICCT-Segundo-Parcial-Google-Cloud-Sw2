from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.db import (
    create_workshop_registration,
    delete_workshop_registration,
    get_workshop_by_id,
    list_workshop_registrations,
    update_workshop_approval_status_with_password,
    update_workshop_registration,
)
from app.schemas import (
    WorkshopApprovalStatusUpdate,
    WorkshopRegistrationCreate,
    WorkshopRegistrationResponse,
)
from app.security import hash_password


# ================================================================
# ARCHIVO: workshops.py
# TIPO: Controlador de talleres
# ESTE ARCHIVO SI TIENE METODOS
#
# QUE HACE ESTE ARCHIVO:
# Maneja el registro, listado, actualizacion, aprobacion y eliminacion
# de talleres dentro del sistema.
# Este archivo cumple el rol de controlador del modulo de talleres y
# coordina la entrada y salida de datos relacionados a ese modulo.
#
# CONTROLADORES / METODOS QUE TIENE:
# - register_workshop:
#   Registra un taller nuevo en estado pendiente.
# - get_workshops:
#   Lista todos los talleres registrados.
# - edit_workshop:
#   Actualiza los datos de un taller.
# - edit_workshop_approval_status:
#   Cambia el estado de aprobacion de un taller.
# - remove_workshop:
#   Elimina un taller del sistema.
# Cada metodo responde a una accion concreta sobre el ciclo de vida del taller.
# ================================================================
router = APIRouter(prefix=settings.api_prefix, tags=["workshops"])


# -------------------------------------------------------------------
# LOGICA:
# Aqui se maneja el ciclo de vida del taller: registro, edicion,
# aprobacion y eliminacion.
# Aqui "logica" significa las reglas de negocio sobre estados del
# taller y las condiciones para activarlo o modificarlo.
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# CONEXION CON EL MOVIL:
# Si existe una vista movil para talleres, desde aqui se reciben los
# datos del formulario de registro y las actualizaciones de estado.
# Este comentario señala el punto donde una app o interfaz movil
# enviaria datos del taller al backend para ser procesados.
# -------------------------------------------------------------------
# ================================================================
# CONTROLADOR: REGISTRO DE TALLER
# Atiende la creacion de talleres nuevos.
# ================================================================
@router.post(
    "/workshops",
    response_model=WorkshopRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_workshop(payload: WorkshopRegistrationCreate) -> WorkshopRegistrationResponse:
    # Recibe la solicitud de registro de taller enviada desde el formulario del sistema.
    # LOGICA: todo taller nuevo nace pendiente y sin contraseña asignada.
    # Esto obliga a que un administrador revise el registro antes de habilitar acceso.
    # Todo taller nuevo entra como pendiente hasta que un administrador revise y apruebe su registro.
    created = create_workshop_registration(
        {
            **payload.model_dump(),
            "approval_status": "pendiente",
            "password_hash": None,
        }
    )
    # ================================================================
    # METODO: RESPUESTA DE REGISTRO
    # Devuelve el taller creado con el esquema de salida esperado.
    # ================================================================
    return WorkshopRegistrationResponse.model_validate(created)


# ================================================================
# CONTROLADOR: LISTADO DE TALLERES
# Devuelve todos los talleres registrados.
# ================================================================
@router.get(
    "/workshops",
    response_model=list[WorkshopRegistrationResponse],
)
def get_workshops() -> list[WorkshopRegistrationResponse]:
    rows = list_workshop_registrations()
    # ================================================================
    # METODO: RESPUESTA DE LISTADO
    # Convierte cada taller al esquema de salida correspondiente.
    # ================================================================
    return [WorkshopRegistrationResponse.model_validate(row) for row in rows]


# ================================================================
# CONTROLADOR: EDICION DE TALLER
# Actualiza los datos principales de un taller.
# ================================================================
@router.put(
    "/workshops/{workshop_id}",
    response_model=WorkshopRegistrationResponse,
)
def edit_workshop(workshop_id: int, payload: WorkshopRegistrationCreate) -> WorkshopRegistrationResponse:
    # LOGICA: editar datos del taller no debe cambiar ni su aprobacion ni su contraseña.
    # Asi los datos administrativos sensibles solo cambian en flujos especificos.
    # La edicion del perfil no debe cambiar por accidente ni el estado de aprobacion ni la contraseña.
    updated = update_workshop_registration(
        workshop_id,
        {
            **payload.model_dump(),
            "approval_status": None,
            "password_hash": None,
        },
    )

    # ================================================================
    # VALIDACION: TALLER EXISTENTE
    # AQUI SE HACE ESTA VALIDACION DE EXISTENCIA DEL TALLER A EDITAR.
    # ================================================================
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    # ================================================================
    # METODO: RESPUESTA DE EDICION
    # Devuelve el taller actualizado.
    # ================================================================
    return WorkshopRegistrationResponse.model_validate(updated)


# ================================================================
# CONTROLADOR: CAMBIO DE ESTADO DE TALLER
# Modifica el estado de aprobacion del taller.
# ================================================================
@router.put(
    "/workshops/{workshop_id}/approval-status",
    response_model=WorkshopRegistrationResponse,
)
def edit_workshop_approval_status(
    workshop_id: int,
    payload: WorkshopApprovalStatusUpdate,
) -> WorkshopRegistrationResponse:
    # LOGICA: aqui se validan transiciones permitidas de estado para el taller.
    # La validacion impide cambios de estado incoherentes con las reglas del negocio.
    # Primero se consulta el estado actual para validar transiciones de negocio.
    # ================================================================
    # VALIDACION: EXISTENCIA Y TRANSICION DE ESTADO
    # AQUI SE HACE ESTA VALIDACION DE EXISTENCIA DEL TALLER Y TRANSICION VALIDA DE APROBACION.
    # ================================================================
    current_workshop = get_workshop_by_id(workshop_id)

    if not current_workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    current_status = str(current_workshop["approval_status"])
    next_status = payload.approval_status

    if current_status == "activo" and next_status == "pendiente":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un taller activo ya no puede volver a pendiente; solo puede pasar a rechazado",
        )

    # Cuando un taller pasa a activo se le asigna la contraseña temporal inicial para su primer acceso.
    # ================================================================
    # METODO: ACTUALIZACION DE APROBACION
    # Aplica el nuevo estado y genera contraseña temporal si corresponde.
    # ================================================================
    password_hash = hash_password(settings.workshop_initial_password) if next_status == "activo" else None
    updated = update_workshop_approval_status_with_password(
        workshop_id,
        next_status,
        password_hash,
    )

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    # ================================================================
    # METODO: RESPUESTA DE CAMBIO DE ESTADO
    # Devuelve el taller con su nuevo estado de aprobacion.
    # ================================================================
    return WorkshopRegistrationResponse.model_validate(updated)


# ================================================================
# CONTROLADOR: ELIMINACION DE TALLER
# Elimina un taller del sistema.
# ================================================================
@router.delete(
    "/workshops/{workshop_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_workshop(workshop_id: int) -> None:
    deleted = delete_workshop_registration(workshop_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
