"""Router de la categoría Modelos (catálogo de autos).

Incluye:
- Página HTML con el catálogo (galería) y filtros de consulta.
- API JSON para las operaciones CRUD (insertar, actualizar, borrar, consultar).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Integer, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_auth
from app.config import settings
from app.database import get_db
from app.models.modelo import Modelo
from app.models.user import User
from app.schemas.modelo import (
    TIPOS_CARROCERIA,
    TRANSMISIONES,
    ModeloCreate,
    ModeloOut,
    ModeloUpdate,
)

router = APIRouter(prefix="/modelos", tags=["Modelos"])
templates = Jinja2Templates(directory="app/templates")

# Opciones de ordenamiento disponibles para las consultas
ORDENES = {
    "recientes": Modelo.created_at.desc(),
    "precio_asc": Modelo.precio.asc(),
    "precio_desc": Modelo.precio.desc(),
    "anio_desc": Modelo.anio.desc(),
    "anio_asc": Modelo.anio.asc(),
    "marca": Modelo.marca.asc(),
}


def _aplicar_filtros(stmt, q, marca, tipo, disponible, anio_min, anio_max):
    """Construye el WHERE de una consulta de modelos de forma dinámica."""
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Modelo.marca.ilike(like),
                Modelo.nombre.ilike(like),
                Modelo.descripcion.ilike(like),
            )
        )
    if marca:
        stmt = stmt.where(Modelo.marca == marca)
    if tipo:
        stmt = stmt.where(Modelo.tipo == tipo)
    if disponible is not None:
        stmt = stmt.where(Modelo.disponible == disponible)
    if anio_min is not None:
        stmt = stmt.where(Modelo.anio >= anio_min)
    if anio_max is not None:
        stmt = stmt.where(Modelo.anio <= anio_max)
    return stmt


# ===================== Página HTML =====================
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def modelos_page(
    request: Request,
    q: Optional[str] = Query(default=None),
    marca: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    disponible: Optional[str] = Query(default=None),
    anio_min: Optional[int] = Query(default=None, ge=1900, le=2100),
    anio_max: Optional[int] = Query(default=None, ge=1900, le=2100),
    orden: str = Query(default="recientes"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    # Interpretar el filtro de disponibilidad (viene como texto desde el form)
    disp_bool: Optional[bool] = None
    if disponible in ("1", "true", "si"):
        disp_bool = True
    elif disponible in ("0", "false", "no"):
        disp_bool = False

    stmt = _aplicar_filtros(
        select(Modelo), q, marca, tipo, disp_bool, anio_min, anio_max
    )
    stmt = stmt.order_by(ORDENES.get(orden, ORDENES["recientes"]))
    result = await db.execute(stmt)
    modelos = result.scalars().all()

    # Datos para los selectores de filtro
    marcas_result = await db.execute(
        select(Modelo.marca).distinct().order_by(Modelo.marca)
    )
    marcas = [m for (m,) in marcas_result.all()]

    # Estadísticas globales (consultas de agregación: COUNT, SUM, AVG, MIN, MAX)
    stats_result = await db.execute(
        select(
            func.count(Modelo.id),
            func.sum(func.cast(Modelo.disponible, Integer)),
            func.avg(Modelo.precio),
            func.min(Modelo.anio),
            func.max(Modelo.anio),
        )
    )
    total, disponibles, precio_prom, anio_min_db, anio_max_db = stats_result.one()

    stats = {
        "total": total or 0,
        "disponibles": disponibles or 0,
        "precio_promedio": float(precio_prom or 0),
        "anio_min": anio_min_db,
        "anio_max": anio_max_db,
    }

    filtros_activos = bool(q or marca or tipo or disp_bool is not None or anio_min or anio_max)

    return templates.TemplateResponse(
        "modelos.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "user": current_user,
            "modelos": modelos,
            "marcas": marcas,
            "tipos": TIPOS_CARROCERIA,
            "transmisiones": TRANSMISIONES,
            "stats": stats,
            "filtros": {
                "q": q or "",
                "marca": marca or "",
                "tipo": tipo or "",
                "disponible": disponible or "",
                "anio_min": anio_min or "",
                "anio_max": anio_max or "",
                "orden": orden,
            },
            "filtros_activos": filtros_activos,
        },
    )


# ===================== API JSON (CRUD + consultas) =====================
@router.get("/api", response_model=list[ModeloOut])
async def api_listar(
    q: Optional[str] = Query(default=None, description="Búsqueda por marca, modelo o descripción"),
    marca: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    disponible: Optional[bool] = Query(default=None),
    anio_min: Optional[int] = Query(default=None, ge=1900, le=2100),
    anio_max: Optional[int] = Query(default=None, ge=1900, le=2100),
    orden: str = Query(default="recientes"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Consulta (READ) de modelos con filtros y paginación."""
    stmt = _aplicar_filtros(
        select(Modelo), q, marca, tipo, disponible, anio_min, anio_max
    )
    stmt = (
        stmt.order_by(ORDENES.get(orden, ORDENES["recientes"]))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/api/{modelo_id}", response_model=ModeloOut)
async def api_obtener(
    modelo_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Consulta (READ) de un modelo por su id."""
    modelo = await db.get(Modelo, modelo_id)
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    return modelo


@router.post("/api", response_model=ModeloOut, status_code=status.HTTP_201_CREATED)
async def api_crear(
    data: ModeloCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Inserción (CREATE) de un nuevo modelo. Requiere permisos de admin."""
    modelo = Modelo(**data.model_dump())
    db.add(modelo)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ya existe un modelo con esa marca, nombre y año",
        )
    await db.refresh(modelo)
    return modelo


@router.put("/api/{modelo_id}", response_model=ModeloOut)
async def api_actualizar(
    modelo_id: int,
    data: ModeloUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Actualización (UPDATE) parcial de un modelo. Requiere permisos de admin."""
    modelo = await db.get(Modelo, modelo_id)
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")

    cambios = data.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(modelo, campo, valor)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Los datos entran en conflicto con otro modelo existente",
        )
    await db.refresh(modelo)
    return modelo


@router.delete("/api/{modelo_id}", status_code=status.HTTP_200_OK)
async def api_eliminar(
    modelo_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Borrado (DELETE) de un modelo. Requiere permisos de admin."""
    modelo = await db.get(Modelo, modelo_id)
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")

    await db.delete(modelo)
    await db.commit()
    return {"success": True, "id": modelo_id, "mensaje": "Modelo eliminado"}
