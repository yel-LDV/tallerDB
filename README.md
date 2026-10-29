# TallerDB - Catálogo de Autos (categoría «Modelos»)

Aplicación **FastAPI + Jinja2 + SQLAlchemy async** con registro público de
usuarios, catálogo de autos con búsqueda/filtros y visor de **modelos 3D**.
La base de datos es configurable entre **SQLite, MySQL, MariaDB y PostgreSQL**;
si el motor configurado no responde, la aplicación **no arranca** (fail-fast).

## Características

- **Registro público** de usuarios con validación en servidor, contraseñas bcrypt
  y sesión persistente; las cuentas quedan guardadas en la base de datos.
- **Login / logout** con sesiones HttpOnly y SameSite=Lax.
- **Administración**: usuario admin por defecto (`admin@tallerdb.local` /
  `admin123`), creación de más administradores y gestión de usuarios desde el
  panel.
- **Catálogo «Modelos»** con galería, búsqueda, filtros por marca/tipo/año/
  disponibilidad, ordenamiento, estadísticas y paginación.
- **CRUD completo** vía API REST (crear/editar/borrar requiere administrador).
- **Modelos 3D en formato GLB**: subida desde el panel de administración,
  visor interactivo con `model-viewer`, servido mediante endpoint autenticado.
- **Bases de datos**: SQLite, MySQL, MariaDB y PostgreSQL con `DATABASE_URL` o
  variables por motor. Arranque fail-fast salvo con SQLite.
- **MariaDB local en un comando** con `./startdb.sh` y `./stopdb.sh`
  (instancia propia en `.mariadb/`, datos persistentes).
- **Comprobaciones CLI**: `python app/main.py testdb` valida la base de datos y
  `python app/main.py test` ejecuta toda la suite.
- **Dark/Light mode** (preferencia del sistema por defecto, persiste en localStorage).

## Stack

| Capa | Tecnología |
|------|------------|
| Web | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 (async) |
| DB | SQLite · MySQL/MariaDB (`asyncmy`) · PostgreSQL (`asyncpg`) |
| Templates | Jinja2 |
| Auth | Starlette Sessions + bcrypt |
| Validación | Pydantic 2 |
| Config | pydantic-settings + `config.json` + `.env` |
| 3D | Google `<model-viewer>` (servido localmente) |
| Tests | pytest + httpx |

## Estructura

```
tallerdbProyect/
├── app/
│   ├── config.py / config_loader.py   # Settings + URL de BD por motor
│   ├── database.py                    # Engine async, fail-fast e init de esquema
│   ├── main.py                        # FastAPI app + middleware + /health, /ready + CLI
│   ├── models/
│   │   ├── user.py                    # Entidad User
│   │   └── modelo.py                  # Entidad Modelo (incluye campos 3D)
│   ├── schemas/
│   │   ├── auth.py
│   │   └── modelo.py
│   ├── auth/
│   │   ├── security.py / deps.py / router.py
│   ├── modelos/
│   │   ├── router.py                  # Página HTML + API CRUD + endpoints 3D
│   │   └── storage.py                 # Validación y almacenamiento de GLB
│   ├── static/
│   │   ├── style.css
│   │   └── vendor/model-viewer.min.js
│   └── templates/
│       ├── base.html / landing.html / login.html / register.html
│       ├── dashboard.html
│       └── modelos.html               # Catálogo + visor/gestión 3D
├── database/
│   ├── schema_mariadb.sql             # DDL para MariaDB/MySQL
│   ├── schema_postgresql.sql          # DDL para PostgreSQL
│   ├── seed_modelos.sql               # Datos de ejemplo
│   ├── pruebas_crud.sql               # Pruebas INSERT/SELECT/UPDATE/DELETE
│   ├── init/                          # Init automático del contenedor MariaDB/MySQL
│   └── init_postgres/                 # Init automático del contenedor PostgreSQL
├── docs/INFORME_EVIDENCIA.md
├── alembic/                           # Migraciones manuales opcionales
├── tests/                             # Pruebas (auth, filtros, 3D, configuración)
├── docker-compose.yml                 # App + MariaDB (por defecto)
├── docker-compose.mysql.yml           # App + MySQL
├── docker-compose.postgres.yml        # App + PostgreSQL
├── startdb.sh                         # Inicia MariaDB local (.mariadb/)
├── stopdb.sh                          # Apaga MariaDB local sin borrar datos
├── requirements.txt
└── run.py
```

