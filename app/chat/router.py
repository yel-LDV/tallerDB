"""Router de chat — WebSocket endpoint y API REST para mensajes.

El WebSocket permite mensajes en tiempo real entre dos usuarios.
Los mensajes se almacenan en la BD para el historial.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_auth
from app.chat.websocket import manager
from app.config import settings
from app.database import get_db
from app.models.mensaje import Mensaje
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])
templates = Jinja2Templates(directory="app/templates")


def base_context(request: Request, **extra):
    return {"request": request, "app_name": settings.app_name, **extra}


# ===================== WebSocket =====================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: int = Query(...)):
    """Endpoint WebSocket para chat en tiempo real.

    El cliente debe pasar user_id como query param.
    Los mensajes se envían como JSON: {"destinatario_id": 2, "contenido": "Hola", "anuncio_id": 1}
    """
    from app.database import async_session_maker
    from app.models.mensaje import Mensaje

    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            destinatario_id = data.get("destinatario_id")
            contenido = data.get("contenido", "").strip()
            anuncio_id = data.get("anuncio_id")

            if not contenido or not destinatario_id:
                continue

            # Persistir el mensaje en la base de datos
            async with async_session_maker() as session:
                mensaje = Mensaje(
                    remitente_id=user_id,
                    destinatario_id=destinatario_id,
                    anuncio_id=anuncio_id,
                    contenido=contenido,
                    leido=False,
                )
                session.add(mensaje)
                await session.commit()
                await session.refresh(mensaje)

            # Enviar al destinatario en tiempo real
            await manager.send_message(destinatario_id, {
                "type": "message",
                "remitente_id": user_id,
                "contenido": contenido,
                "anuncio_id": anuncio_id,
                "id": mensaje.id,
            })

            # Confirmar al remitente
            await manager.send_message(user_id, {
                "type": "sent",
                "contenido": contenido,
                "id": mensaje.id,
            })

    except WebSocketDisconnect:
        manager.disconnect(user_id)


# ===================== API REST — Mensajes =====================

@router.post("/api/mensaje")
async def enviar_mensaje(
    remitente_id: int,
    destinatario_id: int,
    contenido: str,
    anuncio_id: int | None = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Enviar un mensaje vía REST (fallback si WebSocket no disponible)."""
    if current_user.id != remitente_id:
        raise HTTPException(status_code=403, detail="No puedes enviar mensajes como otro usuario")

    contenido = contenido.strip()
    if not contenido:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    mensaje = Mensaje(
        remitente_id=remitente_id,
        destinatario_id=destinatario_id,
        anuncio_id=anuncio_id,
        contenido=contenido,
        leido=False,
    )
    db.add(mensaje)
    await db.commit()
    await db.refresh(mensaje)

    return {"id": mensaje.id, "remitente_id": mensaje.remitente_id, "contenido": mensaje.contenido}


@router.get("/api/mensajes")
async def historial_mensajes(
    con_usuario_id: int = Query(..., alias="con_usuario_id"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Obtener historial de mensajes entre el usuario y otro."""
    stmt = (
        select(Mensaje)
        .where(
            (
                (Mensaje.remitente_id == current_user.id) & (Mensaje.destinatario_id == con_usuario_id)
            )
            | (
                (Mensaje.remitente_id == con_usuario_id) & (Mensaje.destinatario_id == current_user.id)
            )
        )
        .order_by(Mensaje.creado_at.asc())
    )
    result = await db.execute(stmt)
    mensajes = result.scalars().all()

    return [
        {
            "id": m.id,
            "remitente_id": m.remitente_id,
            "destinatario_id": m.destinatario_id,
            "contenido": m.contenido,
            "leido": m.leido,
            "creado_at": m.creado_at.isoformat(),
        }
        for m in mensajes
    ]


# ===================== Página de chat =====================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def chat_page(
    request: Request,
    con_usuario_id: int | None = Query(None, alias="con_usuario_id"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Página de chat: si hay con_usuario_id, abre la conversación; si no, muestra lista de conversaciones."""
    from sqlalchemy import func as sql_func

    if con_usuario_id is not None:
        # Chat con un usuario específico
        stmt = (
            select(Mensaje)
            .where(
                (
                    (Mensaje.remitente_id == current_user.id) & (Mensaje.destinatario_id == con_usuario_id)
                )
                | (
                    (Mensaje.remitente_id == con_usuario_id) & (Mensaje.destinatario_id == current_user.id)
                )
            )
            .order_by(Mensaje.creado_at.asc())
        )
        result = await db.execute(stmt)
        mensajes = result.scalars().all()

        otro_user = await db.get(User, con_usuario_id)
        if not otro_user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return templates.TemplateResponse(
            "chat.html",
            base_context(
                request,
                user=current_user,
                otro_usuario=otro_user,
                mensajes=mensajes,
            ),
        )
    else:
        # Lista de conversaciones (usuarios con los que ha habido mensajes)
        stmt = (
            select(Mensaje.destinatario_id, sql_func.max(Mensaje.creado_at).label("ultimo"))
            .where(Mensaje.remitente_id == current_user.id)
            .group_by(Mensaje.destinatario_id)
            .order_by(sql_func.max(Mensaje.creado_at).desc())
        )
        result = await db.execute(stmt)
        conversaciones = result.all()

        # Obtener info de cada usuario
        contactos = []
        for row in conversaciones:
            user = await db.get(User, row.destinatario_id)
            if user:
                contactos.append({"user": user, "ultimo": row.ultimo})

        # También los que han escrito al usuario
        stmt2 = (
            select(Mensaje.remitente_id, sql_func.max(Mensaje.creado_at).label("ultimo"))
            .where(Mensaje.destinatario_id == current_user.id)
            .group_by(Mensaje.remitente_id)
            .order_by(sql_func.max(Mensaje.creado_at).desc())
        )
        result2 = await db.execute(stmt2)
        for row in result2.all():
            if not any(c["user"].id == row.remitente_id for c in contactos):
                user = await db.get(User, row.remitente_id)
                if user:
                    contactos.append({"user": user, "ultimo": row.ultimo})

        return templates.TemplateResponse(
            "chat.html",
            base_context(
                request,
                user=current_user,
                otro_usuario=None,
                mensajes=[],
                contactos=contactos,
            ),
        )
