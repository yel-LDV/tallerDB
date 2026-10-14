import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_register_get(client: AsyncClient):
    response = await client.get("/register")
    assert response.status_code == 200
    assert "Registrarse" in response.text


@pytest.mark.asyncio
async def test_login_get(client: AsyncClient):
    response = await client.get("/login")
    assert response.status_code == 200
    assert "Iniciar sesión" in response.text


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client: AsyncClient):
    response = await client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_register_post_validation(client: AsyncClient):
    # Passwords don't match
    response = await client.post("/register", data={
        "email": "test@example.com",
        "password": "password123",
        "confirm_password": "different"
    })
    assert response.status_code == 400
    assert "no coinciden" in response.text


@pytest.mark.asyncio
async def test_register_post_short_password(client: AsyncClient):
    response = await client.post("/register", data={
        "email": "test@example.com",
        "password": "short",
        "confirm_password": "short"
    })
    assert response.status_code == 400
    assert "8 caracteres" in response.text