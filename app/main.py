from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Permite ejecutar `python app/main.py ...` desde cualquier directorio.
if __package__ in (None, ""):
    sys.path.insert(0, str(_PROJECT_ROOT))
    os.chdir(_PROJECT_ROOT)

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.auth.deps import get_current_user
from app.auth.router import router as auth_router
from app.config import settings
from app.database import check_database_connection, init_db
from app.modelos.router import router as modelos_router
from app.models.user import User

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Si la base de datos configurada no responde, esta excepción detiene el
    # arranque. No hay fallback silencioso a SQLite.
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="TallerDB - Sistema de catálogo de autos (Modelos)",
    lifespan=lifespan,
)

# Security middleware (order matters!)
# HTTPSRedirectMiddleware solo se activa explícitamente con FORCE_HTTPS=true:
# en Docker/local es habitual servir HTTP detrás de un proxy que ya termina TLS.
if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            host.strip()
            for host in settings.allowed_hosts.split(",")
            if host.strip()
        ],
    )

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie_name,
    max_age=60 * 60 * 24 * settings.session_max_age_days,
    https_only=settings.force_https,
    same_site="lax",
)


# Security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.force_https:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_router)
app.include_router(modelos_router)


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "landing.html",
        {"request": request, "app_name": settings.app_name},
    )


@app.get("/health")
async def health():
    """Liveness: el proceso está vivo."""
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    """Readiness: la base de datos responde."""
    try:
        await check_database_connection()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    return {"status": "ready"}


# ===================== CLI (testdb / test) =====================
async def _database_self_test() -> int:
    """Comprueba conexión, esquema, columnas 3D y un round-trip con rollback."""
    import uuid
    from decimal import Decimal

    from sqlalchemy import inspect, text

    from app.database import engine, init_db

    # La CLI prioriza una salida legible sobre el eco de SQL de DEBUG.
    engine.echo = False

    print(f"Motor configurado: {settings.database_type}")
    print(f"URL: {engine.url.render_as_string(hide_password=True)}")

    try:
        await check_database_connection()
    except Exception as exc:
        print(f"[ERROR] No se pudo conectar a la base de datos: {exc}")
        print("        Si usas MariaDB local: ./startdb.sh")
        await engine.dispose()
        return 1

    try:
        await init_db()

        async with engine.connect() as conn:
            version_sql = (
                "SELECT sqlite_version()"
                if engine.dialect.name == "sqlite"
                else "SELECT version()"
            )
            version = (await conn.execute(text(version_sql))).scalar_one()
            print(f"Servidor: {version}")

            tables = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )
            missing_tables = {"users", "modelos"} - tables
            if missing_tables:
                print(
                    "[ERROR] Faltan tablas: "
                    + ", ".join(sorted(missing_tables))
                )
                return 1
            print("[OK] Tablas users y modelos presentes")

            columns = await conn.run_sync(
                lambda sync_conn: {
                    column["name"]
                    for column in inspect(sync_conn).get_columns("modelos")
                }
            )
            required_3d = {
                "modelo_3d_key",
                "modelo_3d_url",
                "modelo_3d_formato",
                "modelo_3d_tamano",
                "modelo_3d_subido_at",
            }
            missing_3d = required_3d - columns
            if missing_3d:
                print(
                    "[ERROR] Faltan columnas 3D en modelos: "
                    + ", ".join(sorted(missing_3d))
                )
                return 1
            print("[OK] Columnas 3D presentes")

            users_before = (
                await conn.execute(text("SELECT COUNT(*) FROM users"))
            ).scalar_one()
            modelos_before = (
                await conn.execute(text("SELECT COUNT(*) FROM modelos"))
            ).scalar_one()

            # Las lecturas anteriores abrieron una transacción implícita.
            await conn.commit()
            transaction = await conn.begin()
            try:
                email = f"__testdb_{uuid.uuid4().hex}@example.invalid"
                marca = "__testdb__"
                nombre = uuid.uuid4().hex

                await conn.execute(
                    text(
                        "INSERT INTO users (email, hashed_password) "
                        "VALUES (:email, :hashed_password)"
                    ),
                    {"email": email, "hashed_password": "testdb"},
                )
                await conn.execute(
                    text(
                        "INSERT INTO modelos "
                        "(marca, nombre, anio, precio, tipo, transmision, disponible) "
                        "VALUES (:marca, :nombre, :anio, :precio, "
                        "'sedan', 'manual', :disponible)"
                    ),
                    {
                        "marca": marca,
                        "nombre": nombre,
                        "anio": 2000,
                        "precio": Decimal("1.00"),
                        "disponible": True,
                    },
                )
                await conn.execute(
                    text(
                        "UPDATE modelos SET modelo_3d_key = :key, "
                        "modelo_3d_formato = 'glb', modelo_3d_tamano = 1, "
                        "modelo_3d_url = :url "
                        "WHERE marca = :marca AND nombre = :nombre"
                    ),
                    {
                        "key": "testdb.glb",
                        "url": "/modelos/0/3d",
                        "marca": marca,
                        "nombre": nombre,
                    },
                )

                usuario = (
                    await conn.execute(
                        text("SELECT email FROM users WHERE email = :email"),
                        {"email": email},
                    )
                ).scalar_one()
                clave_3d = (
                    await conn.execute(
                        text(
                            "SELECT modelo_3d_key FROM modelos "
                            "WHERE marca = :marca AND nombre = :nombre"
                        ),
                        {"marca": marca, "nombre": nombre},
                    )
                ).scalar_one()
                if usuario != email or clave_3d != "testdb.glb":
                    print("[ERROR] El round-trip de lectura devolvió datos inesperados")
                    return 1
            finally:
                await transaction.rollback()

            users_after = (
                await conn.execute(text("SELECT COUNT(*) FROM users"))
            ).scalar_one()
            modelos_after = (
                await conn.execute(text("SELECT COUNT(*) FROM modelos"))
            ).scalar_one()
            if (users_after, modelos_after) != (users_before, modelos_before):
                print("[ERROR] El rollback dejó datos persistidos")
                return 1

            print(
                f"[OK] Lectura/escritura y rollback verificados "
                f"(users={users_before}, modelos={modelos_before})"
            )
    except Exception as exc:
        print(f"[ERROR] La comprobación de base de datos falló: {exc}")
        return 1
    finally:
        await engine.dispose()

    print("[OK] Base de datos lista para usar")
    return 0


