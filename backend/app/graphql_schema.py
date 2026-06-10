from __future__ import annotations

from datetime import datetime
from typing import Optional

import strawberry
from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig
from strawberry.types import Info

from app.constants import MECANICO_ROLE, PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE
from app.core.dependencies import AuthenticatedUser, get_optional_current_active_user
from app.db import (
    accept_emergency_mecanico_assignment,
    assign_emergency_mecanico_with_notification,
    create_sucursal,
    delete_sucursal,
    get_emergency_ai_recommendation,
    get_emergency_report_by_id,
    get_emergency_tracking_context,
    get_mecanico_by_cliente_id,
    get_mecanico_by_id,
    get_secretaria_by_cliente_id,
    get_sucursal_by_id,
    get_workshop_by_id,
    list_emergency_reports,
    list_mecanicos,
    list_sucursales,
    upsert_emergency_ai_recommendation,
    update_sucursal,
    update_sucursal_estado,
)
from app.notifications import send_push_to_client
from app.services.ai_assignment_service import build_ai_assignment_recommendation

CLIENT_ROLE = "client"

_SUCURSAL_READ_ROLES = frozenset(
    {PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE, MECANICO_ROLE, CLIENT_ROLE}
)
_SUCURSAL_WRITE_ROLES = frozenset({PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE})
_EMERGENCIA_READ_ROLES = frozenset(
    {PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE, MECANICO_ROLE, CLIENT_ROLE}
)
_MECANICO_READ_ROLES = frozenset({PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE})
_RECOMENDACION_IA_READ_ROLES = frozenset({PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE})
_ASIGNAR_MECANICO_ROLES = frozenset({PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE})
_ACEPTAR_ASISTENCIA_ROLES = frozenset({MECANICO_ROLE})

_VALID_ESTADOS = frozenset({"ACTIVO", "INACTIVO"})


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _require_role(info: Info, allowed_roles: frozenset[str]) -> AuthenticatedUser:
    user: AuthenticatedUser | None = info.context.get("current_user")
    if user is None:
        raise PermissionError("No autenticado")
    if user.role not in allowed_roles:
        raise PermissionError("No tienes permisos para realizar esta acción")
    return user


def _require_active_user(info: Info) -> AuthenticatedUser:
    user = _require_role(
        info,
        frozenset(
            {PROTECTED_ADMIN_ROLE, SECRETARIA_ROLE, WORKSHOP_ROLE, MECANICO_ROLE, CLIENT_ROLE}
        ),
    )
    if user.role == WORKSHOP_ROLE and user.status != "activo":
        raise PermissionError("La cuenta no está activa")
    if user.role != WORKSHOP_ROLE and user.status != "active":
        raise PermissionError("La cuenta no está activa")
    return user


def _get_secretaria_scope(current_user: AuthenticatedUser) -> dict[str, object] | None:
    if current_user.role != SECRETARIA_ROLE:
        return None

    secretaria = get_secretaria_by_cliente_id(current_user.id)
    if not secretaria:
        raise PermissionError("La secretaria autenticada no tiene una sucursal afiliada configurada.")
    return secretaria


def _get_mecanico_for_operational_scope(
    *,
    mecanico_id: int,
    operational_scope_id: int,
) -> dict[str, object] | None:
    mecanico = get_mecanico_by_id(mecanico_id)
    if not mecanico:
        return None

    workshop_id = mecanico.get("workshop_id")
    sucursal_id = mecanico.get("sucursal_id")
    if workshop_id is not None and int(workshop_id) == operational_scope_id:
        return mecanico
    if sucursal_id is not None and int(sucursal_id) == operational_scope_id:
        return mecanico
    return None


def _filter_emergency_rows_for_secretaria(
    rows: list[dict[str, object]],
    secretaria: dict[str, object],
) -> list[dict[str, object]]:
    target_sucursal_id = int(secretaria["sucursal_id"])
    mecanicos_by_id = {
        int(item["id"]): item
        for item in list_mecanicos()
        if item.get("id") is not None
    }
    filtered_rows: list[dict[str, object]] = []

    for row in rows:
        assigned_mecanico_id = row.get("assigned_mecanico_id")
        if assigned_mecanico_id is None:
            continue
        matching_mecanico = mecanicos_by_id.get(int(assigned_mecanico_id))
        if matching_mecanico and int(matching_mecanico.get("sucursal_id") or 0) == target_sucursal_id:
            filtered_rows.append(row)

    return filtered_rows


