from pathlib import Path

from app.config import settings


UPLOADS_ROOT = Path(settings.uploads_dir)
VEHICLE_UPLOADS_DIR = UPLOADS_ROOT / "vehicles"
EMERGENCY_UPLOADS_DIR = UPLOADS_ROOT / "emergencias"
EMERGENCY_PHOTOS_DIR = EMERGENCY_UPLOADS_DIR / "photos"
EMERGENCY_AUDIO_DIR = EMERGENCY_UPLOADS_DIR / "audio"

UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
VEHICLE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EMERGENCY_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
EMERGENCY_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

PROTECTED_ADMIN_EMAIL = settings.protected_admin_email.lower().strip()
PROTECTED_ADMIN_ROLE = "admin"
PROTECTED_ADMIN_ID = 0
SECRETARIA_ROLE = "secretaria"
MECANICO_ROLE = "mecanico"
WORKSHOP_ROLE = "workshop"

MAX_EMERGENCY_PHOTOS = 6
MAX_EMERGENCY_PHOTO_BYTES = 20 * 1024 * 1024
MAX_EMERGENCY_AUDIO_BYTES = 40 * 1024 * 1024
ALLOWED_PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_AUDIO_SUFFIXES = {".aac", ".m4a", ".mp3", ".wav", ".ogg", ".webm"}
