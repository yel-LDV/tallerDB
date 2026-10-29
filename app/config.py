"""Configuración principal - config.json + variables de entorno.

La precedencia es: entorno/.env > config.json > defaults. Para lograrlo,
los valores de config.json se usan como ``default_factory`` y no como
argumentos del constructor, ya que pydantic-settings da prioridad a los
kwargs sobre las variables de entorno.
"""

import os

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config_loader import (
    get_admin_config,
    get_config,
    get_secret_key,
    normalize_database_type,
)


def _app_default(key: str, default):
    return get_config().get(f"app.{key}", default)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Base de datos
    database_url: str = Field(default_factory=lambda: get_config().database_url())
    database_type: str = Field(default_factory=lambda: get_config().database_type())
    database_connect_timeout: float = Field(
        default_factory=lambda: get_config().database_connect_timeout()
    )

    # Aplicación
    secret_key: str = Field(default_factory=get_secret_key)
    session_cookie_name: str = Field(
        default_factory=lambda: _app_default("session_cookie_name", "session")
    )
    session_max_age_days: int = Field(
        default_factory=lambda: int(_app_default("session_max_age_days", 7))
    )
    app_name: str = Field(default_factory=lambda: _app_default("name", "TallerDB"))
    app_host: str = Field(default_factory=lambda: _app_default("host", "0.0.0.0"))
    app_port: int = Field(default_factory=lambda: int(_app_default("port", 8000)))
    debug: bool = Field(default_factory=lambda: bool(_app_default("debug", True)))
    force_https: bool = Field(
        default_factory=lambda: bool(_app_default("force_https", False))
    )
    allowed_hosts: str = Field(
        default_factory=lambda: _app_default(
            "allowed_hosts", "localhost,127.0.0.1,*.tallerdb.local"
        )
    )

    # Usuario administrador inicial (lo crea scripts/create_admin.py)
    admin_email: str = Field(
        default_factory=lambda: get_admin_config().get(
            "email", "admin@tallerdb.local"
        )
    )
    admin_password: str = Field(
        default_factory=lambda: get_admin_config().get("password", "admin123")
    )

    # Archivos 3D
    uploads_dir: str = Field(
        default_factory=lambda: get_config().get("uploads.dir", "./uploads")
    )
    max_3d_size_mb: int = Field(
        default_factory=lambda: int(get_config().get("uploads.max_3d_size_mb", 25))
    )

    @field_validator("database_type", mode="before")
    @classmethod
    def _normalize_db_type(cls, value):
        # DATABASE_URL tiene prioridad sobre DATABASE_TYPE: si está definida,
        # el tipo se deduce de la URL y un DATABASE_TYPE inválido se ignora.
        direct_url = os.environ.get("DATABASE_URL", "").strip()
        if direct_url:
            return get_config()._type_from_url(
                get_config()._normalize_direct_url(direct_url)
            )
        return normalize_database_type(value)

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db_url(cls, value):
        if value is None or not str(value).strip():
            return get_config().database_url()
        return get_config()._normalize_direct_url(str(value))

    @field_validator("admin_email")
    @classmethod
    def _normalize_admin_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("max_3d_size_mb")
    @classmethod
    def _validate_max_3d_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("MAX_3D_SIZE_MB debe ser mayor que cero.")
        return value

    @field_validator("session_max_age_days")
    @classmethod
    def _validate_session_days(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("SESSION_MAX_AGE_DAYS debe ser mayor que cero.")
        return value

    @model_validator(mode="after")
    def _sync_type_from_url(self):
        # Si se da una URL completa, el tipo se deduce de su esquema.
        if os.environ.get("DATABASE_URL"):
            self.database_type = get_config()._type_from_url(self.database_url)
        return self


# Instancia global
settings = Settings()


# Exportar para compatibilidad
__all__ = ["settings", "Settings"]