def _filter_emergency_rows_for_mecanico(
    rows: list[dict[str, object]],
    *,
    current_user: AuthenticatedUser,
) -> list[dict[str, object]]:
    mecanico = get_mecanico_by_cliente_id(current_user.id)
    mecanico_id = int(mecanico["id"]) if mecanico and mecanico.get("id") is not None else None
    current_email = _normalize_optional_text(current_user.email)
    filtered_rows: list[dict[str, object]] = []

    for row in rows:
        assignment_status = _normalize_optional_text(row.get("assignment_status"))
        if assignment_status == "rechazado":
            continue

        assigned_mecanico_id = row.get("assigned_mecanico_id")
        if mecanico_id is not None and assigned_mecanico_id is not None and int(assigned_mecanico_id) == mecanico_id:
            filtered_rows.append(row)
            continue

        assigned_mecanico_email = _normalize_optional_text(row.get("assigned_mecanico_email"))
        if current_email and assigned_mecanico_email == current_email:
            filtered_rows.append(row)

    return filtered_rows


def _ensure_current_mecanico_is_assigned(
    *,
    current_user: AuthenticatedUser,
    context: dict[str, object],
) -> int:
    assigned_mecanico_email = _normalize_optional_text(context.get("assigned_mecanico_email"))
    current_email = _normalize_optional_text(current_user.email)
    mecanico = get_mecanico_by_cliente_id(current_user.id)
    mecanico_id = int(mecanico["id"]) if mecanico and mecanico.get("id") is not None else None
    assigned_mecanico_id = context.get("assigned_mecanico_id")

    if mecanico_id is not None and assigned_mecanico_id is not None and int(assigned_mecanico_id) == mecanico_id:
        return mecanico_id
    if assigned_mecanico_email and assigned_mecanico_email == current_email and mecanico_id is not None:
        return mecanico_id

    raise PermissionError("Solo el mecánico asignado puede operar sobre esta emergencia.")


def _normalize_emergency_assignment_fields(row: dict[str, object]) -> dict[str, object]:
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
    return row


def _build_emergency_tracking_metadata(
    *,
    report_id: int,
    mecanico: dict[str, object],
    sucursal: dict[str, object] | None,
    emergency_report: dict[str, object],
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "open_screen": "emergency_tracking",
        "emergencia_id": report_id,
        "emergency_id": report_id,
        "mecanico_id": mecanico.get("id"),
        "mechanic_id": mecanico.get("id"),
        "mechanic_name": _normalize_optional_text(mecanico.get("full_name")),
        "mechanic_phone": _normalize_optional_text(mecanico.get("phone")),
        "mechanic_specialty": _normalize_optional_text(mecanico.get("specialty")),
        "tracking_available": True,
        "origin_latitude": emergency_report.get("latitude"),
        "origin_longitude": emergency_report.get("longitude"),
        "destination_latitude": emergency_report.get("latitude"),
        "destination_longitude": emergency_report.get("longitude"),
    }
    if sucursal is not None:
        metadata["sucursal_id"] = sucursal.get("id")
        metadata["sucursal_nombre"] = sucursal.get("nombre")
    return metadata


def _build_push_data_from_metadata(*, notification_type: str, metadata: dict[str, object]) -> dict[str, str]:
    payload = {"type": notification_type}
    for key, value in metadata.items():
        if value is None:
            continue
        payload[str(key)] = str(value)
    return payload


@strawberry.type
class Sucursal:
    id: int
    nombre: str
    direccion: str
    zona: Optional[str]
    telefono: Optional[str]
    email: Optional[str]
    latitud: Optional[float]
    longitud: Optional[float]
    horario_atencion: Optional[str]
    responsable: Optional[str]
    estado: str
    fecha_registro: datetime
    fecha_modificacion: Optional[datetime]
    mecanicos_activos_count: int = 0
    secretarias_activas_count: int = 0
    operativa: bool = True


