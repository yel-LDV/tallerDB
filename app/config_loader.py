"""
Config loader - Lee config.json y permite override con variables de entorno.
Prioridad: entorno/.env > config.json > defaults

Soporta SQLite, MySQL, MariaDB y PostgreSQL. La URL se construye con
``sqlalchemy.engine.URL`` para codificar correctamente credenciales con
caracteres especiales.
"""
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.engine import URL

# Cargar variables del archivo .env en os.environ para que los overrides
# por variable de entorno (p. ej. DATABASE_TYPE, MARIADB_HOST) funcionen.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv es opcional
    pass


SUPPORTED_DATABASE_TYPES = {"sqlite", "mysql", "mariadb", "postgresql"}

DATABASE_TYPE_ALIASES = {
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "pgsql": "postgresql",
    "mysql": "mysql",
    "mariadb": "mariadb",
    "maria": "mariadb",
    "sqlite": "sqlite",
    "sqlite3": "sqlite",
}


def normalize_database_type(value: Optional[str]) -> str:
    """Normaliza y valida el tipo de base de datos.

    Un valor desconocido debe fallar en el arranque, nunca caer en SQLite.
    """
    if value is None or not str(value).strip():
        return "sqlite"

    normalized = str(value).strip().lower()
    normalized = DATABASE_TYPE_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_DATABASE_TYPES:
        supported = ", ".join(sorted(SUPPORTED_DATABASE_TYPES))
        raise ValueError(
            f"Tipo de base de datos no soportado: {value!r}. "
            f"Valores válidos: {supported}."
        )
    return normalized


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
                "connect_timeout": 5,
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
                "postgresql": {
                    "host": "localhost",
                    "port": 5432,
                    "user": "taller",
                    "password": "tallerpass",
                    "database": "tallerdb",
                    "sslmode": "",
                },
            },
            "uploads": {
                "dir": "./uploads",
                "max_3d_size_mb": 25,
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
        """Obtiene un valor del entorno (sin transformarlo) o del config."""
        env_val = os.environ.get(env_var)
        if env_val is not None and env_val != "":
            return env_val
        return self.get(key, default)

    @staticmethod
    def _env(*names: str) -> Optional[str]:
        """Devuelve el primer valor de entorno no vacío de una lista."""
        for name in names:
            value = os.environ.get(name)
            if value is not None and value != "":
                return value
        return None

    def _value(self, config_key: str, *env_names: str, default: Any = None) -> Any:
        """Prioriza variables de entorno; luego config.json; luego default."""
        env_value = self._env(*env_names)
        if env_value is not None:
            return env_value
        value = self.get(config_key, None)
        return default if value is None or value == "" else value

    @staticmethod
    def _as_int(value: Any, name: str, default: int) -> int:
        if value is None or value == "":
            return default
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} debe ser un número entero.") from exc
        return number

    @staticmethod
    def _type_from_url(url: str) -> str:
        scheme = url.split("://", 1)[0].strip().lower()
        if scheme.startswith("postgres"):
            return "postgresql"
        if scheme.startswith("mariadb"):
            return "mariadb"
        if scheme.startswith("mysql"):
            return "mysql"
        if scheme.startswith("sqlite"):
            return "sqlite"
        raise ValueError(
            f"DATABASE_URL usa un esquema no soportado: {scheme!r}. "
            "Usa sqlite, mysql, mariadb o postgresql."
        )

    def database_type(self) -> str:
        """Tipo de base de datos activo, normalizado y validado."""
        direct_url = self._env("DATABASE_URL")
        if direct_url:
            return self._type_from_url(direct_url)

        raw_type = self._env("DATABASE_TYPE")
        if raw_type is None:
            raw_type = self.get("database.type", "sqlite")
        return normalize_database_type(raw_type)

    @staticmethod
    def _normalize_direct_url(url: str) -> str:
        """Convierte esquemas síncronos comunes en sus equivalentes async."""
        url = url.strip()
        replacements = {
            "postgres://": "postgresql+asyncpg://",
            "postgresql://": "postgresql+asyncpg://",
            "mariadb://": "mysql+asyncmy://",
            "mysql://": "mysql+asyncmy://",
            "sqlite://": "sqlite+aiosqlite://",
        }
        for prefix, replacement in replacements.items():
            if url.startswith(prefix):
                url = replacement + url[len(prefix):]
                break

        # asyncpg recibe ``ssl``, no ``sslmode``. Las URLs de PostgreSQL
        # copiadas de proveedores suelen traer ``?sslmode=require``.
        if url.startswith("postgresql+asyncpg://"):
            parsed = urlsplit(url)
            if parsed.query:
                pairs = parse_qsl(parsed.query, keep_blank_values=True)
                converted = [
                    ("ssl" if key == "sslmode" else key, value)
                    for key, value in pairs
                ]
                if converted != pairs:
                    url = urlunsplit(parsed._replace(query=urlencode(converted)))
        return url

    def database_url(self) -> str:
        """Construye DATABASE_URL según configuración.

        Tipos soportados:
          - sqlite: archivo local (default en desarrollo)
          - mysql / mariadb: servidor MySQL o MariaDB vía asyncmy
          - postgresql: servidor PostgreSQL vía asyncpg
        """
        direct_url = self._env("DATABASE_URL")
        if direct_url:
            return self._normalize_direct_url(direct_url)

        db_type = self.database_type()

        if db_type == "sqlite":
            path = self._value(
                "database.sqlite.path", "SQLITE_PATH", "DB_PATH", default="./dev.db"
            )
            return f"sqlite+aiosqlite:///{path}"

        if db_type in ("mysql", "mariadb"):
            prefix = "MARIADB" if db_type == "mariadb" else "MYSQL"
            host = self._value(
                f"database.{db_type}.host", f"{prefix}_HOST", "DB_HOST", default="localhost"
            )
            port = self._as_int(
                self._value(
                    f"database.{db_type}.port",
                    f"{prefix}_PORT",
                    "DB_PORT",
                    default=3306,
                ),
                "El puerto de MySQL/MariaDB",
                3306,
            )
            user = self._value(
                f"database.{db_type}.user", f"{prefix}_USER", "DB_USER", default="taller"
            )
            password = self._value(
                f"database.{db_type}.password",
                f"{prefix}_PASSWORD",
                "DB_PASSWORD",
                default="tallerpass",
            )
            database = self._value(
                f"database.{db_type}.database",
                f"{prefix}_DATABASE",
                "DB_NAME",
                default="tallerdb",
            )
            charset = self._value(
                f"database.{db_type}.charset",
                f"{prefix}_CHARSET",
                "DB_CHARSET",
                default="utf8mb4",
            )

            if not 1 <= port <= 65535:
                raise ValueError("El puerto de MySQL/MariaDB debe estar entre 1 y 65535.")

            url = URL.create(
                drivername="mysql+asyncmy",
                username=str(user),
                password=str(password),
                host=str(host),
                port=port,
                database=str(database),
                query={"charset": str(charset)},
            )
            return url.render_as_string(hide_password=False)

        # PostgreSQL
        host = self._value(
            "database.postgresql.host", "POSTGRES_HOST", "DB_HOST", default="localhost"
        )
        port = self._as_int(
            self._value(
                "database.postgresql.port", "POSTGRES_PORT", "DB_PORT", default=5432
            ),
            "El puerto de PostgreSQL",
            5432,
        )
        user = self._value(
            "database.postgresql.user", "POSTGRES_USER", "DB_USER", default="taller"
        )
        password = self._value(
            "database.postgresql.password",
            "POSTGRES_PASSWORD",
            "DB_PASSWORD",
            default="tallerpass",
        )
        database = self._value(
            "database.postgresql.database",
            "POSTGRES_DATABASE",
            "DB_NAME",
            default="tallerdb",
        )
        sslmode = self._value(
            "database.postgresql.sslmode",
            "POSTGRES_SSLMODE",
            "DB_SSLMODE",
            default="",
        )

        if not 1 <= port <= 65535:
            raise ValueError("El puerto de PostgreSQL debe estar entre 1 y 65535.")

        query = {}
        if sslmode:
            query["ssl"] = str(sslmode)

        url = URL.create(
            drivername="postgresql+asyncpg",
            username=str(user),
            password=str(password),
            host=str(host),
            port=port,
            database=str(database),
            query=query or None,
        )
        return url.render_as_string(hide_password=False)

    def database_connect_timeout(self) -> float:
        raw = self._value(
            "database.connect_timeout",
            "DATABASE_CONNECT_TIMEOUT",
            "DB_CONNECT_TIMEOUT",
            default=5,
        )
        try:
            timeout = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("DATABASE_CONNECT_TIMEOUT debe ser un número.") from exc
        if timeout <= 0:
            raise ValueError("DATABASE_CONNECT_TIMEOUT debe ser mayor que cero.")
        return timeout

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


def get_database_type() -> str:
    return get_config().database_type()


def get_secret_key() -> str:
    value = get_config().get_env_override(
        "app.secret_key", "SECRET_KEY", "dev-secret-change-me"
    )
    # config.json puede traer secret_key vacío; nunca dejamos la sesión sin clave.
    return value or "dev-secret-change-me"


def get_app_config() -> Dict[str, Any]:
    return get_config().get("app", {})


def get_security_config() -> Dict[str, Any]:
    return get_config().get("security", {})


def get_admin_config() -> Dict[str, Any]:
    return get_config().get("admin", {})
