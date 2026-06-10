import logging

from app.config import settings
from app.db import list_active_device_fcm_tokens, list_active_workshop_fcm_tokens

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:
    firebase_admin = None
    credentials = None
    messaging = None


logger = logging.getLogger(__name__)
_firebase_app_initialized = False


def ensure_firebase_app() -> bool:
    global _firebase_app_initialized

    if _firebase_app_initialized:
        return True

    if not settings.fcm_enabled:
        return False

    if firebase_admin is None or credentials is None:
        logger.warning("FCM habilitado, pero firebase-admin no esta instalado")
        return False

    credentials_path = (settings.firebase_credentials_path or "").strip()
    if not credentials_path:
        logger.warning("FCM habilitado, pero FIREBASE_CREDENTIALS_PATH no esta configurado")
        return False

    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(credentials_path))
        _firebase_app_initialized = True
        return True
    except Exception:
        logger.exception("No se pudo inicializar Firebase Admin SDK")
        return False


def send_push_to_client(client_id: int | None, title: str, body: str, data: dict[str, str]) -> bool:
    if client_id is None:
        return False

    try:
        devices = list_active_device_fcm_tokens(client_id)
    except Exception:
        logger.exception("No se pudieron consultar tokens FCM del cliente %s", client_id)
        return False

    if not devices or not ensure_firebase_app() or messaging is None:
        return False

    sent = False
    for device in devices:
        token = str(device.get("fcm_token", "")).strip()
        if not token:
            continue
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data,
                token=token,
            )
            messaging.send(message)
            sent = True
        except Exception:
            logger.exception("No se pudo enviar push FCM al cliente %s", client_id)
    return sent


def send_push_to_workshop(workshop_id: int | None, title: str, body: str, data: dict[str, str]) -> None:
    if workshop_id is None:
        return

    try:
        devices = list_active_workshop_fcm_tokens(workshop_id)
    except Exception:
        logger.exception("No se pudieron consultar tokens FCM del taller %s", workshop_id)
        return

    if not devices or not ensure_firebase_app() or messaging is None:
        return

    for device in devices:
        token = str(device.get("fcm_token", "")).strip()
        if not token:
            continue
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data,
                token=token,
            )
            messaging.send(message)
        except Exception:
            logger.exception("No se pudo enviar push FCM al taller %s", workshop_id)
