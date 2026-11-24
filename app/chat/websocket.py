"""Gestor de conexiones WebSocket para el chat en tiempo real.

Cada usuario autenticado mantiene una conexión WebSocket. Los mensajes se
envían al destinatario si está conectado, y siempre se persisten en la BD.
"""

import logging
from typing import Dict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gestiona las conexiones WebSocket activas por usuario."""

    def __init__(self) -> None:
        # user_id -> WebSocket
        self._active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """Aceptar y registrar una conexión WebSocket."""
        await websocket.accept()
        self._active_connections[user_id] = websocket
        logger.info("Usuario %s conectado al chat (total: %d)", user_id, len(self._active_connections))

    def disconnect(self, user_id: int) -> None:
        """Eliminar una conexión WebSocket."""
        self._active_connections.pop(user_id, None)
        logger.info("Usuario %s desconectado del chat", user_id)

    async def send_message(self, user_id: int, message: dict) -> None:
        """Enviar un mensaje a un usuario específico si está conectado."""
        websocket = self._active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception:
                logger.exception("Error al enviar mensaje a usuario %s", user_id)
                self.disconnect(user_id)

    @property
    def is_connected(self) -> Dict[int, bool]:
        """Devuelve el estado de conexión de todos los usuarios."""
        return {uid: True for uid in self._active_connections}


# Instancia global compartida por todas las conexiones
manager = ConnectionManager()
