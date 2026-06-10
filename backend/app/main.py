from collections.abc import Mapping
from datetime import datetime, timedelta
import base64
import hashlib
import json
import logging
import math
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
from threading import Lock
import unicodedata
import urllib.error
import urllib.request
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Query, Security, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy.exc import IntegrityError, OperationalError

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import whisper
except ImportError:
    whisper = None

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:
    firebase_admin = None
    credentials = None
    messaging = None

from app.api.v1.auth import router as auth_router
from app.config import settings
from app.services.ai_assignment_service import build_ai_assignment_recommendation
from app.services.ai_service import AIServiceError, process_emergency_report_with_ai
from app.api.v1.health import router as health_router
from app.api.v1.recepciones import router as recepciones_router
from app.graphql_schema import graphql_router
from app.core.dependencies import (
    AuthenticatedUser,
    create_access_token,
    get_current_active_user,
    get_optional_current_active_user,
    require_roles,
)
from app.db import (
    accept_emergency_mecanico_assignment,
    assign_emergency_mecanico_with_notification,
    accept_emergency_report,
    assign_emergency_mecanico,
    create_emergency_tracking_event,
    count_unread_client_notifications,
    create_client_notification,
    count_active_sucursales,
    count_client_vehicles,
    create_client,
    create_emergency_report,
    create_or_link_mecanico,
    create_sucursal,
    create_vehicle,
    create_workshop_registration,
    delete_sucursal,
    delete_emergency_report,
    delete_client,
    delete_vehicle,
    delete_workshop_registration,
    delete_mecanico,
    delete_mecanico_for_workshop,
    get_client_by_email,
    get_client_by_id,
    get_emergency_report_by_id,
    get_emergency_tracking_context,
    get_mecanico_by_cliente_id,
    get_mecanico_by_id,
    get_sucursal_by_id,
    get_vehicle_by_any_id,
    get_vehicle_by_client_and_plate,
    get_mecanico_by_workshop,
    get_vehicle_by_id,
    get_workshop_by_id,
    get_workshop_by_email,
    init_database,
    list_audit_logs,
    list_active_device_fcm_tokens,
    list_active_workshop_fcm_tokens,
    list_client_notifications,
    list_emergency_history,
    deactivate_client_fcm_token,
    deactivate_workshop_fcm_token,
    mark_client_notification_read,
    reject_emergency_mecanico_assignment,
    reject_emergency_report,
    upsert_workshop_fcm_token,
    list_emergency_reports,
    list_assignable_mecanicos,
    list_clients,
    list_mecanicos,
    list_sucursales,
    list_sucursales_for_mobile,
    list_mecanicos_by_workshop,
    list_vehicles,
    list_workshop_registrations,
    update_client,
    update_client_password,
    update_client_status,
    update_emergency_status,
    update_emergency_ai_result,
    update_mecanico_profile,
    update_sucursal,
    update_sucursal_estado,
    update_vehicle,
    update_workshop_approval_status_with_password,
    update_workshop_password,
    update_workshop_registration,
    upsert_device_fcm_token,
    list_secretarias,
    get_secretaria_by_id,
    get_secretaria_by_cliente_id,
    get_emergency_ai_recommendation,
    create_secretaria,
    list_mecanicos_for_ai_recommendation,
    update_secretaria,
    update_secretaria_status,
    upsert_emergency_ai_recommendation,
    delete_secretaria,
    list_emergency_tracking_events,
)
UPLOADS_ROOT = Path(settings.uploads_dir)
VEHICLE_UPLOADS_DIR = UPLOADS_ROOT / "vehicles"
EMERGENCY_UPLOADS_DIR = UPLOADS_ROOT / "emergencias"
EMERGENCY_PHOTOS_DIR = EMERGENCY_UPLOADS_DIR / "photos"
EMERGENCY_AUDIO_DIR = EMERGENCY_UPLOADS_DIR / "audio"
UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
VEHICLE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EMERGENCY_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
EMERGENCY_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)
PROTECTED_ADMIN_EMAIL = settings.protected_admin_email.lower().strip()
PROTECTED_ADMIN_ROLE = "admin"
PROTECTED_ADMIN_ID = 0
WORKSHOP_ROLE = "workshop"
CLIENT_ROLE = "client"
SECRETARIA_ROLE = "secretaria"
MECANICO_ROLE = "mecanico"
PRIVILEGED_CLIENT_SCOPE_ROLES = {
    PROTECTED_ADMIN_ROLE,
    WORKSHOP_ROLE,
    SECRETARIA_ROLE,
    MECANICO_ROLE,
}
_firebase_app_initialized = False
LOGIN_MAX_ATTEMPTS = 3
LOGIN_LOCKOUT_MINUTES = 10
_login_attempts_lock = Lock()
_login_attempts: dict[str, dict[str, object]] = {}

# Limites y formatos aceptados para el flujo de emergencias.
MAX_EMERGENCY_PHOTOS = 6
MAX_EMERGENCY_PHOTO_BYTES = 5 * 1024 * 1024
MAX_EMERGENCY_AUDIO_BYTES = 15 * 1024 * 1024
ALLOWED_PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_AUDIO_SUFFIXES = {".aac", ".m4a", ".mp3", ".wav", ".ogg", ".webm"}
ALLOWED_EMERGENCY_PROBLEM_TYPES = {
    "Batería",
    "Neumático",
    "Combustible",
    "Motor",
    "Sistema eléctrico",
    "Accidente",
    "Cerrajería / llaves",
    "Otro",
}
STANDARDIZED_EMERGENCY_PROBLEM_TYPES = ALLOWED_EMERGENCY_PROBLEM_TYPES - {"Otro"}
EMERGENCY_BASE_PRICES = {
    "Batería": 50,
    "Neumático": 50,
    "Combustible": 60,
    "Motor": 100,
    "Sistema eléctrico": 90,
    "Accidente": 150,
    "Cerrajería / llaves": 80,
}
_whisper_model = None
_whisper_model_lock = Lock()


class WorkshopRegistrationCreate(BaseModel):
    workshop_name: str = Field(min_length=3, max_length=160)
    contact_name: str = Field(min_length=3, max_length=160)
    phone: str = Field(min_length=7, max_length=40)
    email: EmailStr
    zone: str = Field(min_length=2, max_length=120)
    specialty: str = Field(min_length=2, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, min_length=2, max_length=120)
    utc_offset_minutes: int | None = Field(default=None, ge=-840, le=840)


class WorkshopRegistrationUpdate(WorkshopRegistrationCreate):
    password: str | None = Field(default=None, min_length=6, max_length=255)


class WorkshopRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workshop_name: str
    contact_name: str
    phone: str
    email: EmailStr
    zone: str
    specialty: str
    approval_status: str
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    utc_offset_minutes: int | None = None
    created_at: datetime


class WorkshopApprovalStatusUpdate(BaseModel):
    approval_status: str = Field(pattern="^(pendiente|activo|rechazado)$")


class SucursalBase(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    direccion: str = Field(min_length=5, max_length=255)
    zona: str | None = Field(default=None, max_length=120)
    telefono: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    horario_atencion: str | None = Field(default=None, max_length=160)
    responsable: str | None = Field(default=None, max_length=160)
    estado: str = Field(default="ACTIVO", pattern="^(ACTIVO|INACTIVO)$")


class SucursalCreate(SucursalBase):
    pass


class SucursalUpdate(SucursalBase):
    pass


class SucursalEstadoUpdate(BaseModel):
    estado: str = Field(pattern="^(ACTIVO|INACTIVO)$")


class SucursalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    direccion: str
    zona: str | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    latitud: float | None = None
    latitude: float | None = None
    longitud: float | None = None
    longitude: float | None = None
    horario_atencion: str | None = None
    responsable: str | None = None
    estado: str
    fecha_registro: datetime
    fecha_modificacion: datetime | None = None
    mecanicos_activos_count: int | None = None
    secretarias_activas_count: int | None = None
    operativa: bool | None = None
    motivo_no_operativa: str | None = None
    especialidad: str | None = None

    @model_validator(mode="before")
    @classmethod
    def populate_coordinate_aliases(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        if normalized.get("latitude") is None:
            normalized["latitude"] = normalized.get("latitud")
        if normalized.get("longitude") is None:
            normalized["longitude"] = normalized.get("longitud")
        return normalized


class SucursalMobileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    direccion: str
    zona: str | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    latitud: float
    latitude: float
    longitud: float
    longitude: float
    horario_atencion: str | None = None
    responsable: str | None = None
    estado: str
    operativa: bool = True
    mecanicos_activos_count: int | None = None
    secretarias_activas_count: int | None = None
    especialidad: str | None = None

    @model_validator(mode="before")
    @classmethod
    def populate_coordinate_aliases(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        if normalized.get("latitude") is None:
            normalized["latitude"] = normalized.get("latitud")
        if normalized.get("longitude") is None:
            normalized["longitude"] = normalized.get("longitud")
        return normalized


class SecretariaBase(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr
    sucursal_id: int = Field(ge=1)


class SecretariaCreate(SecretariaBase):
    password: str = Field(min_length=6, max_length=255)


class SecretariaUpdate(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    sucursal_id: int = Field(ge=1)
    password: str | None = Field(default=None, min_length=6, max_length=255)


class SecretariaEstadoUpdate(BaseModel):
    status: str = Field(pattern="^(activo|inactivo)$")


class SecretariaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    sucursal_id: int
    sucursal_nombre: str | None = None
    sucursal_zona: str | None = None
    sucursal_direccion: str | None = None
    full_name: str
    phone: str | None = None
    email: EmailStr
    status: str
    created_at: datetime
    updated_at: datetime


class MecanicoBase(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    phone: str = Field(min_length=7, max_length=40)
    email: EmailStr
    specialty: str = Field(min_length=2, max_length=120)
    status: str = Field(pattern="^(disponible|ocupado|fuera_de_servicio)$")


class MecanicoCreate(MecanicoBase):
    cliente_id: int | None = Field(default=None, ge=1)
    identity_card: str | None = Field(default=None, min_length=5, max_length=40)
    password: str | None = Field(default=None, min_length=6, max_length=255)
    workshop_id: int | None = Field(default=None, ge=1)
    sucursal_id: int | None = Field(default=None, ge=1)


class MecanicoResponse(MecanicoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int | None = None
    identity_card: str | None = None
    cliente_status: str | None = None
    cliente_role: str | None = None
    workshop_id: int | None = None
    sucursal_id: int | None = None
    sucursal_nombre: str | None = None
    sucursal_zona: str | None = None
    sucursal_direccion: str | None = None
    created_at: datetime
    updated_at: datetime


class ClientRegistrationCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    identity_card: str = Field(
        min_length=5,
        max_length=40,
        validation_alias=AliasChoices("identity_card", "identityCard", "ci"),
    )
    full_name: str = Field(
        min_length=3,
        max_length=160,
        validation_alias=AliasChoices("full_name", "fullName", "name"),
    )
    email: EmailStr
    phone: str = Field(
        min_length=7,
        max_length=40,
        validation_alias=AliasChoices("phone", "telefono"),
    )
    password: str = Field(min_length=6, max_length=255)
    confirm_password: str | None = Field(
        default=None,
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("confirm_password", "confirmPassword"),
    )
    role: str = Field(default="client", min_length=2, max_length=40)
    accepted_terms: bool = Field(
        default=False,
        validation_alias=AliasChoices("accepted_terms", "acceptedTerms", "termsAccepted"),
    )

    @model_validator(mode="after")
    def validate_registration(self) -> "ClientRegistrationCreate":
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")

        if not self.accepted_terms:
            raise ValueError("Debes aceptar los terminos y condiciones")

        return self


class ClientRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    identity_card: str
    full_name: str
    email: EmailStr
    phone: str
    role: str
    status: str
    accepted_terms: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=255)
    account_type: str | None = Field(default=None, pattern="^(admin|workshop|client)$")


class AccountTypeLookupRequest(BaseModel):
    email: EmailStr


class AccountTypeLookupResponse(BaseModel):
    role: str | None = None


class LoginResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    role: str
    status: str
    requires_password_change: bool = False
    access_token: str | None = None
    token_type: str | None = None


class IaAnalyzeEmergencyRequest(BaseModel):
    emergency_id: int
    description: str = Field(min_length=3, max_length=1000)
    source: str = Field(min_length=2, max_length=120)


class IaAnalyzeEmergencyResponse(BaseModel):
    status: str
    service: str
    emergency_id: int
    classification: str
    priority: str
    summary: str


class IaQueueTestRequest(BaseModel):
    emergency_id: int
    description: str = Field(min_length=3, max_length=1000)
    source: str = Field(min_length=2, max_length=120)


class IaQueueTestResponse(BaseModel):
    status: str
    queue: str
    emergency_id: int


class WorkshopPasswordChangeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: EmailStr
    new_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("new_password", "newPassword", "password"),
    )
    confirm_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("confirm_password", "confirmPassword"),
    )

    @model_validator(mode="after")
    def validate_passwords(self) -> "WorkshopPasswordChangeRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")

        return self


class ClientPasswordChangeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: EmailStr
    current_password: str = Field(
        min_length=1,
        max_length=255,
        validation_alias=AliasChoices("current_password", "currentPassword"),
    )
    new_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("new_password", "newPassword", "password"),
    )
    confirm_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("confirm_password", "confirmPassword"),
    )

    @model_validator(mode="after")
    def validate_passwords(self) -> "ClientPasswordChangeRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")

        if self.current_password == self.new_password:
            raise ValueError("La nueva contraseña debe ser distinta a la actual")

        return self


class ClientForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: EmailStr
    new_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("new_password", "newPassword", "password"),
    )
    confirm_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("confirm_password", "confirmPassword"),
    )

    @model_validator(mode="after")
    def validate_passwords(self) -> "ClientForgotPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")

        return self


class WorkshopForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: EmailStr
    new_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("new_password", "newPassword", "password"),
    )
    confirm_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("confirm_password", "confirmPassword"),
    )

    @model_validator(mode="after")
    def validate_passwords(self) -> "WorkshopForgotPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")

        return self


class UnifiedForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: EmailStr
    new_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("new_password", "newPassword", "password"),
    )
    confirm_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("confirm_password", "confirmPassword"),
    )

    @model_validator(mode="after")
    def validate_passwords(self) -> "UnifiedForgotPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")

        return self


class ClientStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|suspended)$")


class ClientUpdate(BaseModel):
    identity_card: str = Field(min_length=5, max_length=40)
    full_name: str = Field(min_length=3, max_length=160)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=40)
    password: str | None = Field(default=None, min_length=6, max_length=255)
    role: str = Field(min_length=2, max_length=40)
    status: str = Field(pattern="^(active|suspended)$")
    accepted_terms: bool = True


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    brand: str
    model: str
    year: int
    plate: str
    color: str
    is_primary: bool
    photo_path: str | None = None
    photo_url: str | None = None
    created_at: datetime


class EmergencyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int | None = None
    vehicle_id: int | None = None
    vehicle_name: str
    vehicle_plate: str
    problem_type: str
    price: int | None = None
    emergency_status: str | None = None
    problem_type_standardized: str | None = None
    photo_problem_type_standardized: str | None = None
    photo_classification_confidence: float | None = None
    photo_classification_error: str | None = None
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    zone: str | None = None
    nearest_workshop_id: int | None = None
    nearest_workshop_name: str | None = None
    nearest_workshop_specialty: str | None = None
    nearest_workshop_zone: str | None = None
    nearest_workshop_distance_meters: float | None = None
    audio_duration_seconds: float | None = None
    audio_transcript: str | None = None
    audio_transcript_status: str | None = None
    audio_transcript_error: str | None = None
    photo_paths: list[str] = Field(default_factory=list)
    photo_urls: list[str] = Field(default_factory=list)
    audio_path: str | None = None
    audio_url: str | None = None
    ia_categoria: str | None = None
    ia_prioridad: str | None = None
    ia_confidence: float | None = None
    ia_procesado_en: datetime | None = None
    rejection_reason: str | None = None
    rejected_at: datetime | None = None
    rejected_by_user_id: int | None = None
    closed_at: datetime | None = None
    closed_by_user_id: int | None = None
    created_at: datetime
    assignment_id: int | None = None
    assignment_status: str | None = None
    # Canonical emergency assignment fields. Prefer these in new clients.
    assigned_mecanico_id: int | None = None
    assigned_mecanico_name: str | None = None
    assigned_mecanico_phone: str | None = None
    assigned_mecanico_email: str | None = None
    assigned_mecanico_specialty: str | None = None
    # Legacy API aliases preserved for backward compatibility. Prefer assigned_mecanico_*.
    assigned_mechanic_id: int | None = None
    assigned_mechanic_name: str | None = None
    assigned_mechanic_phone: str | None = None
    assigned_mechanic_email: str | None = None
    assigned_mechanic_specialty: str | None = None
    assigned_technician_id: int | None = None
    assigned_technician_name: str | None = None
    assigned_technician_phone: str | None = None
    assigned_technician_email: str | None = None
    assigned_technician_specialty: str | None = None


class EmergencyReportListResponse(EmergencyReportResponse):
    client_name: str | None = None


class EmergencyStatusUpdate(BaseModel):
    emergency_status: str = Field(pattern="^(activo|rechazado)$")


class EmergencyRejectRequest(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def validate_motivo(self) -> "EmergencyRejectRequest":
        self.motivo = self.motivo.strip()
        if len(self.motivo) < 5:
            raise ValueError("El motivo de rechazo debe tener al menos 5 caracteres")
        return self


class EmergencyRejectResponse(EmergencyReportResponse):
    notification_created: bool
    push_sent: bool


class AIRecommendedMechanicResponse(BaseModel):
    id: int
    full_name: str | None = None
    specialty: str | None = None
    status: str | None = None
    sucursal_id: int | None = None
    sucursal_nombre: str | None = None
    carga_trabajo: int = 0
    distance_km: float | None = None


class EmergencyAIRecommendationResponse(BaseModel):
    categoria: str | None = None
    prioridad: str | None = None
    especialidad_requerida: str | None = None
    sucursal_recomendada_id: int | None = None
    sucursal_recomendada: str | None = None
    mecanico_recomendado_id: int | None = None
    mecanico_recomendado: str | None = None
    confidence: float | None = None
    mecanicos_recomendados: list[AIRecommendedMechanicResponse] = Field(default_factory=list)
    created_at: datetime | None = None


class ClientNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    titulo: str
    mensaje: str
    emergencia_id: int | None = None
    leida: bool
    created_at: datetime
    read_at: datetime | None = None
    metadata: dict[str, object] | None = None


class ClientNotificationUnreadCountResponse(BaseModel):
    unread_count: int


class EmergencyMecanicoAssignmentRequest(BaseModel):
    mecanico_id: int = Field(
        ge=1,
        validation_alias=AliasChoices("mecanico_id", "mechanic_id", "technician_id"),
    )


class MobileEmergencyTrackingMechanicResponse(BaseModel):
    id: int
    name: str
    phone: str | None = None
    specialty: str | None = None


class MobileEmergencyTrackingSucursalResponse(BaseModel):
    id: int
    nombre: str
    latitud: float
    longitud: float


class MobileEmergencyTrackingDestinationResponse(BaseModel):
    latitud: float
    longitud: float


class MobileEmergencyTrackingResponse(BaseModel):
    emergencia_id: int
    status: str
    tracking_available: bool
    tracking_reason: str | None = None
    mechanic: MobileEmergencyTrackingMechanicResponse | None = None
    sucursal: MobileEmergencyTrackingSucursalResponse | None = None
    destination: MobileEmergencyTrackingDestinationResponse | None = None


class DeviceFcmTokenCreate(BaseModel):
    user_id: int = Field(ge=1)
    fcm_token: str = Field(min_length=20, max_length=4096)
    platform: str = Field(default="android", pattern="^(android|ios|web)$")


class DeviceFcmTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    fcm_token: str
    platform: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DeviceFcmTokenDeactivate(BaseModel):
    fcm_token: str = Field(min_length=20, max_length=4096)


class WorkshopFcmTokenCreate(BaseModel):
    fcm_token: str = Field(min_length=20, max_length=4096)
    platform: str = Field(default="android", pattern="^(android|ios|web)$")


class WorkshopFcmTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workshop_id: int
    fcm_token: str
    platform: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EmergencyTrackingEventCreate(BaseModel):
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    heading: float | None = None
    speed: float | None = Field(default=None, ge=0)
    event_type: str = Field(default="moving", pattern="^(started|moving|arrived|cancelled)$")


class EmergencyTrackingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    emergencia_id: int
    mecanico_id: int
    latitud: float
    longitud: float
    heading: float | None = None
    speed: float | None = None
    event_type: str
    created_at: datetime


class EmergencyTrackingMecanicoResponse(BaseModel):
    id: int
    nombre: str
    telefono: str | None = None
    email: str | None = None
    especialidad: str | None = None


class EmergencyTrackingOriginResponse(BaseModel):
    sucursal_id: int | None = None
    nombre: str | None = None
    latitud: float
    longitud: float


class EmergencyTrackingDestinationResponse(BaseModel):
    latitud: float
    longitud: float
    direccion: str | None = None
    zona: str | None = None


class EmergencyTrackingResponse(BaseModel):
    emergencia_id: int
    emergency_id: int
    client_id: int | None = None
    estado_tracking: str
    estado_emergencia: str
    mecanico: EmergencyTrackingMecanicoResponse
    origen: EmergencyTrackingOriginResponse
    destino: EmergencyTrackingDestinationResponse
    eventos: list[EmergencyTrackingEventResponse] = Field(default_factory=list)


class EmergencyHistoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    emergencia_id: int
    evento: str
    descripcion: str
    actor_user_id: int | None = None
    actor_role: str | None = None
    source_app: str
    created_at: datetime
    metadata_json: dict[str, object] | None = None


class AuditLogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    action: str
    actor_user_id: int | None = None
    actor_role: str | None = None
    source_app: str
    endpoint: str | None = None
    before_json: dict[str, object] | None = None
    after_json: dict[str, object] | None = None
    created_at: datetime


class PushTestRequest(BaseModel):
    fcm_token: str = Field(min_length=20, max_length=4096)
    title: str = Field(default="Prueba FCM", min_length=1, max_length=120)
    body: str = Field(default="Notificación de prueba desde el servidor.", min_length=1, max_length=300)


class PushTestResponse(BaseModel):
    sent: bool
    message: str


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
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


def login_attempt_key(account_type: str, email: str) -> str:
    return f"{account_type}:{email.lower().strip()}"


#
# ============================================================
# FLUJO IMPORTANTE: BLOQUEO DE INTENTOS DE LOGIN
# Aqui se controla cuantas veces falla un login y cuando se debe
# bloquear temporalmente el acceso por seguridad.
# Palabras clave de busqueda:
# - BLOQUEO LOGIN
# - INTENTOS FALLIDOS
# - SEGURIDAD LOGIN
# ============================================================
#
def get_login_attempt_state(account_type: str, email: str) -> dict[str, object]:
    key = login_attempt_key(account_type, email)

    with _login_attempts_lock:
        state = _login_attempts.get(key)

        if not state:
            return {"attempts": 0, "locked_until": None}

        locked_until = state.get("locked_until")
        if isinstance(locked_until, datetime) and locked_until <= datetime.utcnow():
            _login_attempts.pop(key, None)
            return {"attempts": 0, "locked_until": None}

        return dict(state)


def ensure_login_not_locked(account_type: str, email: str) -> None:
    state = get_login_attempt_state(account_type, email)
    locked_until = state.get("locked_until")

    if not isinstance(locked_until, datetime):
        return

    remaining_seconds = max(1, int((locked_until - datetime.utcnow()).total_seconds()))
    remaining_minutes = max(1, (remaining_seconds + 59) // 60)
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "message": f"Demasiados intentos fallidos. Intenta nuevamente en {remaining_minutes} min.",
            "code": "LOGIN_ATTEMPTS_EXCEEDED",
            "account_type": account_type,
            "remaining_attempts": 0,
            "locked_until": locked_until.isoformat() + "Z",
        },
    )


def register_failed_login_attempt(account_type: str, email: str) -> None:
    key = login_attempt_key(account_type, email)

    with _login_attempts_lock:
        state = _login_attempts.get(key, {"attempts": 0, "locked_until": None})
        attempts = int(state.get("attempts") or 0) + 1
        remaining_attempts = max(0, LOGIN_MAX_ATTEMPTS - attempts)

        if attempts >= LOGIN_MAX_ATTEMPTS:
            locked_until = datetime.utcnow() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
            _login_attempts[key] = {"attempts": attempts, "locked_until": locked_until}
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": f"Demasiados intentos fallidos. Intenta nuevamente en {LOGIN_LOCKOUT_MINUTES} min.",
                    "code": "LOGIN_ATTEMPTS_EXCEEDED",
                    "account_type": account_type,
                    "remaining_attempts": 0,
                    "locked_until": locked_until.isoformat() + "Z",
                },
            )

        _login_attempts[key] = {"attempts": attempts, "locked_until": None}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "message": "Correo o contraseña incorrectos",
            "code": "INVALID_CREDENTIALS",
            "account_type": account_type,
            "remaining_attempts": remaining_attempts,
        },
    )


def reset_login_attempts(account_type: str, email: str) -> None:
    key = login_attempt_key(account_type, email)

    with _login_attempts_lock:
        _login_attempts.pop(key, None)


def normalize_plate(plate: str) -> str:
    return plate.strip().upper()


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def normalize_problem_type(problem_type: str) -> str:
    normalized = problem_type.strip()

    if normalized not in ALLOWED_EMERGENCY_PROBLEM_TYPES:
        allowed_values = ", ".join(sorted(ALLOWED_EMERGENCY_PROBLEM_TYPES))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"problem_type invalido. Valores permitidos: {allowed_values}",
        )

    return normalized


#
# ============================================================
# FLUJO IMPORTANTE: NORMALIZACION Y CLASIFICACION DE EMERGENCIAS
# Aqui se interpreta el tipo de problema reportado y se apoyan
# los procesos de clasificacion por texto, fotos y audio.
# Palabras clave de busqueda:
# - CLASIFICACION EMERGENCIA
# - IA EMERGENCIA
# - NORMALIZAR PROBLEMA
# ============================================================
#
def normalize_text_for_matching(value: str | None) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    lowered = without_accents.lower()
    return re.sub(r"\s+", " ", lowered).strip()


def standardize_problem_type(
    problem_type: str,
    description: str | None,
    audio_transcript: str | None = None,
    photo_problem_type_standardized: str | None = None,
) -> str | None:
    if problem_type != "Otro":
        return problem_type if problem_type in STANDARDIZED_EMERGENCY_PROBLEM_TYPES else None

    candidate_text = " ".join(
        part for part in [normalize_optional_text(description), normalize_optional_text(audio_transcript)] if part
    )
    haystack = normalize_text_for_matching(candidate_text)

    if not haystack:
        return None

    rules: list[tuple[str, tuple[str, ...]]] = [
        (
            "Batería",
            (
                "bateria",
                "arranque",
                "no enciende",
                "no quiere encender",
                "no arranca",
                "sin corriente",
                "descargada",
                "pasar corriente",
                "se apago",
            ),
        ),
        ("Neumático", ("neumatico", "llanta", "pinch", "rueda", "revent", "desinflad", "goma")),
        ("Combustible", ("combustible", "gasolina", "diesel", "tanque", "sin gasolina", "sin diesel", "sin nafta")),
        ("Motor", ("motor", "sobrecalent", "humo", "temperatura", "radiador", "recalent", "aceite")),
        ("Sistema eléctrico", ("electrico", "eléctrico", "fusible", "cable", "corto", "tablero", "luces", "alternador")),
        ("Accidente", ("accidente", "choque", "colision", "colisión", "impacto", "atropell")),
        ("Cerrajería / llaves", ("llave", "llaves", "cerrajer", "cerrajeria", "cerrado", "quedaron dentro")),
    ]

    best_match: str | None = None
    best_score = 0

    for category, keywords in rules:
        score = sum(1 for keyword in keywords if keyword in haystack)
        if score > best_score:
            best_match = category
            best_score = score

    if best_match is not None:
        return best_match

    if photo_problem_type_standardized in STANDARDIZED_EMERGENCY_PROBLEM_TYPES:
        return photo_problem_type_standardized

    return None


def extract_response_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = getattr(response, "output", None)
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            content = getattr(item, "content", None)
            if not isinstance(content, list):
                continue
            for part in content:
                text = getattr(part, "text", None)
                if isinstance(text, str) and text.strip():
                    parts.append(text)
        if parts:
            return "\n".join(parts)

    return ""


