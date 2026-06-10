import secrets

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.constants import PROTECTED_ADMIN_EMAIL, PROTECTED_ADMIN_ID, PROTECTED_ADMIN_ROLE, WORKSHOP_ROLE
from app.db import get_client_by_email, get_workshop_by_email, update_workshop_password
from app.schemas import LoginRequest, LoginResponse, WorkshopPasswordChangeRequest
from app.security import hash_password, is_protected_admin_email, normalize_email, verify_password


# ================================================================
# ARCHIVO: auth.py
# TIPO: Controlador de autenticacion
# ESTE ARCHIVO SI TIENE METODOS
#
# QUE HACE ESTE ARCHIVO:
# Maneja el inicio de sesion del sistema y el cambio de contraseña
# inicial de los talleres.
# Aqui "controlador" significa que este archivo recibe las peticiones
# HTTP, valida datos de entrada, llama a la logica necesaria y devuelve
# la respuesta final al cliente.
#
# CONTROLADORES / METODOS QUE TIENE:
# - login:
#   Recibe credenciales y decide si el acceso corresponde a un
#   administrador, taller o cliente.
# - change_workshop_password:
#   Permite cambiar la contraseña temporal inicial de un taller.
# En este archivo, "metodos" son las funciones que atienden rutas de
# FastAPI y ejecutan una accion concreta del modulo de autenticacion.
# ================================================================
router = APIRouter(prefix=settings.api_prefix, tags=["auth"])


