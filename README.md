# TallerDB - Catálogo de Autos (categoría «Modelos»)

Proyecto base con **FastAPI + Jinja2 + MariaDB + Sessions + Dark Mode**, extendido
con un **catálogo de autos** (categoría «Modelos») que incluye interfaz web y API REST
con operaciones CRUD.

## Características

- **Login / Registro** con validación servidor
- **Sesiones seguras** (HttpOnly, SameSite=Lax, 7 días)
- **Hash de contraseñas** con bcrypt
- **Dark/Light mode** (preferencia del sistema por defecto, persiste en localStorage)
- **Nueva categoría «Modelos»** — catálogo de autos con galería, búsqueda, filtros,
  ordenamiento, estadísticas y CRUD completo vía API REST
- **Conexión a MariaDB** (driver asíncrono `asyncmy`), configurable también con SQLite
- **Migraciones** con Alembic
- **Scripts SQL** de esquema, datos de ejemplo y pruebas CRUD

## Stack

| Capa | Tecnología |
|------|------------|
| Web | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 (async) |
| DB | MariaDB 11 / MySQL (driver `asyncmy`) · SQLite opcional |
| Templates | Jinja2 |
| Auth | Starlette Sessions + bcrypt |
| Validación | Pydantic 2 |
| Config | pydantic-settings |
| Migraciones | Alembic 1.13 |

## Estructura

```
tallerdbProyect/
├── app/
│   ├── config.py / config_loader.py   # Settings + construcción de la URL de BD
│   ├── database.py                    # SQLAlchemy async engine/session
│   ├── main.py                        # FastAPI app + middleware
│   ├── models/
│   │   ├── user.py                    # Entidad User
│   │   └── modelo.py                  # Entidad Modelo (tabla modelos)  ← NUEVO
│   ├── schemas/
│   │   ├── auth.py
│   │   └── modelo.py                  # Validación Pydantic del catálogo ← NUEVO
│   ├── auth/
│   │   ├── security.py / deps.py / router.py
│   ├── modelos/                       # Categoría Modelos                   ← NUEVO
│   │   └── router.py                  # Página HTML + API CRUD
│   └── templates/
│       ├── base.html / login.html / register.html / dashboard.html
│       └── modelos.html               # Interfaz del catálogo               ← NUEVO
├── database/                          # Scripts SQL                          ← NUEVO
│   ├── schema_mariadb.sql             # DDL del esquema
│   ├── seed_modelos.sql               # Datos de ejemplo
│   ├── pruebas_crud.sql               # Pruebas INSERT/SELECT/UPDATE/DELETE
│   └── init/                          # Init automático del contenedor MariaDB
│       ├── 01_schema.sql
│       └── 02_seed_modelos.sql
├── docs/INFORME_EVIDENCIA.md          # Informe (portada, desarrollo, etc.)  ← NUEVO
├── alembic/                           # Migraciones
├── tests/                             # Pruebas (auth + modelos)
├── docker-compose.yml                 # App + MariaDB
├── requirements.txt
└── run.py
```

## Instalación

### Opción A — Docker (MariaDB)

```bash
cp .env.example .env
docker compose up --build
# La base de datos se crea y se puebla automáticamente con database/init/
```

Abrir: http://localhost:8000

### Opción B — Local con MariaDB

```bash
# 1. Entorno virtual
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Crear la base de datos y el esquema
mariadb -u root -p < database/schema_mariadb.sql

# 3. Datos de ejemplo
mariadb -u taller -p tallerdb < database/seed_modelos.sql

# 3. Configurar .env  (ver ".env")
#    DATABASE_TYPE=mariadb  y las variables MARIAB_* … MARIADB_*

# 4. Migraciones y usuario admin
alembic upgrade head
python scripts/create_admin.py

# 5. Levantar servidor
python run.py
```

## Uso

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/register` | GET/POST | Registro público |
| `/login` | GET/POST | Inicio de sesión |
| `/logout` | POST | Cerrar sesión |
| `/dashboard` | GET | Panel protegido (requiere auth) |
| **`/modelos`** | **GET** | **Catálogo de autos con filtros (requiere auth)** |
| **`/modelos/api`** | **GET/POST** | **Listar / crear modelos (POST requiere admin)** |
| **`/modelos/api/{id}`** | **GET/PUT/DELETE** | **Consultar / actualizar / borrar (PUT y DELETE requieren admin)** |
| `/docs` | GET | Swagger UI (API docs) |

> Solo los administradores pueden crear, editar y borrar modelos. Cualquier usuario
> autenticado puede consultar el catálogo.

## Scripts SQL (`database/`)

| Archivo | Propósito |
|---------|-----------|
| `schema_mariadb.sql` | Crea la base de datos y las tablas (`users`, `modelos`). |
| `seed_modelos.sql` | Inserta 18 autos de ejemplo. |
| `pruebas_crud.sql` | Demuestra INSERT / SELECT / UPDATE / DELETE con `ROLLBACK`. |
| `init/*.sql` | Ejecutados automáticamente por la imagen de MariaDB en Docker. |

```bash
# Pruebas CRUD (incluye una violación de UNIQUE a propósito)
mariadb -u taller -p --force tallerdb < database/pruebas_crud.sql
```

## Base de datos: SQLite o MariaDB

El tipo de base de datos se controla con `DATABASE_TYPE` y la sección correspondiente
en `config.json` / variables de entorno:

```env
# MariaDB (recomendado)
DATABASE_TYPE=mariadb
MARIADB_HOST=localhost
MARIADB_PORT=3306
MARIADB_USER=taller
MARIADB_PASSWORD=tallerpass
MARIADB_DATABASE=tallerdb

# SQLite (desarrollo rápido, sin servidor)
DATABASE_TYPE=sqlite
SQLITE_PATH=./dev.db
```

## Evidencia / informe

El informe completo con portada, introducción, descripción de interfaces, pruebas
CRUD, código SQL, resultados, recomendaciones, conclusiones y referencias APA está en:

```
docs/INFORME_EVIDENCIA.md
```

## Desarrollo

```bash
# Nueva migración tras cambiar modelos
alembic revision --autogenerate -m "descripcion"

# Tests
pytest
```
