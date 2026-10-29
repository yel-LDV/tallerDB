"""Router de la categoría Modelos (catálogo de autos).

Incluye:
- Página HTML con el catálogo (galería) y filtros de consulta.
- API JSON para las operaciones CRUD (insertar, actualizar, borrar, consultar).
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, BeforeValidator, Field
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_auth
from app.config import settings
from app.database import get_db
from app.modelos.storage import (
    InvalidModel3D,
    Model3DTooLarge,
    delete_glb,
    glb_path,
    save_glb,
)
from app.models.modelo import Modelo
from app.models.user import User
from app.schemas.modelo import (
    TIPOS_CARROCERIA,
    TRANSMISIONES,
    ModeloCreate,
    ModeloOut,
    ModeloUpdate,
)

logger = logging.getLogger(__name__)

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


def _vacio_a_none(valor):
    """Antes de validar, convierte cadenas vacías en None (API JSON)."""
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


# En la API se conserva el tipo entero en OpenAPI, pero se aceptan años vacíos.
AnioApi = Annotated[
    Optional[Annotated[int, Field(ge=1900, le=2100)]],
    BeforeValidator(_vacio_a_none),
]


class _FiltrosAnioApi(BaseModel):
    anio_min: AnioApi = None
    anio_max: AnioApi = None


def _limpiar_texto(valor: Optional[str]) -> Optional[str]:
    """Normaliza un parámetro de texto: quita espacios y convierte vacío en None."""
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


def _escape_like(valor: str) -> str:
    """Escapa los comodines de SQL LIKE para que la búsqueda sea literal."""
    return valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _parse_anio(valor: Optional[str], nombre: str) -> tuple[Optional[int], Optional[str]]:
    """Convierte el valor de un filtro de año en int, sin romper el formulario."""
    if valor is None or not valor.strip():
        return None, None

    try:
        anio = int(valor)
    except ValueError:
        return None, f"{nombre} debe ser un número entero."

    if not 1900 <= anio <= 2100:
        return None, f"{nombre} debe estar entre 1900 y 2100."

    return anio, None


def _parse_disponible(valor: Optional[str]) -> tuple[Optional[bool], Optional[str]]:
    """Acepta los valores usados por el formulario y la API."""
    if valor is None or not valor.strip():
        return None, None

    normalizado = valor.strip().lower()
    if normalizado in ("1", "true", "si", "sí"):
        return True, None
    if normalizado in ("0", "false", "no"):
        return False, None

    return None, "La disponibilidad seleccionada no es válida."


def _parse_tipo(valor: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Valida el tipo de carrocería contra las opciones del catálogo."""
    if not valor:
        return None, None
    if valor not in TIPOS_CARROCERIA:
        return None, "El tipo de carrocería seleccionado no es válido."
    return valor, None


def _parse_orden(valor: Optional[str]) -> str:
    """Devuelve un criterio de ordenamiento válido."""
    return valor if valor in ORDENES else "recientes"


def _parse_entero(valor: Optional[str], default: int, maximo: Optional[int] = None) -> int:
    """Convierte page/per_page sin devolver un 422 si la URL trae basura."""
    if valor is None or not valor.strip():
        return default

    try:
        numero = int(valor)
    except ValueError:
        return default

    if numero < 1:
        return default
    if maximo is not None:
        numero = min(numero, maximo)
    return numero


def _url_pagina(request: Request, page: int) -> str:
    """Construye una URL de paginación conservando los filtros actuales."""
    params = [(k, v) for k, v in request.query_params.multi_items() if k != "page"]
    params.append(("page", str(page)))
    return f"{request.url.path}?{urlencode(params)}"


