"""
Config loader - Lee config.json y permite override con variables de entorno.
Prioridad: .env > config.json > defaults
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from functools import lru_cache

# Cargar variables del archivo .env en os.environ para que los overrides
# por variable de entorno (p. ej. DATABASE_TYPE, MARIADB_HOST) funcionen.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv es opcional
    pass


class ConfigLoader:
    """Carga configuración desde config.json y variables de entorno."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config()
        self._config: Dict[str, Any] = {}
        self.load()

    def _find_config(self) -> str:
        """Busca config.json en directorios comunes."""
        search_paths = [
            Path.cwd() / "config.json",
            Path(__file__).parent.parent / "config.json",
            Path("/app/config.json"),
        ]
        for p in search_paths:
            if p.exists():
                return str(p)
        return str(Path.cwd() / "config.json")

    def load(self) -> None:
        """Carga configuración desde archivo."""
        if Path(self.config_path).exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            self._config = self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Configuración por defecto."""
        return {
            "app": {
                "name": "TallerDB",
                "host": "0.0.0.0",
                "port": 8000,
                "debug": True,
                "secret_key": "",
                "session_cookie_name": "session",
                "session_max_age_days": 7,
            },
            "database": {
                "type": "sqlite",
                "sqlite": {"path": "./dev.db"},
                "mysql": {
                    "host": "localhost",
                    "port": 3306,
                    "user": "taller",
                    "password": "tallerpass",
                    "database": "tallerdb",
                    "charset": "utf8mb4",
                },
                "mariadb": {
                    "host": "localhost",
                    "port": 3306,
                    "user": "taller",
                    "password": "tallerpass",
                    "database": "tallerdb",
                    "charset": "utf8mb4",
                },
            },
            "security": {
                "bcrypt_rounds": 12,
                "password_min_length": 8,
                "password_max_length": 72,
            },
            "admin": {
                "email": "admin@tallerdb.local",
                "password": "admin123",
                "force_change_on_first_login": False,
            },
            "cors": {
                "enabled": False,
                "allow_origins": [],
                "allow_credentials": True,
                "allow_methods": ["GET", "POST"],
                "allow_headers": ["*"],
            },
            "rate_limit": {
                "enabled": False,
                "requests_per_minute": 60,
                "login_attempts_per_hour": 10,
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "file": "logs/app.log",
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene valor con notación de punto (ej: 'database.mysql.host')."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def get_env_override(self, key: str, env_var: str, default: Any = None) -> Any:
        """Obtiene valor con override de variable de entorno."""
        env_val = os.environ.get(env_var)
        if env_val is not None:
            # Intentar parsear como JSON para tipos complejos
            try:
                return json.loads(env_val)
            except json.JSONDecodeError:
                return env_val
        return self.get(key, default)

    def database_url(self) -> str:
        """Construye DATABASE_URL según configuración.

        Tipos soportados:
          - sqlite: archivo local (default en desarrollo)
          - mysql / mariadb: servidor MySQL o MariaDB vía asyncmy
        """
        db_type = self.get_env_override("database.type", "DATABASE_TYPE", "sqlite").lower()

        if db_type in ("mysql", "mariadb"):
            # MariaDB y MySQL comparten el driver asyncmy, solo cambian los
            # nombres de sección/variables de entorno para leer la config.
            section = db_type
            env_prefix = "MARIADB" if db_type == "mariadb" else "MYSQL"

            host = self.get_env_override(
                f"database.{section}.host", f"{env_prefix}_HOST", "localhost"
            )
            port = self.get_env_override(
                f"database.{section}.port", f"{env_prefix}_PORT", 3306
            )
            user = self.get_env_override(
                f"database.{section}.user", f"{env_prefix}_USER", "taller"
            )
            password = self.get_env_override(
                f"database.{section}.password", f"{env_prefix}_PASSWORD", "tallerpass"
            )
            database = self.get_env_override(
                f"database.{section}.database", f"{env_prefix}_DATABASE", "tallerdb"
            )
            charset = self.get_env_override(
                f"database.{section}.charset", f"{env_prefix}_CHARSET", "utf8mb4"
            )
            return f"mysql+asyncmy://{user}:{password}@{host}:{port}/{database}?charset={charset}"

        # SQLite por defecto
        path = self.get_env_override("database.sqlite.path", "SQLITE_PATH", "./dev.db")
        return f"sqlite+aiosqlite:///{path}"

    def to_dict(self) -> Dict[str, Any]:
        """Retorna configuración completa."""
        return self._config.copy()


@lru_cache()
def get_config() -> ConfigLoader:
    """Singleton para acceso global a configuración."""
    return ConfigLoader()


# Helper functions para uso directo
def get_database_url() -> str:
    return get_config().database_url()


def get_secret_key() -> str:
    return get_config().get_env_override("app.secret_key", "SECRET_KEY", "dev-secret-change-me")


def get_app_config() -> Dict[str, Any]:
    return get_config().get("app", {})


def get_security_config() -> Dict[str, Any]:
    return get_config().get("security", {})


def get_admin_config() -> Dict[str, Any]:
    return get_config().get("admin", {})