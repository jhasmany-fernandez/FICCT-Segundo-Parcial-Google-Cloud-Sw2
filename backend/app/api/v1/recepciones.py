from datetime import UTC, datetime
import math
import secrets

from fastapi import APIRouter, HTTPException, Query, Security, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import settings
from app.constants import MECANICO_ROLE, PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE
from app.core.dependencies import AuthenticatedUser, get_current_active_user, require_roles
from app.db import (
    create_client_notification,
    create_client_notifications,
    create_recepcion_diagnostic,
    create_recepcion_observation,
    deliver_recepcion_work,
    create_recepcion_record,
    finalize_recepcion_work,
    get_client_by_id,
    get_active_recepcion_by_emergency_id,
    get_emergency_report_by_id,
    get_emergency_tracking_context,
    get_mecanico_by_cliente_id,
    get_recepcion_record_by_id,
    get_recepcion_record_by_emergency_id,
    get_recepcion_status_by_id,
    get_secretaria_by_cliente_id,
    list_assignable_mecanicos,
    list_mecanicos,
    list_recepcion_records,
    list_sucursales,
    update_recepcion_record,
)
from app.notifications import send_push_to_client
from app.security import normalize_email, normalize_optional_text, normalize_plate


router = APIRouter(prefix=settings.api_prefix, tags=["recepciones"])

ALLOWED_RECEPCION_STATUS = {
    "registrada",
    "en_diagnostico",
    "en_trabajo",
    "finalizada",
    "entregada",
}
ALLOWED_FUEL_LEVELS = {"vacio", "1/4", "1/2", "3/4", "lleno"}
ALLOWED_REPORTED_BY = {"cliente", "secretaria"}
ALLOWED_PROBLEM_PRIORITY = {"baja", "media", "alta"}
ALLOWED_WORK_STATUS = {"pendiente", "en_proceso", "pausado", "completado"}


def _notification_push_data(notification_type: str, metadata: dict[str, object]) -> dict[str, str]:
    payload = {"type": notification_type}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, bool):
            payload[key] = "true" if value else "false"
            continue
        payload[key] = str(value)
    return payload


def _notify_client_operational_event(
    *,
    client_id: int | None,
    emergency_id: int | None,
    notification_type: str,
    title: str,
    message: str,
    metadata: dict[str, object],
) -> None:
    if client_id is None:
        return

    create_client_notification(
        {
            "cliente_id": client_id,
            "emergencia_id": emergency_id,
            "tipo": notification_type,
            "titulo": title,
            "mensaje": message,
            "metadata": metadata,
        }
    )
    send_push_to_client(
        client_id,
        title,
        message,
        _notification_push_data(notification_type, metadata),
    )


