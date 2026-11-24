"""Router de ofertas y tratos — negociación entre comprador y vendedor.

Flujo:
1. Comprador envía oferta al vendedor
2. Vendedor puede aceptar, rechazar o hacer contraoferta
3. Si hay contraoferta, el comprador puede aceptar, rechazar o contraofertar de nuevo
4. Cuando ambos aceptan, se crea un Trato
5. Si uno cancela, se notifica al otro para que decida cerrar o hacer última oferta
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anuncios.schemas import AnuncioOut
from app.auth.deps import require_auth
from app.config import settings
from app.database import get_db
from app.models.anuncio import Anuncio, AnuncioEstado
from app.models.oferta import Oferta, OfertaEstado
from app.models.trato import Trato, TratoEstado
from app.models.user import User
from app.ventas.schemas import (
    OfertaCreate,
    OfertaOut,
    OfertaResponder,
    TratoOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ofertas", tags=["Ofertas"])
templates = Jinja2Templates(directory="app/templates")


def base_context(request: Request, **extra):
    return {"request": request, "app_name": settings.app_name, **extra}


# ===================== Crear oferta =====================

@router.post("/api", response_model=OfertaOut, status_code=status.HTTP_201_CREATED)
async def crear_oferta(
    data: OfertaCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Un comprador envía una oferta de compra a un vendedor.

    Requisito: el comprador debe haber enviado al menos un mensaje al vendedor
    antes de poder hacer una oferta. Esto asegura que haya contacto previo.
    """
    from app.models.mensaje import Mensaje

    anuncio = await db.get(Anuncio, data.anuncio_id)
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    if anuncio.estado != AnuncioEstado.activo:
        raise HTTPException(status_code=400, detail="Este anuncio ya no está activo")
    if anuncio.vendedor_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes ofertar tu propio anuncio")

    # Validar que el comprador haya enviado al menos un mensaje al vendedor
    mensaje_result = await db.execute(
        select(Mensaje).where(
            Mensaje.remitente_id == current_user.id,
            Mensaje.destinatario_id == anuncio.vendedor_id
        ).limit(1)
    )
    if not mensaje_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Debes contactar al vendedor por mensaje antes de hacer una oferta. Envía un mensaje desde la página del anuncio."
        )

    oferta = Oferta(
        anuncio_id=data.anuncio_id,
        comprador_id=current_user.id,
        monto=data.monto,
        estado=OfertaEstado.pendiente,
        mensaje=data.mensaje,
    )
    db.add(oferta)
    await db.commit()
    await db.refresh(oferta)

    return OfertaOut(
        id=oferta.id,
        anuncio_id=oferta.anuncio_id,
        comprador_id=oferta.comprador_id,
        monto=oferta.monto,
        estado=oferta.estado.value,
        mensaje=oferta.mensaje,
        creado_at=oferta.creado_at.isoformat(),
    )


# ===================== Responder oferta =====================

