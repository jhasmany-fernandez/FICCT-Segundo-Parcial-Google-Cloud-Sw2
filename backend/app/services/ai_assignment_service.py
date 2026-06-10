from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from app.db import list_mecanicos_for_ai_recommendation, list_sucursales


SPECIALTY_BY_CATEGORY = {
    "falla_motor": "Motor",
    "bateria": "Electricidad",
    "combustible": "General",
    "cerrajeria": "Cerrajeria",
    "accidente": "Emergencia",
}


def _normalize_text(value: object) -> str:
    return str(value or "").strip().casefold()


def _normalize_specialty(value: object) -> str:
    normalized = _normalize_text(value)
    return normalized.replace("í", "i")


def resolve_required_specialty(categoria: str | None) -> str | None:
    if categoria is None:
        return None
    return SPECIALTY_BY_CATEGORY.get(_normalize_text(categoria))


def _has_compatible_specialty(mechanic_specialty: object, required_specialty: str | None) -> bool:
    if required_specialty is None:
        return True

    normalized_required = _normalize_specialty(required_specialty)
    normalized_mechanic = _normalize_specialty(mechanic_specialty)

    if normalized_required == "general":
        return True

    return normalized_required in normalized_mechanic


def _distance_km(
    origin_lat: object,
    origin_lng: object,
    destination_lat: object,
    destination_lng: object,
) -> float | None:
    try:
        lat1 = radians(float(origin_lat))
        lng1 = radians(float(origin_lng))
        lat2 = radians(float(destination_lat))
        lng2 = radians(float(destination_lng))
    except (TypeError, ValueError):
        return None

    delta_lat = lat2 - lat1
    delta_lng = lng2 - lng1
    a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lng / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))


def build_ai_assignment_recommendation(emergency: dict[str, object]) -> dict[str, object]:
    categoria = str(emergency.get("ia_categoria") or "").strip() or None
    prioridad = str(emergency.get("ia_prioridad") or "").strip() or None
    confidence = emergency.get("ia_confidence")
    required_specialty = resolve_required_specialty(categoria)
    nearest_workshop_id = emergency.get("nearest_workshop_id")

    sucursales = [row for row in list_sucursales(estado="ACTIVO") if row.get("operativa")]
    compatible_sucursales: list[dict[str, object]] = []

    for sucursal in sucursales:
        mechanics = list_mecanicos_for_ai_recommendation(int(sucursal["id"]))
        compatible_mechanics = [
            mechanic
            for mechanic in mechanics
            if _has_compatible_specialty(mechanic.get("specialty"), required_specialty)
        ]
        if not compatible_mechanics:
            continue

        distance_km = _distance_km(
            emergency.get("latitude"),
            emergency.get("longitude"),
            sucursal.get("latitud"),
            sucursal.get("longitud"),
        )
        compatible_sucursales.append(
            {
                **sucursal,
                "distance_km": distance_km,
                "compatible_mechanics": compatible_mechanics,
            }
        )

    selected_sucursal = None
    if nearest_workshop_id is not None:
        selected_sucursal = next(
            (
                sucursal
                for sucursal in compatible_sucursales
                if int(sucursal["id"]) == int(nearest_workshop_id)
            ),
            None,
        )

    if selected_sucursal is None and compatible_sucursales:
        selected_sucursal = min(
            compatible_sucursales,
            key=lambda sucursal: (
                sucursal.get("distance_km") is None,
                sucursal.get("distance_km") or 0.0,
                int(sucursal["id"]),
            ),
        )

    recommended_mechanics: list[dict[str, object]] = []
    recommended_mechanic = None

    if selected_sucursal is not None:
        recommended_mechanics = sorted(
            selected_sucursal["compatible_mechanics"],
            key=lambda mechanic: (
                0 if _normalize_text(mechanic.get("status")) == "disponible" else 1,
                0 if _has_compatible_specialty(mechanic.get("specialty"), required_specialty) else 1,
                selected_sucursal.get("distance_km") is None,
                selected_sucursal.get("distance_km") or 0.0,
                int(mechanic.get("carga_trabajo") or 0),
                int(mechanic["id"]),
            ),
        )
        if recommended_mechanics:
            recommended_mechanic = recommended_mechanics[0]

    return {
        "categoria": categoria,
        "prioridad": prioridad,
        "confidence": confidence,
        "especialidad_requerida": required_specialty,
        "sucursal_recomendada_id": selected_sucursal.get("id") if selected_sucursal else None,
        "sucursal_recomendada_nombre": selected_sucursal.get("nombre") if selected_sucursal else None,
        "mecanico_recomendado_id": recommended_mechanic.get("id") if recommended_mechanic else None,
        "mecanico_recomendado_nombre": recommended_mechanic.get("full_name") if recommended_mechanic else None,
        "mecanicos_recomendados": [
            {
                "id": mechanic["id"],
                "full_name": mechanic.get("full_name"),
                "specialty": mechanic.get("specialty"),
                "status": mechanic.get("status"),
                "sucursal_id": mechanic.get("sucursal_id"),
                "sucursal_nombre": mechanic.get("sucursal_nombre"),
                "carga_trabajo": int(mechanic.get("carga_trabajo") or 0),
                "distance_km": selected_sucursal.get("distance_km") if selected_sucursal else None,
            }
            for mechanic in recommended_mechanics[:5]
        ],
    }