class RecepcionClientePayload(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    identity_card: str = Field(min_length=5, max_length=40)
    phone: str = Field(min_length=7, max_length=40)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    mobile_client_id: int | None = Field(default=None, ge=1)


class RecepcionVehiculoPayload(BaseModel):
    plate: str = Field(min_length=3, max_length=40)
    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    year: int = Field(ge=1900, le=2100)
    color: str = Field(min_length=2, max_length=80)
    vin: str | None = Field(default=None, max_length=80)
    engine_number: str | None = Field(default=None, max_length=80)


class RecepcionFichaPayload(BaseModel):
    codigo_ficha: str | None = Field(default=None, min_length=6, max_length=40)
    emergencia_id: int | None = Field(default=None, ge=1)
    status: str = Field(default="registrada")
    fecha_recepcion: datetime | None = None
    kilometraje: int | None = Field(default=None, ge=0)
    nivel_combustible: str | None = None
    assigned_mechanic_id: int | None = Field(default=None, ge=1)
    observaciones_generales: str | None = None


class RecepcionAccesorioPayload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: int = Field(default=1, gt=0)
    notes: str | None = Field(default=None, max_length=255)


class RecepcionProblemaPayload(BaseModel):
    description: str = Field(min_length=3)
    priority: str | None = None
    reported_by: str


class RecepcionCreateRequest(BaseModel):
    cliente: RecepcionClientePayload
    vehiculo: RecepcionVehiculoPayload
    ficha: RecepcionFichaPayload
    accesorios: list[RecepcionAccesorioPayload] = Field(default_factory=list)
    problemas: list[RecepcionProblemaPayload] = Field(default_factory=list)


class RecepcionUpdateRequest(RecepcionCreateRequest):
    pass


class DiagnosticoCreateRequest(BaseModel):
    diagnostic_text: str = Field(min_length=3)
    estimated_work: str | None = None
    estimated_cost: float | None = Field(default=None, ge=0)


class ObservacionCreateRequest(BaseModel):
    observation_text: str = Field(min_length=3)
    work_status: str | None = None


class RecepcionAccesorioResponse(BaseModel):
    id: int
    ficha_id: int
    name: str
    quantity: int
    notes: str | None = None


class RecepcionProblemaResponse(BaseModel):
    id: int
    ficha_id: int
    description: str
    priority: str | None = None
    reported_by: str
    created_at: datetime


class RecepcionDiagnosticoResponse(BaseModel):
    id: int
    ficha_id: int
    mechanic_id: int
    diagnostic_text: str
    estimated_work: str | None = None
    estimated_cost: float | None = None
    created_at: datetime
    updated_at: datetime
    mechanic_name: str | None = None


class RecepcionObservacionResponse(BaseModel):
    id: int
    ficha_id: int
    mechanic_id: int
    observation_text: str
    work_status: str | None = None
    created_at: datetime
    mechanic_name: str | None = None


class RecepcionClienteResponse(BaseModel):
    id: int
    full_name: str
    identity_card: str
    phone: str
    email: str | None = None
    address: str | None = None
    mobile_client_id: int | None = None


class RecepcionVehiculoResponse(BaseModel):
    id: int
    plate: str
    brand: str
    model: str
    year: int
    color: str
    vin: str | None = None
    engine_number: str | None = None


class RecepcionFichaMetaResponse(BaseModel):
    codigo_ficha: str
    emergencia_id: int | None = None
    status: str
    fecha_recepcion: datetime
    kilometraje: int | None = None
    nivel_combustible: str | None = None
    recepcionado_por_user_id: int
    recepcionado_por_role: str
    assigned_mechanic_id: int | None = None
    assigned_mechanic_name: str | None = None
    observaciones_generales: str | None = None
    finalized_at: datetime | None = None
    delivered_at: datetime | None = None
    delivered_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime


class RecepcionRecordResponse(BaseModel):
    id: int
    codigo_ficha: str
    status: str
    fecha_recepcion: datetime
    finalized_at: datetime | None = None
    delivered_at: datetime | None = None
    delivered_by_user_id: int | None = None
    cliente: RecepcionClienteResponse
    vehiculo: RecepcionVehiculoResponse
    ficha: RecepcionFichaMetaResponse
    accesorios: list[RecepcionAccesorioResponse]
    problemas: list[RecepcionProblemaResponse]
    diagnosticos: list[RecepcionDiagnosticoResponse]
    observaciones: list[RecepcionObservacionResponse]


class RecepcionListItemResponse(BaseModel):
    id: int
    codigo_ficha: str
    emergencia_id: int | None = None
    status: str
    fecha_recepcion: datetime
    client_full_name: str
    client_identity_card: str
    client_phone: str
    client_email: str | None = None
    plate: str
    vehicle_label: str
    finalized_at: datetime | None = None
    delivered_at: datetime | None = None
    delivered_by_user_id: int | None = None
    assigned_mechanic_id: int | None = None
    assigned_mechanic_name: str | None = None
    updated_at: datetime


class RecepcionListResponse(BaseModel):
    items: list[RecepcionListItemResponse]
    total: int
    limit: int
    offset: int


class RecepcionEstadoResponse(BaseModel):
    ficha_id: int
    codigo_ficha: str
    status: str
    vehicle: str
    plate: str
    last_diagnostic: str | None = None
    last_observation: str | None = None
    finalized_at: datetime | None = None
    delivered_at: datetime | None = None
    delivered_by_user_id: int | None = None
    updated_at: datetime


class RecepcionCreatedResponse(BaseModel):
    id: int
    codigo_ficha: str
    emergencia_id: int | None = None
    status: str
    cliente_id: int
    vehiculo_id: int
    fecha_recepcion: datetime
    assigned_mechanic_id: int | None = None
    created_at: datetime


class RecepcionMechanicOptionResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str
    status: str


class FichaRecepcionCreateRequest(BaseModel):
    cliente_id: int | None = Field(default=None, ge=1)
    emergencia_id: int | None = Field(default=None, ge=1)
    recibido_por_id: int | None = Field(default=None, ge=1)
    vehiculo: str | None = Field(default=None, max_length=240)
    placa: str | None = Field(default=None, max_length=40)
    marca: str | None = Field(default=None, max_length=120)
    modelo: str | None = Field(default=None, max_length=120)
    anio: int | None = Field(default=None, ge=1900, le=2100)
    problema_reportado: str = Field(min_length=3)
    accesorios_recibidos: str | None = None
    observaciones: str | None = None
    assigned_mechanic_id: int | None = Field(default=None, ge=1)


class FichaRecepcionListItemResponse(BaseModel):
    id: int
    cliente_id: int | None = None
    emergencia_id: int | None = None
    codigo_ficha: str
    estado: str
    vehiculo: str
    placa: str | None = None
    problema_reportado: str
    fecha_ingreso: datetime
    finalized_at: datetime | None = None
    delivered_at: datetime | None = None
    delivered_by_user_id: int | None = None
    assigned_mechanic_id: int | None = None
    assigned_mechanic_name: str | None = None
    created_at: datetime
    updated_at: datetime


class FichaRecepcionDetailResponse(BaseModel):
    id: int
    cliente_id: int | None = None
    emergencia_id: int | None = None
    recibido_por_id: int | None = None
    codigo_ficha: str
    estado: str
    vehiculo: str
    placa: str | None = None
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = None
    problema_reportado: str
    accesorios_recibidos: str | None = None
    observaciones: str | None = None
    fecha_ingreso: datetime
    finalized_at: datetime | None = None
    delivered_at: datetime | None = None
    delivered_by_user_id: int | None = None
    assigned_mechanic_id: int | None = None
    assigned_mechanic_name: str | None = None
    created_at: datetime
    updated_at: datetime


class RecepcionFinalizeRequest(BaseModel):
    admin_override: bool = False


def _generate_codigo_ficha() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"REC-{timestamp}-{secrets.token_hex(2).upper()}"


def _ensure_allowed_value(value: str | None, allowed_values: set[str], field_name: str) -> None:
    if value is None:
        return

    if value not in allowed_values:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Valor inválido para {field_name}",
        )


def _ensure_client_exists_with_role(client_id: int, *, expected_role: str | None = None) -> dict[str, object]:
    client = get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if expected_role and str(client.get("role", "")).lower().strip() != expected_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El usuario indicado no tiene rol {expected_role}",
        )

    if str(client.get("status", "")).lower().strip() != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cuenta del usuario indicado no está activa",
        )

    return client


