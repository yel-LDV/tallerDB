"""Router de anuncios — CRUD, catálogo público y página de detalle.

Cada usuario puede publicar sus autos en venta. Los anuncios son públicos
y accesibles por su slug: /auto/toyota-corolla-2023-abc123.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anuncios.schemas import (
    AnuncioCreate,
    AnuncioOut,
    AnuncioUpdate,
    TIPOS_CARROCERIA,
    TRANSMISIONES,
)
from app.anuncios.slug_generator import generate_slug
from app.auth.deps import get_current_user, require_auth
from app.config import settings
from app.database import get_db
from app.models.anuncio import Anuncio, AnuncioEstado
from app.models.foto import Foto
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auto", tags=["Anuncios"])
templates = Jinja2Templates(directory="app/templates")


def base_context(request: Request, **extra):
    return {"request": request, "app_name": settings.app_name, **extra}


# ===================== Página para publicar vehículo =====================

@router.get("/publicar", response_class=HTMLResponse)
async def publicar_page(
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Página para publicar un nuevo vehículo. Requiere autenticación."""
    return templates.TemplateResponse(
        "publicar.html",
        base_context(
            request,
            user=current_user,
        ),
    )


# ===================== Catálogo público =====================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def catalogo_page(
    request: Request,
    q: Optional[str] = Query(default=None),
    marca: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    anio_min_str: Optional[str] = Query(default=None),
    anio_max_str: Optional[str] = Query(default=None),
    orden: Optional[str] = Query(default="recientes"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=24, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Catálogo público: anuncios activos + sección de vendidos recientes."""
    # Convertir strings vacíos a None y luego a int
    anio_min = int(anio_min_str) if anio_min_str and anio_min_str.strip() else None
    anio_max = int(anio_max_str) if anio_max_str and anio_max_str.strip() else None

    stmt = select(Anuncio).where(Anuncio.estado == AnuncioEstado.activo)

    # Filtros
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Anuncio.marca.ilike(like),
                Anuncio.nombre.ilike(like),
                Anuncio.descripcion.ilike(like),
            )
        )
    if marca:
        stmt = stmt.where(Anuncio.marca == marca)
    if tipo:
        stmt = stmt.where(Anuncio.tipo == tipo)
    if anio_min:
        stmt = stmt.where(Anuncio.anio >= anio_min)
    if anio_max:
        stmt = stmt.where(Anuncio.anio <= anio_max)

    # Conteo total activos
    count_stmt = select(func.count(Anuncio.id)).where(Anuncio.estado == AnuncioEstado.activo)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one() or 0

    # Orden
    ordenes = {
        "recientes": Anuncio.creado_at.desc(),
        "precio_asc": Anuncio.precio_oferta.asc(),
        "precio_desc": Anuncio.precio_oferta.desc(),
        "anio_desc": Anuncio.anio.desc(),
        "marca": Anuncio.marca.asc(),
    }
    stmt = stmt.order_by(ordenes.get(orden, ordenes["recientes"]))

    # Paginación
    total_paginas = max(1, (total + per_page - 1) // per_page)
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    anuncios = result.scalars().all()

    # Marcas para filtro
    marcas_result = await db.execute(
        select(Anuncio.marca).distinct().where(Anuncio.estado == AnuncioEstado.activo).order_by(Anuncio.marca)
    )
    marcas = [m for (m,) in marcas_result.all()]

    # Anuncios vendidos recientes (últimos 8) para mostrar en el catálogo
    vendidos_result = await db.execute(
        select(Anuncio)
        .where(Anuncio.estado == AnuncioEstado.vendido)
        .order_by(Anuncio.actualizado_at.desc())
        .limit(8)
    )
    vendidos = vendidos_result.scalars().all()

    return templates.TemplateResponse(
        "catalogo.html",
        base_context(
            request,
            user=current_user,
            anuncios=anuncios,
            vendidos=vendidos,
            marcas=marcas,
            tipos=TIPOS_CARROCERIA,
            filtros={"q": q or "", "marca": marca or "", "tipo": tipo or "", "anio_min": anio_min, "anio_max": anio_max, "orden": orden},
            paginacion={
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_paginas": total_paginas,
            },
        ),
    )


# ===================== API JSON (antes de /{slug} para evitar conflicto) =====================

@router.get("/api", response_model=list[AnuncioOut])
async def api_listar(
    q: Optional[str] = Query(default=None, max_length=100),
    marca: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    anio_min_str: Optional[str] = Query(default=None),
    anio_max_str: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """API pública de anuncios activos."""
    anio_min = int(anio_min_str) if anio_min_str and anio_min_str.strip() else None
    anio_max = int(anio_max_str) if anio_max_str and anio_max_str.strip() else None

    stmt = select(Anuncio).where(Anuncio.estado == AnuncioEstado.activo)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Anuncio.marca.ilike(like), Anuncio.nombre.ilike(like))
        )
    if marca:
        stmt = stmt.where(Anuncio.marca == marca)
    if tipo:
        stmt = stmt.where(Anuncio.tipo == tipo)
    if anio_min:
        stmt = stmt.where(Anuncio.anio >= anio_min)
    if anio_max:
        stmt = stmt.where(Anuncio.anio <= anio_max)
    stmt = stmt.order_by(Anuncio.creado_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/api", response_model=AnuncioOut, status_code=status.HTTP_201_CREATED)
async def api_crear(
    data: AnuncioCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Crear un nuevo anuncio. Cualquier usuario autenticado puede publicar."""
    slug = generate_slug(data.marca, data.nombre, data.anio)
    anuncio = Anuncio(
        vendedor_id=current_user.id,
        slug=slug,
        **data.model_dump(),
    )
    db.add(anuncio)
    await db.commit()
    await db.refresh(anuncio)
    return anuncio


@router.get("/api/{anuncio_id}", response_model=AnuncioOut)
async def api_obtener(
    anuncio_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Obtener un anuncio por ID."""
    anuncio = await db.get(Anuncio, anuncio_id)
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    return anuncio


@router.put("/api/{anuncio_id}", response_model=AnuncioOut)
async def api_actualizar(
    anuncio_id: int,
    data: AnuncioUpdate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un anuncio. Solo el vendedor puede editar."""
    anuncio = await db.get(Anuncio, anuncio_id)
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    if anuncio.vendedor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el vendedor puede editar")

    cambios = data.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(anuncio, campo, valor)

    await db.commit()
    await db.refresh(anuncio)
    return anuncio


@router.delete("/api/{anuncio_id}", status_code=200)
async def api_eliminar(
    anuncio_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un anuncio. Solo el vendedor puede eliminar."""
    anuncio = await db.get(Anuncio, anuncio_id)
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    if anuncio.vendedor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el vendedor puede eliminar")

    await db.delete(anuncio)
    await db.commit()
    return {"success": True, "id": anuncio_id, "mensaje": "Anuncio eliminado"}


# ===================== Página de detalle del anuncio (después de /api) =====================

@router.get("/{slug}", response_class=HTMLResponse)
async def anuncio_detalle(
    request: Request,
    slug: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Página pública de detalle de un anuncio con fotos y especificaciones."""
    result = await db.execute(select(Anuncio).where(Anuncio.slug == slug))
    anuncio = result.scalar_one_or_none()
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    # Fotos
    fotos_result = await db.execute(
        select(Foto).where(Foto.anuncio_id == anuncio.id).order_by(Foto.orden)
    )
    fotos = fotos_result.scalars().all()

    return templates.TemplateResponse(
        "anuncio_detalle.html",
        base_context(
            request,
            user=current_user,
            anuncio=anuncio,
            fotos=fotos,
        ),
    )
