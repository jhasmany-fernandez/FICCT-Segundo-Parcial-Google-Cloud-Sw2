import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import OperationalError

from app.constants import PROTECTED_ADMIN_EMAIL, PROTECTED_ADMIN_ROLE
from app.config import settings
from app.db import (
    create_password_reset_token_record,
    get_client_by_id,
    get_password_reset_token_by_hash,
    mark_password_reset_token_used_record,
)


# -------------------------------------------------------------------
# LOGICA:
# Este modulo concentra reglas reutilizables de seguridad, validacion
# y normalizacion usadas por distintos endpoints.
# Aqui "logica" significa reglas compartidas que ayudan a mantener
# consistencia y seguridad en varios controladores.
# -------------------------------------------------------------------
def hash_password(password: str) -> str:
    # Genera un salt unico por contraseña para evitar hashes repetidos aunque dos usuarios usen la misma clave.
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    # Separa el salt almacenado y vuelve a calcular el hash para comparar de forma segura.
    try:
        salt, expected_digest = password_hash.split("$", 1)
    except ValueError:
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return secrets.compare_digest(candidate_digest, expected_digest)


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(account_type: str, account_id: int) -> dict[str, object]:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.password_reset_token_expires_minutes)
    plain_token = secrets.token_urlsafe(32)
    token_hash = hash_password_reset_token(plain_token)

    record = create_password_reset_token_record(
        {
            "account_type": account_type.strip().lower(),
            "account_id": account_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "used_at": None,
            "created_at": issued_at,
        }
    )

    return {
        "id": int(record["id"]),
        "account_type": str(record["account_type"]),
        "account_id": int(record["account_id"]),
        "token": plain_token,
        "expires_at": record["expires_at"],
        "created_at": record["created_at"],
    }


def verify_password_reset_token(token: str) -> dict[str, object] | None:
    normalized_token = token.strip()
    if not normalized_token:
        return None

    record = get_password_reset_token_by_hash(hash_password_reset_token(normalized_token))
    if not record:
        return None

    if record.get("used_at") is not None:
        return None

    expires_at = record.get("expires_at")
    if not isinstance(expires_at, datetime):
        return None

    if expires_at <= datetime.now(UTC):
        return None

    return record


def mark_password_reset_token_used(token_id: int) -> dict[str, object] | None:
    return mark_password_reset_token_used_record(token_id, datetime.now(UTC))


def normalize_plate(plate: str) -> str:
    return plate.strip().upper()


def normalize_email(email: str) -> str:
    return email.lower().strip()


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def is_protected_admin_email(email: str) -> bool:
    return normalize_email(email) == PROTECTED_ADMIN_EMAIL


def is_protected_admin_role(role: str) -> bool:
    return role.lower().strip() == PROTECTED_ADMIN_ROLE


def ensure_client_exists(client_id: int) -> None:
    try:
        # LOGICA: centraliza la validacion del cliente para no repetirla en cada endpoint.
        # Antes de registrar vehiculos o emergencias, valida que el cliente exista en base de datos.
        client = get_client_by_id(client_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
