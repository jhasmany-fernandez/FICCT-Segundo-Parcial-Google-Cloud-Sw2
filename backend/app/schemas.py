from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, model_validator


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


class MecanicoBase(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    phone: str = Field(min_length=7, max_length=40)
    email: EmailStr
    specialty: str = Field(min_length=2, max_length=120)
    status: str = Field(pattern="^(disponible|ocupado|fuera_de_servicio)$")


class MecanicoCreate(MecanicoBase):
    workshop_id: int | None = Field(default=None, ge=1)
    sucursal_id: int | None = Field(default=None, ge=1)


class MecanicoResponse(MecanicoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workshop_id: int | None = None
    sucursal_id: int | None = None
    sucursal_nombre: str | None = None
    sucursal_zona: str | None = None
    sucursal_direccion: str | None = None
    created_at: datetime
    updated_at: datetime


# Legacy schema aliases preserved for backward compatibility.
# Prefer MecanicoBase/MecanicoCreate/MecanicoResponse in new code.
TechnicianBase = MecanicoBase
TechnicianCreate = MecanicoCreate
TechnicianResponse = MecanicoResponse


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


class LoginResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone: str
    role: str
    status: str
    access_token: str | None = None
    token_type: str | None = None


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
