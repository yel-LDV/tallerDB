"""Almacenamiento local de fotos de anuncios.

Las imágenes se validan por cabecera (magic bytes) para evitar código
malicioso. Formatos permitidos: JPG, PNG, WebP. Máximo 5 MB por foto,
hasta 10 fotos por anuncio.
"""

import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

# Magic bytes para formatos soportados
IMAGE_MAGIC: dict[str, list[tuple[bytes, str]]] = {
    "jpg": [(b"\xff\xd8\xff", "JPEG")],
    "png": [(b"\x89PNG\r\n\x1a\n", "PNG")],
    "webp": [(b"RIFF", "WebP (check WEBP)")],
}

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_PHOTOS_PER_ANNOUNCEMENT = 10


class InvalidImage(ValueError):
    """El archivo no es una imagen válida."""


class ImageTooLarge(InvalidImage):
    """La imagen supera el tamaño máximo configurado."""


class TooManyPhotos(ValueError):
    """El anuncio ya tiene el máximo de fotos permitido."""


def fotos_dir() -> Path:
    directory = Path(settings.uploads_dir).expanduser().resolve() / "fotos"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _detect_format(header: bytes) -> str:
    """Detecta el formato de imagen a partir de los magic bytes."""
    if header[:3] == b"\xff\xd8\xff":
        return "jpg"
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if header[:4] == b"RIFF":
        # WebP tiene "WEBP" en bytes 8-12
        if len(header) >= 12 and header[8:12] == b"WEBP":
            return "webp"
    raise InvalidImage("El archivo no es una imagen válida (JPG, PNG o WebP).")


async def save_photo(
    upload: UploadFile,
    max_bytes: int = 5 * 1024 * 1024,
    current_count: int = 0,
) -> tuple[str, int, str]:
    """Valida y guarda una foto. Devuelve (clave interna, tamaño, formato)."""
    if current_count >= MAX_PHOTOS_PER_ANNOUNCEMENT:
        raise TooManyPhotos(
            f"Se permiten como máximo {MAX_PHOTOS_PER_ANNOUNCEMENT} fotos por anuncio."
        )

    filename = (upload.filename or "").strip()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidImage("El archivo debe ser JPG, PNG o WebP.")

    content_type = (upload.content_type or "").lower().split(";")[0].strip()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidImage("El tipo de archivo no es una imagen válida.")

    directory = fotos_dir()
    key = f"{uuid.uuid4().hex}.{ext}"
    destination = directory / key

    header = b""
    total = 0
    temp_name: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=directory, suffix=".part", delete=False
        ) as temp_file:
            temp_name = temp_file.name
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ImageTooLarge(
                        f"La imagen supera el límite de "
                        f"{max_bytes // (1024 * 1024)} MB."
                    )
                if len(header) < 12:
                    header += chunk[: 12 - len(header)]
                temp_file.write(chunk)

            if total == 0:
                raise InvalidImage("El archivo está vacío.")

            formato = _detect_format(header)

            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_name, destination)
        temp_name = None
        return key, total, formato
    except Exception:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def photo_path(key: str | None) -> Path | None:
    """Ruta segura de una clave interna; evita path traversal."""
    if not key:
        return None
    safe_name = Path(key).name
    path = fotos_dir() / safe_name
    return path if path.is_file() else None


def delete_photo(key: str | None) -> None:
    """Borra una foto; el fallo de disco no debe romper la operación de BD."""
    path = photo_path(key)
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("No se pudo borrar la foto %s", path)