def build_data_url_for_image(relative_path: str) -> str:
    absolute_path = (UPLOADS_ROOT / relative_path).resolve()

    try:
        absolute_path.relative_to(UPLOADS_ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError("Ruta de imagen invalida") from exc

    if not absolute_path.is_file():
        raise RuntimeError("No se encontro la imagen a clasificar")

    mime_type, _ = mimetypes.guess_type(absolute_path.name)
    mime_type = mime_type or "application/octet-stream"
    encoded = base64.b64encode(absolute_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def classify_emergency_photos(photo_relative_paths: list[str]) -> tuple[str | None, float | None, str | None]:
    if not photo_relative_paths or not settings.photo_classification_enabled:
        return None, None, None

    if OpenAI is None:
        return None, None, "La dependencia openai no esta instalada"

    if not os.getenv("OPENAI_API_KEY"):
        return None, None, "OPENAI_API_KEY no esta configurada"

    try:
        content: list[dict[str, object]] = [
            {
                "type": "input_text",
                "text": (
                    "Clasifica estas fotos de una emergencia vehicular en exactamente una categoria. "
                    "Categorias permitidas: Batería, Neumático, Combustible, Motor, Sistema eléctrico, "
                    "Accidente, Cerrajería / llaves. "
                    "Responde solo JSON con este formato exacto: "
                    '{"category":"<categoria>","confidence":0.0,"reason":"<breve>"}'
                ),
            }
        ]

        for photo_relative_path in photo_relative_paths:
            content.append(
                {
                    "type": "input_image",
                    "image_url": build_data_url_for_image(photo_relative_path),
                    "detail": "low",
                }
            )

        client = OpenAI()
        response = client.responses.create(
            model=settings.photo_classification_model,
            input=[{"role": "user", "content": content}],
        )
        parsed = json.loads(extract_response_text(response))

        category = parsed.get("category")
        confidence_raw = parsed.get("confidence")

        if category not in STANDARDIZED_EMERGENCY_PROBLEM_TYPES:
            return None, None, "La clasificacion visual devolvio una categoria invalida"

        confidence = None
        if isinstance(confidence_raw, (int, float)):
            confidence = max(0.0, min(float(confidence_raw), 1.0))

        return str(category), confidence, None
    except Exception as exc:
        logger.exception("No se pudo clasificar visualmente la emergencia")
        return None, None, str(exc)


def determine_standardized_problem_type(
    problem_type: str,
    description: str | None,
    audio_transcript: str | None = None,
    photo_problem_type_standardized: str | None = None,
) -> str | None:
    return standardize_problem_type(
        problem_type=problem_type,
        description=description,
        audio_transcript=audio_transcript,
        photo_problem_type_standardized=photo_problem_type_standardized,
    )


def resolve_emergency_price(price: int | None, standardized_problem_type: str | None) -> int | None:
    if price is not None:
        return price

    if standardized_problem_type is None:
        return None

    return EMERGENCY_BASE_PRICES.get(standardized_problem_type)


def get_whisper_model():
    global _whisper_model

    if _whisper_model is not None:
        return _whisper_model

    with _whisper_model_lock:
        if _whisper_model is None:
            if whisper is None:
                raise RuntimeError("La dependencia openai-whisper no esta instalada")

            _whisper_model = whisper.load_model(settings.whisper_model)

    return _whisper_model


def transcribe_emergency_audio(audio_relative_path: str | None) -> tuple[str | None, str | None, str | None]:
    if not audio_relative_path:
        return None, None, None

    if not settings.whisper_enabled:
        return None, "disabled", None

    if shutil.which("ffmpeg") is None:
        return None, "error", "ffmpeg no esta disponible en el contenedor"

    absolute_path = (UPLOADS_ROOT / audio_relative_path).resolve()

    try:
        absolute_path.relative_to(UPLOADS_ROOT.resolve())
    except ValueError:
        return None, "error", "Ruta de audio invalida"

    if not absolute_path.is_file():
        return None, "error", "No se encontro el archivo de audio"

    try:
        model = get_whisper_model()
        options: dict[str, object] = {"fp16": False}

        language = normalize_optional_text(settings.whisper_language)
        if language:
            options["language"] = language

        result = model.transcribe(str(absolute_path), **options)
        transcript = normalize_optional_text(str(result.get("text", "")))
        return transcript, "completed", None
    except Exception as exc:
        logger.exception("No se pudo transcribir el audio de la emergencia")
        return None, "error", str(exc)


def is_protected_admin_email(email: str) -> bool:
    return email.lower().strip() == PROTECTED_ADMIN_EMAIL


def is_protected_admin_role(role: str) -> bool:
    return _normalize_role_name(role) == PROTECTED_ADMIN_ROLE


def workshop_login_status(approval_status: object) -> str:
    return "active" if str(approval_status) == "activo" else "pending"


def ensure_client_exists(client_id: int) -> None:
    try:
        client = get_client_by_id(client_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")


def ensure_mecanico_sucursal_activa(sucursal_id: int | None) -> dict[str, object]:
    try:
        active_sucursales = count_active_sucursales()
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if active_sucursales < 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Debe registrar al menos una sucursal activa antes de crear mecánicos.",
        )

    if sucursal_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El campo sucursal_id es obligatorio para registrar o editar mecánicos.",
        )

    try:
        sucursal = get_sucursal_by_id(sucursal_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not sucursal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La sucursal seleccionada no existe")

    if str(sucursal.get("estado") or "") != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La sucursal seleccionada debe estar activa para afiliar mecánicos.",
        )

    return sucursal


def get_secretaria_scope(current_user: AuthenticatedUser) -> dict[str, object] | None:
    if current_user.role != SECRETARIA_ROLE:
        return None

    try:
        secretaria = get_secretaria_by_cliente_id(current_user.id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not secretaria:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La secretaria autenticada no tiene una sucursal afiliada configurada.",
        )

    return secretaria


def ensure_secretaria_can_manage_mecanico(
    *,
    current_user: AuthenticatedUser,
    mecanico_id: int,
    workshop_id: int | None = None,
) -> None:
    secretaria = get_secretaria_scope(current_user)
    if not secretaria:
        return

    mecanico = get_mecanico_by_workshop(mecanico_id, workshop_id) if workshop_id else get_mecanico_by_id(mecanico_id)
    if not mecanico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mecánico no encontrado")

    if int(mecanico.get("sucursal_id") or 0) != int(secretaria["sucursal_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes administrar mecánicos afiliados a tu propia sucursal.",
        )


def get_mecanico_for_operational_scope(
    *,
    mecanico_id: int,
    operational_scope_id: int,
) -> dict[str, object] | None:
    mecanico = get_mecanico_by_workshop(mecanico_id, operational_scope_id)
    if mecanico:
        return mecanico

    mecanico = get_mecanico_by_id(mecanico_id)
    if not mecanico:
        return None

    if int(mecanico.get("sucursal_id") or 0) == operational_scope_id:
        return mecanico

    return None


def get_emergency_report_for_operational_scope(
    *,
    report_id: int,
    scope_id: int,
) -> dict[str, object] | None:
    report = get_emergency_report_by_id(report_id)
    if not report:
        return None

    candidate_scope_ids: set[int] = set()
    nearest_workshop_id = report.get("nearest_workshop_id")
    if nearest_workshop_id is not None:
        candidate_scope_ids.add(int(nearest_workshop_id))

    recommendation = get_emergency_ai_recommendation(report_id)
    if recommendation:
        recommended_sucursal_id = recommendation.get("sucursal_recomendada_id")
        if recommended_sucursal_id is not None:
            candidate_scope_ids.add(int(recommended_sucursal_id))

        recommended_mecanico_id = recommendation.get("mecanico_recomendado_id")
        if recommended_mecanico_id is not None:
            recommended_mecanico = get_mecanico_by_id(int(recommended_mecanico_id))
            if recommended_mecanico:
                recommended_workshop_id = recommended_mecanico.get("workshop_id")
                if recommended_workshop_id is not None:
                    candidate_scope_ids.add(int(recommended_workshop_id))
                recommended_sucursal_id = recommended_mecanico.get("sucursal_id")
                if recommended_sucursal_id is not None:
                    candidate_scope_ids.add(int(recommended_sucursal_id))

    if scope_id in candidate_scope_ids:
        return report

    return None


def _build_mecanico_write_payload(payload: MecanicoCreate, *, workshop_id: int | None) -> dict[str, object]:
    return {
        "cliente_id": payload.cliente_id,
        "identity_card": payload.identity_card.strip() if payload.identity_card else None,
        "password_hash": hash_password(payload.password) if payload.password else None,
        "workshop_id": workshop_id or payload.workshop_id,
        "sucursal_id": payload.sucursal_id,
        "full_name": payload.full_name.strip(),
        "phone": payload.phone.strip(),
        "email": str(payload.email).lower().strip(),
        "specialty": payload.specialty.strip(),
        "status": payload.status,
    }


def _raise_mecanico_write_error(exc: Exception) -> None:
    detail = str(exc)
    if "password" in detail.lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail or "No se pudo vincular la cuenta del mecánico",
    ) from exc


def _coerce_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None

    return None


def _calculate_distance_meters(
    origin_latitude: object,
    origin_longitude: object,
    target_latitude: object,
    target_longitude: object,
) -> float | None:
    lat1 = _coerce_float(origin_latitude)
    lon1 = _coerce_float(origin_longitude)
    lat2 = _coerce_float(target_latitude)
    lon2 = _coerce_float(target_longitude)

    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    earth_radius_meters = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_meters * c


def _find_nearest_sucursal_id_for_emergency(
    row: Mapping[str, object],
    active_sucursales: list[dict[str, object]],
) -> int | None:
    nearest_sucursal_id: int | None = None
    nearest_distance: float | None = None

    for sucursal in active_sucursales:
        distance = _calculate_distance_meters(
            row.get("latitude"),
            row.get("longitude"),
            sucursal.get("latitud"),
            sucursal.get("longitud"),
        )
        if distance is None:
            continue
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_sucursal_id = int(sucursal["id"])

    return nearest_sucursal_id


def filter_emergency_rows_for_secretaria(
    rows: list[dict[str, object]],
    secretaria: Mapping[str, object],
) -> list[dict[str, object]]:
    target_sucursal_id = int(secretaria["sucursal_id"])
    active_sucursales = list_sucursales("ACTIVO")
    mecanicos_by_id = {
        int(item["id"]): item
        for item in list_mecanicos()
        if item.get("id") is not None
    }
    filtered_rows: list[dict[str, object]] = []

    for row in rows:
        assigned_mecanico_id = row.get("assigned_mecanico_id")
        if assigned_mecanico_id is not None:
            matching_mecanico = mecanicos_by_id.get(int(assigned_mecanico_id))
            if matching_mecanico and int(matching_mecanico.get("sucursal_id") or 0) == target_sucursal_id:
                filtered_rows.append(row)
            continue

        nearest_sucursal_id = _find_nearest_sucursal_id_for_emergency(row, active_sucursales)
        if nearest_sucursal_id == target_sucursal_id:
            filtered_rows.append(row)

    return filtered_rows


def filter_emergency_rows_for_mecanico(
    rows: list[dict[str, object]],
    *,
    current_user: AuthenticatedUser,
) -> list[dict[str, object]]:
    mecanico = get_mecanico_by_cliente_id(current_user.id)
    mecanico_id = int(mecanico["id"]) if mecanico and mecanico.get("id") is not None else None
    current_email = normalize_optional_text(current_user.email)
    filtered_rows: list[dict[str, object]] = []

    for row in rows:
        assignment_status = normalize_optional_text(str(row.get("assignment_status") or ""))
        if assignment_status == "rechazado":
            continue

        assigned_mecanico_id = row.get("assigned_mecanico_id")
        if mecanico_id is not None and assigned_mecanico_id is not None and int(assigned_mecanico_id) == mecanico_id:
            filtered_rows.append(row)
            continue

        assigned_mecanico_email = normalize_optional_text(str(row.get("assigned_mecanico_email") or ""))
        if current_email and assigned_mecanico_email == current_email:
            filtered_rows.append(row)

    return filtered_rows


def ensure_current_mecanico_is_assigned(
    *,
    current_user: AuthenticatedUser,
    context: Mapping[str, object],
) -> int:
    assigned_mecanico_email = normalize_optional_text(str(context.get("assigned_mecanico_email") or ""))
    current_email = normalize_optional_text(current_user.email)
    mecanico = get_mecanico_by_cliente_id(current_user.id)
    mecanico_id = int(mecanico["id"]) if mecanico and mecanico.get("id") is not None else None
    assigned_mecanico_id = context.get("assigned_mecanico_id")

    if mecanico_id is not None and assigned_mecanico_id is not None and int(assigned_mecanico_id) == mecanico_id:
        return mecanico_id
    if assigned_mecanico_email and assigned_mecanico_email == current_email and mecanico_id is not None:
        return mecanico_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Solo el mecánico asignado puede operar sobre esta emergencia.",
    )


def get_secretaria_scoped_emergency(
    *,
    current_user: AuthenticatedUser,
    report_id: int,
) -> dict[str, object] | None:
    secretaria = get_secretaria_scope(current_user)
    if not secretaria:
        return None

    report = get_emergency_report_by_id(report_id)
    if not report:
        return None

    filtered_rows = filter_emergency_rows_for_secretaria([report], secretaria)
    if not filtered_rows:
        return None

    return filtered_rows[0]


def ensure_client_can_access_emergency_tracking(
    *,
    current_user: AuthenticatedUser,
    emergency_id: int,
) -> None:
    try:
        report = get_emergency_report_by_id(emergency_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada.",
        )

    client_id = report.get("client_id")
    if client_id is None or int(client_id) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes consultar el tracking de una emergencia ajena.",
        )


def ensure_operational_user_can_access_emergency_tracking(
    *,
    current_user: AuthenticatedUser,
    emergency_id: int,
) -> None:
    if current_user.role == MECANICO_ROLE:
        context = get_emergency_tracking_context(emergency_id)
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergencia no encontrada.",
            )
        ensure_current_mecanico_is_assigned(
            current_user=current_user,
            context=context,
        )
        return

    if current_user.role == SECRETARIA_ROLE:
        scoped_report = get_secretaria_scoped_emergency(
            current_user=current_user,
            report_id=emergency_id,
        )
        if not scoped_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergencia no encontrada o fuera del alcance permitido.",
            )
        return

    try:
        report = get_emergency_report_by_id(emergency_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada.",
        )


def ensure_tracking_event_write_access(
    *,
    current_user: AuthenticatedUser,
    context: Mapping[str, object],
) -> None:
    if current_user.role == MECANICO_ROLE:
        ensure_current_mecanico_is_assigned(
            current_user=current_user,
            context=context,
        )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos para actualizar tracking.",
    )


def _normalize_role_name(role: str | None) -> str:
    normalized = (role or "").lower().strip()

    if normalized in {"tecnico", "técnico", "technician", "mecanico", "mecánico"}:
        return MECANICO_ROLE

    return normalized


def _resolve_client_scope(
    *,
    requested_client_id: int | None,
    current_user: AuthenticatedUser | None,
    operation_label: str,
) -> int:
    if current_user is None:
        if requested_client_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe enviar client_id o autenticarse con Bearer token.",
            )
        ensure_client_exists(requested_client_id)
        return requested_client_id

    current_role = _normalize_role_name(current_user.role)

    if current_role == CLIENT_ROLE:
        if requested_client_id is not None and requested_client_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No puedes {operation_label} para otro cliente autenticado.",
            )
        return current_user.id

    if current_role in PRIVILEGED_CLIENT_SCOPE_ROLES:
        if requested_client_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe enviar client_id para esta operación.",
            )
        ensure_client_exists(requested_client_id)
        return requested_client_id

    if requested_client_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe enviar client_id para esta operación.",
        )

    ensure_client_exists(requested_client_id)
    return requested_client_id


def require_mobile_notifications_user(
    current_user: AuthenticatedUser = Security(get_current_active_user),
) -> AuthenticatedUser:
    current_role = _normalize_role_name(current_user.role)

    if current_role not in {CLIENT_ROLE, SECRETARIA_ROLE, MECANICO_ROLE}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a notificaciones móviles.",
        )

    return current_user


def _vehicle_display_name(vehicle: Mapping[str, object]) -> str:
    brand = str(vehicle.get("brand") or "").strip()
    model = str(vehicle.get("model") or "").strip()
    display = " ".join(part for part in [brand, model] if part).strip()
    return display or "Vehículo registrado"


def _resolve_vehicle_for_emergency(
    *,
    client_id: int,
    vehicle_id: int | None,
    vehicle_plate: str | None,
    allow_plate_fallback: bool,
) -> dict[str, object]:
    if count_client_vehicles(client_id) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe registrar al menos un vehículo antes de reportar una emergencia.",
        )

    if vehicle_id is not None:
        vehicle = get_vehicle_by_any_id(vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El vehículo seleccionado no existe.",
            )

        if int(vehicle["client_id"]) != client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El vehículo seleccionado no pertenece al cliente autenticado.",
            )

        return vehicle

    normalized_plate = normalize_plate(vehicle_plate) if allow_plate_fallback and vehicle_plate else None
    if normalized_plate:
        vehicle = get_vehicle_by_client_and_plate(client_id, normalized_plate)
        if vehicle:
            return vehicle

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Debe seleccionar un vehículo registrado para reportar la emergencia.",
    )


def ensure_firebase_app() -> bool:
    global _firebase_app_initialized

    if _firebase_app_initialized:
        return True

    if not settings.fcm_enabled:
        return False

    if firebase_admin is None or credentials is None:
        logger.warning("FCM habilitado, pero firebase-admin no esta instalado")
        return False

    credentials_path = normalize_optional_text(settings.firebase_credentials_path)
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


#
# ============================================================
# FLUJO IMPORTANTE: NOTIFICACIONES PUSH DEL TALLER Y DEL SISTEMA
# Desde este bloque se prepara Firebase y se envian los push FCM
# al cliente cuando ocurre algo importante en una emergencia.
# Palabras clave de busqueda:
# - NOTIFICACION TALLER
# - PUSH FCM
# - FIREBASE EMERGENCIA
# ============================================================
#
def send_push_to_client(client_id: int | None, title: str, body: str, data: dict[str, str]) -> bool:
    # PALABRA CLAVE: AQUI SE HACEN LAS NOTIFICACIONES DEL TALLER Y DEL SISTEMA POR FCM.
    # Punto central de notificaciones push: cualquier flujo de emergencias
    # que necesite avisar al cliente termina enviando el mensaje desde aqui.
    if client_id is None:
        return False

    try:
        devices = list_active_device_fcm_tokens(client_id)
    except OperationalError:
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
    except OperationalError:
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