def _normalize_cliente_payload(payload: RecepcionClientePayload) -> dict[str, object]:
    mobile_client_id = payload.mobile_client_id
    if mobile_client_id is not None:
        _ensure_client_exists_with_role(mobile_client_id, expected_role="client")

    return {
        "full_name": payload.full_name.strip(),
        "identity_card": payload.identity_card.strip(),
        "phone": payload.phone.strip(),
        "email": normalize_email(str(payload.email)) if payload.email is not None else None,
        "address": normalize_optional_text(payload.address),
        "mobile_client_id": mobile_client_id,
    }


def _normalize_vehiculo_payload(payload: RecepcionVehiculoPayload) -> dict[str, object]:
    return {
        "plate": normalize_plate(payload.plate),
        "brand": payload.brand.strip(),
        "model": payload.model.strip(),
        "year": payload.year,
        "color": payload.color.strip(),
        "vin": normalize_optional_text(payload.vin),
        "engine_number": normalize_optional_text(payload.engine_number),
    }


def _normalize_ficha_payload(
    payload: RecepcionFichaPayload,
    *,
    current_user: AuthenticatedUser,
    keep_original_recepcionista: bool = False,
    existing_codigo_ficha: str | None = None,
) -> dict[str, object]:
    _ensure_allowed_value(payload.status, ALLOWED_RECEPCION_STATUS, "status")
    _ensure_allowed_value(payload.nivel_combustible, ALLOWED_FUEL_LEVELS, "nivel_combustible")

    if payload.emergencia_id is not None and not get_emergency_report_by_id(payload.emergencia_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

    if payload.assigned_mechanic_id is not None:
        _ensure_client_exists_with_role(payload.assigned_mechanic_id, expected_role=MECANICO_ROLE)

    normalized = {
        "codigo_ficha": (payload.codigo_ficha or existing_codigo_ficha or _generate_codigo_ficha()).strip().upper(),
        "emergencia_id": payload.emergencia_id,
        "status": payload.status,
        "fecha_recepcion": payload.fecha_recepcion,
        "finalized_at": None,
        "delivered_at": None,
        "delivered_by_user_id": None,
        "kilometraje": payload.kilometraje,
        "nivel_combustible": payload.nivel_combustible,
        "assigned_mechanic_id": payload.assigned_mechanic_id,
        "observaciones_generales": normalize_optional_text(payload.observaciones_generales),
    }

    if keep_original_recepcionista:
        return normalized

    return {
        **normalized,
        "recepcionado_por_user_id": current_user.id,
        "recepcionado_por_role": current_user.role,
    }


def _list_assignable_mechanics(current_user: AuthenticatedUser) -> list[RecepcionMechanicOptionResponse]:
    secretaria_sucursal_id: int | None = None
    if current_user.role == SECRETARIA_ROLE:
        secretaria = get_secretaria_by_cliente_id(current_user.id)
        if not secretaria:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La secretaria autenticada no tiene una sucursal afiliada configurada.",
            )
        secretaria_sucursal_id = int(secretaria["sucursal_id"])

    mechanic_users = [
        RecepcionMechanicOptionResponse(
            id=int(row["cliente_id"]),
            full_name=str(row["full_name"]),
            email=str(row["email"]),
            phone=str(row["phone"]),
            status=str(row["status"]),
        )
        for row in list_assignable_mecanicos(secretaria_sucursal_id)
    ]

    return sorted(mechanic_users, key=lambda item: (item.full_name.casefold(), item.id))


def _ensure_linked_mecanico_profile(cliente_id: int) -> None:
    try:
        linked_profile = get_mecanico_by_cliente_id(cliente_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if linked_profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta autenticada no tiene un perfil de mecánico vinculado.",
        )


def _normalize_accessories(items: list[RecepcionAccesorioPayload]) -> list[dict[str, object]]:
    return [
        {
            "name": item.name.strip(),
            "quantity": item.quantity,
            "notes": normalize_optional_text(item.notes),
        }
        for item in items
    ]


def _normalize_problems(items: list[RecepcionProblemaPayload]) -> list[dict[str, object]]:
    normalized_items: list[dict[str, object]] = []
    for item in items:
        _ensure_allowed_value(item.priority, ALLOWED_PROBLEM_PRIORITY, "priority")
        _ensure_allowed_value(item.reported_by, ALLOWED_REPORTED_BY, "reported_by")
        normalized_items.append(
            {
                "description": item.description.strip(),
                "priority": item.priority,
                "reported_by": item.reported_by,
            }
        )
    return normalized_items


def _build_recepcion_detail_response(detail: dict[str, object]) -> dict[str, object]:
    return {
        "id": detail["id"],
        "codigo_ficha": detail["codigo_ficha"],
        "status": detail["status"],
        "fecha_recepcion": detail["fecha_recepcion"],
        "finalized_at": detail.get("finalized_at"),
        "delivered_at": detail.get("delivered_at"),
        "delivered_by_user_id": detail.get("delivered_by_user_id"),
        "cliente": {
            "id": detail["reception_client_id"],
            "full_name": detail["client_full_name"],
            "identity_card": detail["client_identity_card"],
            "phone": detail["client_phone"],
            "email": detail.get("client_email"),
            "address": detail.get("client_address"),
            "mobile_client_id": detail.get("mobile_client_id"),
        },
        "vehiculo": {
            "id": detail["vehicle_id"],
            "plate": detail["plate"],
            "brand": detail["brand"],
            "model": detail["model"],
            "year": detail["year"],
            "color": detail["color"],
            "vin": detail.get("vin"),
            "engine_number": detail.get("engine_number"),
        },
        "ficha": {
            "codigo_ficha": detail["codigo_ficha"],
            "emergencia_id": detail.get("emergencia_id"),
            "status": detail["status"],
            "fecha_recepcion": detail["fecha_recepcion"],
            "kilometraje": detail.get("kilometraje"),
            "nivel_combustible": detail.get("nivel_combustible"),
            "recepcionado_por_user_id": detail["recepcionado_por_user_id"],
            "recepcionado_por_role": detail["recepcionado_por_role"],
            "assigned_mechanic_id": detail.get("assigned_mechanic_id"),
            "assigned_mechanic_name": detail.get("assigned_mechanic_name"),
            "observaciones_generales": detail.get("observaciones_generales"),
            "finalized_at": detail.get("finalized_at"),
            "delivered_at": detail.get("delivered_at"),
            "delivered_by_user_id": detail.get("delivered_by_user_id"),
            "created_at": detail["created_at"],
            "updated_at": detail["updated_at"],
        },
        "accesorios": detail.get("accesorios", []),
        "problemas": detail.get("problemas", []),
        "diagnosticos": detail.get("diagnosticos", []),
        "observaciones": detail.get("observaciones", []),
    }


