"""Router de fotos para anuncios.

Endpoints para subir, eliminar y servir fotos de un anuncio.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_auth
from app.database import get_db
from app.fotos.storage import (
    ImageTooLarge,
    InvalidImage,
    TooManyPhotos,
    delete_photo,
    photo_path,
    save_photo,
)
from app.models.anuncio import Anuncio
from app.models.foto import Foto
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fotos", tags=["Fotos"])


@router.post("/anuncio/{anuncio_id}", response_model=dict)
async def subir_foto(
    anuncio_id: int,
    archivo: UploadFile = File(..., description="Foto JPG, PNG o WebP (máx 5MB)"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Subir una foto a un anuncio. Solo el vendedor puede subir fotos."""
    result = await db.get(Anuncio, anuncio_id)
    if not result:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    if result.vendedor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el vendedor puede subir fotos")

    # Contar fotos actuales
    count_result = await db.execute(
        select(func.count(Foto.id)).where(Foto.anuncio_id == anuncio_id)
    )
    current_count = count_result.scalar_one()

    try:
        key, size, formato = await save_photo(archivo, current_count=current_count)
    except TooManyPhotos as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImageTooLarge as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
    except InvalidImage as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    foto = Foto(
        anuncio_id=anuncio_id,
        archivo_key=key,
        tamano=size,
        orden=current_count,
        formato=formato,
    )
    db.add(foto)
    await db.commit()
    await db.refresh(foto)

    return {
        "id": foto.id,
        "anuncio_id": foto.anuncio_id,
        "orden": foto.orden,
        "formato": foto.formato,
        "tamano": foto.tamano,
        "url": f"/fotos/{foto.id}",
    }


@router.delete("/anuncio/{anuncio_id}/{foto_id}", status_code=200)
async def eliminar_foto(
    anuncio_id: int,
    foto_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una foto de un anuncio. Solo el vendedor puede eliminar."""
    result = await db.get(Anuncio, anuncio_id)
    if not result:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    if result.vendedor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el vendedor puede eliminar fotos")

    foto = await db.get(Foto, foto_id)
    if not foto or foto.anuncio_id != anuncio_id:
        raise HTTPException(status_code=404, detail="Foto no encontrada")

    old_key = foto.archivo_key
    await db.delete(foto)
    await db.commit()
    delete_photo(old_key)

    return {"success": True, "id": foto_id, "mensaje": "Foto eliminada"}


@router.get("/{foto_id}")
async def servir_foto(
    foto_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Sirve una foto del anuncio (pública)."""
    foto = await db.get(Foto, foto_id)
    if not foto:
        raise HTTPException(status_code=404, detail="Foto no encontrada")

    path = photo_path(foto.archivo_key)
    if path is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    content_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(foto.formato, "image/jpeg")

    return FileResponse(
        path,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
