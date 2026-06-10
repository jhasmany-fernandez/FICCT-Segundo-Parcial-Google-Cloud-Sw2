import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.constants import MECANICO_ROLE, PROTECTED_ADMIN_EMAIL, PROTECTED_ADMIN_ID, PROTECTED_ADMIN_ROLE, WORKSHOP_ROLE
from app.db import get_client_by_id, get_workshop_by_id


bearer_scheme = HTTPBearer(auto_error=False)


def _normalize_role_name(role: str | None) -> str:
    normalized = (role or "").strip().lower()

    if normalized in {"tecnico", "técnico", "technician", "mecanico", "mecánico"}:
        return MECANICO_ROLE

    return normalized


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _jwt_secret_bytes() -> bytes:
    return settings.jwt_secret.encode("utf-8")


def create_access_token(
    *,
    subject: str,
    role: str,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + (expires_delta or timedelta(minutes=settings.jwt_access_expires_minutes))

    header = {
        "alg": "HS256",
        "typ": "JWT",
    }
    payload = {
        "sub": subject,
        "role": role,
        "email": email,
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.jwt_issuer,
    }

    encoded_header = _base64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    encoded_payload = _base64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(_jwt_secret_bytes(), signing_input, hashlib.sha256).digest()
    encoded_signature = _base64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(token: str) -> dict[str, object]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise credentials_exception from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(_jwt_secret_bytes(), signing_input, hashlib.sha256).digest()

    try:
        provided_signature = _base64url_decode(encoded_signature)
    except Exception as exc:  # noqa: BLE001
        raise credentials_exception from exc

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise credentials_exception

    try:
        payload = json.loads(_base64url_decode(encoded_payload).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise credentials_exception from exc

    if not isinstance(payload, dict):
        raise credentials_exception

    token_type = str(payload.get("type", ""))
    issuer = str(payload.get("iss", ""))
    subject = payload.get("sub")
    role = payload.get("role")
    email = payload.get("email")
    expires_at = payload.get("exp")

    if token_type != "access" or issuer != settings.jwt_issuer:
        raise credentials_exception

    if not isinstance(subject, str) or not subject.strip():
        raise credentials_exception

    if not isinstance(role, str) or not role.strip():
        raise credentials_exception

    if not isinstance(email, str) or not email.strip():
        raise credentials_exception

    if not isinstance(expires_at, int):
        raise credentials_exception

    now_ts = int(datetime.now(UTC).timestamp())
    if expires_at <= now_ts:
        raise credentials_exception

    return payload


@dataclass(slots=True)
class AuthenticatedUser:
    id: int
    email: str
    full_name: str | None
    phone: str | None
    role: str
    status: str


def _load_authenticated_user(payload: dict[str, object]) -> AuthenticatedUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario autenticado no válido",
        headers={"WWW-Authenticate": "Bearer"},
    )

    subject = str(payload["sub"])
    role = _normalize_role_name(str(payload["role"]))
    email = str(payload["email"])

    if role == PROTECTED_ADMIN_ROLE:
        if subject != str(PROTECTED_ADMIN_ID) or email.lower().strip() != PROTECTED_ADMIN_EMAIL:
            raise credentials_exception

        return AuthenticatedUser(
            id=PROTECTED_ADMIN_ID,
            email=PROTECTED_ADMIN_EMAIL,
            full_name=settings.protected_admin_full_name,
            phone=settings.protected_admin_phone,
            role=PROTECTED_ADMIN_ROLE,
            status="active",
        )

    try:
        user_id = int(subject)
    except ValueError as exc:
        raise credentials_exception from exc

    if role == WORKSHOP_ROLE:
        workshop = get_workshop_by_id(user_id)
        if not workshop:
            raise credentials_exception

        workshop_email = str(workshop.get("email", "")).lower().strip()
        if workshop_email != email.lower().strip():
            raise credentials_exception

        return AuthenticatedUser(
            id=int(workshop["id"]),
            email=str(workshop["email"]),
            full_name=str(workshop.get("workshop_name") or ""),
            phone=str(workshop.get("phone") or ""),
            role=WORKSHOP_ROLE,
            status=str(workshop.get("approval_status") or "pendiente"),
        )

    client = get_client_by_id(user_id)
    if not client:
        raise credentials_exception

    client_email = str(client.get("email", "")).lower().strip()
    if client_email != email.lower().strip():
        raise credentials_exception

    return AuthenticatedUser(
        id=int(client["id"]),
        email=str(client["email"]),
        full_name=str(client.get("full_name") or ""),
        phone=str(client.get("phone") or ""),
        role=_normalize_role_name(str(client.get("role") or role)),
        status=str(client.get("status") or "active"),
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    return _load_authenticated_user(payload)


def get_current_active_user(
    current_user: AuthenticatedUser = Security(get_current_user),
) -> AuthenticatedUser:
    if current_user.role == WORKSHOP_ROLE and current_user.status != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta no está activa",
        )

    if current_user.role != WORKSHOP_ROLE and current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta no está activa",
        )

    return current_user


def get_optional_current_active_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AuthenticatedUser | None:
    if credentials is None:
        return None

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    current_user = _load_authenticated_user(payload)

    if current_user.role == WORKSHOP_ROLE and current_user.status != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta no está activa",
        )

    if current_user.role != WORKSHOP_ROLE and current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta no está activa",
        )

    return current_user


def require_roles(*allowed_roles: str):
    normalized_roles = {_normalize_role_name(role) for role in allowed_roles}

    def dependency(
        current_user: AuthenticatedUser = Security(get_current_active_user),
    ) -> AuthenticatedUser:
        if _normalize_role_name(current_user.role) not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción",
            )
        return current_user

    return dependency