@strawberry.type
class Emergencia:
    id: int
    codigo: str
    emergency_status: str
    ia_categoria: Optional[str]
    ia_prioridad: Optional[str]
    ia_confidence: Optional[float]
    nearest_workshop_id: Optional[int]
    assigned_mecanico_id: Optional[int]
    created_at: datetime


@strawberry.type
class Mecanico:
    id: int
    full_name: str
    specialty: Optional[str]
    status: str
    sucursal_id: Optional[int]


@strawberry.type
class RecomendacionIA:
    categoria: Optional[str]
    prioridad: Optional[str]
    especialidad_requerida: Optional[str]
    sucursal_recomendada: Optional[str]
    mecanico_recomendado: Optional[str]
    confidence: Optional[float]


@strawberry.type
class MutationResult:
    success: bool
    message: str


def _row_to_sucursal(row: dict) -> Sucursal:
    return Sucursal(
        id=int(row["id"]),
        nombre=str(row["nombre"]),
        direccion=str(row["direccion"]),
        zona=str(row["zona"]) if row.get("zona") is not None else None,
        telefono=str(row["telefono"]) if row.get("telefono") is not None else None,
        email=str(row["email"]) if row.get("email") is not None else None,
        latitud=float(row["latitud"]) if row.get("latitud") is not None else None,
        longitud=float(row["longitud"]) if row.get("longitud") is not None else None,
        horario_atencion=str(row["horario_atencion"]) if row.get("horario_atencion") is not None else None,
        responsable=str(row["responsable"]) if row.get("responsable") is not None else None,
        estado=str(row["estado"]),
        fecha_registro=row["fecha_registro"],
        fecha_modificacion=row.get("fecha_modificacion"),
        mecanicos_activos_count=int(row.get("mecanicos_activos_count") or 0),
        secretarias_activas_count=int(row.get("secretarias_activas_count") or 0),
        operativa=bool(row.get("operativa", True)),
    )


def _row_to_emergencia(row: dict[str, object]) -> Emergencia:
    normalized = _normalize_emergency_assignment_fields(dict(row))
    return Emergencia(
        id=int(normalized["id"]),
        codigo=f"EMG-{int(normalized['id'])}",
        emergency_status=str(normalized.get("emergency_status") or ""),
        ia_categoria=_normalize_optional_text(normalized.get("ia_categoria")),
        ia_prioridad=_normalize_optional_text(normalized.get("ia_prioridad")),
        ia_confidence=float(normalized["ia_confidence"]) if normalized.get("ia_confidence") is not None else None,
        nearest_workshop_id=(
            int(normalized["nearest_workshop_id"]) if normalized.get("nearest_workshop_id") is not None else None
        ),
        assigned_mecanico_id=(
            int(normalized["assigned_mecanico_id"]) if normalized.get("assigned_mecanico_id") is not None else None
        ),
        created_at=normalized["created_at"],
    )


def _row_to_mecanico(row: dict[str, object]) -> Mecanico:
    return Mecanico(
        id=int(row["id"]),
        full_name=str(row.get("full_name") or ""),
        specialty=_normalize_optional_text(row.get("specialty")),
        status=str(row.get("status") or ""),
        sucursal_id=int(row["sucursal_id"]) if row.get("sucursal_id") is not None else None,
    )


@strawberry.input
class SucursalInput:
    nombre: str
    direccion: str
    zona: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    horario_atencion: Optional[str] = None
    responsable: Optional[str] = None
    estado: str = "ACTIVO"


def _build_sucursal_payload(input: SucursalInput) -> dict[str, object]:
    return {
        "nombre": input.nombre.strip(),
        "direccion": input.direccion.strip(),
        "zona": input.zona.strip() if input.zona else None,
        "telefono": input.telefono.strip() if input.telefono else None,
        "email": input.email.strip() if input.email else None,
        "latitud": input.latitud,
        "longitud": input.longitud,
        "horario_atencion": input.horario_atencion.strip() if input.horario_atencion else None,
        "responsable": input.responsable.strip() if input.responsable else None,
        "estado": input.estado,
    }