def _run_test_suite(extra_args: list[str]) -> int:
    """Ejecuta pytest (descubre automáticamente tests nuevos)."""
    import shlex
    import subprocess

    args = list(extra_args)
    if args and args[0] == "--":
        args = args[1:]
    if not args:
        args = ["-q"]

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        *args,
    ]
    print("Ejecutando:", " ".join(shlex.quote(part) for part in command))
    result = subprocess.run(command, cwd=_PROJECT_ROOT)
    if result.returncode == 0:
        print("[OK] Toda la suite de pruebas pasó")
    else:
        print(f"[ERROR] La suite de pruebas falló (código {result.returncode})")
    return result.returncode


def _build_cli():
    import argparse

    parser = argparse.ArgumentParser(
        prog="python app/main.py",
        description=(
            "Comprobaciones de TallerDB. Sin comando muestra esta ayuda. "
            "Para arrancar el servidor usa `python run.py`."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "testdb",
        help=(
            "Verifica la conexión, crea el esquema si falta y prueba "
            "lectura/escritura con rollback."
        ),
    )

    test_parser = subparsers.add_parser(
        "test",
        help="Ejecuta toda la suite pytest (incluye pruebas futuras).",
    )
    test_parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Argumentos adicionales para pytest, por ejemplo: -q tests/test_config.py",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_cli()
    args = parser.parse_args(argv)

    if args.command == "testdb":
        return asyncio.run(_database_self_test())
    if args.command == "test":
        return _run_test_suite(args.pytest_args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