def _compose_vehicle_label(detail: dict[str, object]) -> str:
    explicit_label = normalize_optional_text(
        " ".join(
            [
                str(detail.get("brand") or "").strip(),
                str(detail.get("model") or "").strip(),
                str(detail.get("year") or "").strip(),
            ]
        )
    )
    return explicit_label or "Vehículo no especificado"


def _compose_problem_report(detail: dict[str, object]) -> str:
    problems = detail.get("problemas") or []
    if problems:
        first_problem = problems[0]
        return str(first_problem.get("description") or "").strip()
    return "Sin problema reportado"


def _compose_accessories_text(detail: dict[str, object]) -> str | None:
    accessories = detail.get("accesorios") or []
    if not accessories:
        return None

    parts: list[str] = []
    for item in accessories:
        name = str(item.get("name") or "").strip()
        quantity = int(item.get("quantity") or 1)
        notes = normalize_optional_text(item.get("notes"))
        piece = f"{name} x{quantity}" if name else f"Item x{quantity}"
        if notes:
            piece = f"{piece} ({notes})"
        parts.append(piece)

    return ", ".join(parts) if parts else None


def _build_ficha_recepcion_response(detail: dict[str, object]) -> FichaRecepcionDetailResponse:
    return FichaRecepcionDetailResponse(
        id=int(detail["id"]),
        cliente_id=detail.get("mobile_client_id"),
        emergencia_id=detail.get("emergencia_id"),
        recibido_por_id=int(detail["recepcionado_por_user_id"]),
        codigo_ficha=str(detail["codigo_ficha"]),
        estado=str(detail["status"]),
        vehiculo=_compose_vehicle_label(detail),
        placa=normalize_optional_text(detail.get("plate")),
        marca=normalize_optional_text(detail.get("brand")),
        modelo=normalize_optional_text(detail.get("model")),
        anio=detail.get("year"),
        problema_reportado=_compose_problem_report(detail),
        accesorios_recibidos=_compose_accessories_text(detail),
        observaciones=normalize_optional_text(detail.get("observaciones_generales")),
        fecha_ingreso=detail["fecha_recepcion"],
        finalized_at=detail.get("finalized_at"),
        delivered_at=detail.get("delivered_at"),
        delivered_by_user_id=detail.get("delivered_by_user_id"),
        assigned_mechanic_id=detail.get("assigned_mechanic_id"),
        assigned_mechanic_name=detail.get("assigned_mechanic_name"),
        created_at=detail["created_at"],
        updated_at=detail["updated_at"],
    )


def _build_ficha_recepcion_list_item(detail: dict[str, object]) -> FichaRecepcionListItemResponse:
    return FichaRecepcionListItemResponse(
        id=int(detail["id"]),
        cliente_id=detail.get("mobile_client_id"),
        emergencia_id=detail.get("emergencia_id"),
        codigo_ficha=str(detail["codigo_ficha"]),
        estado=str(detail["status"]),
        vehiculo=_compose_vehicle_label(detail),
        placa=normalize_optional_text(detail.get("plate")),
        problema_reportado=_compose_problem_report(detail),
        fecha_ingreso=detail["fecha_recepcion"],
        finalized_at=detail.get("finalized_at"),
        delivered_at=detail.get("delivered_at"),
        delivered_by_user_id=detail.get("delivered_by_user_id"),
        assigned_mechanic_id=detail.get("assigned_mechanic_id"),
        assigned_mechanic_name=detail.get("assigned_mechanic_name"),
        created_at=detail["created_at"],
        updated_at=detail["updated_at"],
    )


def _ensure_mobile_mechanic_can_access_emergency_ficha(
    *,
    current_user: AuthenticatedUser,
    emergency_id: int,
    detail: dict[str, object],
) -> None:
    if detail.get("assigned_mechanic_id") == current_user.id:
        return

    context = get_emergency_tracking_context(emergency_id)
    if not context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

    assigned_email = normalize_optional_text(context.get("assigned_mecanico_email"))
    current_email = normalize_optional_text(current_user.email)
    if assigned_email and current_email and assigned_email == current_email:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Solo el mecánico asignado puede consultar la ficha de recepción de esta emergencia.",
    )


def _calculate_distance_meters(
    origin_latitude: object,
    origin_longitude: object,
    destination_latitude: object,
    destination_longitude: object,
) -> float | None:
    try:
        lat1 = float(origin_latitude)
        lon1 = float(origin_longitude)
        lat2 = float(destination_latitude)
        lon2 = float(destination_longitude)
    except (TypeError, ValueError):
        return None

    radius_meters = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_meters * c


