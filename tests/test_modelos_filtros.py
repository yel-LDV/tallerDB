"""Pruebas de integración para la búsqueda y los filtros del catálogo."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.deps import require_auth
from app.database import Base, get_db
from app.main import app
from app.models.modelo import Modelo
from app.models.user import User  # noqa: F401  (registra la tabla en Base.metadata)


@pytest.fixture
async def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    session_maker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    usuario = SimpleNamespace(
        id=1,
        email="test@example.com",
        is_admin=True,
        is_active=True,
    )

    async def override_require_auth():
        return usuario

    async with session_maker() as session:
        session.add_all(
            [
                Modelo(
                    marca="Toyota",
                    nombre="Corolla",
                    anio=2024,
                    precio=Decimal("25000.00"),
                    color="Rojo",
                    tipo="sedan",
                    transmision="automatica",
                    disponible=True,
                ),
                Modelo(
                    marca="Toyota",
                    nombre="RAV4",
                    anio=2023,
                    precio=Decimal("35000.00"),
                    color="Blanco",
                    tipo="suv",
                    transmision="automatica",
                    disponible=False,
                ),
                Modelo(
                    marca="Toyota",
                    nombre="Yaris",
                    anio=2022,
                    precio=Decimal("18000.00"),
                    color="Gris",
                    tipo="hatchback",
                    transmision="manual",
                    disponible=True,
                ),
                Modelo(
                    marca="Honda",
                    nombre="Civic",
                    anio=2022,
                    precio=Decimal("20000.00"),
                    color="Negro",
                    tipo="sedan",
                    transmision="manual",
                    disponible=True,
                ),
                Modelo(
                    marca="Honda",
                    nombre="CR-V",
                    anio=2021,
                    precio=Decimal("28000.00"),
                    color="Gris",
                    tipo="suv",
                    transmision="automatica",
                    disponible=True,
                ),
                Modelo(
                    marca="Ford",
                    nombre="F-150",
                    anio=2020,
                    precio=Decimal("40000.00"),
                    color="Azul",
                    tipo="pickup",
                    transmision="manual",
                    disponible=False,
                ),
                Modelo(
                    marca="Mazda",
                    nombre="3",
                    anio=2025,
                    precio=Decimal("22000.00"),
                    color="Rojo",
                    tipo="hatchback",
                    transmision="automatica",
                    disponible=True,
                ),
            ]
        )
        await session.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth] = override_require_auth

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ===================== Regresión: años vacíos =====================
@pytest.mark.asyncio
async def test_anios_vacios_no_devuelven_422(client: AsyncClient):
    response = await client.get("/modelos?anio_min=&anio_max=")
    assert response.status_code == 200
    assert "Toyota Corolla" in response.text


@pytest.mark.asyncio
async def test_formulario_vacio_devuelve_catalogo_completo(client: AsyncClient):
    response = await client.get(
        "/modelos?q=&marca=&tipo=&disponible=&anio_min=&anio_max=&orden=recientes"
    )
    assert response.status_code == 200
    assert "Mostrando 1-7 de 7 resultados" in response.text


# ===================== Filtros =====================
@pytest.mark.asyncio
async def test_filtros_combinados(client: AsyncClient):
    response = await client.get(
        "/modelos?marca=Toyota&tipo=sedan&disponible=1&anio_min=2024&anio_max=2024"
    )
    assert response.status_code == 200
    assert "Toyota Corolla" in response.text
    assert "Toyota RAV4" not in response.text
    assert "Honda Civic" not in response.text
    assert "Mostrando 1-1 de 1 resultados" in response.text
    assert '<span class="stat-value">1</span>' in response.text


@pytest.mark.asyncio
async def test_busqueda_por_nombre(client: AsyncClient):
    response = await client.get("/modelos?q=corolla")
    assert response.status_code == 200
    assert "Toyota Corolla" in response.text
    assert "Honda Civic" not in response.text


@pytest.mark.asyncio
async def test_busqueda_por_color(client: AsyncClient):
    response = await client.get("/modelos?q=rojo")
    assert response.status_code == 200
    assert "Toyota Corolla" in response.text
    assert "Mazda 3" in response.text
    assert "Honda Civic" not in response.text


@pytest.mark.asyncio
async def test_busqueda_escapa_comodines_like(client: AsyncClient):
    response = await client.get("/modelos?q=%25")
    assert response.status_code == 200
    assert "No hay modelos que coincidan con los filtros" in response.text
    assert "Limpiar filtros" in response.text


@pytest.mark.asyncio
async def test_busqueda_escapa_html(client: AsyncClient):
    response = await client.get("/modelos?q=<script>alert(1)</script>")
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


@pytest.mark.asyncio
async def test_rango_de_anios_invertido_muestra_error_amigable(client: AsyncClient):
    response = await client.get("/modelos?anio_min=2025&anio_max=2024")
    assert response.status_code == 200
    assert "El año desde no puede ser mayor que el año hasta." in response.text
    # Los valores escritos por el usuario se conservan en el formulario.
    assert 'value="2025"' in response.text
    assert 'value="2024"' in response.text


@pytest.mark.asyncio
async def test_anio_invalido_muestra_error_amigable(client: AsyncClient):
    response = await client.get("/modelos?anio_min=abc")
    assert response.status_code == 200
    assert "Año desde debe ser un número entero." in response.text


@pytest.mark.asyncio
async def test_tipo_invalido_muestra_error_amigable(client: AsyncClient):
    response = await client.get("/modelos?tipo=inventado")
    assert response.status_code == 200
    assert "El tipo de carrocería seleccionado no es válido." in response.text


# ===================== Ordenamiento =====================
@pytest.mark.asyncio
async def test_api_orden_precio_desc(client: AsyncClient):
    response = await client.get("/modelos/api?orden=precio_desc")
    assert response.status_code == 200
    precios = [Decimal(item["precio"]) for item in response.json()]
    assert precios == sorted(precios, reverse=True)


@pytest.mark.asyncio
async def test_api_orden_invalido_cae_en_recientes(client: AsyncClient):
    response = await client.get("/modelos/api?orden=no-existe")
    assert response.status_code == 200
    assert len(response.json()) == 7


@pytest.mark.asyncio
async def test_api_acepta_anios_vacios(client: AsyncClient):
    response = await client.get("/modelos/api?anio_min=&anio_max=")
    assert response.status_code == 200
    assert len(response.json()) == 7


@pytest.mark.asyncio
async def test_api_filtra_por_anios(client: AsyncClient):
    response = await client.get("/modelos/api?anio_min=2023&anio_max=2024")
    assert response.status_code == 200
    anios = [item["anio"] for item in response.json()]
    assert anios
    assert all(2023 <= anio <= 2024 for anio in anios)


@pytest.mark.asyncio
async def test_api_anio_invalido_sigue_validando(client: AsyncClient):
    response = await client.get("/modelos/api?anio_min=1800")
    assert response.status_code == 422


# ===================== Paginación =====================
@pytest.mark.asyncio
async def test_paginacion_conserva_filtros(client: AsyncClient):
    response = await client.get("/modelos?marca=Toyota&per_page=2&page=2")
    assert response.status_code == 200
    assert "Mostrando 3-3 de 3 resultados" in response.text
    assert "Página 2 de 2" in response.text
    assert "marca=Toyota&amp;per_page=2&amp;page=1" in response.text


@pytest.mark.asyncio
async def test_pagina_fuera_de_rango_se_ajusta(client: AsyncClient):
    response = await client.get("/modelos?per_page=2&page=99")
    assert response.status_code == 200
    assert "Mostrando 7-7 de 7 resultados" in response.text
    assert "Página 4 de 4" in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=-1",
        "page=abc",
        "per_page=0",
        "per_page=101",
        "per_page=abc",
    ],
)
async def test_parametros_de_paginacion_invalidos_no_rompen_la_pagina(
    client: AsyncClient, query: str
):
    response = await client.get(f"/modelos?{query}")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_q_demasiado_largo_no_devuelve_422(client: AsyncClient):
    response = await client.get(f"/modelos?q={'x' * 150}")
    assert response.status_code == 200
    assert "No hay modelos que coincidan con los filtros" in response.text
