import asyncio
import logging
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def _ensure_sqlite_directory() -> None:
    """Crea el directorio del archivo SQLite si no existe."""
    if not _is_sqlite_url(settings.database_url):
        return

    database = make_url(settings.database_url).database
    if not database or database == ":memory:":
        return

    Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_directory()

_engine_kwargs = {
    "echo": settings.debug,
    "future": True,
    "pool_pre_ping": True,
}

if not _is_sqlite_url(settings.database_url):
    # Pool razonable para servidores MySQL/MariaDB/PostgreSQL. NullPool abría
    # una conexión nueva por petición y era especialmente costoso en PostgreSQL.
    _engine_kwargs.update(
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        pool_timeout=30,
    )

engine = create_async_engine(settings.database_url, **_engine_kwargs)

async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


async def check_database_connection(timeout: float | None = None) -> None:
    """Comprueba que la base de datos configurada responde.

    Para SQLite la conexión crea el archivo si hace falta. Para el resto de
    motores se ejecuta ``SELECT 1`` con un timeout corto. Cualquier fallo se
    convierte en ``RuntimeError`` para detener el arranque de la aplicación.
    """
    wait_seconds = timeout if timeout is not None else settings.database_connect_timeout
    safe_url = engine.url.render_as_string(hide_password=True)

    try:
        async with asyncio.timeout(wait_seconds):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo conectar a la base de datos configurada ({safe_url}). "
            f"La aplicación no se iniciará. Detalle: {exc}"
        ) from exc


def _ensure_nullable_columns(conn) -> None:
    """Añade columnas nullable nuevas a tablas existentes.

    ``create_all`` no modifica tablas ya creadas. Este paso permite que una
    instalación con el esquema anterior reciba, por ejemplo, las columnas 3D
    sin tener que borrar la base de datos. Para cambios más complejos se
    mantienen las migraciones de Alembic.
    """
    from app.models.modelo import Modelo  # noqa: F401  (registra la tabla)

    inspector = inspect(conn)
    if "modelos" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("modelos")}
    preparer = conn.dialect.identifier_preparer
    table_name = preparer.quote("modelos")

    for column in Modelo.__table__.columns:
        if column.name in existing or not column.nullable:
            continue
        column_type = column.type.compile(dialect=conn.dialect)
        statement = (
            f"ALTER TABLE {table_name} ADD COLUMN "
            f"{preparer.quote(column.name)} {column_type} NULL"
        )
        logger.info("Añadiendo columna %s a modelos", column.name)
        conn.execute(text(statement))


async def init_db() -> None:
    """Verifica la conexión y garantiza el esquema mínimo."""
    from app.models.modelo import Modelo  # noqa: F401
    from app.models.user import User  # noqa: F401

    try:
        await check_database_connection()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_ensure_nullable_columns)
    except Exception:
        logger.exception("No se pudo inicializar la base de datos")
        raise