def _find_nearest_sucursal_id_for_emergency(
    row: dict[str, object],
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


def _secretaria_can_access_emergency(
    *,
    current_user: AuthenticatedUser,
    emergency_id: int,
) -> bool:
    secretaria = get_secretaria_by_cliente_id(current_user.id)
    if not secretaria or secretaria.get("sucursal_id") is None:
        return False

    report = get_emergency_report_by_id(emergency_id)
    if not report:
        return False

    target_sucursal_id = int(secretaria["sucursal_id"])
    assigned_mecanico_id = report.get("assigned_mecanico_id")
    if assigned_mecanico_id is not None:
        mecanicos_by_id = {
            int(item["id"]): item
            for item in list_mecanicos()
            if item.get("id") is not None
        }
        matching_mecanico = mecanicos_by_id.get(int(assigned_mecanico_id))
        return bool(
            matching_mecanico
            and int(matching_mecanico.get("sucursal_id") or 0) == target_sucursal_id
        )

    active_sucursales = list_sucursales("ACTIVO")
    return _find_nearest_sucursal_id_for_emergency(report, active_sucursales) == target_sucursal_id


def _ensure_recepcion_access(
    recepcion_id: int,
    current_user: AuthenticatedUser,
    *,
    allow_client_owner: bool,
) -> dict[str, object]:
    detail = get_recepcion_record_by_id(recepcion_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficha de recepción no encontrada")

    role = current_user.role.lower().strip()
    if role in {PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE}:
        return detail

    if role == MECANICO_ROLE:
        assigned_mechanic_id = detail.get("assigned_mechanic_id")
        if assigned_mechanic_id is None or assigned_mechanic_id == current_user.id:
            return detail

    if allow_client_owner and role == "client" and detail.get("mobile_client_id") == current_user.id:
        return detail

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos para acceder a esta ficha de recepción",
    )


def _build_minimal_recepcion_payload(
    payload: FichaRecepcionCreateRequest,
    *,
    current_user: AuthenticatedUser,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    if payload.cliente_id is None and payload.emergencia_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debes enviar al menos cliente_id o emergencia_id",
        )

    emergency = None
    if payload.emergencia_id is not None:
        emergency = get_emergency_report_by_id(payload.emergencia_id)
        if not emergency:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

        active_for_emergency = get_active_recepcion_by_emergency_id(payload.emergencia_id)
        if active_for_emergency:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La emergencia ya tiene una ficha de recepción activa",
            )

    resolved_client_id = payload.cliente_id or (int(emergency["client_id"]) if emergency and emergency.get("client_id") else None)
    if resolved_client_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pudo determinar el cliente asociado a la ficha",
        )

    client = _ensure_client_exists_with_role(resolved_client_id, expected_role="client")

    if emergency and emergency.get("client_id") is not None and int(emergency["client_id"]) != resolved_client_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La emergencia indicada pertenece a un cliente diferente",
        )

    if payload.assigned_mechanic_id is not None:
        _ensure_client_exists_with_role(payload.assigned_mechanic_id, expected_role=MECANICO_ROLE)

    vehicle_label = normalize_optional_text(payload.vehiculo)
    brand = normalize_optional_text(payload.marca)
    model = normalize_optional_text(payload.modelo)
    if not brand and vehicle_label:
        brand = vehicle_label
    if not model:
        model = "No especificado"

    cliente_payload = {
        "full_name": str(client["full_name"]).strip(),
        "identity_card": str(client["identity_card"]).strip(),
        "phone": str(client["phone"]).strip(),
        "email": normalize_email(str(client["email"])) if client.get("email") is not None else None,
        "address": None,
        "mobile_client_id": resolved_client_id,
    }
    vehiculo_payload = {
        "plate": normalize_plate(payload.placa) if payload.placa else f"SINPLACA-{resolved_client_id}",
        "brand": brand or "Vehículo",
        "model": model,
        "year": payload.anio or datetime.now(UTC).year,
        "color": "No especificado",
        "vin": None,
        "engine_number": None,
    }
    ficha_payload = {
        "codigo_ficha": _generate_codigo_ficha(),
        "emergencia_id": payload.emergencia_id,
        "status": "registrada",
        "fecha_recepcion": None,
        "finalized_at": None,
        "delivered_at": None,
        "delivered_by_user_id": None,
        "kilometraje": None,
        "nivel_combustible": None,
        "assigned_mechanic_id": payload.assigned_mechanic_id,
        "observaciones_generales": normalize_optional_text(payload.observaciones),
        "recepcionado_por_user_id": payload.recibido_por_id or current_user.id,
        "recepcionado_por_role": current_user.role,
    }
    accessories = []
    if normalize_optional_text(payload.accesorios_recibidos):
        accessories.append(
            {
                "name": "Accesorios recibidos",
                "quantity": 1,
                "notes": normalize_optional_text(payload.accesorios_recibidos),
            }
        )
    problems = [
        {
            "description": payload.problema_reportado.strip(),
            "priority": None,
            "reported_by": "cliente",
        }
    ]
    return cliente_payload, vehiculo_payload, ficha_payload, accessories, problems


