"""Pruebas del comportamiento fail-fast al arrancar sin base de datos."""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

import app.database as database


@pytest.mark.asyncio
async def test_sqlite_siempre_responde(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ok.db'}")
    monkeypatch.setattr(database, "engine", engine)

    try:
        await database.check_database_connection(timeout=2)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_init_db_falla_si_el_servidor_no_responde(monkeypatch):
    # Puerto 1: conexión rechazada de inmediato, sin depender de la red.
    engine = create_async_engine("postgresql+asyncpg://u:p@127.0.0.1:1/db")
    monkeypatch.setattr(database, "engine", engine)

    try:
        with pytest.raises(RuntimeError, match="No se pudo conectar"):
            await database.init_db()
    finally:
        await engine.dispose()