def compact_push_text(value: object, *, fallback: str, max_length: int = 120) -> str:
    text_value = normalize_optional_text(str(value)) if value is not None else None
    if not text_value:
        return fallback

    single_line = re.sub(r"\s+", " ", text_value)
    if len(single_line) <= max_length:
        return single_line

    return f"{single_line[: max_length - 3].rstrip()}..."


def build_client_notification_response(row: Mapping[str, object]) -> ClientNotificationResponse:
    payload = dict(row)
    metadata = payload.get("metadata")
    if isinstance(metadata, str):
        try:
            payload["metadata"] = json.loads(metadata)
        except json.JSONDecodeError:
            payload["metadata"] = None
    return ClientNotificationResponse.model_validate(payload)


def emergency_incident_label(report: Mapping[str, object]) -> str:
    return compact_push_text(
        report.get("description")
        or report.get("problem_type_standardized")
        or report.get("problem_type")
        or report.get("vehicle_name"),
        fallback="Incidente reportado",
    )


def normalize_tracking_status(value: object, *, has_assignment: bool) -> str:
    if has_assignment:
        return "assigned"

    normalized = normalize_optional_text(str(value)) if value is not None else None
    if normalized == "activo":
        return "active"
    if normalized == "pendiente":
        return "pending"
    if normalized == "rechazado":
        return "rejected"

    return normalized or "pending"


def push_coordinate(value: object) -> str | None:
    if value is None:
        return None

    try:
        return str(float(value))
    except (TypeError, ValueError):
        return None


def add_coordinate_pair(
    data: dict[str, str],
    *,
    latitude_key: str,
    longitude_key: str,
    latitude: object,
    longitude: object,
) -> None:
    normalized_latitude = push_coordinate(latitude)
    normalized_longitude = push_coordinate(longitude)

    if normalized_latitude is None or normalized_longitude is None:
        return

    data[latitude_key] = normalized_latitude
    data[longitude_key] = normalized_longitude


def _normalize_tracking_metadata_value(value: object) -> object | None:
    normalized = _coerce_float(value)
    if normalized is not None:
        return normalized
    return None


def build_emergency_tracking_metadata(
    *,
    report_id: int,
    mecanico: Mapping[str, object],
    sucursal: Mapping[str, object] | None,
    emergency_report: Mapping[str, object],
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "open_screen": "emergency_tracking",
        "emergencia_id": report_id,
        "emergency_id": report_id,
        "client_id": int(emergency_report["client_id"]) if emergency_report.get("client_id") is not None else None,
        "mecanico_id": int(mecanico["id"]),
        "mechanic_id": int(mecanico["id"]),
        "mechanic_name": str(mecanico.get("full_name") or "").strip(),
        "mechanic_phone": str(mecanico.get("phone") or "").strip(),
        "mechanic_specialty": str(mecanico.get("specialty") or "").strip(),
        "sucursal_id": int(mecanico["sucursal_id"]) if mecanico.get("sucursal_id") is not None else None,
        "sucursal_nombre": str((sucursal or {}).get("nombre") or mecanico.get("sucursal_nombre") or "").strip(),
    }

    origin_latitude = _normalize_tracking_metadata_value((sucursal or {}).get("latitud"))
    origin_longitude = _normalize_tracking_metadata_value((sucursal or {}).get("longitud"))
    destination_latitude = _normalize_tracking_metadata_value(emergency_report.get("latitude"))
    destination_longitude = _normalize_tracking_metadata_value(emergency_report.get("longitude"))

    if origin_latitude is None or origin_longitude is None or destination_latitude is None or destination_longitude is None:
        metadata["tracking_available"] = False
        metadata["tracking_reason"] = "Faltan coordenadas de origen o destino"
        return metadata

    metadata["tracking_available"] = True
    metadata["origin_latitude"] = origin_latitude
    metadata["origin_longitude"] = origin_longitude
    metadata["destination_latitude"] = destination_latitude
    metadata["destination_longitude"] = destination_longitude
    return metadata


def build_push_data_from_metadata(
    *,
    notification_type: str,
    metadata: Mapping[str, object],
) -> dict[str, str]:
    push_data: dict[str, str] = {"type": notification_type}

    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, bool):
            push_data[key] = "true" if value else "false"
            continue
        push_data[key] = str(value)

    return push_data


def _normalize_tracking_event_type(value: object) -> str:
    normalized = normalize_optional_text(str(value)) if value is not None else None
    if normalized in {"started", "moving", "arrived", "cancelled"}:
        return normalized
    return "moving"


def ensure_emergency_tracking_ready(context: Mapping[str, object]) -> None:
    emergency_status = str(context.get("emergency_status") or "").strip().lower()
    assigned_mecanico_id = context.get("assigned_mecanico_id")
    assignment_status = str(context.get("assignment_status") or "").strip().lower()

    if emergency_status != "activo":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La emergencia debe estar aceptada para consultar tracking.",
        )

    if assigned_mecanico_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La emergencia todavía no tiene un mecánico asignado.",
        )

    if assignment_status != "aceptado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El mecánico asignado debe aceptar la solicitud antes de iniciar tracking.",
        )

    origin_latitude = _coerce_float(context.get("origin_latitude"))
    origin_longitude = _coerce_float(context.get("origin_longitude"))
    destination_latitude = _coerce_float(context.get("destination_latitude"))
    destination_longitude = _coerce_float(context.get("destination_longitude"))

    if origin_latitude is None or origin_longitude is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La sucursal del mecánico asignado no tiene coordenadas configuradas.",
        )

    if destination_latitude is None or destination_longitude is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La emergencia no tiene coordenadas de destino registradas.",
        )


def build_emergency_tracking_response(
    *,
    context: Mapping[str, object],
    events: list[Mapping[str, object]],
) -> EmergencyTrackingResponse:
    latest_event_type = (
        _normalize_tracking_event_type(events[-1].get("event_type"))
        if events
        else "started"
    )

    payload = {
        "emergencia_id": int(context["emergencia_id"]),
        "emergency_id": int(context["emergencia_id"]),
        "client_id": int(context["client_id"]) if context.get("client_id") is not None else None,
        "estado_tracking": latest_event_type,
        "estado_emergencia": str(context.get("emergency_status") or ""),
        "mecanico": {
            "id": int(context["assigned_mecanico_id"]),
            "nombre": str(context.get("assigned_mecanico_name") or "").strip(),
            "telefono": normalize_optional_text(str(context.get("assigned_mecanico_phone") or "")),
            "email": normalize_optional_text(str(context.get("assigned_mecanico_email") or "")),
            "especialidad": normalize_optional_text(str(context.get("assigned_mecanico_specialty") or "")),
        },
        "origen": {
            "sucursal_id": int(context["sucursal_id"]) if context.get("sucursal_id") is not None else None,
            "nombre": normalize_optional_text(str(context.get("sucursal_nombre") or "")),
            "latitud": float(context["origin_latitude"]),
            "longitud": float(context["origin_longitude"]),
        },
        "destino": {
            "latitud": float(context["destination_latitude"]),
            "longitud": float(context["destination_longitude"]),
            "direccion": normalize_optional_text(str(context.get("address") or "")),
            "zona": normalize_optional_text(str(context.get("zone") or "")),
        },
        "eventos": [
            {
                "id": int(event["id"]),
                "emergencia_id": int(event["emergencia_id"]),
                "mecanico_id": int(event["mecanico_id"]),
                "latitud": float(event["latitud"]),
                "longitud": float(event["longitud"]),
                "heading": _coerce_float(event.get("heading")),
                "speed": _coerce_float(event.get("speed")),
                "event_type": _normalize_tracking_event_type(event.get("event_type")),
                "created_at": event["created_at"],
            }
            for event in events
        ],
    }

    return EmergencyTrackingResponse.model_validate(payload)


def get_emergency_tracking_context_or_404(emergency_id: int) -> dict[str, object]:
    try:
        context = get_emergency_tracking_context(emergency_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada.",
        )

    return context


def get_emergency_tracking_response(
    *,
    emergency_id: int,
) -> EmergencyTrackingResponse:
    context = get_emergency_tracking_context_or_404(emergency_id)
    ensure_emergency_tracking_ready(context)

    try:
        events = list_emergency_tracking_events(emergency_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return build_emergency_tracking_response(context=context, events=events)


def build_public_upload_url(relative_path: str) -> str:
    return f"/uploads/{relative_path}"


#
# ============================================================
# FLUJO IMPORTANTE: MANEJO DE ARCHIVOS SUBIDOS
# Aqui se guardan, limpian y convierten en URL publicas los archivos
# de vehiculos y emergencias, incluyendo fotos y audio.
# Palabras clave de busqueda:
# - SUBIDA DE ARCHIVOS
# - FOTOS EMERGENCIA
# - AUDIO EMERGENCIA
# ============================================================
#
def remove_file_if_exists(path: Path) -> None:
    if path.is_file():
        path.unlink()


def save_upload_with_limit(
    upload: UploadFile,
    *,
    destination_dir: Path,
    relative_dir: str,
    allowed_suffixes: set[str],
    max_bytes: int | None,
    invalid_type_detail: str,
    too_large_detail: str | None = None,
) -> tuple[str, str]:
    suffix = Path(upload.filename or "").suffix.lower()

    if suffix not in allowed_suffixes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=invalid_type_detail)

    filename = f"{uuid4().hex}{suffix}"
    relative_path = f"{relative_dir}/{filename}"
    absolute_path = destination_dir / filename
    bytes_written = 0

    with absolute_path.open("wb") as buffer:
        while chunk := upload.file.read(1024 * 1024):
            bytes_written += len(chunk)
            if max_bytes is not None and bytes_written > max_bytes:
                buffer.close()
                remove_file_if_exists(absolute_path)
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=too_large_detail)
            buffer.write(chunk)

    return relative_path, build_public_upload_url(relative_path)


def cleanup_uploaded_files(*relative_paths: str | None) -> None:
    for relative_path in relative_paths:
        remove_uploaded_file(relative_path)


def save_vehicle_photo(photo: UploadFile | None) -> tuple[str | None, str | None]:
    if photo is None or not photo.filename:
        return None, None

    return save_upload_with_limit(
        photo,
        destination_dir=VEHICLE_UPLOADS_DIR,
        relative_dir="vehicles",
        allowed_suffixes=ALLOWED_PHOTO_SUFFIXES,
        max_bytes=None,
        invalid_type_detail="La foto debe ser JPG, JPEG, PNG o WEBP",
    )


def save_emergency_photo(photo: UploadFile) -> tuple[str, str]:
    return save_upload_with_limit(
        photo,
        destination_dir=EMERGENCY_PHOTOS_DIR,
        relative_dir="emergencias/photos",
        allowed_suffixes=ALLOWED_PHOTO_SUFFIXES,
        max_bytes=MAX_EMERGENCY_PHOTO_BYTES,
        invalid_type_detail="Cada foto debe ser JPG, JPEG, PNG o WEBP",
        too_large_detail="Archivo demasiado grande: cada foto puede pesar como máximo 5 MB.",
    )


def save_emergency_audio(audio: UploadFile | None) -> tuple[str | None, str | None]:
    if audio is None or not audio.filename:
        return None, None

    return save_upload_with_limit(
        audio,
        destination_dir=EMERGENCY_AUDIO_DIR,
        relative_dir="emergencias/audio",
        allowed_suffixes=ALLOWED_AUDIO_SUFFIXES,
        max_bytes=MAX_EMERGENCY_AUDIO_BYTES,
        invalid_type_detail="El audio debe ser AAC, M4A, MP3, WAV, OGG o WEBM",
        too_large_detail="Archivo demasiado grande: el audio puede pesar como máximo 15 MB.",
    )


def remove_vehicle_photo(photo_path: str | None) -> None:
    if not photo_path:
        return

    candidate = (UPLOADS_ROOT / photo_path).resolve()

    try:
        candidate.relative_to(UPLOADS_ROOT.resolve())
    except ValueError:
        return

    remove_file_if_exists(candidate)


def remove_uploaded_file(relative_path: str | None) -> None:
    if not relative_path:
        return

    candidate = (UPLOADS_ROOT / relative_path).resolve()

    try:
        candidate.relative_to(UPLOADS_ROOT.resolve())
    except ValueError:
        return

    remove_file_if_exists(candidate)


def parse_json_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]

    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []

        if isinstance(decoded, list):
            return [str(item) for item in decoded]

    return []


def relative_upload_path_from_url(value: str | None) -> str | None:
    normalized = normalize_optional_text(value)

    if not normalized:
        return None

    parsed_path = urlparse(normalized).path if normalized.startswith(("http://", "https://")) else normalized
    parsed_path = parsed_path.lstrip("/")

    if parsed_path.startswith("uploads/"):
        parsed_path = parsed_path.removeprefix("uploads/")

    if not parsed_path:
        return None

    candidate = (UPLOADS_ROOT / parsed_path).resolve()

    try:
        candidate.relative_to(UPLOADS_ROOT.resolve())
    except ValueError:
        return None

    return parsed_path if candidate.is_file() else None


def existing_upload_urls_from_media_lists(photo_paths: object, photo_urls: object) -> tuple[list[str], list[str]]:
    existing_paths: list[str] = []

    for raw_value in [*parse_json_string_list(photo_paths), *parse_json_string_list(photo_urls)]:
        relative_path = relative_upload_path_from_url(raw_value)

        if relative_path and relative_path not in existing_paths:
            existing_paths.append(relative_path)

    return existing_paths, [build_public_upload_url(relative_path) for relative_path in existing_paths]


def normalize_emergency_media_fields(row: dict[str, object]) -> dict[str, object]:
    existing_photo_paths, existing_photo_urls = existing_upload_urls_from_media_lists(
        row.get("photo_paths"),
        row.get("photo_urls"),
    )
    row["photo_paths"] = existing_photo_paths
    row["photo_urls"] = existing_photo_urls

    audio_path = relative_upload_path_from_url(str(row.get("audio_path"))) if row.get("audio_path") else None
    audio_url_path = relative_upload_path_from_url(str(row.get("audio_url"))) if row.get("audio_url") else None
    existing_audio_path = audio_path or audio_url_path
    row["audio_path"] = existing_audio_path
    row["audio_url"] = build_public_upload_url(existing_audio_path) if existing_audio_path else None

    return row


def normalize_emergency_assignment_fields(row: dict[str, object]) -> dict[str, object]:
    if row.get("assigned_mecanico_id") is None:
        row["assigned_mecanico_id"] = row.get("assigned_mechanic_id") or row.get("assigned_technician_id")
    if row.get("assigned_mecanico_name") is None:
        row["assigned_mecanico_name"] = row.get("assigned_mechanic_name") or row.get("assigned_technician_name")
    if row.get("assigned_mecanico_phone") is None:
        row["assigned_mecanico_phone"] = row.get("assigned_mechanic_phone") or row.get("assigned_technician_phone")
    if row.get("assigned_mecanico_email") is None:
        row["assigned_mecanico_email"] = row.get("assigned_mechanic_email") or row.get("assigned_technician_email")
    if row.get("assigned_mecanico_specialty") is None:
        row["assigned_mecanico_specialty"] = row.get("assigned_mechanic_specialty") or row.get("assigned_technician_specialty")
    # Legacy API aliases preserved for backward compatibility. Prefer assigned_mecanico_*.
    row["assigned_mechanic_id"] = row.get("assigned_mecanico_id")
    row["assigned_mechanic_name"] = row.get("assigned_mecanico_name")
    row["assigned_mechanic_phone"] = row.get("assigned_mecanico_phone")
    row["assigned_mechanic_email"] = row.get("assigned_mecanico_email")
    row["assigned_mechanic_specialty"] = row.get("assigned_mecanico_specialty")
    row["assigned_technician_id"] = row.get("assigned_mecanico_id")
    row["assigned_technician_name"] = row.get("assigned_mecanico_name")
    row["assigned_technician_phone"] = row.get("assigned_mecanico_phone")
    row["assigned_technician_email"] = row.get("assigned_mecanico_email")
    row["assigned_technician_specialty"] = row.get("assigned_mecanico_specialty")
    return row


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_ROOT)), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^https?://("
        r"localhost|"
        r"127\.0\.0\.1|"
        r"10\.\d+\.\d+\.\d+|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|"
        r"192\.168\.\d+\.\d+|"
        r"\d+\.\d+\.\d+\.\d+"
        r")(:\d+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(recepciones_router)
