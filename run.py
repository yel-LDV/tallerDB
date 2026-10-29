import asyncio

import uvicorn

from app.config import settings
from app.database import check_database_connection, engine


async def _preflight() -> None:
    """Comprueba la base de datos antes de arrancar, incluso con reload.

    Uvicorn mantiene vivo el proceso padre cuando ``reload=True`` aunque el
    hijo falle. Esta comprobación garantiza que el comando termine con error
    si la base configurada no está disponible.
    """
    try:
        await check_database_connection()
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from None
    finally:
        # No dejamos conexiones del pool atadas a este event loop: uvicorn
        # creará su propio loop (y su propio pool) al arrancar.
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_preflight())
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        # En producción (DEBUG=false) el reloader debe estar apagado para que
        # un fallo de base de datos termine el proceso y no quede vivo.
        reload=settings.debug,
    )
