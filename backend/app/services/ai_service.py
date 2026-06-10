from __future__ import annotations

from datetime import datetime, timezone
import json
import mimetypes
from pathlib import Path
import uuid
import urllib.error
import urllib.request

from app.config import settings


class AIServiceError(Exception):
    pass


def _build_multipart_body(fields: dict[str, str], file_field_name: str, file_path: Path) -> tuple[bytes, str]:
    boundary = f"----sw2ai{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for key, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
            str(value).encode(),
            b"\r\n",
        ])

    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        (
            f'Content-Disposition: form-data; name="{file_field_name}"; '
            f'filename="{file_path.name}"\r\n'
        ).encode(),
        f"Content-Type: {mime_type}\r\n\r\n".encode(),
        file_path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    return b"".join(chunks), boundary


def _post_request(url: str, *, data: bytes, headers: dict[str, str]) -> dict[str, object]:
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=settings.ai_service_timeout_seconds) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="ignore")
        raise AIServiceError(f"HTTP {exc.code} en {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AIServiceError(f"No se pudo conectar a {url}: {exc.reason}") from exc


def _post_file(endpoint: str, *, emergency_id: int, field_name: str, file_path: str | Path) -> dict[str, object]:
    path = Path(file_path)
    if not path.is_file():
        raise AIServiceError(f"Archivo no encontrado para enviar a VM3: {path}")
    body, boundary = _build_multipart_body({"emergencia_id": str(emergency_id)}, field_name, path)
    return _post_request(
        f"{settings.base_url_ai}{endpoint}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def _post_json(endpoint: str, payload: dict[str, object]) -> dict[str, object]:
    return _post_request(
        f"{settings.base_url_ai}{endpoint}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )


def upload_image(emergency_id: int, image_path: str | Path) -> dict[str, object]:
    return _post_file("/ai/evidencias/imagen", emergency_id=emergency_id, field_name="imagen", file_path=image_path)


def upload_audio(emergency_id: int, audio_path: str | Path) -> dict[str, object]:
    return _post_file("/ai/evidencias/audio", emergency_id=emergency_id, field_name="audio", file_path=audio_path)


def speech_to_text(emergency_id: int, audio_path: str | Path) -> dict[str, object]:
    return _post_file("/ai/speech-to-text", emergency_id=emergency_id, field_name="audio", file_path=audio_path)


def classify_incident(texto: str) -> dict[str, object]:
    return _post_json("/ai/clasificar-incidente", {"texto": texto})


def _build_incident_text(problem_type: str, description: str | None, transcript: str | None) -> str:
    parts = [problem_type.strip()]
    if description:
        parts.append(description.strip())
    if transcript:
        parts.append(transcript.strip())
    return ". ".join(part for part in parts if part)


def process_emergency_report_with_ai(
    *,
    emergency_id: int,
    problem_type: str,
    description: str | None,
    photo_paths: list[str],
    audio_path: str | None,
) -> dict[str, object]:
    uploads_root = Path(settings.uploads_dir)

    for photo_path in photo_paths:
        upload_image(emergency_id, uploads_root / photo_path)

    transcript: str | None = None
    transcript_status: str | None = None
    transcript_error: str | None = None

    if audio_path:
        absolute_audio_path = uploads_root / audio_path
        upload_audio(emergency_id, absolute_audio_path)
        speech_payload = speech_to_text(emergency_id, absolute_audio_path)
        transcript = str(speech_payload.get("texto") or "").strip() or None
        transcript_status = "completado"

    classification = classify_incident(_build_incident_text(problem_type, description, transcript))
    return {
        "ia_categoria": classification.get("categoria"),
        "ia_prioridad": classification.get("prioridad"),
        "ia_confidence": classification.get("confidence"),
        "ia_procesado_en": datetime.now(timezone.utc).isoformat(),
        "audio_transcript": transcript,
        "audio_transcript_status": transcript_status,
        "audio_transcript_error": transcript_error,
    }