app.include_router(graphql_router, prefix=f"{settings.api_prefix}/graphql")


#
# ============================================================
# FLUJO IMPORTANTE: STARTUP DEL BACKEND
# Aqui se inicializa la base de datos cuando arranca FastAPI.
# Palabras clave de busqueda:
# - STARTUP BACKEND
# - INICIO BACKEND
# - INIT DATABASE
# ============================================================
#
@app.on_event("startup")
def on_startup() -> None:
    try:
        init_database()
    except OperationalError:
        logger.exception("No se pudo inicializar la base de datos en startup")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Backend running"}


def call_ms_ia_multimedia_analyze(payload: IaAnalyzeEmergencyRequest) -> dict[str, object]:
    request_body = json.dumps(payload.model_dump()).encode("utf-8")
    request = urllib.request.Request(
        f"{settings.ms_ia_multimedia_url.rstrip('/')}/analyze/emergency",
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=settings.ms_ia_timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") or "El microservicio IA respondió con error"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con ms-ia-multimedia",
        ) from exc

    try:
        parsed_response = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Respuesta inválida desde ms-ia-multimedia",
        ) from exc

    if not isinstance(parsed_response, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Respuesta inválida desde ms-ia-multimedia",
        )

    return parsed_response


def publish_emergency_analysis_requested(payload: IaQueueTestRequest) -> None:
    import pika
    from pika.exceptions import AMQPError

    parameters = pika.URLParameters(settings.rabbitmq_url)
    message = json.dumps(payload.model_dump(), ensure_ascii=False).encode("utf-8")

    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=settings.rabbitmq_analysis_queue, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=settings.rabbitmq_analysis_queue,
            body=message,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
        connection.close()
    except AMQPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo publicar el mensaje en RabbitMQ",
        ) from exc


@app.post(
    f"{settings.api_prefix}/integrations/ia/queue-test",
    response_model=IaQueueTestResponse,
)
def queue_emergency_analysis(payload: IaQueueTestRequest) -> IaQueueTestResponse:
    publish_emergency_analysis_requested(payload)
    return IaQueueTestResponse(
        status="queued",
        queue=settings.rabbitmq_analysis_queue,
        emergency_id=payload.emergency_id,
    )


@app.post(
    f"{settings.api_prefix}/integrations/ia/analyze-test",
    response_model=IaAnalyzeEmergencyResponse,
)
def analyze_emergency_with_ia(payload: IaAnalyzeEmergencyRequest) -> IaAnalyzeEmergencyResponse:
    response = call_ms_ia_multimedia_analyze(payload)
    return IaAnalyzeEmergencyResponse(**response)


@app.post(
    f"{settings.api_prefix}/devices/fcm-token",
    response_model=DeviceFcmTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_device_fcm_token(
    payload: DeviceFcmTokenCreate,
    current_user: AuthenticatedUser = Security(get_current_active_user),
) -> DeviceFcmTokenResponse:
    if current_user.role == WORKSHOP_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los talleres no pueden registrar tokens FCM en este endpoint.",
        )

    if current_user.role != PROTECTED_ADMIN_ROLE and current_user.id != payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes registrar tu propio token FCM.",
        )

    ensure_client_exists(payload.user_id)

    try:
        device = upsert_device_fcm_token(
            {
                "user_id": payload.user_id,
                "fcm_token": payload.fcm_token.strip(),
                "platform": payload.platform,
            }
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return DeviceFcmTokenResponse.model_validate(device)


@app.delete(
    f"{settings.api_prefix}/devices/fcm-token",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deactivate_device_fcm_token(
    payload: DeviceFcmTokenDeactivate,
    current_user: AuthenticatedUser = Security(get_current_active_user),
) -> None:
    try:
        deactivate_client_fcm_token(current_user.id, payload.fcm_token.strip())
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc


@app.post(
    f"{settings.api_prefix}/mobile/workshop/fcm-token",
    response_model=WorkshopFcmTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_workshop_fcm_token(
    payload: WorkshopFcmTokenCreate,
    current_user: AuthenticatedUser = Security(require_roles(WORKSHOP_ROLE)),
) -> WorkshopFcmTokenResponse:
    try:
        device = upsert_workshop_fcm_token(
            {
                "workshop_id": current_user.id,
                "fcm_token": payload.fcm_token.strip(),
                "platform": payload.platform,
            }
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return WorkshopFcmTokenResponse.model_validate(device)


@app.delete(
    f"{settings.api_prefix}/mobile/workshop/fcm-token",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deactivate_workshop_device_token(
    payload: DeviceFcmTokenDeactivate,
    current_user: AuthenticatedUser = Security(require_roles(WORKSHOP_ROLE)),
) -> None:
    try:
        deactivate_workshop_fcm_token(current_user.id, payload.fcm_token.strip())
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc


@app.get(
    f"{settings.api_prefix}/mobile/notificaciones",
    response_model=list[ClientNotificationResponse],
)
def get_mobile_notifications(
    current_user: AuthenticatedUser = Security(require_mobile_notifications_user),
) -> list[ClientNotificationResponse]:
    try:
        rows = list_client_notifications(current_user.id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return [build_client_notification_response(row) for row in rows]


@app.patch(
    f"{settings.api_prefix}/mobile/notificaciones/{{notification_id}}/leida",
    response_model=ClientNotificationResponse,
)
def mark_mobile_notification_read(
    notification_id: int,
    current_user: AuthenticatedUser = Security(require_mobile_notifications_user),
) -> ClientNotificationResponse:
    try:
        row = mark_client_notification_read(notification_id, current_user.id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")

    return build_client_notification_response(row)


@app.get(
    f"{settings.api_prefix}/mobile/notificaciones/unread-count",
    response_model=ClientNotificationUnreadCountResponse,
)
def get_mobile_unread_notifications_count(
    current_user: AuthenticatedUser = Security(require_mobile_notifications_user),
) -> ClientNotificationUnreadCountResponse:
    try:
        unread_count = count_unread_client_notifications(current_user.id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return ClientNotificationUnreadCountResponse(unread_count=unread_count)


@app.get(
    f"{settings.api_prefix}/mobile/emergencias/{{emergencia_id}}/tracking",
    response_model=EmergencyTrackingResponse,
)
def get_mobile_emergency_tracking(
    emergencia_id: int,
    current_user: AuthenticatedUser = Security(require_roles(CLIENT_ROLE)),
) -> EmergencyTrackingResponse:
    ensure_client_can_access_emergency_tracking(
        current_user=current_user,
        emergency_id=emergencia_id,
    )
    return get_emergency_tracking_response(emergency_id=emergencia_id)


@app.post(
    f"{settings.api_prefix}/mobile/emergencias/{{emergencia_id}}/tracking/events",
    response_model=EmergencyTrackingEventResponse,
)
def create_mobile_emergency_tracking_event(
    emergencia_id: int,
    payload: EmergencyTrackingEventCreate,
    current_user: AuthenticatedUser = Security(require_roles(MECANICO_ROLE)),
) -> EmergencyTrackingEventResponse:
    context = get_emergency_tracking_context_or_404(emergencia_id)
    ensure_emergency_tracking_ready(context)
    ensure_tracking_event_write_access(
        current_user=current_user,
        context=context,
    )

    try:
        existing_events = list_emergency_tracking_events(emergencia_id)
        created_event = create_emergency_tracking_event(
            {
                "emergency_id": emergencia_id,
                "mecanico_id": int(context["assigned_mecanico_id"]),
                "latitud": payload.latitud,
                "longitud": payload.longitud,
                "heading": payload.heading,
                "speed": payload.speed,
                "event_type": payload.event_type,
            },
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            source_app="mobile_mecanico",
            endpoint=f"{settings.api_prefix}/mobile/emergencias/{{emergencia_id}}/tracking/events",
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not existing_events:
        notification_metadata = {
            "open_screen": "emergency_tracking",
            "emergencia_id": emergencia_id,
            "emergency_id": emergencia_id,
            "tracking_event_id": int(created_event["id"]),
            "event_type": str(created_event.get("event_type") or "moving"),
            "status": "tracking_started",
        }
        client_id = context.get("client_id")
        if client_id is not None:
            try:
                create_client_notification(
                    {
                        "cliente_id": int(client_id),
                        "emergencia_id": emergencia_id,
                        "tipo": "tracking_started",
                        "titulo": "Tracking iniciado",
                        "mensaje": "Tu mecánico ya inició el seguimiento en ruta.",
                        "metadata": notification_metadata,
                    }
                )
            except OperationalError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Base de datos no disponible",
                ) from exc

            send_push_to_client(
                int(client_id),
                "Tracking iniciado",
                "Tu mecánico ya inició el seguimiento en ruta.",
                build_push_data_from_metadata(
                    notification_type="tracking_started",
                    metadata=notification_metadata,
                ),
            )

    return EmergencyTrackingEventResponse.model_validate(created_event)


@app.post(
    f"{settings.api_prefix}/mobile/push-test",
    response_model=PushTestResponse,
)
def test_push_notification(
    payload: PushTestRequest,
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE)),
) -> PushTestResponse:
    if not ensure_firebase_app() or messaging is None:
        return PushTestResponse(
            sent=False,
            message="Firebase no está inicializado o FCM deshabilitado.",
        )

    try:
        message = messaging.Message(
            notification=messaging.Notification(title=payload.title, body=payload.body),
            data={"type": "test"},
            token=payload.fcm_token.strip(),
        )
        messaging.send(message)
        return PushTestResponse(sent=True, message="Notificación enviada correctamente.")
    except Exception as exc:
        return PushTestResponse(sent=False, message=str(exc))


@app.post(
    f"{settings.api_prefix}/workshops",
    response_model=WorkshopRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_workshop(payload: WorkshopRegistrationCreate) -> WorkshopRegistrationResponse:
    created = create_workshop_registration(
        {
            **payload.model_dump(),
            "approval_status": "pendiente",
            "password_hash": None,
        }
    )
    return WorkshopRegistrationResponse.model_validate(created)


@app.post(
    f"{settings.api_prefix}/vehiculos",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_vehicle(
    client_id: int | None = Form(default=None, ge=1),
    brand: str = Form(min_length=1, max_length=120),
    model: str = Form(min_length=1, max_length=120),
    year: int = Form(ge=1900, le=2100),
    plate: str = Form(min_length=3, max_length=40),
    color: str = Form(min_length=2, max_length=80),
    is_primary: bool = Form(default=False),
    photo: UploadFile | None = File(default=None),
    current_user: AuthenticatedUser | None = Security(get_optional_current_active_user),
) -> VehicleResponse:
    resolved_client_id = _resolve_client_scope(
        requested_client_id=client_id,
        current_user=current_user,
        operation_label="registrar vehículos",
    )
    photo_path, photo_url = save_vehicle_photo(photo)
    vehicle_payload = {
        "client_id": resolved_client_id,
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

    return VehicleResponse.model_validate(created)


@app.post(
    f"{settings.api_prefix}/emergencias",
    response_model=EmergencyReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_emergency(
    client_id: int | None = Form(default=None, ge=1),
    vehicle_id: int | None = Form(default=None, ge=1),
    vehicle_name: str | None = Form(default=None, min_length=1, max_length=160),
    vehicle_plate: str | None = Form(default=None, min_length=3, max_length=40),
    problem_type: str = Form(min_length=2, max_length=120),
    price: int | None = Form(default=None, ge=0),
    description: str | None = Form(default=None, min_length=3, max_length=4000),
    latitude: float | None = Form(default=None, ge=-90, le=90),
    longitude: float | None = Form(default=None, ge=-180, le=180),
    address: str | None = Form(default=None, max_length=255),
    zone: str | None = Form(default=None, max_length=120),
    nearest_workshop_id: int | None = Form(default=None, ge=1),
    nearest_workshop_name: str | None = Form(default=None, max_length=160),
    nearest_workshop_specialty: str | None = Form(default=None, max_length=120),
    nearest_workshop_zone: str | None = Form(default=None, max_length=120),
    nearest_workshop_distance_meters: float | None = Form(default=None, ge=0),
    audio_duration_seconds: float | None = Form(default=None, ge=0),
    photos: list[UploadFile] = File(default=[]),
    audio: UploadFile | None = File(default=None),
    current_user: AuthenticatedUser | None = Security(get_optional_current_active_user),
) -> EmergencyReportResponse:
    #
    # ============================================================
    # FLUJO IMPORTANTE: REGISTRO COMPLETO DE EMERGENCIA
    # Aqui entra la solicitud principal del cliente.
    # Este flujo valida datos, guarda fotos/audio, transcribe audio,
    # clasifica imagenes, calcula precio y registra la emergencia.
    # Palabras clave de busqueda:
    # - REGISTRO EMERGENCIA
    # - SOLICITUD DE EMERGENCIA
    # - GUARDAR EMERGENCIA
    # ============================================================
    #
    resolved_client_id = _resolve_client_scope(
        requested_client_id=client_id,
        current_user=current_user,
        operation_label="reportar la emergencia",
    )
    current_role = _normalize_role_name(current_user.role) if current_user is not None else ""
    if current_role == CLIENT_ROLE and vehicle_id is None:
        if count_client_vehicles(resolved_client_id) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe registrar al menos un vehículo antes de reportar una emergencia.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe seleccionar un vehículo registrado para reportar la emergencia.",
        )
    selected_vehicle = _resolve_vehicle_for_emergency(
        client_id=resolved_client_id,
        vehicle_id=vehicle_id,
        vehicle_plate=vehicle_plate,
        allow_plate_fallback=current_role != CLIENT_ROLE,
    )

    # FastAPI entrega todos los campos `photos`; filtramos entradas vacias para
    # mantener el contrato flexible con clientes moviles.
    valid_photos = [photo for photo in photos if photo.filename]

    if len(valid_photos) > MAX_EMERGENCY_PHOTOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Se permiten como maximo {MAX_EMERGENCY_PHOTOS} fotos por emergencia",
        )

    photo_paths: list[str] = []
    photo_urls: list[str] = []
    audio_path: str | None = None
    audio_transcript: str | None = None
    audio_transcript_status: str | None = "pendiente" if audio is not None and audio.filename else None
    audio_transcript_error: str | None = None
    photo_problem_type_standardized: str | None = None
    photo_classification_confidence: float | None = None
    photo_classification_error: str | None = None

    try:
        for photo in valid_photos:
            relative_path, public_url = save_emergency_photo(photo)
            photo_paths.append(relative_path)
            photo_urls.append(public_url)

        audio_path, audio_url = save_emergency_audio(audio)
        normalized_problem_type = normalize_problem_type(problem_type)
        standardized_problem_type = determine_standardized_problem_type(
            problem_type=normalized_problem_type,
            description=description,
            audio_transcript=audio_transcript,
            photo_problem_type_standardized=photo_problem_type_standardized,
        )
        resolved_price = resolve_emergency_price(price, standardized_problem_type)

        payload = {
            "client_id": resolved_client_id,
            "vehicle_id": int(selected_vehicle["id"]),
            "vehicle_name": _vehicle_display_name(selected_vehicle),
            "vehicle_plate": str(selected_vehicle["plate"]),
            "problem_type": normalized_problem_type,
            "price": resolved_price,
            "emergency_status": "pendiente",
            "problem_type_standardized": standardized_problem_type,
            "photo_problem_type_standardized": photo_problem_type_standardized,
            "photo_classification_confidence": photo_classification_confidence,
            "photo_classification_error": normalize_optional_text(photo_classification_error),
            "description": normalize_optional_text(description),
            "latitude": latitude,
            "longitude": longitude,
            "address": normalize_optional_text(address),
            "zone": normalize_optional_text(zone),
            "nearest_workshop_id": nearest_workshop_id,
            "nearest_workshop_name": normalize_optional_text(nearest_workshop_name),
            "nearest_workshop_specialty": normalize_optional_text(nearest_workshop_specialty),
            "nearest_workshop_zone": normalize_optional_text(nearest_workshop_zone),
            "nearest_workshop_distance_meters": nearest_workshop_distance_meters,
            "audio_duration_seconds": audio_duration_seconds,
            "audio_transcript": audio_transcript,
            "audio_transcript_status": audio_transcript_status,
            "audio_transcript_error": normalize_optional_text(audio_transcript_error),
            "photo_paths": json.dumps(photo_paths),
            "photo_urls": json.dumps(photo_urls),
            "audio_path": audio_path,
            "audio_url": audio_url,
            "ia_categoria": None,
            "ia_prioridad": None,
            "ia_confidence": None,
            "ia_procesado_en": None,
        }

        created = create_emergency_report(
            payload,
            actor_user_id=resolved_client_id,
            actor_role=current_role or CLIENT_ROLE,
            source_app="mobile_cliente" if current_role == CLIENT_ROLE or not current_role else "web",
            endpoint=f"{settings.api_prefix}/emergencias",
        )
    except HTTPException:
        cleanup_uploaded_files(*photo_paths, audio_path)
        raise
    except OperationalError as exc:
        cleanup_uploaded_files(*photo_paths, audio_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    try:
        ai_payload = process_emergency_report_with_ai(
            emergency_id=int(created["id"]),
            problem_type=str(created.get("problem_type") or ""),
            description=created.get("description"),
            photo_paths=photo_paths,
            audio_path=audio_path,
        )
        updated_ai_row = update_emergency_ai_result(
            int(created["id"]),
            ai_payload,
            actor_user_id=None,
            actor_role="sistema",
            source_app="vm3_ai_service",
            endpoint=settings.base_url_ai,
        )
        if updated_ai_row is not None:
            created = updated_ai_row
    except AIServiceError as exc:
        logger.warning(
            "No se pudo procesar la emergencia %s con VM3: %s",
            created.get("id"),
            exc,
        )

    normalize_emergency_media_fields(created)
    normalize_emergency_assignment_fields(created)

    # Notificar al taller más cercano si tiene tokens FCM registrados
    nearest_workshop_id_val = created.get("nearest_workshop_id")
    if nearest_workshop_id_val is not None:
        incident_label = emergency_incident_label(created)
        send_push_to_workshop(
            int(nearest_workshop_id_val),
            "Nueva emergencia",
            f"Nueva solicitud: {incident_label}",
            {
                "type": "new_emergency",
                "emergency_id": str(created.get("id", "")),
                "problem_type": str(created.get("problem_type", "")),
                "incident_description": incident_label,
            },
        )

    return EmergencyReportResponse.model_validate(created)


@app.get(
    f"{settings.api_prefix}/emergencias",
    response_model=list[EmergencyReportListResponse],
)
def get_emergency_reports(
    nearest_workshop_id: int | None = Query(default=None, ge=1),
    emergency_status: str | None = Query(default=None, pattern="^(pendiente|activo|rechazado|cerrada)$"),
    current_user: AuthenticatedUser | None = Security(get_optional_current_active_user),
) -> list[EmergencyReportListResponse]:
    secretaria = get_secretaria_scope(current_user) if current_user else None
    current_role = _normalize_role_name(current_user.role) if current_user else ""

    try:
        rows = list_emergency_reports(
            nearest_workshop_id=nearest_workshop_id,
            secretaria_sucursal_id=None,
            emergency_status=emergency_status,
        )
        if secretaria:
            rows = filter_emergency_rows_for_secretaria(rows, secretaria)
        elif current_role == MECANICO_ROLE and current_user is not None:
            rows = filter_emergency_rows_for_mecanico(rows, current_user=current_user)
        elif current_role == CLIENT_ROLE and current_user is not None:
            rows = [row for row in rows if row.get("client_id") == current_user.id]
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    for row in rows:
        normalize_emergency_media_fields(row)
        normalize_emergency_assignment_fields(row)

    return [EmergencyReportListResponse.model_validate(row) for row in rows]


@app.put(
    f"{settings.api_prefix}/emergencias/{{report_id}}/status",
    response_model=EmergencyReportResponse,
)
def edit_emergency_status(
    report_id: int,
    payload: EmergencyStatusUpdate,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)
    ),
) -> EmergencyReportResponse:
    #
    # ============================================================
    # FLUJO IMPORTANTE: ADMIN O SECRETARIA ACEPTAN EMERGENCIA
    # Aqui un usuario privilegiado cambia el estado de la solicitud.
    # Si la acepta y pasa a "activo", desde aqui tambien se dispara
    # la notificacion push para avisar al cliente.
    # Palabras clave de busqueda:
    # - ADMIN ACEPTA EMERGENCIA
    # - SECRETARIA ACEPTA EMERGENCIA
    # - CAMBIO ESTADO EMERGENCIA
    # - NOTIFICACION EMERGENCIA ACEPTADA
    # ============================================================
    #
    if payload.emergency_status == "rechazado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para rechazar una emergencia debes usar /api/emergencias/{report_id}/rechazar con un motivo.",
        )

    scoped_secretaria_report = None
    scoped_operational_report = None
    effective_workshop_id = workshop_id

    if current_user.role == SECRETARIA_ROLE:
        try:
            scoped_secretaria_report = get_secretaria_scoped_emergency(
                current_user=current_user,
                report_id=report_id,
            )
        except OperationalError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible",
            ) from exc

        if not scoped_secretaria_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergencia no encontrada o fuera del alcance permitido",
            )

        # Para secretaria el alcance se valida por sucursal afiliada, no por workshop_id legado.
        effective_workshop_id = None
    elif payload.emergency_status == "activo":
        if effective_workshop_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debes indicar workshop_id para aceptar la emergencia.",
            )

        try:
            if current_user.role == PROTECTED_ADMIN_ROLE:
                scoped_operational_report = get_emergency_report_by_id(report_id)
            else:
                scoped_operational_report = get_emergency_report_for_operational_scope(
                    report_id=report_id,
                    scope_id=effective_workshop_id,
                )
        except OperationalError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible",
            ) from exc

        if not scoped_operational_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergencia no encontrada o fuera del alcance permitido",
            )

    try:
        notification_payload = None
        if payload.emergency_status == "activo":
            notification_payload = {
                "cliente_id": None,
                "emergencia_id": report_id,
                "tipo": "emergency_accepted",
                "titulo": "Emergencia aceptada",
                "mensaje": "Tu emergencia fue aceptada. Estamos buscando un mecánico disponible.",
                "metadata": {
                    "status": "accepted",
                    "open_screen": "notifications",
                    "emergency_id": report_id,
                },
            }

            updated, _created_notification, transitioned_to_active = accept_emergency_report(
                report_id,
                nearest_workshop_id=(
                    effective_workshop_id
                    if scoped_operational_report
                    and scoped_operational_report.get("nearest_workshop_id") is not None
                    and int(scoped_operational_report["nearest_workshop_id"]) == effective_workshop_id
                    else None
                ),
                notification_payload=notification_payload,
                actor_user_id=current_user.id,
                actor_role=current_user.role,
                source_app="web",
                endpoint=f"{settings.api_prefix}/emergencias/{{report_id}}/status",
            )
        else:
            updated = update_emergency_status(
                report_id,
                payload.emergency_status,
                nearest_workshop_id=effective_workshop_id,
            )
            transitioned_to_active = False
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada o no pertenece al workshop_id indicado",
        )

    normalize_emergency_media_fields(updated)

    if payload.emergency_status == "activo" and transitioned_to_active:
        send_push_to_client(
            int(updated["client_id"]) if updated.get("client_id") is not None else None,
            "Emergencia aceptada",
            "Tu emergencia fue aceptada. Estamos buscando un mecánico disponible.",
            {
                "type": "emergency_accepted",
                "emergency_id": str(report_id),
                "status": "accepted",
                "open_screen": "notifications",
            },
        )

    normalize_emergency_assignment_fields(updated)
    return EmergencyReportResponse.model_validate(updated)


