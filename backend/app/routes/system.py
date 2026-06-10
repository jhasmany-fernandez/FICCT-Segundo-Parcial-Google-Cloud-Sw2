import logging

from fastapi import APIRouter
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.db import check_database_connection, init_database


logger = logging.getLogger(__name__)

# ================================================================
# ARCHIVO: system.py
# TIPO: Controlador del sistema
# ESTE ARCHIVO SI TIENE METODOS
#
# QUE HACE ESTE ARCHIVO:
# Maneja tareas generales del backend como inicializacion de base de
# datos, endpoint raiz y verificacion de estado del servicio.
# Este controlador agrupa acciones tecnicas del sistema que no
# pertenecen a un modulo de negocio especifico.
#
# CONTROLADORES / METODOS QUE TIENE:
# - on_startup:
#   Inicializa la base de datos al arrancar la aplicacion.
# - read_root:
#   Devuelve un mensaje simple para comprobar que el backend responde.
# - healthcheck:
#   Verifica el estado general del backend y de la base de datos.
# Los metodos de este archivo se usan para operacion, monitoreo e inicio del sistema.
# ================================================================
router = APIRouter()


# ================================================================
# METODO: INICIALIZACION EN STARTUP
# Prepara el sistema al momento de arrancar la aplicacion.
# ================================================================
@router.on_event("startup")
def on_startup() -> None:
    try:
        # Al iniciar la aplicacion, crea tablas y ajustes faltantes para dejar la base lista para operar.
        init_database()
    except OperationalError:
        # ================================================================
        # VALIDACION: ERROR DE CONEXION EN STARTUP
        # AQUI SE HACE ESTA VALIDACION DE FALLO DE INICIALIZACION DE BASE DE DATOS EN STARTUP.
        # ================================================================
        logger.exception("No se pudo inicializar la base de datos en startup")


# ================================================================
# CONTROLADOR: RUTA RAIZ
# Responde con un mensaje simple para comprobar que el backend vive.
# ================================================================
@router.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Backend running"}


 # ================================================================
 # CONTROLADOR: HEALTHCHECK
 # Devuelve el estado del backend y la conexion a base de datos.
 # ================================================================
@router.get(f"{settings.api_prefix}/health")
def healthcheck() -> dict[str, object]:
    database_ok = False

    try:
        # ================================================================
        # VALIDACION: DISPONIBILIDAD DE BASE DE DATOS
        # AQUI SE HACE ESTA VALIDACION DE CONEXION OPERATIVA A LA BASE DE DATOS.
        # ================================================================
        # Comprueba si la API puede abrir una conexion real con la base de datos.
        database_ok = check_database_connection()
    except Exception:
        database_ok = False

    return {
        "status": "ok",
        "environment": settings.app_env,
        "database": "connected" if database_ok else "unavailable",
    }
