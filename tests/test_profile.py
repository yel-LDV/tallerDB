"""Pruebas de la página de perfil y del cambio de contraseña."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import verify_password
from app.database import Base, get_db
from app.main import app
from app.models.modelo import Modelo  # noqa: F401  (registra la tabla)
from app.models.user import User

PASSWORD = "ClaveSegura123!"
NEW_PASSWORD = "NuevaClave456!"


@pytest.fixture
async def contexto(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'perfil.db'}")
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


async def _registrar(client: AsyncClient, email: str = "perfil@example.com") -> None:
    response = await client.post(
        "/register",
        data={
            "email": email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


async def _usuario(session_maker, email: str) -> User | None:
    async with session_maker() as session:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


@pytest.mark.asyncio
async def test_perfil_requiere_sesion(contexto):
    client, _ = contexto

    get_response = await client.get("/profile", follow_redirects=False)
    post_response = await client.post(
        "/profile/password",
        data={
            "current_password": PASSWORD,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
        follow_redirects=False,
    )

    assert get_response.status_code == 303
    assert get_response.headers["location"] == "/login"
    assert post_response.status_code == 303
    assert post_response.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_perfil_muestra_datos_propios(contexto):
    client, _ = contexto
    await _registrar(client, "mi-cuenta@example.com")

    response = await client.get("/profile")

    assert response.status_code == 200
    assert "mi-cuenta@example.com" in response.text
    assert "Cambiar contraseña" in response.text
    assert "Usuario estándar" in response.text


@pytest.mark.asyncio
async def test_cambio_password_valida_contrasena_actual(contexto):
    client, _ = contexto
    await _registrar(client)

    response = await client.post(
        "/profile/password",
        data={
            "current_password": "incorrecta",
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 400
    assert "contraseña actual no es correcta" in response.text


@pytest.mark.asyncio
async def test_cambio_password_valida_confirmacion_y_longitud(contexto):
    client, _ = contexto
    await _registrar(client)

    no_coinciden = await client.post(
        "/profile/password",
        data={
            "current_password": PASSWORD,
            "new_password": NEW_PASSWORD,
            "confirm_password": "otra-distinta",
        },
    )
    assert no_coinciden.status_code == 400
    assert "no coinciden" in no_coinciden.text

    corta = await client.post(
        "/profile/password",
        data={
            "current_password": PASSWORD,
            "new_password": "corta",
            "confirm_password": "corta",
        },
    )
    assert corta.status_code == 400
    assert "al menos 8 caracteres" in corta.text


@pytest.mark.asyncio
async def test_cambio_password_actualiza_solo_al_usuario_actual(contexto):
    client, session_maker = contexto
    await _registrar(client, "principal@example.com")

    async with session_maker() as session:
        otro = User(
            email="otro@example.com",
            hashed_password="hash-de-otro",
            is_active=True,
            is_admin=False,
        )
        session.add(otro)
        await session.commit()

    response = await client.post(
        "/profile/password",
        data={
            "current_password": PASSWORD,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/profile?ok=1"

    principal = await _usuario(session_maker, "principal@example.com")
    otro = await _usuario(session_maker, "otro@example.com")
    assert principal is not None and otro is not None
    assert verify_password(NEW_PASSWORD, principal.hashed_password)
    assert not verify_password(PASSWORD, principal.hashed_password)
    assert otro.hashed_password == "hash-de-otro"

    exito = await client.get("/profile?ok=1")
    assert exito.status_code == 200
    assert "contraseña se actualizó correctamente" in exito.text


@pytest.mark.asyncio
async def test_login_usa_la_nueva_password(contexto):
    client, _ = contexto
    await _registrar(client, "login-nuevo@example.com")

    cambio = await client.post(
        "/profile/password",
        data={
            "current_password": PASSWORD,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
        follow_redirects=False,
    )
    assert cambio.status_code == 303

    client.cookies.clear()
    antigua = await client.post(
        "/login",
        data={"email": "login-nuevo@example.com", "password": PASSWORD},
        follow_redirects=False,
    )
    assert antigua.status_code == 401

    client.cookies.clear()
    nueva = await client.post(
        "/login",
        data={"email": "login-nuevo@example.com", "password": NEW_PASSWORD},
        follow_redirects=False,
    )
    assert nueva.status_code == 303
    assert nueva.headers["location"] == "/dashboard"
