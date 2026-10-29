"""Pruebas de integración del registro público de usuarios."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import verify_password
from app.database import Base, get_db
from app.main import app
from app.models.modelo import Modelo  # noqa: F401  (registra la tabla)
from app.models.user import User


@pytest.fixture
async def contexto(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}")
    session_maker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_maker

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


async def _usuario(session_maker, email: str) -> User | None:
    async with session_maker() as session:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


@pytest.mark.asyncio
async def test_registro_crea_cuenta_persistente(contexto):
    client, session_maker = contexto

    response = await client.post(
        "/register",
        data={
            "email": "  Nueva.Persona@Example.COM ",
            "password": "ClaveSegura123!",
            "confirm_password": "ClaveSegura123!",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard?bienvenido=1"

    user = await _usuario(session_maker, "nueva.persona@example.com")
    assert user is not None
    assert user.is_active is True
    assert user.is_admin is False
    assert user.hashed_password != "ClaveSegura123!"
    assert verify_password("ClaveSegura123!", user.hashed_password)


@pytest.mark.asyncio
async def test_registro_inicia_sesion(contexto):
    client, _ = contexto

    response = await client.post(
        "/register",
        data={
            "email": "sesion@example.com",
            "password": "ClaveSegura123!",
            "confirm_password": "ClaveSegura123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Bienvenido" in response.text
    assert "sesion@example.com" in response.text


@pytest.mark.asyncio
async def test_email_duplicado_no_crea_otra_cuenta(contexto):
    client, session_maker = contexto
    datos = {
        "email": "duplicado@example.com",
        "password": "ClaveSegura123!",
        "confirm_password": "ClaveSegura123!",
    }

    primero = await client.post("/register", data=datos)
    assert primero.status_code == 303

    client.cookies.clear()
    segundo = await client.post("/register", data=datos)

    assert segundo.status_code == 400
    assert "ya está registrado" in segundo.text

    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == "duplicado@example.com")
        )
        assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_registro_valida_email_y_contrasena(contexto):
    client, _ = contexto

    email_invalido = await client.post(
        "/register",
        data={
            "email": "no-es-un-email",
            "password": "ClaveSegura123!",
            "confirm_password": "ClaveSegura123!",
        },
    )
    assert email_invalido.status_code == 400
    assert "correo electrónico válido" in email_invalido.text

    contrasena_corta = await client.post(
        "/register",
        data={
            "email": "corta@example.com",
            "password": "corta",
            "confirm_password": "corta",
        },
    )
    assert contrasena_corta.status_code == 400
    assert "8 caracteres" in contrasena_corta.text


@pytest.mark.asyncio
async def test_registro_conserva_email_tras_error(contexto):
    client, _ = contexto

    response = await client.post(
        "/register",
        data={
            "email": "conservar@example.com",
            "password": "ClaveSegura123!",
            "confirm_password": "otra-distinta",
        },
    )

    assert response.status_code == 400
    assert "no coinciden" in response.text
    assert 'value="conservar@example.com"' in response.text