# -------------------------------------------------------------------
# LOGICA:
# Aqui se decide que tipo de usuario intenta entrar al sistema
# (administrador, taller o cliente) y que validaciones aplicar.
# En este contexto, "logica" significa las reglas del negocio:
# que camino seguir, que se permite, que se bloquea y que condiciones
# deben cumplirse antes de responder.
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# CONEXION CON EL MOVIL:
# La app movil usa estos endpoints para iniciar sesion y, en el caso
# de talleres, cambiar la contraseña temporal inicial.
# En este contexto, "conexion con el movil" significa el punto donde
# el backend recibe peticiones HTTP enviadas desde la aplicacion del
# telefono, por ejemplo cuando el usuario toca "Iniciar sesion" o
# cuando un taller envia su nueva contraseña.
# -------------------------------------------------------------------
# ================================================================
# CONTROLADOR: LOGIN
# Este controlador procesa la ruta de inicio de sesion.
# ================================================================
@router.post(
    "/auth/login",
    response_model=LoginResponse,
)
def login(payload: LoginRequest) -> LoginResponse:
    # Este endpoint recibe las credenciales enviadas por la pantalla de login del movil o del frontend web.
    # Normaliza el correo para evitar errores por mayusculas, espacios o formatos inconsistentes.
    normalized_email = normalize_email(payload.email)

    # ================================================================
    # VALIDACION: ADMINISTRADOR PROTEGIDO
    # AQUI SE HACE ESTA VALIDACION DE CORREO RESERVADO Y CLAVE DEL ADMINISTRADOR.
    # ================================================================
    if is_protected_admin_email(normalized_email):
        # LOGICA: si el correo es el reservado del administrador, no se consulta la base de datos.
        # Esto se hace porque el administrador protegido se maneja desde configuracion y no desde tablas.
        # El administrador protegido no se valida contra la tabla de clientes sino contra la configuracion del sistema.
        if payload.password != settings.protected_admin_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contraseña incorrectos",
            )

        return LoginResponse(
            id=PROTECTED_ADMIN_ID,
            email=PROTECTED_ADMIN_EMAIL,
            full_name=settings.protected_admin_full_name,
            phone=settings.protected_admin_phone,
            role=PROTECTED_ADMIN_ROLE,
            status="active",
            access_token=secrets.token_urlsafe(32),
            token_type="bearer",
        )

    workshop = get_workshop_by_email(normalized_email)

    # ================================================================
    # VALIDACION: ACCESO DE TALLER
    # AQUI SE HACE ESTA VALIDACION DE HABILITACION Y CREDENCIALES DEL TALLER.
    # ================================================================
    if workshop:
        # LOGICA: si existe un taller con ese correo, el login sigue el flujo de talleres.
        # Esto evita mezclar reglas de clientes con reglas de talleres.
        # Solo los talleres aprobados por el administrador pueden entrar al panel.
        if workshop["approval_status"] != "activo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El taller todavía no fue habilitado por el administrador",
            )

        password_hash = workshop.get("password_hash")
        # Verifica la contraseña almacenada del taller antes de emitir un token temporal de sesion.
        if not isinstance(password_hash, str) or not verify_password(payload.password, password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contraseña incorrectos",
            )

        if verify_password(settings.workshop_initial_password, password_hash):
            # Fuerza el cambio de la contraseña inicial para no dejar credenciales temporales activas.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "WORKSHOP_PASSWORD_CHANGE_REQUIRED",
                    "message": "Debes cambiar la contraseña temporal antes de acceder al dashboard",
                    "email": normalized_email,
                },
            )

        return LoginResponse(
            id=int(workshop["id"]),
            email=str(workshop["email"]),
            full_name=str(workshop["workshop_name"]),
            phone=str(workshop["phone"]),
            role=WORKSHOP_ROLE,
            status=str(workshop["approval_status"]),
            access_token=secrets.token_urlsafe(32),
            token_type="bearer",
        )

    client = get_client_by_email(normalized_email)

    # LOGICA: si no fue admin ni taller, el ultimo flujo posible es autenticar como cliente.
    # Esta decision organiza el login por tipos de usuario.
    # Si no coincide con admin ni taller, el acceso se resuelve contra el catalogo de clientes.
    # ================================================================
    # VALIDACION: ACCESO DE CLIENTE
    # AQUI SE HACE ESTA VALIDACION DE CREDENCIALES Y ESTADO ACTIVO DEL CLIENTE.
    # ================================================================
    if not client or not verify_password(payload.password, str(client["password_hash"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    if client["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta suspendida",
        )

    # ================================================================
    # METODO: RESPUESTA DE LOGIN EXITOSO
    # Devuelve el esquema final de autenticacion para el cliente.
    # ================================================================
    return LoginResponse(
        id=int(client["id"]),
        email=str(client["email"]),
        full_name=str(client["full_name"]),
        phone=str(client["phone"]),
        role=str(client["role"]),
        status=str(client["status"]),
        access_token=secrets.token_urlsafe(32),
        token_type="bearer",
    )

@router.post("/workshops/change-password")
# ================================================================
# CONTROLADOR: CAMBIO DE CONTRASENA DE TALLER
# Atiende el cambio de la clave temporal inicial del taller.
# ================================================================
def change_workshop_password(payload: WorkshopPasswordChangeRequest) -> dict[str, str]:
    # Este endpoint se usa cuando el taller entra por primera vez desde su interfaz y debe cambiar la clave temporal.
    # El request llega desde la pantalla donde el usuario escribe su nueva contraseña.
    # LOGICA: solo se permite el cambio si el taller sigue usando la clave temporal inicial.
    # La idea es impedir que el flujo especial se reutilice despues del primer cambio.
    normalized_email = normalize_email(payload.email)
    workshop = get_workshop_by_email(normalized_email)

    # ================================================================
    # VALIDACION: EXISTENCIA Y ESTADO DEL TALLER
    # AQUI SE HACE ESTA VALIDACION DE TALLER REGISTRADO Y APROBADO PARA CAMBIAR CLAVE.
    # ================================================================
    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    if workshop["approval_status"] != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El taller todavía no fue habilitado por el administrador",
        )

    password_hash = workshop.get("password_hash")
    # Esta operacion solo aplica mientras el taller siga usando la contraseña temporal entregada al activarse.
    # ================================================================
    # VALIDACION: CONTRASENA TEMPORAL
    # AQUI SE HACE ESTA VALIDACION DE USO VIGENTE DE LA CONTRASENA TEMPORAL INICIAL.
    # ================================================================
    if not isinstance(password_hash, str) or not verify_password(settings.workshop_initial_password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este taller ya no usa la contraseña temporal inicial",
        )

    updated = update_workshop_password(int(workshop["id"]), hash_password(payload.new_password))

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    return {"message": "La contraseña del taller fue actualizada correctamente"}