@router.post("/api/{oferta_id}/responder", response_model=OfertaOut)
async def responder_oferta(
    oferta_id: int,
    data: OfertaResponder,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Responder a una oferta: aceptar, rechazar o contraoferta.

    - El vendedor responde a ofertas del comprador (estado pendiente).
    - El comprador responde a contraofertas del vendedor (estado contraoferta).
    """
    oferta = await db.get(Oferta, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    anuncio = await db.get(Anuncio, oferta.anuncio_id)
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    # Determinar quién puede responder según el estado de la oferta
    if oferta.estado == OfertaEstado.pendiente:
        # Oferta original del comprador → solo el vendedor responde
        if anuncio.vendedor_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Solo el vendedor puede responder a esta oferta"
            )
    elif oferta.estado == OfertaEstado.contraoferta:
        # Contraoferta del vendedor → solo el comprador original responde
        # El comprador original es quien inició la cadena de ofertas
        # Buscamos la raíz de la cadena para saber quién es el comprador real
        root_oferta = oferta
        while root_oferta.oferta_anterior_id is not None:
            prev = await db.get(Oferta, root_oferta.oferta_anterior_id)
            if prev is None:
                break
            root_oferta = prev
        comprador_original_id = root_oferta.comprador_id
        if comprador_original_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Solo el comprador puede responder a esta contraoferta"
            )
    else:
        raise HTTPException(status_code=400, detail="Esta oferta ya fue resuelta")

    if data.accion == "aceptar":
        # Alguien acepta → crear trato
        oferta.estado = OfertaEstado.aceptada

        # Determinar comprador y vendedor reales
        root_oferta = oferta
        while root_oferta.oferta_anterior_id is not None:
            prev = await db.get(Oferta, root_oferta.oferta_anterior_id)
            if prev is None:
                break
            root_oferta = prev
        comprador_id = root_oferta.comprador_id
        vendedor_id = anuncio.vendedor_id

        # El monto final es el de la última oferta en la cadena (la más reciente)
        # Si esta oferta es una contraoferta (tiene oferta_anterior_id),
        # buscamos la última oferta hija que herede de esta
        monto_final = oferta.monto
        # Buscamos si hay una oferta posterior (contraoferta) que tenga esta como anterior
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(Oferta).where(Oferta.oferta_anterior_id == oferta.id)
        )
        ultima_oferta = result.scalar_one_or_none()
        if ultima_oferta is not None:
            monto_final = ultima_oferta.monto

        await db.commit()

        trato = Trato(
            oferta_id=oferta.id,
            comprador_id=comprador_id,
            vendedor_id=vendedor_id,
            monto_final=monto_final,
            estado=TratoEstado.activo,
        )
        db.add(trato)

        # Marcar anuncio como vendido
        anuncio.estado = AnuncioEstado.vendido
        await db.commit()
        await db.refresh(oferta)

    elif data.accion == "rechazar":
        oferta.estado = OfertaEstado.rechazada
        await db.commit()
        await db.refresh(oferta)

    elif data.accion == "contraoferta":
        if data.monto is None:
            raise HTTPException(
                status_code=400, detail="Una contraoferta debe incluir un monto"
            )
        # Determinar quién hace la contraoferta y quién es el contraparte
        if oferta.estado == OfertaEstado.pendiente:
            # Vendedor contraoferta
            nuevo_comprador_id = anuncio.vendedor_id
        else:
            # Comprador contraoferta a una contraoferta del vendedor
            root_oferta = oferta
            while root_oferta.oferta_anterior_id is not None:
                prev = await db.get(Oferta, root_oferta.oferta_anterior_id)
                if prev is None:
                    break
                root_oferta = prev
            nuevo_comprador_id = root_oferta.comprador_id

        nueva_oferta = Oferta(
            anuncio_id=oferta.anuncio_id,
            comprador_id=nuevo_comprador_id,
            oferta_anterior_id=oferta.id,
            monto=data.monto,
            estado=OfertaEstado.contraoferta,
            mensaje=data.mensaje,
        )
        oferta.estado = OfertaEstado.contraoferta
        db.add(nueva_oferta)
        await db.commit()
        await db.refresh(oferta)

    return OfertaOut(
        id=oferta.id,
        anuncio_id=oferta.anuncio_id,
        comprador_id=oferta.comprador_id,
        monto=oferta.monto,
        estado=oferta.estado.value,
        mensaje=oferta.mensaje,
        creado_at=oferta.creado_at.isoformat(),
    )


# ===================== Cancelar oferta =====================

@router.post("/api/{oferta_id}/cancelar", response_model=OfertaOut)
async def cancelar_oferta(
    oferta_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Cancelar una oferta pendiente. El otro usuario es notificado."""
    oferta = await db.get(Oferta, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    # Solo comprador o vendedor pueden cancelar
    anuncio = await db.get(Anuncio, oferta.anuncio_id)
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    if current_user.id != oferta.comprador_id and current_user.id != anuncio.vendedor_id:
        raise HTTPException(status_code=403, detail="No puedes cancelar esta oferta")

    if oferta.estado not in (OfertaEstado.pendiente, OfertaEstado.contraoferta):
        raise HTTPException(status_code=400, detail="Esta oferta ya fue resuelta")

    oferta.estado = OfertaEstado.cancelada
    await db.commit()
    await db.refresh(oferta)

    return OfertaOut(
        id=oferta.id,
        anuncio_id=oferta.anuncio_id,
        comprador_id=oferta.comprador_id,
        monto=oferta.monto,
        estado=oferta.estado.value,
        mensaje=oferta.mensaje,
        creado_at=oferta.creado_at.isoformat(),
    )


# ===================== Listar ofertas de un anuncio =====================

@router.get("/api/anuncio/{anuncio_id}", response_model=list[OfertaOut])
async def listar_ofertas_anuncio(
    anuncio_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Listar ofertas de un anuncio. Solo vendedor o comprador pueden ver."""
    anuncio = await db.get(Anuncio, anuncio_id)
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    # Solo vendedor o participantes pueden ver
    if anuncio.vendedor_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Solo el vendedor puede ver las ofertas"
        )

    result = await db.execute(
        select(Oferta)
        .where(Oferta.anuncio_id == anuncio_id)
        .order_by(Oferta.creado_at.desc())
    )
    ofertas = result.scalars().all()

    return [
        OfertaOut(
            id=o.id,
            anuncio_id=o.anuncio_id,
            comprador_id=o.comprador_id,
            monto=o.monto,
            estado=o.estado.value,
            mensaje=o.mensaje,
            creado_at=o.creado_at.isoformat(),
        )
        for o in ofertas
    ]


# ===================== Panel de ofertas (HTML) =====================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def panel_ofertas(
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Panel de ofertas del usuario (como comprador y vendedor)."""
    # Ofertas como comprador
    compras_result = await db.execute(
        select(Oferta).where(Oferta.comprador_id == current_user.id).order_by(Oferta.creado_at.desc())
    )
    ofertas_compra = compras_result.scalars().all()

    # Ofertas como vendedor (del anuncio)
    anuncios_result = await db.execute(
        select(Anuncio).where(Anuncio.vendedor_id == current_user.id)
    )
    mis_anuncios = anuncios_result.scalars().all()

    ofertas_venta = []
    for anuncio in mis_anuncios:
        ofertas_result = await db.execute(
            select(Oferta)
            .where(Oferta.anuncio_id == anuncio.id)
            .order_by(Oferta.creado_at.desc())
        )
        for o in ofertas_result.scalars().all():
            ofertas_venta.append((anuncio, o))

    return templates.TemplateResponse(
        "ofertas.html",
        base_context(
            request,
            user=current_user,
            ofertas_compra=ofertas_compra,
            ofertas_venta=ofertas_venta,
        ),
    )


# ===================== Tratos =====================

@router.get("/tratos/api", response_model=list[TratoOut])
async def listar_tratos(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Listar tratos del usuario (como comprador o vendedor)."""
    result = await db.execute(
        select(Trato)
        .where(
            (Trato.comprador_id == current_user.id) | (Trato.vendedor_id == current_user.id)
        )
        .order_by(Trato.creado_at.desc())
    )
    tratos = result.scalars().all()

    return [
        TratoOut(
            id=t.id,
            oferta_id=t.oferta_id,
            comprador_id=t.comprador_id,
            vendedor_id=t.vendedor_id,
            monto_final=t.monto_final,
            estado=t.estado.value,
        )
        for t in tratos
    ]


@router.post("/tratos/api/{trato_id}/cerrar", response_model=TratoOut)
async def cerrar_trato(
    trato_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Cerrar un trato (ambos de acuerdo)."""
    trato = await db.get(Trato, trato_id)
    if not trato:
        raise HTTPException(status_code=404, detail="Trato no encontrado")

    if current_user.id not in (trato.comprador_id, trato.vendedor_id):
        raise HTTPException(status_code=403, detail="No participas en este trato")

    trato.estado = TratoEstado.cerrado
    trato.cerrado_at = datetime.now(timezone.utc)
    await db.commit()

    return TratoOut(
        id=trato.id,
        oferta_id=trato.oferta_id,
        comprador_id=trato.comprador_id,
        vendedor_id=trato.vendedor_id,
        monto_final=trato.monto_final,
        estado=trato.estado.value,
    )