## Instalación

### Opción A — Docker con MariaDB (por defecto)

```bash
cp .env.example .env
docker compose up --build
# La base de datos se crea y se puebla automáticamente con database/init/
```

Abrir: <http://localhost:8000>

### Opción B — Docker con MySQL o PostgreSQL

```bash
# MySQL
docker compose -f docker-compose.mysql.yml up --build

# PostgreSQL
docker compose -f docker-compose.postgres.yml up --build
```

### Opción C — Local con MariaDB

```bash
# 1. Entorno virtual
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configurar .env (los valores por defecto ya apuntan a MariaDB local)
cp .env.example .env

# 3. Iniciar MariaDB del proyecto (crea datos, base, esquema y datos de ejemplo)
./startdb.sh

# 4. Usuario admin y servidor
python scripts/create_admin.py
python run.py

# 5. Apagar MariaDB al terminar (los datos se conservan)
./stopdb.sh
```

`startdb.sh` usa una instancia propia en `.mariadb/` (ignorada por git):

| Recurso | Ruta por defecto |
|---------|------------------|
| Datos | `.mariadb/data` |
| Socket | `.mariadb/run/mariadb.sock` |
| PID | `.mariadb/run/mariadb.pid` |
| Log | `.mariadb/log/mariadb.err` |

- Escucha en `127.0.0.1:${MARIADB_PORT:-3306}` con root local por socket.
- Crea la base y el usuario de `.env` (`MARIADB_DATABASE`, `MARIADB_USER`,
  `MARIADB_PASSWORD`) de forma idempotente.
- La primera vez inicializa el datadir; si el catálogo está vacío carga
  `database/init/02_seed_modelos.sql`.
- `./startdb.sh --no-seed` evita cargar los datos de ejemplo.
- `./stopdb.sh` apaga por socket y, si hace falta, por PID; **no borra datos**.

Alternativa manual para MariaDB/MySQL/PostgreSQL:
```bash
mariadb -u root -p < database/schema_mariadb.sql
# psql -U taller -d tallerdb -f database/schema_postgresql.sql
mariadb -u taller -p tallerdb < database/seed_modelos.sql
```

Al arrancar, la aplicación comprueba la conexión, crea las tablas que falten y
añade columnas nullable nuevas (por ejemplo las 3D) a instalaciones existentes.

## Uso

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET | Landing pública; redirige al panel si hay sesión |
| `/register` | GET/POST | Registro público de usuarios |
| `/login` | GET/POST | Inicio de sesión |
| `/logout` | POST | Cerrar sesión |
| `/dashboard` | GET | Panel protegido (requiere auth) |
| `/health` | GET | Liveness del proceso |
| `/ready` | GET | Readiness: comprueba la base de datos |
| **`/modelos`** | **GET** | **Catálogo con búsqueda, filtros y paginación** |
| **`/modelos/api`** | **GET/POST** | **Listar / crear modelos (POST requiere admin)** |
| **`/modelos/api/{id}`** | **GET/PUT/DELETE** | **Consultar / actualizar / borrar (PUT y DELETE requieren admin)** |
| **`/modelos/api/{id}/3d`** | **POST/DELETE** | **Subir / quitar el GLB (requiere admin)** |
| **`/modelos/{id}/3d`** | **GET** | **Descargar el GLB (requiere sesión)** |
| `/admin/users` | GET | Listar usuarios (JSON, requiere admin) |
| `/admin/users/create` | POST | Crear usuario/administrador (requiere admin) |
| `/admin/users/{id}/toggle-admin` | POST | Otorgar o quitar permisos de admin |
| `/admin/users/{id}/toggle-active` | POST | Activar o desactivar una cuenta |
| `/docs` | GET | Swagger UI |

