import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.main import app
from app.schemas.modelo import ModeloCreate, ModeloUpdate


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ===================== Control de acceso =====================
@pytest.mark.asyncio
async def test_modelos_page_requires_auth(client: AsyncClient):
    response = await client.get("/modelos", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_modelos_api_requires_auth(client: AsyncClient):
    response = await client.get("/modelos/api", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_modelos_api_create_requires_auth(client: AsyncClient):
    response = await client.post(
        "/modelos/api",
        json={"marca": "X", "nombre": "Y", "anio": 2024, "precio": 1000},
        follow_redirects=False,
    )
    assert response.status_code == 303


# ===================== Validación de esquemas =====================
def test_modelo_create_valido():
    modelo = ModeloCreate(
        marca="Toyota",
        nombre="Corolla",
        anio=2024,
        precio=28900.00,
        tipo="sedan",
        transmision="automatica",
    )
    assert modelo.marca == "Toyota"
    assert modelo.disponible is True  # valor por defecto


def test_modelo_anio_fuera_de_rango():
    with pytest.raises(ValidationError):
        ModeloCreate(marca="X", nombre="Y", anio=1800, precio=1000)


def test_modelo_precio_negativo():
    with pytest.raises(ValidationError):
        ModeloCreate(marca="X", nombre="Y", anio=2024, precio=-5)


def test_modelo_update_parcial():
    # Todos los campos son opcionales en la actualización parcial
    update = ModeloUpdate(precio=15000)
    assert update.precio == 15000
    assert update.marca is None
