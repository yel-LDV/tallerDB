"""Configuración principal - Usa config_loader + pydantic-settings para validación."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.config_loader import get_config, get_database_url, get_secret_key, get_admin_config


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Base settings (override con .env)
    database_url: str = ""
    secret_key: str = ""
    session_cookie_name: str = "session"
    app_name: str = "TallerDB"
    debug: bool = True

    # Admin user (creado automáticamente al iniciar)
    admin_email: str = "admin@tallerdb.local"
    admin_password: str = "admin123"

    def __init__(self, **kwargs):
        # Cargar defaults desde config.json si no vienen en kwargs
        cfg = get_config()

        defaults = {
            "database_url": cfg.database_url(),
            "secret_key": get_secret_key(),
            "app_name": cfg.get("app.name", "TallerDB"),
            "debug": cfg.get("app.debug", True),
            "session_cookie_name": cfg.get("app.session_cookie_name", "session"),
            "admin_email": get_admin_config().get("email", "admin@tallerdb.local"),
            "admin_password": get_admin_config().get("password", "admin123"),
        }

        # Merge: kwargs > .env > config.json > defaults
        merged = {**defaults, **kwargs}
        super().__init__(**merged)


# Instancia global
settings = Settings()


# Exportar para compatibilidad
__all__ = ["settings", "Settings"]