> Solo los administradores pueden crear, editar, borrar modelos y gestionar sus
> archivos 3D. Cualquier usuario autenticado puede consultar el catálogo.

## Usuario administrador

El proyecto incluye un administrador por defecto, definido en `.env`:

| Campo | Valor por defecto |
|-------|-------------------|
| Email | `admin@tallerdb.local` |
| Contraseña | `admin123` |

Se crea ejecutando el script idempotente (si ya existe, no lo duplica):

```bash
python scripts/create_admin.py
```

- Con `./start.sh` se ejecuta automáticamente antes de levantar el servidor.
- Con Docker Compose también se ejecuta al arrancar el contenedor de la app.
- Con `./startdb.sh && python run.py` ejecútalo una vez antes del primer
  arranque (la app crea el esquema, pero no el usuario admin).

> **Importante:** cambia `ADMIN_EMAIL` y `ADMIN_PASSWORD` en `.env` **antes**
> del primer arranque en producción. La contraseña debe tener entre 8 y 72
> bytes (límite de bcrypt). Si el usuario ya existe, el script no actualiza la
> contraseña; para cambiarla, edita la base de datos o crea otro administrador.

### Crear más administradores

Con una sesión de administrador:

1. Entra en `/dashboard`.
2. En **Gestión de Usuarios**, pulsa **Crear Admin**.
3. Indica email, contraseña y confirmación (mínimo 8 caracteres).

Desde esa misma tabla también puedes:

- **Otorgar o quitar permisos** de administrador a un usuario existente
  (botón de candado).
- **Activar o desactivar** cuentas.
- Ver el listado completo de usuarios registrados.

Por API (con la sesión de admin):

```bash
# Crear un administrador
curl -X POST http://localhost:8000/admin/users/create \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"email":"otro-admin@tallerdb.local","password":"clave-segura","is_admin":true}'

# Convertir un usuario existente en administrador
curl -X POST http://localhost:8000/admin/users/2/toggle-admin \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"is_admin":true}'
```

> Por seguridad, un administrador no puede quitarse sus propios permisos ni
> desactivar su propia cuenta. El registro público (`/register`) siempre crea
> usuarios estándar; los permisos de admin se otorgan desde el panel.

## Base de datos

La precedencia de configuración es: **variables de entorno / `.env` >
`config.json` > valores por defecto**. El `.env` incluido usa **MariaDB local**
(`DATABASE_TYPE=mariadb`, `MARIADB_HOST=127.0.0.1`).

```env
# MariaDB
DATABASE_TYPE=mariadb
MARIADB_HOST=127.0.0.1
MARIADB_PORT=3306
MARIADB_USER=taller
MARIADB_PASSWORD=tallerpass
MARIADB_DATABASE=tallerdb

# MySQL (mismas claves con prefijo MYSQL_)
DATABASE_TYPE=mysql

# PostgreSQL
DATABASE_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=taller
POSTGRES_PASSWORD=tallerpass
POSTGRES_DATABASE=tallerdb

# SQLite (desarrollo rápido, sin servidor)
DATABASE_TYPE=sqlite
SQLITE_PATH=./dev.db

# Override total (máxima prioridad)
DATABASE_URL=postgresql://taller:tallerpass@localhost:5432/tallerdb
```

También se aceptan las variables genéricas `DB_HOST`, `DB_PORT`, `DB_USER`,
`DB_PASSWORD`, `DB_NAME` y `DB_CHARSET`. Un `DATABASE_TYPE` desconocido detiene
el arranque con un error de validación; nunca se cae silenciosamente a SQLite.

### Fail-fast y despliegue

- Con **SQLite** la aplicación crea el archivo y arranca.
- Con MySQL/MariaDB/PostgreSQL se ejecuta `SELECT 1` con timeout
  (`DATABASE_CONNECT_TIMEOUT`, 5 s por defecto) antes de aceptar peticiones.
