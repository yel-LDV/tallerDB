"""Router de reportes — reportar usuarios y panel admin."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_auth
from app.config import settings
from app.database import get_db
from app.models.reporte import Reporte, ReporteEstado, ReporteMotivo
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reportes", tags=["Reportes"])
templates = Jinja2Templates(directory="app/templates")


def base_context(request: Request, **extra):
    return {"request": request, "app_name": settings.app_name, **extra}


class ReporteCreate(BaseModel):
    usuario_reportado_id: int = Field(..., gt=0)
    anuncio_id: int | None = None
    motivo: str = Field(..., pattern="^(contenido_inapropiado|fraude|acoso|anuncio_falso|spam|otro)$")
    detalles: str | None = None


class ReporteResolve(BaseModel):
    accion: str = Field(..., pattern="^(resuelto|en_revision|descartado)$")
    notas: str | None = None


# ===================== Crear reporte =====================

@router.post("/api", status_code=status.HTTP_201_CREATED)
async def crear_reporte(
    data: ReporteCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Reportar a un usuario. No es visible por el usuario reportado."""
    if data.usuario_reportado_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes reportarte a ti mismo")

    # Verificar que el usuario reportado existe
    reportado = await db.get(User, data.usuario_reportado_id)
    if not reportado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    reporte = Reporte(
        reportante_id=current_user.id,
        usuario_reportado_id=data.usuario_reportado_id,
        anuncio_id=data.anuncio_id,
        motivo=ReporteMotivo(data.motivo),
        detalles=data.detalles,
        estado=ReporteEstado.pendiente,
    )
    db.add(reporte)
    await db.commit()
    await db.refresh(reporte)

    return {
        "id": reporte.id,
        "motivo": reporte.motivo.value,
        "estado": reporte.estado.value,
        "mensaje": "Reporte enviado. Un administrador lo revisará.",
    }


# ===================== Panel admin — Listar reportes =====================

@router.get("/api", response_model=list[dict])
async def listar_reportes(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Listar todos los reportes. Solo administradores."""
    result = await db.execute(
        select(Reporte).order_by(Reporte.creado_at.desc())
    )
    reportes = result.scalars().all()

    return [
        {
            "id": r.id,
            "reportante_id": r.reportante_id,
            "usuario_reportado_id": r.usuario_reportado_id,
            "anuncio_id": r.anuncio_id,
            "motivo": r.motivo.value,
            "detalles": r.detalles,
            "estado": r.estado.value,
            "notas_admin": r.notas_admin,
            "resuelto_at": r.resuelto_at.isoformat() if r.resuelto_at else None,
            "creado_at": r.creado_at.isoformat(),
        }
        for r in reportes
    ]


# ===================== Resolver reporte =====================

from datetime import datetime

@router.post("/api/{reporte_id}/resolver", status_code=200)
async def resolver_reporte(
    reporte_id: int,
    data: ReporteResolve,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Resolver un reporte con acción y notas. Solo administradores."""
    reporte = await db.get(Reporte, reporte_id)
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    estado_map = {
        "resuelto": ReporteEstado.resuelto,
        "en_revision": ReporteEstado.en_revision,
        "descartado": ReporteEstado.descartado,
    }
    reporte.estado = estado_map[data.accion]
    reporte.notas_admin = data.notas
    reporte.resuelto_at = datetime.now()
    await db.commit()

    return {
        "id": reporte.id,
        "estado": reporte.estado.value,
        "notas_admin": reporte.notas_admin,
        "mensaje": f"Reporte marcado como {data.accion}.",
    }


# ===================== Página admin de reportes =====================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def panel_reportes(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Panel de administración de reportes."""
    result = await db.execute(
        select(Reporte).order_by(Reporte.creado_at.desc())
    )
    reportes = result.scalars().all()

    return templates.TemplateResponse(
        "reportes_admin.html",
        base_context(
            request,
            user=current_user,
            reportes=reportes,
        ),
    )