def _aplicar_filtros(stmt, q, marca, tipo, disponible, anio_min, anio_max):
    """Construye el WHERE de una consulta de modelos de forma dinámica."""
    if q:
        like = f"%{_escape_like(q.strip())}%"
        stmt = stmt.where(
            or_(
                Modelo.marca.ilike(like, escape="\\"),
                Modelo.nombre.ilike(like, escape="\\"),
                Modelo.descripcion.ilike(like, escape="\\"),
                Modelo.color.ilike(like, escape="\\"),
                Modelo.transmision.ilike(like, escape="\\"),
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
    q: Optional[str] = Query(default=None, description="Búsqueda general"),
    marca: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    disponible: Optional[str] = Query(default=None),
    anio_min: Optional[str] = Query(default=None, description="Año mínimo (1900-2100)"),
    anio_max: Optional[str] = Query(default=None, description="Año máximo (1900-2100)"),
    orden: Optional[str] = Query(default="recientes"),
    page: Optional[str] = Query(default=None, description="Página (desde 1)"),
    per_page: Optional[str] = Query(default=None, description="Resultados por página (máx. 100)"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    errores: list[str] = []

    # Normalizar todos los filtros antes de tocar la base de datos.
    q_limpio = _limpiar_texto(q)
    marca_limpia = _limpiar_texto(marca)
    page_num = _parse_entero(page, default=1)
    per_page_num = _parse_entero(per_page, default=24, maximo=100)

    tipo_limpio, error = _parse_tipo(_limpiar_texto(tipo))
    if error:
        errores.append(error)

    disp_bool, error = _parse_disponible(disponible)
    if error:
        errores.append(error)

    anio_min_i, error = _parse_anio(anio_min, "Año desde")
    if error:
        errores.append(error)

    anio_max_i, error = _parse_anio(anio_max, "Año hasta")
    if error:
        errores.append(error)

    if (
        anio_min_i is not None
        and anio_max_i is not None
        and anio_min_i > anio_max_i
    ):
        errores.append("El año desde no puede ser mayor que el año hasta.")
        anio_min_i = None
        anio_max_i = None

    orden_limpio = _parse_orden(orden)

    # Estadísticas de los resultados filtrados (COUNT, SUM, AVG, MIN, MAX)
    stats_stmt = _aplicar_filtros(
        select(
            func.count(Modelo.id),
            # ``cast(boolean, Integer)`` no es portable a PostgreSQL.
            func.sum(case((Modelo.disponible.is_(True), 1), else_=0)),
            func.avg(Modelo.precio),
            func.min(Modelo.anio),
            func.max(Modelo.anio),
        ),
        q_limpio,
        marca_limpia,
        tipo_limpio,
        disp_bool,
        anio_min_i,
        anio_max_i,
    )
    stats_result = await db.execute(stats_stmt)
    total, disponibles, precio_prom, anio_min_db, anio_max_db = stats_result.one()
    total = int(total or 0)

    # Paginación: se mantiene en 24 por defecto para no cambiar la vista actual.
    total_paginas = max(1, (total + per_page_num - 1) // per_page_num)
    page_num = min(page_num, total_paginas)

    stmt = _aplicar_filtros(
        select(Modelo),
        q_limpio,
        marca_limpia,
        tipo_limpio,
        disp_bool,
        anio_min_i,
        anio_max_i,
    )
    stmt = stmt.order_by(
        ORDENES.get(orden_limpio, ORDENES["recientes"]),
        Modelo.id.desc(),
    )
    stmt = stmt.offset((page_num - 1) * per_page_num).limit(per_page_num)
    result = await db.execute(stmt)
    modelos = result.scalars().all()

    # Datos para los selectores de filtro
    marcas_result = await db.execute(
        select(Modelo.marca).distinct().order_by(Modelo.marca)
    )
    marcas = [m for (m,) in marcas_result.all()]

    stats = {
        "total": total,
        "disponibles": int(disponibles or 0),
        "precio_promedio": float(precio_prom or 0),
        "anio_min": anio_min_db,
        "anio_max": anio_max_db,
    }

    filtros_activos = bool(
        q_limpio
        or marca_limpia
        or _limpiar_texto(tipo)
        or _limpiar_texto(disponible)
        or _limpiar_texto(anio_min)
        or _limpiar_texto(anio_max)
    )

    # Valores para volver a pintar el formulario (se conservan los años escritos).
    disponible_form = "1" if disp_bool is True else "0" if disp_bool is False else ""

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
            "max_3d_size_mb": settings.max_3d_size_mb,
            "stats": stats,
            "errores_filtros": errores,
            "filtros": {
                "q": q_limpio or "",
                "marca": marca_limpia or "",
                "tipo": tipo_limpio or "",
                "disponible": disponible_form,
                "anio_min": anio_min or "",
                "anio_max": anio_max or "",
                "orden": orden_limpio,
            },
            "filtros_activos": filtros_activos,
            "paginacion": {
                "page": page_num,
                "per_page": per_page_num,
                "total": total,
                "total_paginas": total_paginas,
                "inicio": (page_num - 1) * per_page_num + 1 if total else 0,
                "fin": min(page_num * per_page_num, total),
                "url_anterior": _url_pagina(request, page_num - 1) if page_num > 1 else None,
                "url_siguiente": (
                    _url_pagina(request, page_num + 1)
                    if page_num < total_paginas
                    else None
                ),
            },
        },
    )


# ===================== API JSON (CRUD + consultas) =====================
@router.get("/api", response_model=list[ModeloOut])
async def api_listar(
    q: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Búsqueda por marca, modelo, color, transmisión o descripción",
    ),
    marca: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    disponible: Optional[bool] = Query(default=None),
    anios: _FiltrosAnioApi = Depends(),
    orden: str = Query(default="recientes"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Consulta (READ) de modelos con filtros y paginación."""
    stmt = _aplicar_filtros(
        select(Modelo), q, marca, tipo, disponible, anios.anio_min, anios.anio_max
    )
    stmt = (
        stmt.order_by(
            ORDENES.get(_parse_orden(orden), ORDENES["recientes"]),
            Modelo.id.desc(),
        )
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

    old_key = modelo.modelo_3d_key
    await db.delete(modelo)
    await db.commit()
    # El archivo se borra después de confirmar la transacción para no perderlo
    # si la base de datos rechaza el DELETE.
    if old_key:
        delete_glb(old_key)
    return {"success": True, "id": modelo_id, "mensaje": "Modelo eliminado"}


# ===================== Modelo 3D (GLB) =====================
def _url_modelo_3d(modelo_id: int, subido_at: datetime | None = None) -> str:
    """URL interna del GLB con versión para invalidar cachés al reemplazarlo."""
    url = f"/modelos/{modelo_id}/3d"
    if subido_at is not None:
        # Milisegundos: dos reemplazos en el mismo segundo deben invalidar caché.
        version = int(
            subido_at.replace(tzinfo=timezone.utc).timestamp() * 1000
        )
        url = f"{url}?v={version}"
    return url


@router.post("/api/{modelo_id}/3d", response_model=ModeloOut)
async def api_subir_modelo_3d(
    modelo_id: int,
    archivo: UploadFile = File(..., description="Archivo GLB (glTF binario)"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Sube o reemplaza el modelo 3D de un auto. Requiere admin."""
    modelo = await db.get(Modelo, modelo_id)
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")

    max_bytes = settings.max_3d_size_mb * 1024 * 1024
    try:
        key, size = await save_glb(archivo, max_bytes)
    except Model3DTooLarge as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
    except InvalidModel3D as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    old_key = modelo.modelo_3d_key
    subido_at = datetime.now(timezone.utc)
    modelo.modelo_3d_key = key
    modelo.modelo_3d_formato = "glb"
    modelo.modelo_3d_tamano = size
    modelo.modelo_3d_subido_at = subido_at
    modelo.modelo_3d_url = _url_modelo_3d(modelo_id, subido_at)

    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        delete_glb(key)
        logger.exception("No se pudo guardar el modelo 3D del auto %s", modelo_id)
        raise HTTPException(
            status_code=500, detail="No se pudo guardar el modelo 3D."
        )

    if old_key and old_key != key:
        delete_glb(old_key)

    await db.refresh(modelo)
    return modelo


@router.delete("/api/{modelo_id}/3d", response_model=ModeloOut)
async def api_eliminar_modelo_3d(
    modelo_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Elimina el modelo 3D asociado a un auto. Requiere admin."""
    modelo = await db.get(Modelo, modelo_id)
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")

    old_key = modelo.modelo_3d_key
    modelo.modelo_3d_key = None
    modelo.modelo_3d_url = None
    modelo.modelo_3d_formato = None
    modelo.modelo_3d_tamano = None
    modelo.modelo_3d_subido_at = None

    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("No se pudo quitar el modelo 3D del auto %s", modelo_id)
        raise HTTPException(
            status_code=500, detail="No se pudo quitar el modelo 3D."
        )

    if old_key:
        delete_glb(old_key)

    await db.refresh(modelo)
    return modelo


@router.get("/{modelo_id}/3d")
async def descargar_modelo_3d(
    modelo_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Sirve el GLB a usuarios autenticados (no se expone como estático)."""
    modelo = await db.get(Modelo, modelo_id)
    if not modelo or not modelo.modelo_3d_key:
        raise HTTPException(status_code=404, detail="Modelo 3D no encontrado")

    path = glb_path(modelo.modelo_3d_key)
    if path is None:
        raise HTTPException(status_code=404, detail="Modelo 3D no encontrado")

    return FileResponse(
        path,
        media_type="model/gltf-binary",
        headers={"Cache-Control": "private, max-age=3600"},
    )