- Si la conexión falla, el proceso termina y Docker lo reinicia según su política.
- `GET /ready` devuelve `503` si la base deja de responder.
- Con `DEBUG=false` se valida el host de la petición con `ALLOWED_HOSTS`
  (`localhost,127.0.0.1,*.tallerdb.local` por defecto). Ajusta esa variable al
  dominio o IP reales del despliegue.
- `FORCE_HTTPS=true` activa la redirección a HTTPS, HSTS y cookies `Secure`;
  déjalo en `false` si TLS termina en un proxy delante de la aplicación.

## Modelos 3D

- Formato admitido: **GLB** (glTF binario versión 2), hasta `MAX_3D_SIZE_MB`
  (25 MB por defecto).
- Los archivos se guardan en `UPLOADS_DIR/modelos3d` (por defecto `./uploads`,
  fuera de `app/static`) y se sirven con `/modelos/{id}/3d` solo a usuarios
  autenticados.
- La validación comprueba extensión, `content-type`, cabecera `glTF`, versión,
  tamaño declarado y chunk JSON; la escritura es atómica.
- En el catálogo, el botón **Ver en 3D** abre el visor; los administradores
  disponen de **Añadir/Reemplazar 3D** y **Quitar 3D**.
- `model-viewer` se sirve localmente desde
  `app/static/vendor/model-viewer.min.js` (sin CDN).

## Scripts SQL (`database/`)

| Archivo | Propósito |
|---------|-----------|
| `schema_mariadb.sql` | Crea la base de datos y las tablas para MariaDB/MySQL. |
| `schema_postgresql.sql` | Crea las tablas para PostgreSQL. |
| `seed_modelos.sql` | Inserta 18 autos de ejemplo. |
| `pruebas_crud.sql` | Demuestra INSERT / SELECT / UPDATE / DELETE con `ROLLBACK`. |
| `init/*.sql` | Ejecutados automáticamente por MariaDB/MySQL en Docker. |
| `init_postgres/*.sql` | Ejecutados automáticamente por PostgreSQL en Docker. |

```bash
# Pruebas CRUD (incluye una violación de UNIQUE a propósito)
mariadb -u taller -p --force tallerdb < database/pruebas_crud.sql
```

## CLI de comprobaciones

`app/main.py` incluye dos comandos de diagnóstico. Funcionan desde cualquier
directorio y no arrancan el servidor (para eso usa `python run.py`).

```bash
# Verifica conexión, crea el esquema si falta, comprueba tablas y columnas 3D
# y hace un INSERT/UPDATE/SELECT con ROLLBACK (no deja datos).
python app/main.py testdb

# Ejecuta toda la suite pytest (descubre automáticamente pruebas nuevas).
python app/main.py test

# Argumentos extra para pytest (archivo, -k, -v, etc.)
python app/main.py test -q tests/test_config.py
python app/main.py test tests/test_modelos_3d.py -vv
```

`testdb` termina con código `0` si todo está correcto y `1` si falla, mostrando
una pista (`./startdb.sh`) cuando la base no responde.

## Tests

```bash
# Recomendado: ejecuta toda la suite con el intérprete actual
python app/main.py test

# Equivalente directo
.venv/bin/python -m pytest -p no:cacheprovider -q
```

Las pruebas cubren autenticación/registro, filtros del catálogo, configuración
de los cuatro motores, fail-fast y el ciclo de vida de los GLB.

## Evidencia / informe

El informe completo con portada, introducción, descripción de interfaces, pruebas
CRUD, código SQL, resultados, recomendaciones, conclusiones y referencias APA está en:

```
docs/INFORME_EVIDENCIA.md
```

## Desarrollo

```bash
# Base de datos local (dejar apagada al terminar)
./startdb.sh
./stopdb.sh

# Diagnóstico de la base de datos
python app/main.py testdb

# Migración manual (opcional; el arranque ya sincroniza columnas nullable)
alembic revision --autogenerate -m "descripcion"
alembic upgrade head

# Servidor con recarga automática
python run.py
```