def _validate_sucursal_input(input: SucursalInput) -> None:
    if not input.nombre or not input.nombre.strip():
        raise ValueError("El nombre es obligatorio")
    if not input.direccion or not input.direccion.strip():
        raise ValueError("La dirección es obligatoria")
    if input.estado not in _VALID_ESTADOS:
        raise ValueError("El estado debe ser ACTIVO o INACTIVO")


@strawberry.type
class Query:
    @strawberry.field
    def sucursales(self, info: Info, estado: Optional[str] = None) -> list[Sucursal]:
        current_user = _require_active_user(info)
        if current_user.role not in _SUCURSAL_READ_ROLES:
            raise PermissionError("No tienes permisos para realizar esta acción")
        if estado is not None and estado not in _VALID_ESTADOS:
            raise ValueError("El estado debe ser ACTIVO o INACTIVO")
        try:
            rows = list_sucursales(estado=estado)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        return [_row_to_sucursal(row) for row in rows]

    @strawberry.field
    def sucursal(self, info: Info, id: int) -> Optional[Sucursal]:
        current_user = _require_active_user(info)
        if current_user.role not in _SUCURSAL_READ_ROLES:
            raise PermissionError("No tienes permisos para realizar esta acción")
        try:
            row = get_sucursal_by_id(id)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        return _row_to_sucursal(row) if row else None

    @strawberry.field
    def emergencias(self, info: Info) -> list[Emergencia]:
        current_user = _require_active_user(info)
        if current_user.role not in _EMERGENCIA_READ_ROLES:
            raise PermissionError("No tienes permisos para realizar esta acción")
        try:
            rows = list_emergency_reports()
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc

        if current_user.role == SECRETARIA_ROLE:
            secretaria = _get_secretaria_scope(current_user)
            rows = _filter_emergency_rows_for_secretaria(rows, secretaria) if secretaria else []
        elif current_user.role == MECANICO_ROLE:
            rows = _filter_emergency_rows_for_mecanico(rows, current_user=current_user)
        elif current_user.role == CLIENT_ROLE:
            rows = [row for row in rows if row.get("client_id") == current_user.id]

        return [_row_to_emergencia(row) for row in rows]

    @strawberry.field
    def mecanicos(self, info: Info) -> list[Mecanico]:
        current_user = _require_active_user(info)
        if current_user.role not in _MECANICO_READ_ROLES:
            raise PermissionError("No tienes permisos para realizar esta acción")
        try:
            rows = list_mecanicos()
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc

        secretaria = _get_secretaria_scope(current_user)
        if secretaria:
            scope_sucursal_id = int(secretaria["sucursal_id"])
            rows = [row for row in rows if int(row.get("sucursal_id") or 0) == scope_sucursal_id]
        elif current_user.role == WORKSHOP_ROLE:
            rows = [row for row in rows if int(row.get("workshop_id") or 0) == current_user.id]

        return [_row_to_mecanico(row) for row in rows]

    @strawberry.field(name="recomendacionIA")
    def recomendacion_ia(self, info: Info, emergenciaId: int) -> RecomendacionIA:
        current_user = _require_active_user(info)
        if current_user.role not in _RECOMENDACION_IA_READ_ROLES:
            raise PermissionError("No tienes permisos para realizar esta acción")
        try:
            emergency = get_emergency_report_by_id(emergenciaId)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc

        if not emergency:
            raise ValueError("Emergencia no encontrada")
        if not emergency.get("ia_categoria") or not emergency.get("ia_prioridad"):
            raise ValueError("La emergencia aun no tiene clasificacion IA disponible.")

        recommendation = build_ai_assignment_recommendation(emergency)
        stored_payload = {
            "emergencia_id": emergenciaId,
            "categoria": recommendation.get("categoria"),
            "prioridad": recommendation.get("prioridad"),
            "especialidad_requerida": recommendation.get("especialidad_requerida"),
            "sucursal_recomendada_id": recommendation.get("sucursal_recomendada_id"),
            "mecanico_recomendado_id": recommendation.get("mecanico_recomendado_id"),
            "confidence": recommendation.get("confidence"),
        }

        try:
            upsert_emergency_ai_recommendation(
                stored_payload,
                actor_user_id=current_user.id,
                actor_role=current_user.role,
                source_app="graphql",
                endpoint="/graphql",
            )
            persisted = get_emergency_ai_recommendation(emergenciaId)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc

        row = persisted or recommendation
        return RecomendacionIA(
            categoria=_normalize_optional_text(row.get("categoria")),
            prioridad=_normalize_optional_text(row.get("prioridad")),
            especialidad_requerida=_normalize_optional_text(row.get("especialidad_requerida")),
            sucursal_recomendada=_normalize_optional_text(
                row.get("sucursal_recomendada_nombre") or row.get("sucursal_recomendada")
            ),
            mecanico_recomendado=_normalize_optional_text(
                row.get("mecanico_recomendado_nombre") or row.get("mecanico_recomendado")
            ),
            confidence=float(row["confidence"]) if row.get("confidence") is not None else None,
        )


