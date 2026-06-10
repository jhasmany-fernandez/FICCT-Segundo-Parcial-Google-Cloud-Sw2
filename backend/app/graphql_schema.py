from __future__ import annotations

from datetime import datetime
from typing import Optional

import strawberry
from fastapi import Depends
from sqlalchemy.exc import IntegrityError, OperationalError
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from app.core.dependencies import AuthenticatedUser, get_optional_current_active_user
from app.db import (
    create_sucursal,
    delete_sucursal,
    get_sucursal_by_id,
    list_sucursales,
    update_sucursal,
    update_sucursal_estado,
)

_READ_ROLES = frozenset({"admin", "secretaria", "workshop", "mecanico"})
_WRITE_ROLES = frozenset({"admin", "secretaria"})

_VALID_ESTADOS = frozenset({"ACTIVO", "INACTIVO"})


def _require_role(info: Info, allowed_roles: frozenset[str]) -> AuthenticatedUser:
    user: AuthenticatedUser | None = info.context.get("current_user")
    if user is None:
        raise PermissionError("No autenticado")
    if user.role not in allowed_roles:
        raise PermissionError("No tienes permisos para realizar esta acción")
    return user


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


def _build_payload(input: SucursalInput) -> dict:
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


def _validate_input(input: SucursalInput) -> None:
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
        _require_role(info, _READ_ROLES)
        if estado is not None and estado not in _VALID_ESTADOS:
            raise ValueError("El estado debe ser ACTIVO o INACTIVO")
        try:
            rows = list_sucursales(estado=estado)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        return [_row_to_sucursal(row) for row in rows]

    @strawberry.field
    def sucursal(self, info: Info, id: int) -> Optional[Sucursal]:
        _require_role(info, _READ_ROLES)
        try:
            row = get_sucursal_by_id(id)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        return _row_to_sucursal(row) if row else None


@strawberry.type
class Mutation:
    @strawberry.mutation
    def crear_sucursal(self, info: Info, input: SucursalInput) -> Sucursal:
        _require_role(info, _WRITE_ROLES)
        _validate_input(input)
        try:
            row = create_sucursal(_build_payload(input))
        except IntegrityError:
            raise ValueError("Ya existe una sucursal activa con el mismo nombre y dirección")
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        return _row_to_sucursal(row)

    @strawberry.mutation
    def actualizar_sucursal(self, info: Info, id: int, input: SucursalInput) -> Sucursal:
        _require_role(info, _WRITE_ROLES)
        _validate_input(input)
        try:
            row = update_sucursal(id, _build_payload(input))
        except IntegrityError:
            raise ValueError("Ya existe una sucursal activa con el mismo nombre y dirección")
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        if not row:
            raise ValueError(f"Sucursal {id} no encontrada")
        return _row_to_sucursal(row)

    @strawberry.mutation
    def cambiar_estado_sucursal(self, info: Info, id: int, estado: str) -> Sucursal:
        _require_role(info, _WRITE_ROLES)
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
        _require_role(info, _WRITE_ROLES)
        try:
            result = delete_sucursal(id)
        except OperationalError as exc:
            raise RuntimeError("Base de datos no disponible") from exc
        if not result:
            raise ValueError(f"Sucursal {id} no encontrada")
        return True


schema = strawberry.Schema(query=Query, mutation=Mutation)


async def get_graphql_context(
    current_user: AuthenticatedUser | None = Depends(get_optional_current_active_user),
) -> dict:
    return {"current_user": current_user}


graphql_router = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
)
