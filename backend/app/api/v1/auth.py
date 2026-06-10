from fastapi import APIRouter, HTTPException, Security, status
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from app.config import settings
from app.core.dependencies import AuthenticatedUser, get_current_active_user
from app.db import (
    get_client_by_email,
    get_workshop_by_email,
    update_client_password,
    update_workshop_password,
)
from app.security import (
    create_password_reset_token as issue_password_reset_token,
    hash_password,
    mark_password_reset_token_used,
    verify_password_reset_token,
)


router = APIRouter()


class AuthMeResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    role: str
    status: str


class PasswordResetRequestCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    message: str
    reset_token: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    token: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("new_password", "newPassword", "password"),
    )


class PasswordResetConfirmResponse(BaseModel):
    message: str


@router.get(
    f"{settings.api_prefix}/auth/me",
    response_model=AuthMeResponse,
)
def get_authenticated_user_profile(
    current_user: AuthenticatedUser = Security(get_current_active_user),
) -> AuthMeResponse:
    return AuthMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role,
        status=current_user.status,
    )


def _resolve_password_reset_account_by_email(email: str) -> tuple[str, int] | None:
    client = get_client_by_email(email)
    if client and client["status"] == "active":
        return ("client", int(client["id"]))

    workshop = get_workshop_by_email(email)
    if workshop and workshop["approval_status"] == "activo":
        return ("workshop", int(workshop["id"]))

    return None


@router.post(
    f"{settings.api_prefix}/auth/forgot-password/request",
    response_model=PasswordResetRequestResponse,
)
def request_password_reset(payload: PasswordResetRequestCreate) -> PasswordResetRequestResponse:
    normalized_email = payload.email.lower().strip()
    account = _resolve_password_reset_account_by_email(normalized_email)

    response = PasswordResetRequestResponse(
        message="Si la cuenta existe, se enviarán instrucciones de recuperación."
    )

    if not account:
        return response

    account_type, account_id = account
    token_data = issue_password_reset_token(account_type, account_id)

    if settings.app_env.lower().strip() == "development":
        response.reset_token = str(token_data["token"])

    return response


@router.post(
    f"{settings.api_prefix}/auth/forgot-password/reset",
    response_model=PasswordResetConfirmResponse,
)
def reset_password_with_token(payload: PasswordResetConfirmRequest) -> PasswordResetConfirmResponse:
    token_record = verify_password_reset_token(payload.token)
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de recuperación inválido, expirado o ya utilizado",
        )

    account_type = str(token_record["account_type"])
    account_id = int(token_record["account_id"])
    new_password_hash = hash_password(payload.new_password)

    if account_type == "client":
        updated = update_client_password(account_id, new_password_hash)
    elif account_type == "workshop":
        updated = update_workshop_password(account_id, new_password_hash)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de recuperación inválido, expirado o ya utilizado",
        )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de recuperación inválido, expirado o ya utilizado",
        )

    marked = mark_password_reset_token_used(int(token_record["id"]))
    if not marked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de recuperación inválido, expirado o ya utilizado",
        )

    return PasswordResetConfirmResponse(message="Contraseña actualizada correctamente.")