@router.post(
    "/recepciones",
    response_model=RecepcionCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recepcion(
    payload: RecepcionCreateRequest,
    current_user: AuthenticatedUser = Security(require_roles(SECRETARIA_ROLE)),
) -> RecepcionCreatedResponse:
    try:
        created = create_recepcion_record(
            cliente_payload=_normalize_cliente_payload(payload.cliente),
            vehiculo_payload=_normalize_vehiculo_payload(payload.vehiculo),
            ficha_payload=_normalize_ficha_payload(payload.ficha, current_user=current_user),
            accessories=_normalize_accessories(payload.accesorios),
            problems=_normalize_problems(payload.problemas),
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            source_app="web",
            endpoint=f"{settings.api_prefix}/recepciones",
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo crear la recepción por datos duplicados o referencias inválidas",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return RecepcionCreatedResponse(
        id=int(created["id"]),
        codigo_ficha=str(created["codigo_ficha"]),
        emergencia_id=created.get("emergencia_id"),
        status=str(created["status"]),
        cliente_id=int(created["reception_client_id"]),
        vehiculo_id=int(created["vehicle_id"]),
        fecha_recepcion=created["fecha_recepcion"],
        assigned_mechanic_id=created.get("assigned_mechanic_id"),
        created_at=created["created_at"],
    )


@router.get(
    "/recepciones",
    response_model=RecepcionListResponse,
)
def get_recepciones(
    status_filter: str | None = Query(default=None, alias="status"),
    plate: str | None = Query(default=None, min_length=1, max_length=40),
    codigo_ficha: str | None = Query(default=None, min_length=1, max_length=40),
    identity_card: str | None = Query(default=None, min_length=1, max_length=40),
    assigned_mechanic_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, MECANICO_ROLE)),
) -> RecepcionListResponse:
    _ensure_allowed_value(status_filter, ALLOWED_RECEPCION_STATUS, "status")
    try:
        rows, total = list_recepcion_records(
            status=status_filter,
            plate=normalize_plate(plate) if plate else None,
            codigo_ficha=codigo_ficha.strip().upper() if codigo_ficha else None,
            identity_card=identity_card.strip() if identity_card else None,
            assigned_mechanic_id=assigned_mechanic_id,
            visible_mechanic_id=current_user.id if current_user.role.lower().strip() == MECANICO_ROLE else None,
            limit=limit,
            offset=offset,
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    items = [
        RecepcionListItemResponse(
            id=int(row["id"]),
            codigo_ficha=str(row["codigo_ficha"]),
            emergencia_id=row.get("emergencia_id"),
            status=str(row["status"]),
            fecha_recepcion=row["fecha_recepcion"],
            client_full_name=str(row["client_full_name"]),
            client_identity_card=str(row["client_identity_card"]),
            client_phone=str(row["client_phone"]),
            client_email=row.get("client_email"),
            plate=str(row["plate"]),
            vehicle_label=f"{row['brand']} {row['model']} {row['year']}",
            finalized_at=row.get("finalized_at"),
            delivered_at=row.get("delivered_at"),
            delivered_by_user_id=row.get("delivered_by_user_id"),
            assigned_mechanic_id=row.get("assigned_mechanic_id"),
            assigned_mechanic_name=row.get("assigned_mechanic_name"),
            updated_at=row["updated_at"],
        )
        for row in rows
    ]

    return RecepcionListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/recepciones/mecanicos-asignables",
    response_model=list[RecepcionMechanicOptionResponse],
)
def get_assignable_recepcion_mechanics(
    current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> list[RecepcionMechanicOptionResponse]:
    try:
        return _list_assignable_mechanics(current_user)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc


@router.post(
    "/fichas-recepcion",
    response_model=FichaRecepcionDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ficha_recepcion(
    payload: FichaRecepcionCreateRequest,
    current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> FichaRecepcionDetailResponse:
    try:
        cliente_payload, vehiculo_payload, ficha_payload, accessories, problems = _build_minimal_recepcion_payload(
            payload,
            current_user=current_user,
        )
        created = create_recepcion_record(
            cliente_payload=cliente_payload,
            vehiculo_payload=vehiculo_payload,
            ficha_payload=ficha_payload,
            accessories=accessories,
            problems=problems,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            source_app="web",
            endpoint=f"{settings.api_prefix}/fichas-recepcion",
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo crear la ficha de recepción por datos duplicados o referencias inválidas",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return _build_ficha_recepcion_response(created)


@router.get(
    "/fichas-recepcion",
    response_model=list[FichaRecepcionListItemResponse],
)
def list_fichas_recepcion(
    current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> list[FichaRecepcionListItemResponse]:
    try:
        rows, _total = list_recepcion_records(limit=100, offset=0)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    details = []
    for row in rows:
        detail = get_recepcion_record_by_id(int(row["id"]))
        if detail is not None:
            details.append(_build_ficha_recepcion_list_item(detail))
    return details


@router.get(
    "/fichas-recepcion/{recepcion_id}",
    response_model=FichaRecepcionDetailResponse,
)
def get_ficha_recepcion(
    recepcion_id: int,
    current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> FichaRecepcionDetailResponse:
    detail = _ensure_recepcion_access(recepcion_id, current_user, allow_client_owner=False)
    return _build_ficha_recepcion_response(detail)


@router.get(
    "/emergencias/{emergencia_id}/ficha-recepcion",
    response_model=FichaRecepcionDetailResponse,
)
def get_operational_emergency_recepcion(
    emergencia_id: int,
    current_user: AuthenticatedUser = Security(
        require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, MECANICO_ROLE)
    ),
) -> FichaRecepcionDetailResponse:
    detail = get_recepcion_record_by_emergency_id(emergencia_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficha de recepción no encontrada")
    current_role = current_user.role.lower().strip()
    if current_role == MECANICO_ROLE:
        _ensure_mobile_mechanic_can_access_emergency_ficha(
            current_user=current_user,
            emergency_id=emergencia_id,
            detail=detail,
        )
    elif current_role == SECRETARIA_ROLE and not _secretaria_can_access_emergency(
        current_user=current_user,
        emergency_id=emergencia_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada o fuera del alcance permitido.",
        )
    return _build_ficha_recepcion_response(detail)


@router.get(
    "/mobile/emergencias/{emergencia_id}/ficha-recepcion",
    response_model=FichaRecepcionDetailResponse,
)
def get_mobile_emergency_recepcion(
    emergencia_id: int,
    current_user: AuthenticatedUser = Security(require_roles(MECANICO_ROLE)),
) -> FichaRecepcionDetailResponse:
    detail = get_recepcion_record_by_emergency_id(emergencia_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficha de recepción no encontrada")
    _ensure_mobile_mechanic_can_access_emergency_ficha(
        current_user=current_user,
        emergency_id=emergencia_id,
        detail=detail,
    )
    return _build_ficha_recepcion_response(detail)


@router.get(
    "/recepciones/{recepcion_id}",
    response_model=RecepcionRecordResponse,
)
def get_recepcion(
    recepcion_id: int,
    current_user: AuthenticatedUser = Security(get_current_active_user),
) -> RecepcionRecordResponse:
    try:
        detail = _ensure_recepcion_access(recepcion_id, current_user, allow_client_owner=True)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return RecepcionRecordResponse.model_validate(_build_recepcion_detail_response(detail))


@router.put(
    "/recepciones/{recepcion_id}",
    response_model=RecepcionRecordResponse,
)
def edit_recepcion(
    recepcion_id: int,
    payload: RecepcionUpdateRequest,
    current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> RecepcionRecordResponse:
    existing = get_recepcion_record_by_id(recepcion_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficha de recepción no encontrada")

    try:
        updated = update_recepcion_record(
            recepcion_id,
            cliente_payload=_normalize_cliente_payload(payload.cliente),
            vehiculo_payload=_normalize_vehiculo_payload(payload.vehiculo),
            ficha_payload=_normalize_ficha_payload(
                payload.ficha,
                current_user=current_user,
                keep_original_recepcionista=True,
                existing_codigo_ficha=str(existing["codigo_ficha"]),
            ),
            accessories=_normalize_accessories(payload.accesorios),
            problems=_normalize_problems(payload.problemas),
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo actualizar la recepción por datos duplicados o referencias inválidas",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficha de recepción no encontrada")

    return RecepcionRecordResponse.model_validate(_build_recepcion_detail_response(updated))


@router.get(
    "/recepciones/{recepcion_id}/ficha",
    response_model=RecepcionRecordResponse,
)
def get_recepcion_ficha(
    recepcion_id: int,
    current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, MECANICO_ROLE)),
) -> RecepcionRecordResponse:
    detail = _ensure_recepcion_access(recepcion_id, current_user, allow_client_owner=False)
    return RecepcionRecordResponse.model_validate(_build_recepcion_detail_response(detail))


@router.post(
    "/recepciones/{recepcion_id}/diagnostico",
    response_model=RecepcionDiagnosticoResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_recepcion_diagnostic(
    recepcion_id: int,
    payload: DiagnosticoCreateRequest,
    current_user: AuthenticatedUser = Security(require_roles(MECANICO_ROLE)),
) -> RecepcionDiagnosticoResponse:
    detail = _ensure_recepcion_access(recepcion_id, current_user, allow_client_owner=False)
    _ensure_client_exists_with_role(current_user.id, expected_role=MECANICO_ROLE)
    _ensure_linked_mecanico_profile(current_user.id)
    current_status = str(detail.get("status") or "").strip().lower()
    if current_status not in {"registrada", "en_diagnostico"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede registrar el diagnóstico inicial en fichas registradas o en diagnóstico",
        )

    try:
        created = create_recepcion_diagnostic(
            {
                "ficha_id": recepcion_id,
                "mechanic_id": current_user.id,
                "diagnostic_text": payload.diagnostic_text.strip(),
                "estimated_work": normalize_optional_text(payload.estimated_work),
                "estimated_cost": payload.estimated_cost,
            },
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            source_app="web",
            endpoint=f"{settings.api_prefix}/recepciones/{{recepcion_id}}/diagnostico",
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo registrar el diagnóstico técnico",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    created["mechanic_name"] = current_user.full_name
    return RecepcionDiagnosticoResponse.model_validate(created)


@router.post(
    "/recepciones/{recepcion_id}/observaciones",
    response_model=RecepcionObservacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_recepcion_observation(
    recepcion_id: int,
    payload: ObservacionCreateRequest,
    current_user: AuthenticatedUser = Security(require_roles(MECANICO_ROLE)),
) -> RecepcionObservacionResponse:
    _ensure_allowed_value(payload.work_status, ALLOWED_WORK_STATUS, "work_status")
    detail = _ensure_recepcion_access(recepcion_id, current_user, allow_client_owner=False)
    _ensure_client_exists_with_role(current_user.id, expected_role=MECANICO_ROLE)
    _ensure_linked_mecanico_profile(current_user.id)
    current_status = str(detail.get("status") or "").strip().lower()
    if current_status not in {"en_diagnostico", "en_trabajo"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden registrar observaciones en fichas en diagnóstico o en trabajo",
        )

    try:
        created = create_recepcion_observation(
            {
                "ficha_id": recepcion_id,
                "mechanic_id": current_user.id,
                "observation_text": payload.observation_text.strip(),
                "work_status": payload.work_status,
            },
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            source_app="web",
            endpoint=f"{settings.api_prefix}/recepciones/{{recepcion_id}}/observaciones",
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo registrar la observación de trabajo",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    created["mechanic_name"] = current_user.full_name
    return RecepcionObservacionResponse.model_validate(created)


@router.post(
    "/recepciones/{recepcion_id}/finalizar",
    response_model=RecepcionRecordResponse,
)
def finalize_recepcion(
    recepcion_id: int,
    payload: RecepcionFinalizeRequest,
    current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, MECANICO_ROLE)),
) -> RecepcionRecordResponse:
    detail = _ensure_recepcion_access(recepcion_id, current_user, allow_client_owner=False)
    current_role = current_user.role.lower().strip()

    if current_role == SECRETARIA_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La secretaria no puede finalizar trabajo técnico",
        )

    if current_role == PROTECTED_ADMIN_ROLE:
        if not payload.admin_override:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El administrador debe confirmar admin_override para finalizar la recepción",
            )
    elif current_role == MECANICO_ROLE:
        if detail.get("assigned_mechanic_id") != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el mecánico asignado puede finalizar la recepción",
            )
        _ensure_linked_mecanico_profile(current_user.id)

    try:
        finalized = finalize_recepcion_work(
            recepcion_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            source_app="web",
            endpoint=f"{settings.api_prefix}/recepciones/{{recepcion_id}}/finalizar",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    client_id = finalized.get("mobile_client_id")
    emergency_id = finalized.get("emergencia_id")
    recepcion_code = str(finalized.get("codigo_ficha") or "")
    notification_metadata = {
        "open_screen": "notifications",
        "recepcion_id": recepcion_id,
        "codigo_ficha": recepcion_code,
        "emergencia_id": emergency_id,
        "status": "finalizada",
    }
    _notify_client_operational_event(
        client_id=int(client_id) if client_id is not None else None,
        emergency_id=int(emergency_id) if emergency_id is not None else None,
        notification_type="recepcion_finalizada",
        title="Recepción finalizada",
        message=f"Tu ficha {recepcion_code or recepcion_id} fue finalizada por el taller.",
        metadata=notification_metadata,
    )

    return RecepcionRecordResponse.model_validate(_build_recepcion_detail_response(finalized))


@router.post(
    "/recepciones/{recepcion_id}/entregar",
    response_model=RecepcionRecordResponse,
)
def deliver_recepcion(
    recepcion_id: int,
    current_user: AuthenticatedUser = Security(require_roles(PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE)),
) -> RecepcionRecordResponse:
    try:
        _ensure_recepcion_access(recepcion_id, current_user, allow_client_owner=False)
        delivered = deliver_recepcion_work(
            recepcion_id,
            delivered_by_user_id=current_user.id,
            actor_role=current_user.role,
            source_app="web",
            endpoint=f"{settings.api_prefix}/recepciones/{{recepcion_id}}/entregar",
        )
    except ValueError as exc:
        message = str(exc)
        if "no encontrada" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    client_id = delivered.get("mobile_client_id")
    emergency_id = delivered.get("emergencia_id")
    recepcion_code = str(delivered.get("codigo_ficha") or "")
    if client_id is not None:
        notifications_payloads = [
            {
                "cliente_id": int(client_id),
                "emergencia_id": int(emergency_id) if emergency_id is not None else None,
                "tipo": "vehiculo_entregado",
                "titulo": "Vehículo entregado",
                "mensaje": f"Tu vehículo asociado a la ficha {recepcion_code or recepcion_id} ya fue entregado.",
                "metadata": {
                    "open_screen": "notifications",
                    "recepcion_id": recepcion_id,
                    "codigo_ficha": recepcion_code,
                    "emergencia_id": emergency_id,
                    "status": "entregada",
                },
            }
        ]
        if emergency_id is not None:
            notifications_payloads.append(
                {
                    "cliente_id": int(client_id),
                    "emergencia_id": int(emergency_id),
                    "tipo": "emergencia_cerrada",
                    "titulo": "Emergencia cerrada",
                    "mensaje": "La emergencia asociada a tu atención fue cerrada correctamente.",
                    "metadata": {
                        "open_screen": "notifications",
                        "recepcion_id": recepcion_id,
                        "codigo_ficha": recepcion_code,
                        "emergencia_id": emergency_id,
                        "status": "cerrada",
                    },
                }
            )
        create_client_notifications(notifications_payloads)

        send_push_to_client(
            int(client_id),
            "Vehículo entregado",
            f"Tu vehículo asociado a la ficha {recepcion_code or recepcion_id} ya fue entregado.",
            _notification_push_data(
                "vehiculo_entregado",
                {
                    "open_screen": "notifications",
                    "recepcion_id": recepcion_id,
                    "codigo_ficha": recepcion_code,
                    "emergencia_id": emergency_id,
                    "status": "entregada",
                },
            ),
        )
        if emergency_id is not None:
            send_push_to_client(
                int(client_id),
                "Emergencia cerrada",
                "La emergencia asociada a tu atención fue cerrada correctamente.",
                _notification_push_data(
                    "emergencia_cerrada",
                    {
                        "open_screen": "notifications",
                        "recepcion_id": recepcion_id,
                        "codigo_ficha": recepcion_code,
                        "emergencia_id": emergency_id,
                        "status": "cerrada",
                    },
                ),
            )

    return RecepcionRecordResponse.model_validate(_build_recepcion_detail_response(delivered))


@router.get(
    "/recepciones/{recepcion_id}/estado",
    response_model=RecepcionEstadoResponse,
)
def get_recepcion_estado(
    recepcion_id: int,
    current_user: AuthenticatedUser = Security(get_current_active_user),
) -> RecepcionEstadoResponse:
    try:
        detail = _ensure_recepcion_access(recepcion_id, current_user, allow_client_owner=True)
        estado = get_recepcion_status_by_id(recepcion_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    if not estado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficha de recepción no encontrada")

    return RecepcionEstadoResponse(
        ficha_id=int(estado["ficha_id"]),
        codigo_ficha=str(estado["codigo_ficha"]),
        status=str(estado["status"]),
        vehicle=f"{estado['brand']} {estado['model']} {estado['year']}",
        plate=str(estado["plate"]),
        last_diagnostic=estado.get("last_diagnostic"),
        last_observation=estado.get("last_observation"),
        finalized_at=estado.get("finalized_at"),
        delivered_at=estado.get("delivered_at"),
        delivered_by_user_id=estado.get("delivered_by_user_id"),
        updated_at=estado["updated_at"],
    )
