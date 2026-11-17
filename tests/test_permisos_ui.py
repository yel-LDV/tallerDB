"""Pruebas de visibilidad de la UI según el rol y protección de endpoints admin."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.modelo import Modelo  # noqa: F401  (registra la tabla)
from app.models.user import User

PASSWORD = "ClaveSegura123!"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
async def contexto(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'permisos.db'}")
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


async def _registrar(client: AsyncClient, email: str = "normal@example.com") -> None:
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


async def _crear_admin(session_maker) -> None:
    async with session_maker() as session:
        session.add(
            User(
                email="admin@example.com",
                hashed_password=hash_password(PASSWORD),
                is_active=True,
                is_admin=True,
            )
        )
        await session.commit()


async def _login(client: AsyncClient, email: str, password: str = PASSWORD):
    return await client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


@pytest.mark.asyncio
async def test_dashboard_usuario_normal_oculta_opciones_admin(contexto):
    client, _ = contexto
    await _registrar(client)

    response = await client.get("/dashboard")

    assert response.status_code == 200
    assert "Gestionar usuarios" not in response.text
    assert "Configuración" not in response.text
    assert "Crear Admin" not in response.text
    assert "createAdminModal" not in response.text
    assert "qa-lock" not in response.text
    assert "Ver modelos" in response.text
    assert "Mi perfil" in response.text


@pytest.mark.asyncio
async def test_dashboard_admin_muestra_gestion_y_sin_hash(contexto):
    client, session_maker = contexto
    await _crear_admin(session_maker)

    login = await _login(client, "admin@example.com")
    assert login.status_code == 303

    response = await client.get("/dashboard")

    assert response.status_code == 200
    assert "Gestionar usuarios" in response.text
    assert "Crear Admin" in response.text
    assert "createAdminModal" in response.text
    # El panel ya no expone el hash de las contraseñas.
    assert "password-cell" not in response.text
    assert "data-password" not in response.text
    assert "Mostrar hash" not in response.text


@pytest.mark.asyncio
async def test_catalogo_usuario_normal_sin_controles_admin(contexto):
    client, _ = contexto
    await _registrar(client)

    response = await client.get("/modelos")

    assert response.status_code == 200
    assert 'id="modeloModal"' not in response.text
    assert 'id="modelo3dModal"' not in response.text
    assert 'id="btn-nuevo-modelo"' not in response.text
    assert "btn-editar-modelo" not in response.text
    assert "btn-eliminar-modelo" not in response.text
    assert "btn-gestionar-3d" not in response.text
    # El visor 3D sí está disponible para cualquier usuario autenticado.
    assert 'id="viewer3dModal"' in response.text
    assert "Mi perfil" in response.text


@pytest.mark.asyncio
async def test_catalogo_admin_muestra_controles(contexto):
    client, session_maker = contexto
    await _crear_admin(session_maker)
    assert (await _login(client, "admin@example.com")).status_code == 303

    response = await client.get("/modelos")

    assert response.status_code == 200
    assert 'id="modeloModal"' in response.text
    assert 'id="modelo3dModal"' in response.text
    assert 'id="btn-nuevo-modelo"' in response.text
    assert "btn-editar-modelo" in response.text
    assert "btn-eliminar-modelo" in response.text
    assert "btn-gestionar-3d" in response.text


@pytest.mark.asyncio
async def test_endpoints_admin_rechazan_usuario_normal(contexto):
    client, _ = contexto
    await _registrar(client)

    assert (await client.get("/admin/users")).status_code == 403
    assert (
        await client.post(
            "/admin/users/create",
            json={
                "email": "otro@example.com",
                "password": PASSWORD,
                "is_admin": True,
            },
        )
    ).status_code == 403
    assert (
        await client.post(
            "/admin/users/2/toggle-admin", json={"is_admin": True}
        )
    ).status_code == 403
    assert (
        await client.post(
            "/admin/users/2/toggle-active", json={"is_active": False}
        )
    ).status_code == 403


def test_docs_deshabilitado_en_produccion():
    """Con DEBUG=false no se exponen /docs, /redoc ni /openapi.json."""
    codigo = (
        "from app.main import app;"
        "assert app.docs_url is None;"
        "assert app.redoc_url is None;"
        "assert app.openapi_url is None"
    )
    entorno = {**os.environ, "DEBUG": "false"}
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=PROJECT_ROOT,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
