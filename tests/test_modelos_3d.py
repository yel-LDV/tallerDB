"""Pruebas del ciclo de vida de los modelos 3D (GLB)."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.deps import require_admin, require_auth
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.modelos.storage import glb_path
from app.models.modelo import Modelo
from app.models.user import User  # noqa: F401  (registra la tabla)


def _glb(payload: bytes = b'{"asset":{"version":"2.0"}}') -> bytes:
    """Construye un GLB mínimo con cabecera y chunk JSON válidos."""
    payload += b" " * ((-len(payload)) % 4)
    chunk = len(payload).to_bytes(4, "little") + b"JSON" + payload
    total = 12 + len(chunk)
    return b"glTF" + (2).to_bytes(4, "little") + total.to_bytes(4, "little") + chunk


@pytest.fixture
async def contexto(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path / "uploads"))

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'modelos3d.db'}")
    session_maker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        modelo = Modelo(
            marca="Toyota",
            nombre="Corolla",
            anio=2024,
            precio=Decimal("19999.99"),
            tipo="sedan",
            transmision="automatica",
            disponible=True,
        )
        session.add(modelo)
        await session.commit()
        await session.refresh(modelo)
        modelo_id = modelo.id

    admin = SimpleNamespace(
        id=1,
        email="admin@example.com",
        is_active=True,
        is_admin=True,
    )

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth] = lambda: admin
    app.dependency_overrides[require_admin] = lambda: admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_maker, modelo_id

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_auth, None)
    app.dependency_overrides.pop(require_admin, None)
    await engine.dispose()


async def _modelo(session_maker, modelo_id: int) -> Modelo:
    async with session_maker() as session:
        modelo = await session.get(Modelo, modelo_id)
        assert modelo is not None
        return modelo


@pytest.mark.asyncio
async def test_subir_y_servir_glb(contexto):
    client, session_maker, modelo_id = contexto
    contenido = _glb(b'{"asset":{"version":"2.0"}}')

    response = await client.post(
        f"/modelos/api/{modelo_id}/3d",
        files={"archivo": ("auto.glb", contenido, "model/gltf-binary")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["modelo_3d_formato"] == "glb"
    assert data["modelo_3d_tamano"] == len(contenido)
    assert data["modelo_3d_subido_at"] is not None
    assert data["modelo_3d_url"].startswith(f"/modelos/{modelo_id}/3d?v=")

    modelo = await _modelo(session_maker, modelo_id)
    assert modelo.modelo_3d_key
    path = glb_path(modelo.modelo_3d_key)
    assert path is not None
    assert path.read_bytes() == contenido

    servido = await client.get(data["modelo_3d_url"])
    assert servido.status_code == 200
    assert servido.headers["content-type"] == "model/gltf-binary"
    assert servido.content == contenido


@pytest.mark.asyncio
async def test_catalogo_muestra_visor_y_gestion_3d(contexto):
    client, _, modelo_id = contexto

    subida = await client.post(
        f"/modelos/api/{modelo_id}/3d",
        files={"archivo": ("auto.glb", _glb(), "model/gltf-binary")},
    )
    assert subida.status_code == 200
    url_3d = subida.json()["modelo_3d_url"]

    response = await client.get("/modelos")

    assert response.status_code == 200
    assert "Ver en 3D" in response.text
    assert "Reemplazar 3D" in response.text
    assert 'class="modelo-3d-chip"' in response.text
    assert f'data-src="{url_3d}"' in response.text
    assert "/static/vendor/model-viewer.min.js" in response.text


@pytest.mark.asyncio
async def test_reemplazar_glb_borra_el_anterior(contexto):
    client, session_maker, modelo_id = contexto
    primero = _glb(b'{"asset":{"version":"2.0"},"extra":"primero"}')
    segundo = _glb(b'{"asset":{"version":"2.0"},"extra":"segundo-mas-grande"}')

    response = await client.post(
        f"/modelos/api/{modelo_id}/3d",
        files={"archivo": ("primero.glb", primero, "model/gltf-binary")},
    )
    assert response.status_code == 200
    old_key = (await _modelo(session_maker, modelo_id)).modelo_3d_key
    old_path = glb_path(old_key)
    assert old_path is not None and old_path.exists()

    response = await client.post(
        f"/modelos/api/{modelo_id}/3d",
        files={"archivo": ("segundo.glb", segundo, "model/gltf-binary")},
    )
    assert response.status_code == 200
    data = response.json()

    assert old_path.exists() is False
    new_path = glb_path((await _modelo(session_maker, modelo_id)).modelo_3d_key)
    assert new_path is not None and new_path.exists()
    assert new_path.read_bytes() == segundo
    assert data["modelo_3d_tamano"] == len(segundo)


@pytest.mark.asyncio
async def test_quitar_glb(contexto):
    client, session_maker, modelo_id = contexto
    contenido = _glb()

    subida = await client.post(
        f"/modelos/api/{modelo_id}/3d",
        files={"archivo": ("auto.glb", contenido, "model/gltf-binary")},
    )
    assert subida.status_code == 200
    key = (await _modelo(session_maker, modelo_id)).modelo_3d_key
    path = glb_path(key)
    assert path is not None and path.exists()

    borrado = await client.delete(f"/modelos/api/{modelo_id}/3d")

    assert borrado.status_code == 200
    data = borrado.json()
    assert data["modelo_3d_url"] is None
    assert data["modelo_3d_formato"] is None
    assert data["modelo_3d_tamano"] is None
    assert path.exists() is False

    servido = await client.get(f"/modelos/{modelo_id}/3d")
    assert servido.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("nombre", "contenido", "content_type"),
    [
        ("auto.obj", _glb(), "application/octet-stream"),
        ("auto.glb", b"no-es-un-glb", "model/gltf-binary"),
        ("auto.glb", _glb(b"no-json"), "model/gltf-binary"),
        (
            "auto.glb",
            b"glTF" + (1).to_bytes(4, "little") + (12).to_bytes(4, "little"),
            "model/gltf-binary",
        ),
    ],
)
async def test_rechaza_archivos_invalidos(
    contexto, nombre, contenido, content_type
):
    client, _, modelo_id = contexto

    response = await client.post(
        f"/modelos/api/{modelo_id}/3d",
        files={"archivo": (nombre, contenido, content_type)},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_rechaza_glb_demasiado_grande(contexto, monkeypatch):
    client, _, modelo_id = contexto
    monkeypatch.setattr(settings, "max_3d_size_mb", 0)

    response = await client.post(
        f"/modelos/api/{modelo_id}/3d",
        files={"archivo": ("auto.glb", _glb(), "model/gltf-binary")},
    )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_eliminar_modelo_borra_su_glb(contexto):
    client, session_maker, modelo_id = contexto

    subida = await client.post(
        f"/modelos/api/{modelo_id}/3d",
        files={"archivo": ("auto.glb", _glb(), "model/gltf-binary")},
    )
    assert subida.status_code == 200
    key = (await _modelo(session_maker, modelo_id)).modelo_3d_key
    path = glb_path(key)
    assert path is not None and path.exists()

    borrado = await client.delete(f"/modelos/api/{modelo_id}")
    assert borrado.status_code == 200

    assert path.exists() is False
    async with session_maker() as session:
        assert await session.get(Modelo, modelo_id) is None