@app.post(
    f"{settings.api_prefix}/emergencias/{{report_id}}/rechazar",
    response_model=EmergencyRejectResponse,
)
def reject_emergency(
    report_id: int,
    payload: EmergencyRejectRequest,
    current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, MECANICO_ROLE)
    ),
) -> EmergencyRejectResponse:
    if current_user.role == MECANICO_ROLE:
        context = get_emergency_tracking_context_or_404(report_id)
        mecanico_id = ensure_current_mecanico_is_assigned(
            current_user=current_user,
            context=context,
        )
        assignment_status = normalize_optional_text(str(context.get("assignment_status") or ""))
        if assignment_status not in {"asignado", "aceptado"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La asignación actual ya no puede ser rechazada.",
            )

        rejected_assignment = reject_emergency_mecanico_assignment(
            report_id,
            mecanico_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            source_app="mobile_mecanico",
            endpoint=f"{settings.api_prefix}/emergencias/{{report_id}}/rechazar",
        )
        if not rejected_assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró una asignación vigente para rechazar.",
            )

        updated_report = get_emergency_report_by_id(report_id)
        if not updated_report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

        normalize_emergency_media_fields(updated_report)
        normalize_emergency_assignment_fields(updated_report)
        return EmergencyRejectResponse.model_validate(
            {
                **updated_report,
                "notification_created": False,
                "push_sent": False,
            }
        )

    # Deuda tecnica documentada: reportes_emergencia no guarda sucursal_id directa.
    # Mientras esa relacion no exista, la restriccion extra para secretaria queda por rol
    # autenticado y no por pertenencia exacta de la emergencia a una sucursal persistida.
    try:
        current_report = get_emergency_report_by_id(report_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not current_report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

    if current_report.get("emergency_status") == "rechazado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La emergencia ya fue rechazada previamente.",
        )

    motivo = payload.motivo.strip()
    client_id = int(current_report["client_id"]) if current_report.get("client_id") is not None else None
    new_status = "rechazado"
    notification_payload = None

    if client_id is not None:
        notification_payload = {
            "cliente_id": client_id,
            "emergencia_id": report_id,
            "tipo": "emergency_rejected",
            "titulo": "Emergencia rechazada",
            "mensaje": f"Tu solicitud de emergencia fue rechazada. Motivo: {motivo}",
            "metadata": json.dumps(
                {
                    "emergencia_id": report_id,
                    "motivo": motivo,
                    "status": new_status,
                },
                ensure_ascii=False,
            ),
        }

    try:
        updated_report, created_notification = reject_emergency_report(
            report_id,
            rejection_reason=motivo,
            rejected_by_user_id=current_user.id,
            notification_payload=notification_payload,
            actor_role=current_user.role,
            source_app="web",
            endpoint=f"{settings.api_prefix}/emergencias/{{report_id}}/rechazar",
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not updated_report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

    push_sent = send_push_to_client(
        client_id,
        "Emergencia rechazada",
        f"Tu solicitud fue rechazada: {motivo}",
        {
            "type": "emergency_rejected",
            "emergency_id": str(report_id),
            "notification_type": "rejection",
        },
    )

    normalize_emergency_media_fields(updated_report)
    normalize_emergency_assignment_fields(updated_report)
    return EmergencyRejectResponse.model_validate(
        {
            **updated_report,
            "notification_created": created_notification is not None,
            "push_sent": push_sent,
        }
    )


@app.get(
    f"{settings.api_prefix}/emergencias/{{emergencia_id}}/tracking",
    response_model=EmergencyTrackingResponse,
)
def get_operational_emergency_tracking(
    emergencia_id: int,
    current_user: AuthenticatedUser = Security(require_roles(MECANICO_ROLE)),
) -> EmergencyTrackingResponse:
    ensure_operational_user_can_access_emergency_tracking(
        current_user=current_user,
        emergency_id=emergencia_id,
    )
    return get_emergency_tracking_response(emergency_id=emergencia_id)


@app.get(
    f"{settings.api_prefix}/emergencias/{{emergencia_id}}/historial",
    response_model=list[EmergencyHistoryItemResponse],
)
def get_emergency_history(
    emergencia_id: int,
    current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, MECANICO_ROLE)
    ),
) -> list[EmergencyHistoryItemResponse]:
    ensure_operational_user_can_access_emergency_tracking(
        current_user=current_user,
        emergency_id=emergencia_id,
    )
    try:
        rows = list_emergency_history(emergencia_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    return [EmergencyHistoryItemResponse.model_validate(row) for row in rows]


@app.get(
    f"{settings.api_prefix}/emergencias/{{report_id}}/recomendacion-ia",
    response_model=EmergencyAIRecommendationResponse,
)
def get_emergency_ai_recommendation_endpoint(
    report_id: int,
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> EmergencyAIRecommendationResponse:
    try:
        emergency = get_emergency_report_by_id(report_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not emergency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

    if not emergency.get("ia_categoria") or not emergency.get("ia_prioridad"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La emergencia aun no tiene clasificacion IA disponible.",
        )

    recommendation = build_ai_assignment_recommendation(emergency)
    stored_payload = {
        "emergencia_id": report_id,
        "categoria": recommendation.get("categoria"),
        "prioridad": recommendation.get("prioridad"),
        "especialidad_requerida": recommendation.get("especialidad_requerida"),
        "sucursal_recomendada_id": recommendation.get("sucursal_recomendada_id"),
        "mecanico_recomendado_id": recommendation.get("mecanico_recomendado_id"),
        "confidence": recommendation.get("confidence"),
    }

    try:
        stored = upsert_emergency_ai_recommendation(
            stored_payload,
            actor_user_id=None,
            actor_role="sistema",
            source_app="ai_assignment_service",
            endpoint=f"{settings.api_prefix}/emergencias/{{report_id}}/recomendacion-ia",
        )
        persisted = get_emergency_ai_recommendation(report_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    response_payload = {
        "categoria": recommendation.get("categoria"),
        "prioridad": recommendation.get("prioridad"),
        "especialidad_requerida": recommendation.get("especialidad_requerida"),
        "sucursal_recomendada_id": recommendation.get("sucursal_recomendada_id"),
        "sucursal_recomendada": (
            persisted.get("sucursal_recomendada_nombre")
            if persisted is not None
            else recommendation.get("sucursal_recomendada_nombre")
        ),
        "mecanico_recomendado_id": recommendation.get("mecanico_recomendado_id"),
        "mecanico_recomendado": (
            persisted.get("mecanico_recomendado_nombre")
            if persisted is not None
            else recommendation.get("mecanico_recomendado_nombre")
        ),
        "confidence": recommendation.get("confidence"),
        "mecanicos_recomendados": recommendation.get("mecanicos_recomendados") or [],
        "created_at": stored.get("created_at"),
    }
    return EmergencyAIRecommendationResponse.model_validate(response_payload)


@app.get(
    f"{settings.api_prefix}/audit",
    response_model=list[AuditLogItemResponse],
)
def get_audit_log(
    entity_type: str | None = Query(default=None, min_length=1, max_length=80),
    entity_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> list[AuditLogItemResponse]:
    try:
        rows = list_audit_logs(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
            offset=offset,
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    return [AuditLogItemResponse.model_validate(row) for row in rows]


@app.post(
    f"{settings.api_prefix}/emergencias/{{report_id}}/aceptar",
    response_model=EmergencyReportListResponse,
)
def accept_mecanico_assignment(
    report_id: int,
    current_user: AuthenticatedUser = Security(require_roles(MECANICO_ROLE)),
) -> EmergencyReportListResponse:
    context = get_emergency_tracking_context_or_404(report_id)
    mecanico_id = ensure_current_mecanico_is_assigned(
        current_user=current_user,
        context=context,
    )
    assignment_status = normalize_optional_text(str(context.get("assignment_status") or ""))
    if assignment_status not in {"asignado", "aceptado"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La asignación actual no puede ser aceptada.",
        )

    accepted_assignment = accept_emergency_mecanico_assignment(
        report_id,
        mecanico_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        source_app="mobile_mecanico",
        endpoint=f"{settings.api_prefix}/emergencias/{{report_id}}/aceptar",
    )
    if not accepted_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró una asignación vigente para aceptar.",
        )

    updated_report = get_emergency_report_by_id(report_id)
    if not updated_report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

    normalize_emergency_media_fields(updated_report)
    normalize_emergency_assignment_fields(updated_report)
    return EmergencyReportListResponse.model_validate(updated_report)


@app.put(
    f"{settings.api_prefix}/emergencias/{{report_id}}/mechanic-assignment",
    response_model=EmergencyReportListResponse,
)
@app.put(
    f"{settings.api_prefix}/emergencias/{{report_id}}/technician-assignment",
    response_model=EmergencyReportListResponse,
    include_in_schema=False,
)
def assign_mecanico_to_emergency(
    report_id: int,
    payload: EmergencyMecanicoAssignmentRequest,
    workshop_id: int = Query(ge=1),
    current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE)
    ),
) -> EmergencyReportListResponse:
    #
    # ============================================================
    # FLUJO IMPORTANTE: ADMIN O SECRETARIA ASIGNAN MECANICO A EMERGENCIA
    # Aqui se valida que la emergencia ya fue aceptada, que el
    # mecanico pertenezca al taller, a una sucursal activa y que este disponible.
    # Luego se guarda la asignacion y se notifica al cliente.
    # Palabras clave de busqueda:
    # - ASIGNAR MECANICO EMERGENCIA
    # - NOTIFICACION MECANICO ASIGNADO
    # - TRACKING DE EMERGENCIA
    # ============================================================
    #
    ensure_secretaria_can_manage_mecanico(
        current_user=current_user,
        mecanico_id=payload.mecanico_id,
        workshop_id=workshop_id if current_user.role != SECRETARIA_ROLE else None,
    )

    if current_user.role == WORKSHOP_ROLE and current_user.id != workshop_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes operar sobre un workshop_id distinto al de tu cuenta autenticada.",
        )

    scoped_secretaria_report = None
    scoped_operational_report = None
    report_scope_workshop_id: int | None = None
    effective_workshop_id = workshop_id

    try:
        if current_user.role == SECRETARIA_ROLE:
            scoped_secretaria_report = get_secretaria_scoped_emergency(
                current_user=current_user,
                report_id=report_id,
            )
            mecanico = get_mecanico_by_id(payload.mecanico_id)
            workshop_reports = []
            effective_workshop_id = (
                int(mecanico["workshop_id"]) if mecanico and mecanico.get("workshop_id") is not None else None
            )
        else:
            mecanico = get_mecanico_for_operational_scope(
                mecanico_id=payload.mecanico_id,
                operational_scope_id=workshop_id,
            )
            if current_user.role == PROTECTED_ADMIN_ROLE:
                scoped_operational_report = get_emergency_report_by_id(report_id)
            else:
                scoped_operational_report = get_emergency_report_for_operational_scope(
                    report_id=report_id,
                    scope_id=workshop_id,
                )
            effective_workshop_id = (
                int(mecanico["workshop_id"]) if mecanico and mecanico.get("workshop_id") is not None else None
            )
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not mecanico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mecánico no encontrado para este taller",
        )

    if current_user.role == SECRETARIA_ROLE:
        report = scoped_secretaria_report
    else:
        report = scoped_operational_report

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada o fuera del alcance permitido",
        )

    if (
        current_user.role != SECRETARIA_ROLE
        and report.get("nearest_workshop_id") is not None
        and int(report["nearest_workshop_id"]) == workshop_id
    ):
        report_scope_workshop_id = workshop_id

    # La secretaria ya queda limitada por su sucursal al elegir el mecanico destino.
    # No filtramos por la asignacion actual para permitir reasignaciones validas.

    if report.get("emergency_status") != "activo":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primero debes aceptar la emergencia para asignar un mecánico",
        )

    sucursal = ensure_mecanico_sucursal_activa(
        int(mecanico["sucursal_id"]) if mecanico.get("sucursal_id") is not None else None
    )
    current_assigned_mecanico_id = (
        report.get("assigned_mecanico_id")
        or report.get("assigned_mechanic_id")
        or report.get("assigned_technician_id")
    )
    estado_mecanico = str(mecanico.get("status"))
    if estado_mecanico != "disponible" and current_assigned_mecanico_id != payload.mecanico_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El mecánico seleccionado no está disponible",
        )

    notification_metadata = build_emergency_tracking_metadata(
        report_id=report_id,
        mecanico=mecanico,
        sucursal=sucursal,
        emergency_report=report,
    )
    notification_payload = {
        "cliente_id": int(report["client_id"]) if report.get("client_id") is not None else None,
        "emergencia_id": report_id,
        "tipo": "mechanic_assigned",
        "titulo": "Mecánico asignado",
        "mensaje": f"{str(mecanico.get('full_name') or '').strip() or 'Mecánico asignado'} fue asignado para auxiliarte.",
        "metadata": notification_metadata,
    }

    try:
        _assignment_row, _created_notification, assignment_changed = assign_emergency_mecanico_with_notification(
            report_id,
            effective_workshop_id,
            payload.mecanico_id,
            report_scope_workshop_id=report_scope_workshop_id,
            notification_payload=notification_payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            source_app="web",
            endpoint=f"{settings.api_prefix}/emergencias/{{report_id}}/mechanic-assignment",
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    updated_report = get_emergency_report_by_id(report_id)

    if not updated_report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

    normalize_emergency_media_fields(updated_report)

    if assignment_changed:
        push_data = build_push_data_from_metadata(
            notification_type="mechanic_assigned",
            metadata=notification_metadata,
        )
        send_push_to_client(
            int(updated_report["client_id"]) if updated_report.get("client_id") is not None else None,
            "Mecánico asignado",
            notification_payload["mensaje"],
            push_data,
        )

    normalize_emergency_assignment_fields(updated_report)
    return EmergencyReportListResponse.model_validate(updated_report)


@app.delete(
    f"{settings.api_prefix}/emergencias/{{report_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_emergency_report(
    report_id: int,
    workshop_id: int | None = Query(default=None, ge=1),
) -> None:
    try:
        deleted = delete_emergency_report(
            report_id,
            nearest_workshop_id=workshop_id,
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada o no pertenece al taller indicado",
        )


@app.get(
    f"{settings.api_prefix}/vehiculos",
    response_model=list[VehicleResponse],
)
def get_vehicles(
    client_id: int | None = Query(default=None, ge=1),
    current_user: AuthenticatedUser | None = Security(get_optional_current_active_user),
) -> list[VehicleResponse]:
    resolved_client_id = _resolve_client_scope(
        requested_client_id=client_id,
        current_user=current_user,
        operation_label="consultar vehículos",
    )
    try:
        rows = list_vehicles(resolved_client_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return [VehicleResponse.model_validate(row) for row in rows]


@app.put(
    f"{settings.api_prefix}/vehiculos/{{vehicle_id}}",
    response_model=VehicleResponse,
)
def edit_vehicle(
    vehicle_id: int,
    client_id: int | None = Form(default=None, ge=1),
    brand: str = Form(min_length=1, max_length=120),
    model: str = Form(min_length=1, max_length=120),
    year: int = Form(ge=1900, le=2100),
    plate: str = Form(min_length=3, max_length=40),
    color: str = Form(min_length=2, max_length=80),
    is_primary: bool = Form(default=False),
    photo: UploadFile | None = File(default=None),
    current_user: AuthenticatedUser | None = Security(get_optional_current_active_user),
) -> VehicleResponse:
    resolved_client_id = _resolve_client_scope(
        requested_client_id=client_id,
        current_user=current_user,
        operation_label="editar vehículos",
    )
    try:
        current_vehicle = get_vehicle_by_id(vehicle_id, resolved_client_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not current_vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")

    new_photo_path, new_photo_url = save_vehicle_photo(photo)
    photo_path = new_photo_path if new_photo_path is not None else current_vehicle.get("photo_path")
    photo_url = new_photo_url if new_photo_url is not None else current_vehicle.get("photo_url")

    vehicle_payload = {
        "client_id": resolved_client_id,
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

    if not updated:
        if new_photo_path is not None:
            remove_vehicle_photo(new_photo_path)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")

    if new_photo_path is not None:
        remove_vehicle_photo(str(current_vehicle.get("photo_path")) if current_vehicle.get("photo_path") else None)

    return VehicleResponse.model_validate(updated)


@app.delete(
    f"{settings.api_prefix}/vehiculos/{{vehicle_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_vehicle(
    vehicle_id: int,
    client_id: int | None = Query(default=None, ge=1),
    current_user: AuthenticatedUser | None = Security(get_optional_current_active_user),
) -> None:
    resolved_client_id = _resolve_client_scope(
        requested_client_id=client_id,
        current_user=current_user,
        operation_label="eliminar vehículos",
    )
    try:
        deleted = delete_vehicle(vehicle_id, resolved_client_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")

    remove_vehicle_photo(str(deleted.get("photo_path")) if deleted.get("photo_path") else None)


@app.get(
    f"{settings.api_prefix}/workshops",
    response_model=list[WorkshopRegistrationResponse],
)
def get_workshops(
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, WORKSHOP_ROLE)),
) -> list[WorkshopRegistrationResponse]:
    rows = list_workshop_registrations()
    return [WorkshopRegistrationResponse.model_validate(row) for row in rows]


@app.get(
    f"{settings.api_prefix}/sucursales",
    response_model=list[SucursalResponse],
)
def get_sucursales(
    estado: str | None = Query(default=None, pattern="^(ACTIVO|INACTIVO)$"),
    _current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE, MECANICO_ROLE)
    ),
) -> list[SucursalResponse]:
    rows = list_sucursales(estado=estado)
    return [SucursalResponse.model_validate(row) for row in rows]


@app.get(
    f"{settings.api_prefix}/secretarias",
    response_model=list[SecretariaResponse],
)
def get_secretarias(
    _current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)
    ),
) -> list[SecretariaResponse]:
    try:
        rows = list_secretarias()
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    return [SecretariaResponse.model_validate(row) for row in rows]


