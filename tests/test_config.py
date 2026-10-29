"""Pruebas de configuración de la base de datos y precedencia de entorno."""

import pytest

from app.config import Settings
from app.config_loader import ConfigLoader


def _loader(tmp_path) -> ConfigLoader:
    # Archivo inexistente: usa defaults internos y luego los overrides de entorno.
    return ConfigLoader(str(tmp_path / "config.json"))


@pytest.fixture(autouse=True)
def _sin_url_directa(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)


@pytest.mark.parametrize(
    ("tipo", "prefijo"),
    [
        ("sqlite", "sqlite+aiosqlite:///"),
        ("mysql", "mysql+asyncmy://"),
        ("mariadb", "mysql+asyncmy://"),
        ("postgresql", "postgresql+asyncpg://"),
    ],
)
def test_database_url_por_motor(monkeypatch, tmp_path, tipo, prefijo):
    monkeypatch.setenv("DATABASE_TYPE", tipo)
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MYSQL_HOST", "mysql.local")
    monkeypatch.setenv("MARIADB_HOST", "maria.local")
    monkeypatch.setenv("POSTGRES_HOST", "pg.local")

    loader = _loader(tmp_path)

    assert loader.database_type() == tipo
    assert loader.database_url().startswith(prefijo)


@pytest.mark.parametrize(
    ("alias", "esperado"),
    [
        ("postgres", "postgresql"),
        ("pgsql", "postgresql"),
        ("maria", "mariadb"),
        ("sqlite3", "sqlite"),
    ],
)
def test_aliases_de_motor(monkeypatch, tmp_path, alias, esperado):
    monkeypatch.setenv("DATABASE_TYPE", alias)
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    assert _loader(tmp_path).database_type() == esperado


def test_tipo_desconocido_falla(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_TYPE", "oracle")
    with pytest.raises(ValueError, match="no soportado"):
        _loader(tmp_path).database_type()


def test_password_se_codifica_en_url(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_TYPE", "postgresql")
    monkeypatch.setenv("POSTGRES_HOST", "pg.local")
    monkeypatch.setenv("POSTGRES_USER", "taller")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:word/with?chars")

    url = _loader(tmp_path).database_url()

    assert "p%40ss%3Aword%2Fwith%3Fchars" in url
    assert "p@ss:word" not in url


def test_database_url_tiene_prioridad(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_TYPE", "sqlite")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://usuario:clave@pg.local:5432/tallerdb"
    )

    loader = _loader(tmp_path)

    assert loader.database_type() == "postgresql"
    assert loader.database_url() == (
        "postgresql+asyncpg://usuario:clave@pg.local:5432/tallerdb"
    )


def test_database_url_mariadb_usa_driver_asyncmy(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "DATABASE_URL", "mariadb://usuario:clave@maria.local:3306/tallerdb"
    )

    loader = _loader(tmp_path)

    assert loader.database_type() == "mariadb"
    assert loader.database_url() == (
        "mysql+asyncmy://usuario:clave@maria.local:3306/tallerdb"
    )


def test_database_url_postgres_ssl_mode_se_traduce(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://usuario:clave@pg.local:5432/tallerdb?sslmode=require",
    )

    url = _loader(tmp_path).database_url()

    assert url.startswith("postgresql+asyncpg://")
    assert "ssl=require" in url
    assert "sslmode" not in url


def test_database_url_ignora_un_tipo_invalido(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_TYPE", "oracle")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://usuario:clave@pg.local:5432/tallerdb"
    )

    loader = _loader(tmp_path)

    assert loader.database_type() == "postgresql"
    assert loader.database_url().startswith("postgresql+asyncpg://")


def test_settings_prioriza_database_url_sobre_tipo_invalido(monkeypatch):
    monkeypatch.setenv("DATABASE_TYPE", "oracle")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://usuario:clave@pg.local:5432/tallerdb"
    )

    settings = Settings()

    assert settings.database_type == "postgresql"
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_database_url_con_esquema_desconocido_falla(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "oracle://usuario:clave@host/db")
    with pytest.raises(ValueError, match="esquema no soportado"):
        _loader(tmp_path).database_type()


def test_settings_prioriza_entorno_sobre_config_json(monkeypatch):
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("APP_NAME", "NombreDesdeEntorno")
    monkeypatch.setenv("ADMIN_EMAIL", "  Admin@Example.COM ")

    settings = Settings()

    assert settings.debug is False
    assert settings.app_name == "NombreDesdeEntorno"
    assert settings.admin_email == "admin@example.com"


def test_timeout_invalido_falla(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_CONNECT_TIMEOUT", "0")
    with pytest.raises(ValueError, match="mayor que cero"):
        _loader(tmp_path).database_connect_timeout()
