"""Almacenamiento local de modelos 3D (GLB).

Los archivos se guardan fuera de ``app/static`` para servirlos mediante un
endpoint autenticado y no exponerlos públicamente.
"""

import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

GLB_MAGIC = b"glTF"
GLB_VERSION = 2
ALLOWED_CONTENT_TYPES = {
    "model/gltf-binary",
    "application/octet-stream",
}


class InvalidModel3D(ValueError):
    """El archivo no es un GLB válido."""


class Model3DTooLarge(InvalidModel3D):
    """El archivo supera el tamaño máximo configurado."""


def model3d_dir() -> Path:
    directory = Path(settings.uploads_dir).expanduser().resolve() / "modelos3d"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def save_glb(upload: UploadFile, max_bytes: int) -> tuple[str, int]:
    """Valida y guarda un GLB. Devuelve (clave interna, tamaño en bytes)."""
    filename = (upload.filename or "").strip()
    if not filename.lower().endswith(".glb"):
        raise InvalidModel3D("El archivo debe tener extensión .glb.")

    content_type = (upload.content_type or "").lower().split(";")[0].strip()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidModel3D("El tipo de archivo no es un modelo GLB válido.")

    directory = model3d_dir()
    key = f"{uuid.uuid4().hex}.glb"
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
                    raise Model3DTooLarge(
                        f"El modelo 3D supera el límite de "
                        f"{max_bytes // (1024 * 1024)} MB."
                    )
                if len(header) < 20:
                    header += chunk[: 20 - len(header)]
                temp_file.write(chunk)

            if len(header) < 20:
                raise InvalidModel3D("El archivo GLB está incompleto.")

            if header[:4] != GLB_MAGIC:
                raise InvalidModel3D("El archivo no tiene la cabecera GLB esperada.")

            version = int.from_bytes(header[4:8], "little")
            if version != GLB_VERSION:
                raise InvalidModel3D("Solo se admiten modelos GLB versión 2.")

            declared_size = int.from_bytes(header[8:12], "little")
            if declared_size != total:
                raise InvalidModel3D("La cabecera GLB no coincide con el tamaño real.")

            # Primer chunk obligatorio: JSON con metadatos glTF.
            json_length = int.from_bytes(header[12:16], "little")
            chunk_type = header[16:20]
            if chunk_type != b"JSON":
                raise InvalidModel3D("El primer chunk del GLB debe ser JSON.")
            if json_length <= 0 or json_length % 4 != 0:
                raise InvalidModel3D("El chunk JSON del GLB no es válido.")
            if 20 + json_length > total:
                raise InvalidModel3D(
                    "El chunk JSON del GLB excede el tamaño del archivo."
                )

            temp_file.flush()
            os.fsync(temp_file.fileno())

        with open(temp_name, "rb") as temp_read:
            temp_read.seek(20)
            json_chunk = temp_read.read(json_length)
        try:
            json.loads(json_chunk.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidModel3D(
                "El chunk JSON del GLB no contiene JSON válido."
            ) from exc

        os.replace(temp_name, destination)
        temp_name = None
        return key, total
    except Exception:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def glb_path(key: str | None) -> Path | None:
    """Ruta segura de una clave interna; evita path traversal."""
    if not key:
        return None
    safe_name = Path(key).name
    path = model3d_dir() / safe_name
    return path if path.is_file() else None


def delete_glb(key: str | None) -> None:
    """Borra un GLB; el fallo de disco no debe romper la operación de BD."""
    path = glb_path(key)
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("No se pudo borrar el archivo 3D %s", path)