@app.get(
    f"{settings.api_prefix}/secretarias/{{secretaria_id}}",
    response_model=SecretariaResponse,
)
def get_secretaria(
    secretaria_id: int,
    _current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)
    ),
) -> SecretariaResponse:
    try:
        row = get_secretaria_by_id(secretaria_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secretaria no encontrada")
    return SecretariaResponse.model_validate(row)


@app.post(
    f"{settings.api_prefix}/secretarias",
    response_model=SecretariaResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_secretaria(
    payload: SecretariaCreate,
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE)),
) -> SecretariaResponse:
    try:
        sucursal = get_sucursal_by_id(payload.sucursal_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sucursal {payload.sucursal_id} no encontrada",
        )

    if str(sucursal.get("estado")) != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La sucursal debe estar ACTIVO para afiliar secretarias",
        )

    identity_card = f"SEC{secrets.token_hex(4).upper()}"

    try:
        created = create_secretaria(
            {
                "identity_card": identity_card,
                "full_name": payload.full_name,
                "email": str(payload.email).lower().strip(),
                "phone": payload.phone or "",
                "password_hash": hash_password(payload.password),
                "sucursal_id": payload.sucursal_id,
            }
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una secretaria con ese correo",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return SecretariaResponse.model_validate(created)


@app.put(
    f"{settings.api_prefix}/secretarias/{{secretaria_id}}",
    response_model=SecretariaResponse,
)
def edit_secretaria(
    secretaria_id: int,
    payload: SecretariaUpdate,
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE)),
) -> SecretariaResponse:
    try:
        sucursal = get_sucursal_by_id(payload.sucursal_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sucursal {payload.sucursal_id} no encontrada",
        )

    try:
        updated = update_secretaria(
            secretaria_id,
            {
                "full_name": payload.full_name,
                "phone": payload.phone or "",
                "password_hash": hash_password(payload.password) if payload.password else None,
                "sucursal_id": payload.sucursal_id,
            },
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una secretaria con ese correo",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secretaria no encontrada")

    return SecretariaResponse.model_validate(updated)


@app.patch(
    f"{settings.api_prefix}/secretarias/{{secretaria_id}}/estado",
    response_model=SecretariaResponse,
)
def patch_secretaria_estado(
    secretaria_id: int,
    payload: SecretariaEstadoUpdate,
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE)),
) -> SecretariaResponse:
    if payload.status == "activo":
        try:
            sec = get_secretaria_by_id(secretaria_id)
        except OperationalError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible",
            ) from exc
        if sec:
            suc = get_sucursal_by_id(int(sec["sucursal_id"]))
            if suc and str(suc.get("estado")) != "ACTIVO":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="La sucursal debe estar ACTIVO para activar la secretaria",
                )

    try:
        updated = update_secretaria_status(secretaria_id, payload.status)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secretaria no encontrada")

    return SecretariaResponse.model_validate(updated)


@app.delete(
    f"{settings.api_prefix}/secretarias/{{secretaria_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_secretaria(
    secretaria_id: int,
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE)),
) -> None:
    try:
        deleted = delete_secretaria(secretaria_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secretaria no encontrada")


@app.get(
    f"{settings.api_prefix}/mobile/sucursales",
    response_model=list[SucursalMobileResponse],
    tags=["mobile"],
)
def get_mobile_sucursales(
    _current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, CLIENT_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE, MECANICO_ROLE)
    ),
) -> list[SucursalMobileResponse]:
    try:
        rows = list_sucursales_for_mobile()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    return [SucursalMobileResponse.model_validate(row) for row in rows]