@strawberry.type
class Mutation:
    @strawberry.mutation
    def crear_sucursal(self, info: Info, input: SucursalInput) -> Sucursal:
        _require_role(info, _SUCURSAL_WRITE_ROLES)
        _validate_sucursal_input(input)
        try:
            row = create_sucursal(_build_sucursal_payload(input))
        except IntegrityError:
            raise ValueError("Ya existe una sucursal activa con el mismo nombre y dirección")
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        return _row_to_sucursal(row)

    @strawberry.mutation
    def actualizar_sucursal(self, info: Info, id: int, input: SucursalInput) -> Sucursal:
        _require_role(info, _SUCURSAL_WRITE_ROLES)
        _validate_sucursal_input(input)
        try:
            row = update_sucursal(id, _build_sucursal_payload(input))
        except IntegrityError:
            raise ValueError("Ya existe una sucursal activa con el mismo nombre y dirección")
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        if not row:
            raise ValueError(f"Sucursal {id} no encontrada")
        return _row_to_sucursal(row)

    @strawberry.mutation
    def cambiar_estado_sucursal(self, info: Info, id: int, estado: str) -> Sucursal:
        _require_role(info, _SUCURSAL_WRITE_ROLES)
        if estado not in _VALID_ESTADOS:
            raise ValueError("El estado debe ser ACTIVO o INACTIVO")
        try:
            row = update_sucursal_estado(id, estado)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        if not row:
            raise ValueError(f"Sucursal {id} no encontrada")
        return _row_to_sucursal(row)

    @strawberry.mutation
    def eliminar_sucursal(self, info: Info, id: int) -> bool:
        _require_role(info, _SUCURSAL_WRITE_ROLES)
        try:
            result = delete_sucursal(id)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        if not result:
            raise ValueError(f"Sucursal {id} no encontrada")
        return True

    @strawberry.mutation(name="asignarMecanico")
    def asignar_mecanico(self, info: Info, emergenciaId: int, mecanicoId: int) -> MutationResult:
        current_user = _require_active_user(info)
        if current_user.role not in _ASIGNAR_MECANICO_ROLES:
            raise PermissionError("No tienes permisos para realizar esta acción")

        try:
            mecanico = get_mecanico_by_id(mecanicoId)
            report = get_emergency_report_by_id(emergenciaId)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc

        if not mecanico:
            raise ValueError("Mecánico no encontrado para este taller")
        if not report:
            raise ValueError("Emergencia no encontrada o fuera del alcance permitido")

        secretaria = _get_secretaria_scope(current_user)
        effective_workshop_id = int(mecanico["workshop_id"]) if mecanico.get("workshop_id") is not None else None
        report_scope_workshop_id: int | None = None

        if current_user.role == WORKSHOP_ROLE:
            if effective_workshop_id != current_user.id:
                raise PermissionError("No puedes operar sobre un workshop distinto al de tu cuenta autenticada.")
            if report.get("nearest_workshop_id") is not None and int(report["nearest_workshop_id"]) == current_user.id:
                report_scope_workshop_id = current_user.id
        elif secretaria:
            if int(mecanico.get("sucursal_id") or 0) != int(secretaria["sucursal_id"]):
                raise PermissionError("Solo puedes administrar mecánicos afiliados a tu propia sucursal.")
            report_rows = _filter_emergency_rows_for_secretaria([report], secretaria)
            if not report_rows:
                raise ValueError("Emergencia no encontrada o fuera del alcance permitido")

        if report.get("emergency_status") != "activo":
            raise ValueError("Primero debes aceptar la emergencia para asignar un mecánico")

        current_assigned_mecanico_id = (
            report.get("assigned_mecanico_id")
            or report.get("assigned_mechanic_id")
            or report.get("assigned_technician_id")
        )
        mecanico_status = str(mecanico.get("status") or "")
        if mecanico_status != "disponible" and current_assigned_mecanico_id != mecanicoId:
            raise ValueError("El mecánico seleccionado no está disponible")

        sucursal = None
        if mecanico.get("sucursal_id") is not None:
            sucursal = get_sucursal_by_id(int(mecanico["sucursal_id"]))

        notification_metadata = _build_emergency_tracking_metadata(
            report_id=emergenciaId,
            mecanico=mecanico,
            sucursal=sucursal,
            emergency_report=report,
        )
        notification_payload = {
            "cliente_id": int(report["client_id"]) if report.get("client_id") is not None else None,
            "emergencia_id": emergenciaId,
            "tipo": "mechanic_assigned",
            "titulo": "Mecánico asignado",
            "mensaje": f"{str(mecanico.get('full_name') or '').strip() or 'Mecánico asignado'} fue asignado para auxiliarte.",
            "metadata": notification_metadata,
        }

        try:
            _assignment_row, _created_notification, assignment_changed = assign_emergency_mecanico_with_notification(
                emergenciaId,
                effective_workshop_id,
                mecanicoId,
                report_scope_workshop_id=report_scope_workshop_id,
                notification_payload=notification_payload,
                actor_user_id=current_user.id,
                actor_role=current_user.role,
                source_app="graphql",
                endpoint="/graphql",
            )
            updated_report = get_emergency_report_by_id(emergenciaId)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc

        if not updated_report:
            raise ValueError("Emergencia no encontrada")

        if assignment_changed:
            send_push_to_client(
                int(updated_report["client_id"]) if updated_report.get("client_id") is not None else None,
                "Mecánico asignado",
                notification_payload["mensaje"],
                _build_push_data_from_metadata(
                    notification_type="mechanic_assigned",
                    metadata=notification_metadata,
                ),
            )

        return MutationResult(success=True, message="Mecánico asignado correctamente")

    @strawberry.mutation(name="aceptarAsistencia")
    def aceptar_asistencia(self, info: Info, emergenciaId: int) -> MutationResult:
        current_user = _require_active_user(info)
        if current_user.role not in _ACEPTAR_ASISTENCIA_ROLES:
            raise PermissionError("No tienes permisos para realizar esta acción")

        try:
            context = get_emergency_tracking_context(emergenciaId)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc

        if not context:
            raise ValueError("Emergencia no encontrada.")

        mecanico_id = _ensure_current_mecanico_is_assigned(
            current_user=current_user,
            context=context,
        )
        assignment_status = _normalize_optional_text(context.get("assignment_status"))
        if assignment_status not in {"asignado", "aceptado"}:
            raise ValueError("La asignación actual no puede ser aceptada.")

        try:
            accepted_assignment = accept_emergency_mecanico_assignment(
                emergenciaId,
                mecanico_id,
                actor_user_id=current_user.id,
                actor_role=current_user.role,
                source_app="graphql",
                endpoint="/graphql",
            )
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc

        if not accepted_assignment:
            raise ValueError("No se encontró una asignación vigente para aceptar.")

        return MutationResult(success=True, message="Asistencia aceptada correctamente")


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    config=StrawberryConfig(auto_camel_case=False),
)


async def get_graphql_context(
    current_user: AuthenticatedUser | None = Depends(get_optional_current_active_user),
) -> dict[str, object]:
    return {"current_user": current_user}


graphql_router = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
)