@app.get(
    f"{settings.api_prefix}/sucursales/{{sucursal_id}}",
    response_model=SucursalResponse,
)
def get_sucursal(
    sucursal_id: int,
    _current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE, MECANICO_ROLE)
    ),
) -> SucursalResponse:
    row = get_sucursal_by_id(sucursal_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    return SucursalResponse.model_validate(row)


@app.post(
    f"{settings.api_prefix}/sucursales",
    response_model=SucursalResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_sucursal(
    payload: SucursalCreate,
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> SucursalResponse:
    try:
        created = create_sucursal(payload.model_dump())
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una sucursal activa con el mismo nombre y dirección.",
        ) from exc
    return SucursalResponse.model_validate(created)


@app.put(
    f"{settings.api_prefix}/sucursales/{{sucursal_id}}",
    response_model=SucursalResponse,
)
def edit_sucursal(
    sucursal_id: int,
    payload: SucursalUpdate,
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> SucursalResponse:
    try:
        updated = update_sucursal(sucursal_id, payload.model_dump())
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una sucursal activa con el mismo nombre y dirección.",
        ) from exc

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")

    return SucursalResponse.model_validate(updated)


@app.patch(
    f"{settings.api_prefix}/sucursales/{{sucursal_id}}/estado",
    response_model=SucursalResponse,
)
def patch_sucursal_estado(
    sucursal_id: int,
    payload: SucursalEstadoUpdate,
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> SucursalResponse:
    updated = update_sucursal_estado(sucursal_id, payload.estado)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    return SucursalResponse.model_validate(updated)


@app.delete(
    f"{settings.api_prefix}/sucursales/{{sucursal_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_sucursal(
    sucursal_id: int,
    _current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> None:
    deleted = delete_sucursal(sucursal_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")


@app.post(f"{settings.api_prefix}/workshops/change-password")
def change_workshop_password(payload: WorkshopPasswordChangeRequest) -> dict[str, str]:
    normalized_email = payload.email.lower().strip()
    workshop = get_workshop_by_email(normalized_email)

    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    password_hash = workshop.get("password_hash")
    uses_initial_password = (
        isinstance(password_hash, str) and verify_password(settings.workshop_initial_password, password_hash)
    )
    accepts_missing_initial_password = not isinstance(password_hash, str) and (
        workshop["approval_status"] != "activo"
    )

    if not uses_initial_password and not accepts_missing_initial_password:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este taller ya no usa la contraseña temporal inicial",
        )

    updated = update_workshop_approval_status_with_password(
        int(workshop["id"]),
        "activo",
        hash_password(payload.new_password),
    )

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    return {"message": "La contraseña del taller fue actualizada correctamente"}


@app.api_route(f"{settings.api_prefix}/workshops/forgot-password", methods=["POST", "PUT"])
def forgot_workshop_password(payload: WorkshopForgotPasswordRequest) -> dict[str, str]:
    normalized_email = payload.email.lower().strip()
    workshop = get_workshop_by_email(normalized_email)

    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    if workshop["approval_status"] != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El taller todavía no fue habilitado por el administrador",
        )

    updated = update_workshop_password(int(workshop["id"]), hash_password(payload.new_password))

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    return {"message": "La contraseña del taller fue restablecida correctamente"}


@app.put(
    f"{settings.api_prefix}/workshops/{{workshop_id}}",
    response_model=WorkshopRegistrationResponse,
)
def edit_workshop(workshop_id: int, payload: WorkshopRegistrationUpdate) -> WorkshopRegistrationResponse:
    updated = update_workshop_registration(
        workshop_id,
        {
            **payload.model_dump(exclude={"password"}),
            "approval_status": None,
            "password_hash": hash_password(payload.password) if payload.password else None,
        },
    )

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    return WorkshopRegistrationResponse.model_validate(updated)


@app.put(
    f"{settings.api_prefix}/workshops/{{workshop_id}}/approval-status",
    response_model=WorkshopRegistrationResponse,
)
def edit_workshop_approval_status(
    workshop_id: int,
    payload: WorkshopApprovalStatusUpdate,
) -> WorkshopRegistrationResponse:
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

    password_hash = hash_password(settings.workshop_initial_password) if next_status == "activo" else None
    updated = update_workshop_approval_status_with_password(
        workshop_id,
        next_status,
        password_hash,
    )

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    return WorkshopRegistrationResponse.model_validate(updated)


@app.delete(
    f"{settings.api_prefix}/workshops/{{workshop_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_workshop(workshop_id: int) -> None:
    deleted = delete_workshop_registration(workshop_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")


@app.post(
    f"{settings.api_prefix}/clientes",
    response_model=ClientRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_client(payload: ClientRegistrationCreate) -> ClientRegistrationResponse:
    normalized_email = payload.email.lower().strip()

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

    client_payload = {
        "identity_card": payload.identity_card,
        "full_name": payload.full_name,
        "email": normalized_email,
        "phone": payload.phone,
        "password_hash": hash_password(payload.password),
        "role": _normalize_role_name(payload.role),
        "status": "active",
        "accepted_terms": payload.accepted_terms,
    }

    try:
        created = create_client(client_payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese carnet o correo",
        ) from exc

    return ClientRegistrationResponse.model_validate(created)


@app.get(
    f"{settings.api_prefix}/clientes",
    response_model=list[ClientRegistrationResponse],
)
def get_clients(
    _current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE)
    ),
) -> list[ClientRegistrationResponse]:
    rows = list_clients()
    return [ClientRegistrationResponse.model_validate(row) for row in rows]


@app.post(f"{settings.api_prefix}/clientes/change-password")
def change_client_password(payload: ClientPasswordChangeRequest) -> dict[str, str]:
    normalized_email = payload.email.lower().strip()
    client = get_client_by_email(normalized_email)

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    if client["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta suspendida",
        )

    password_hash = client.get("password_hash")
    if not isinstance(password_hash, str) or not verify_password(payload.current_password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña actual es incorrecta",
        )

    updated = update_client_password(int(client["id"]), hash_password(payload.new_password))

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    return {"message": "La contraseña del cliente fue actualizada correctamente"}


@app.api_route(f"{settings.api_prefix}/clientes/forgot-password", methods=["POST", "PUT"])
def forgot_client_password(payload: ClientForgotPasswordRequest) -> dict[str, str]:
    normalized_email = payload.email.lower().strip()
    client = get_client_by_email(normalized_email)

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    if client["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta suspendida",
        )

    updated = update_client_password(int(client["id"]), hash_password(payload.new_password))

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    return {"message": "La contraseña del cliente fue restablecida correctamente"}


@app.put(
    f"{settings.api_prefix}/clientes/{{client_id}}/status",
    response_model=ClientRegistrationResponse,
)
def edit_client_status(client_id: int, payload: ClientStatusUpdate) -> ClientRegistrationResponse:
    updated = update_client_status(client_id, payload.status)

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    return ClientRegistrationResponse.model_validate(updated)


@app.put(
    f"{settings.api_prefix}/clientes/{{client_id}}",
    response_model=ClientRegistrationResponse,
)
def edit_client(client_id: int, payload: ClientUpdate) -> ClientRegistrationResponse:
    normalized_email = payload.email.lower().strip()

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

    client_payload = {
        "identity_card": payload.identity_card,
        "full_name": payload.full_name,
        "email": normalized_email,
        "phone": payload.phone,
        "password_hash": hash_password(payload.password) if payload.password else None,
        "role": _normalize_role_name(payload.role),
        "status": payload.status,
        "accepted_terms": payload.accepted_terms,
    }

    try:
        updated = update_client(client_id, client_payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese carnet o correo",
        ) from exc

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    return ClientRegistrationResponse.model_validate(updated)


@app.delete(
    f"{settings.api_prefix}/clientes/{{client_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_client(client_id: int) -> None:
    deleted = delete_client(client_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")


@app.post(
    f"{settings.api_prefix}/auth/login",
    response_model=LoginResponse,
    response_model_exclude_none=True,
)
def login(payload: LoginRequest) -> LoginResponse:
    normalized_email = payload.email.lower().strip()
    requested_account_type = payload.account_type

    if is_protected_admin_email(normalized_email):
        ensure_login_not_locked(PROTECTED_ADMIN_ROLE, normalized_email)

        if requested_account_type and requested_account_type != PROTECTED_ADMIN_ROLE:
            register_failed_login_attempt(PROTECTED_ADMIN_ROLE, normalized_email)

        if payload.password != settings.protected_admin_password:
            register_failed_login_attempt(PROTECTED_ADMIN_ROLE, normalized_email)

        reset_login_attempts(PROTECTED_ADMIN_ROLE, normalized_email)
        return LoginResponse(
            id=PROTECTED_ADMIN_ID,
            email=PROTECTED_ADMIN_EMAIL,
            full_name=settings.protected_admin_full_name,
            phone=settings.protected_admin_phone,
            role=PROTECTED_ADMIN_ROLE,
            status="active",
            requires_password_change=False,
            access_token=create_access_token(
                subject=str(PROTECTED_ADMIN_ID),
                role=PROTECTED_ADMIN_ROLE,
                email=PROTECTED_ADMIN_EMAIL,
            ),
            token_type="Bearer",
        )

    workshop = get_workshop_by_email(normalized_email)

    if workshop:
        ensure_login_not_locked(WORKSHOP_ROLE, normalized_email)

        if requested_account_type and requested_account_type != WORKSHOP_ROLE:
            register_failed_login_attempt(WORKSHOP_ROLE, normalized_email)

        password_hash = workshop.get("password_hash")
        uses_initial_password = (
            isinstance(password_hash, str) and verify_password(settings.workshop_initial_password, password_hash)
        )
        accepts_missing_initial_password = (
            not isinstance(password_hash, str)
            and workshop["approval_status"] != "activo"
            and payload.password == settings.workshop_initial_password
        )

        if not accepts_missing_initial_password and (
            not isinstance(password_hash, str) or not verify_password(payload.password, password_hash)
        ):
            register_failed_login_attempt(WORKSHOP_ROLE, normalized_email)

        if uses_initial_password or accepts_missing_initial_password:
            reset_login_attempts(WORKSHOP_ROLE, normalized_email)
            return LoginResponse(
                id=int(workshop["id"]),
                email=str(workshop["email"]),
                role=WORKSHOP_ROLE,
                status=workshop_login_status(workshop["approval_status"]),
                requires_password_change=True,
            )

        if workshop["approval_status"] != "activo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El taller todavía no fue habilitado por el administrador",
            )

        reset_login_attempts(WORKSHOP_ROLE, normalized_email)
        return LoginResponse(
            id=int(workshop["id"]),
            email=str(workshop["email"]),
            full_name=str(workshop["workshop_name"]),
            phone=str(workshop["phone"]),
            role=WORKSHOP_ROLE,
            status=workshop_login_status(workshop["approval_status"]),
            requires_password_change=False,
            access_token=create_access_token(
                subject=str(workshop["id"]),
                role=WORKSHOP_ROLE,
                email=str(workshop["email"]),
            ),
            token_type="Bearer",
        )

    client = get_client_by_email(normalized_email)

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

    return LoginResponse(
        id=int(client["id"]),
        email=str(client["email"]),
        full_name=str(client["full_name"]),
        phone=str(client["phone"]),
            role=_normalize_role_name(str(client["role"])),
            status=str(client["status"]),
            requires_password_change=False,
            access_token=create_access_token(
                subject=str(client["id"]),
                role=_normalize_role_name(str(client["role"])),
                email=str(client["email"]),
            ),
            token_type="Bearer",
        )


@app.post(
    f"{settings.api_prefix}/auth/account-type",
    response_model=AccountTypeLookupResponse,
)
def lookup_account_type(payload: AccountTypeLookupRequest) -> AccountTypeLookupResponse:
    normalized_email = payload.email.lower().strip()

    workshop = get_workshop_by_email(normalized_email)
    if workshop:
        return AccountTypeLookupResponse(role=WORKSHOP_ROLE)

    client = get_client_by_email(normalized_email)
    if client:
        return AccountTypeLookupResponse(role=_normalize_role_name(str(client["role"])))

    return AccountTypeLookupResponse(role=None)


@app.api_route(f"{settings.api_prefix}/auth/forgot-password", methods=["POST", "PUT"])
def forgot_password(payload: UnifiedForgotPasswordRequest) -> dict[str, str]:
    #
    # ============================================================
    # FLUJO IMPORTANTE: RECUPERACION UNIFICADA DE CONTRASENA
    # Aqui el backend decide automaticamente si el correo pertenece
    # a cliente o taller y ejecuta el reseteo correcto.
    # Palabras clave de busqueda:
    # - FORGOT PASSWORD UNIFICADO
    # - RECUPERACION UNIFICADA
    # ============================================================
    #
    normalized_email = payload.email.lower().strip()

    client = get_client_by_email(normalized_email)
    if client:
        if client["status"] != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cuenta suspendida",
            )

        updated = update_client_password(int(client["id"]), hash_password(payload.new_password))

        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

        return {"message": "La contraseña del cliente fue restablecida correctamente"}

    workshop = get_workshop_by_email(normalized_email)
    if workshop:
        if workshop["approval_status"] != "activo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El taller todavía no fue habilitado por el administrador",
            )

        updated = update_workshop_password(int(workshop["id"]), hash_password(payload.new_password))

        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

        return {"message": "La contraseña del taller fue restablecida correctamente"}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe una cuenta con ese correo")


@app.post(
    f"{settings.api_prefix}/mecanicos",
    response_model=MecanicoResponse,
    status_code=status.HTTP_201_CREATED,
)
@app.post(
    f"{settings.api_prefix}/technicians",
    response_model=MecanicoResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def register_mecanico(
    payload: MecanicoCreate,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE)
    ),
) -> MecanicoResponse:
    secretaria = get_secretaria_scope(current_user)
    if secretaria and payload.sucursal_id != int(secretaria["sucursal_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes crear mecánicos afiliados a tu propia sucursal.",
        )

    target_workshop_id = workshop_id or payload.workshop_id
    ensure_mecanico_sucursal_activa(payload.sucursal_id)
    mecanico_payload = _build_mecanico_write_payload(payload, workshop_id=target_workshop_id)
    try:
        created = create_or_link_mecanico(mecanico_payload)
    except ValueError as exc:
        _raise_mecanico_write_error(exc)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo crear o vincular el perfil del mecánico",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    return MecanicoResponse.model_validate(created)


@app.get(
    f"{settings.api_prefix}/mecanicos",
    response_model=list[MecanicoResponse],
)
@app.get(
    f"{settings.api_prefix}/technicians",
    response_model=list[MecanicoResponse],
    include_in_schema=False,
)
def get_mecanicos(
    workshop_id: int | None = Query(default=None, ge=1),
    _current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE)
    ),
) -> list[MecanicoResponse]:
    rows = list_mecanicos_by_workshop(workshop_id) if workshop_id else list_mecanicos()
    secretaria = get_secretaria_scope(_current_user)
    if secretaria:
        scope_sucursal_id = int(secretaria["sucursal_id"])
        rows = [row for row in rows if int(row.get("sucursal_id") or 0) == scope_sucursal_id]
    return [MecanicoResponse.model_validate(row) for row in rows]


@app.put(
    f"{settings.api_prefix}/mecanicos/{{mecanico_id}}",
    response_model=MecanicoResponse,
)
@app.put(
    f"{settings.api_prefix}/technicians/{{mecanico_id}}",
    response_model=MecanicoResponse,
    include_in_schema=False,
)
def edit_mecanico(
    mecanico_id: int,
    payload: MecanicoCreate,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE)
    ),
) -> MecanicoResponse:
    ensure_secretaria_can_manage_mecanico(
        current_user=current_user,
        mecanico_id=mecanico_id,
        workshop_id=workshop_id,
    )
    secretaria = get_secretaria_scope(current_user)
    if secretaria and payload.sucursal_id != int(secretaria["sucursal_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes asignar mecánicos a tu propia sucursal.",
        )

    ensure_mecanico_sucursal_activa(payload.sucursal_id)
    mecanico_payload = _build_mecanico_write_payload(payload, workshop_id=workshop_id or payload.workshop_id)
    try:
        updated = update_mecanico_profile(
            mecanico_id,
            mecanico_payload,
            workshop_id=workshop_id,
        )
    except ValueError as exc:
        _raise_mecanico_write_error(exc)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo actualizar el perfil del mecánico",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mecánico no encontrado")

    return MecanicoResponse.model_validate(updated)


@app.delete(
    f"{settings.api_prefix}/mecanicos/{{mecanico_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@app.delete(
    f"{settings.api_prefix}/technicians/{{mecanico_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
def remove_mecanico(
    mecanico_id: int,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE)
    ),
) -> None:
    ensure_secretaria_can_manage_mecanico(
        current_user=current_user,
        mecanico_id=mecanico_id,
        workshop_id=workshop_id,
    )
    deleted = (
        delete_mecanico_for_workshop(mecanico_id, workshop_id)
        if workshop_id
        else delete_mecanico(mecanico_id)
    )

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mecánico no encontrado")
