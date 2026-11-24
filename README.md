# TallerDB — Plataforma de Compraventa de Autos

Plataforma web **FastAPI + Jinja2 + SQLAlchemy async** para la compraventa de
autos entre usuarios. Incluye catálogo público, chat en tiempo real, sistema de
ofertas y negociación, galería de fotos, reportes a administradores y visor de
modelos 3D. La base de datos es configurable entre **SQLite, MySQL, MariaDB y
PostgreSQL**; si el motor configurado no responde, la aplicación **no arranca**
(fail-fast).

## Características

### Sistema de Compraventa

- **Anuncios públicos**: cualquier usuario registrado puede publicar autos a la
  venta con slug único (ej: `/auto/toyota-camry-2023-abc123`).
- **Galería de fotos**: hasta 10 fotos por anuncio (JPG/PNG/WebP, máx 5MB cada
  una) con validación de cabecera (magic bytes) para evitar código malicioso.
- **Chat en tiempo real**: comunicación instantánea entre comprador y vendedor
  vía WebSocket, con historial persistente en la base de datos.
- **Ofertas y negociación**: el comprador envía mensajes antes de hacer una
  oferta. El vendedor puede aceptar, rechazar o contraofertar. El proceso
  continúa hasta que ambos aceptan o alguien cancela.
- **Tratos cerrados**: cuando se acepta una oferta, se crea automáticamente un
  trato con el monto final y el estado del anuncio cambia a "vendido".
- **Autos vendidos visibles**: los anuncios vendidos permanecen en el catálogo
  con badge "VENDIDO" para que cualquier usuario vea el resultado.
- **Reportes a administradores**: cualquier usuario puede reportar a otro por
  fraude, acoso, spam, contenido inapropiado o anuncios falsos. Solo los admins
  pueden ver y resolver los reportes.

### Autenticación y Seguridad

- **Registro público** de usuarios con validación en servidor, contraseñas bcrypt
  y sesión persistente.
- **Login / logout** con sesiones HttpOnly y SameSite=Lax.
- **Roles dinámicos**: cada usuario puede ser comprador y vendedor a la vez.
- **Administración**: usuario admin por defecto, gestión de usuarios y reportes.
- **Mi perfil**: consulta de datos y cambio de contraseña.
- **Interfaz por roles**: cada usuario ve solo las acciones permitidas.

### Catálogo y Modelos 3D

- **Catálogo público** con búsqueda, filtros por marca/tipo/año/disponibilidad,
  ordenamiento, estadísticas y paginación.
- **Modelos 3D en formato GLB**: visor interactivo con `model-viewer`.
- **CRUD completo** vía API REST (crear/editar/borrar requiere administrador).
- **Dark/Light mode** con persistencia en localStorage.

### Infraestructura

- **Bases de datos**: SQLite, MySQL, MariaDB y PostgreSQL. Arranque fail-fast.
- **MariaDB local** con `./startdb.sh` y `./stopdb.sh` (datos persistentes).
- **Servidor** con `./start.sh` y `./stop.sh` (venv automático).
- **Docker**: multi-stage, compose para 3 motores DB, health checks.
- **Tests**: pytest con httpx cubriendo auth, CRUD, filtros, 3D, permisos y config.

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
| Chat | WebSocket (FastAPI nativo) |
| 3D | Google `<model-viewer>` (servido localmente) |
| Tests | pytest + httpx |

## Estructura

```
tallerDB/
├── app/
│   ├── config.py / config_loader.py   # Settings + URL de BD por motor
│   ├── database.py                    # Engine async, fail-fast, init de esquema
│   ├── main.py                        # FastAPI app + middleware + /health, /ready + CLI
│   ├── models/                        # Entidades SQLAlchemy
│   │   ├── user.py                    # User
│   │   ├── modelo.py                  # Modelo (catálogo original + 3D)
│   │   ├── anuncio.py                 # Anuncio (auto a la venta)
│   │   ├── foto.py                    # Foto del anuncio
│   │   ├── mensaje.py                 # Mensaje entre usuarios
│   │   ├── oferta.py                  # Oferta de compra
│   │   ├── trato.py                   # Trato cerrado
│   │   └── reporte.py                 # Reporte de usuario
│   ├── schemas/                       # Esquemas Pydantic
│   │   ├── auth.py
│   │   └── modelo.py
│   ├── auth/                          # Autenticación y autorización
│   │   ├── security.py                # Hash/verify bcrypt
│   │   ├── deps.py                    # get_current_user, require_auth, require_admin
│   │   └── router.py                  # Login, register, dashboard, perfil, admin
│   ├── modelos/                       # Catálogo original de modelos
│   │   ├── router.py                  # HTML + API CRUD + 3D
│   │   └── storage.py                 # Validación y almacenamiento de GLB
│   ├── anuncios/                      # Sistema de compraventa — Anuncios
│   │   ├── router.py                  # Catálogo público, CRUD, detalle, filtros
│   │   ├── schemas.py                 # Pydantic schemas
│   │   └── slug_generator.py          # Slugs únicos para URLs
│   ├── fotos/                         # Galería de fotos
│   │   ├── router.py                  # Subir, eliminar, servir fotos
│   │   └── storage.py                 # Validación magic bytes, almacenamiento
│   ├── ventas/                        # Ofertas y tratos
│   │   ├── router.py                  # API de ofertas, negociación, tratos
│   │   └── schemas.py                 # Pydantic schemas
│   ├── chat/                          # Chat en tiempo real
│   │   ├── router.py                  # WebSocket + API REST de mensajes
│   │   └── websocket.py               # ConnectionManager
│   ├── reportes/                      # Reportes a administradores
│   │   └── router.py                  # Crear, listar, resolver reportes
│   ├── static/
│   │   ├── style.css                  # CSS con iconos Lucide
│   │   └── vendor/model-viewer.min.js
│   └── templates/                     # Jinja2 templates
│       ├── base.html / landing.html / login.html / register.html
│       ├── dashboard.html             # Panel con estadísticas
│       ├── profile.html               # Mi perfil
│       ├── modelos.html               # Catálogo original
│       ├── catalogo.html              # Catálogo de autos en venta
│       ├── anuncio_detalle.html       # Detalle del auto con galería
│       ├── chat.html                  # Chat en tiempo real
│       ├── ofertas.html               # Panel de ofertas
│       └── reportes_admin.html        # Panel admin de reportes
├── database/                          # Scripts SQL
│   ├── init/                          # Init automático MariaDB/MySQL
│   └── init_postgres/                 # Init automático PostgreSQL
├── scripts/
│   └── create_admin.py               # Crea usuario admin idempotente
├── tests/                             # Pruebas pytest
├── alembic/                           # Migraciones opcionales
├── docker-compose.yml                 # App + MariaDB
├── docker-compose.mysql.yml           # App + MySQL
├── docker-compose.postgres.yml        # App + PostgreSQL
├── start.sh                           # Inicia servidor (venv + app)
├── stop.sh                            # Detiene servidor
├── startdb.sh                         # Inicia MariaDB local (.mariadb/)
├── stopdb.sh                          # Apaga MariaDB local sin borrar datos
├── requirements.txt
└── run.py                             # Entry point del servidor
```

## Instalación

### Opción A — Docker con MariaDB (por defecto)

```bash
cp .env.example .env
docker compose up --build
```

Abrir: <http://localhost:8000>

### Opción B — Docker con MySQL o PostgreSQL

```bash
# MySQL
docker compose -f docker-compose.mysql.yml up --build

# PostgreSQL
docker compose -f docker-compose.postgres.yml up --build
```

### Opción C — Local con MariaDB (recomendada)

```bash
# 1. Iniciar MariaDB local (crea base, esquema y usuario)
./startdb.sh

# 2. Iniciar servidor (crea venv, instala deps, crea admin, levanta app)
./start.sh

# 3. Detener todo
./stop.sh
./stopdb.sh
```

### Opción D — Local con SQLite (sin servidor)

```bash
# En .env:
DATABASE_TYPE=sqlite
SQLITE_PATH=./dev.db

# Iniciar
./start.sh
```

## Scripts de gestión

| Script | Descripción |
|--------|-------------|
| `./start.sh` | Crea/actualiza venv, instala deps, crea admin, inicia servidor en background |
| `./stop.sh` | Detiene el servidor y limpia procesos huérfanos |
| `./startdb.sh` | Inicia MariaDB local en `.mariadb/` con esquema y datos |
| `./stopdb.sh` | Apaga MariaDB sin borrar datos |

### `./start.sh` — Iniciar el servidor

- Crea el entorno virtual `.venv` si no existe.
- Instala las dependencias de `requirements.txt`.
- Ejecuta `scripts/create_admin.py` para crear el usuario admin.
- Inicia el servidor en background y guarda el PID en `.server.pid`.
- Espera a que responda antes de salir.
- Muestra la URL, logs y comando para detener.

### `./stop.sh` — Detener el servidor

- Lee el PID de `.server.pid` y detiene el proceso.
- Limpia cualquier proceso restante en el puerto 8000.
- Elimina procesos uvicorn/watchfiles huérfanos.

### `./startdb.sh` — Iniciar MariaDB local

- Inicializa el datadir en `.mariadb/data` si es la primera vez.
- Arranca MariaDB en `127.0.0.1:3306` con root local por socket.
- Crea la base de datos y el usuario de `.env` de forma idempotente.
- Carga el esquema si falta (`database/init/01_schema.sql`).
- Opcionalmente carga datos de ejemplo (`--no-seed` para omitir).

### `./stopdb.sh` — Apagar MariaDB local

- Apaga por socket de forma ordenada.
- Si no responde, fuerza por PID.
- **No borra datos**: el directorio `.mariadb/` se conserva.

| Recurso | Ruta por defecto |
|---------|------------------|
| Datos | `.mariadb/data` |
| Socket | `.mariadb/run/mariadb.sock` |
| PID | `.mariadb/run/mariadb.pid` |
| Log | `.mariadb/log/mariadb.err` |

Al arrancar, la aplicación comprueba la conexión, crea las tablas que falten y
sincroniza columnas nuevas de forma automática.

## Uso

### Páginas principales

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET | Landing pública |
| `/register` | GET/POST | Registro público de usuarios |
| `/login` | GET/POST | Inicio de sesión (redirige a `/auto/`) |
| `/logout` | POST | Cerrar sesión |
| `/dashboard` | GET | Panel con estadísticas (requiere auth) |
| `/profile` | GET | Mi perfil: datos y cambio de contraseña |
| `/profile/password` | POST | Cambiar contraseña (requiere auth) |
| `/health` | GET | Liveness del proceso |
| `/ready` | GET | Readiness: comprueba la base de datos |
| `/docs` | GET | Swagger UI (solo `DEBUG=true`) |

### Catálogo de autos en venta

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/auto/` | GET | Catálogo público con filtros y paginación |
| `/auto/api` | GET | Listar anuncios (JSON) |
| `/auto/api` | POST | Publicar auto a la venta (requiere auth) |
| `/auto/api/{id}` | PUT | Editar anuncio (solo el vendedor) |
| `/auto/api/{id}` | DELETE | Eliminar anuncio (solo el vendedor) |
| `/auto/{slug}` | GET | Detalle del auto con galería y especificaciones |

### Chat en tiempo real

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/chat/` | GET | Página de chat con lista de conversaciones |
| `/chat/ws` | WebSocket | Chat en tiempo real (param: `user_id`) |
| `/chat/api/mensaje` | POST | Enviar mensaje REST (query: `remitente_id`, `destinatario_id`, `contenido`) |
| `/chat/api/historial/{otro_usuario_id}` | GET | Historial de mensajes (requiere auth) |

### Ofertas y negociación

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/ofertas/` | GET | Panel de ofertas (requiere auth) |
| `/ofertas/api` | POST | Crear oferta (requiere mensaje previo al vendedor) |
| `/ofertas/api/{id}/responder` | POST | Aceptar, rechazar o contraofertar |
| `/ofertas/api/{id}/cancelar` | POST | Cancelar oferta |
| `/ofertas/api/anuncio/{id}` | GET | Listar ofertas de un anuncio |
| `/ofertas/tratos/api` | GET | Listar tratos cerrados (requiere auth) |

### Fotos de anuncios

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/fotos/anuncio/{id}` | POST | Subir foto (solo el vendedor, máx 10, 5MB) |
| `/fotos/anuncio/{id}/{foto_id}` | DELETE | Eliminar foto (solo el vendedor) |
| `/fotos/{foto_id}` | GET | Servir foto (pública) |

### Reportes

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/reportes/api` | POST | Reportar usuario (requiere auth) |
| `/reportes/api` | GET | Listar reportes (solo admin) |
| `/reportes/api/{id}/resolver` | POST | Resolver reporte (solo admin) |
| `/reportes/` | GET | Panel admin de reportes (solo admin) |

### Modelos originales (catálogo 3D)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/modelos` | GET | Catálogo con búsqueda, filtros y paginación |
| `/modelos/api` | GET/POST | Listar / crear modelos (POST requiere admin) |
| `/modelos/api/{id}` | GET/PUT/DELETE | Consultar / actualizar / borrar |
| `/modelos/api/{id}/3d` | POST/DELETE | Subir / quitar GLB (requiere admin) |
| `/modelos/{id}/3d` | GET | Descargar GLB (requiere sesión) |

### Administración de usuarios

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/admin/users` | GET | Listar usuarios (JSON, requiere admin) |
| `/admin/users/create` | POST | Crear usuario/admin (requiere admin) |
| `/admin/users/{id}/toggle-admin` | POST | Otorgar/quitar admin |
| `/admin/users/{id}/toggle-active` | POST | Activar/desactivar cuenta |

> La interfaz muestra únicamente las acciones permitidas para cada rol. La
> autorización real siempre se valida en el backend (`403` ante intentos no
> autorizados).

## Usuario administrador

El proyecto incluye un administrador por defecto, definido en `.env`:

| Campo | Valor por defecto |
|-------|-------------------|
| Email | `admin@tallerdb.local` |
| Contraseña | `admin123` |

Se crea automáticamente con `./start.sh` o manualmente:

```bash
python scripts/create_admin.py
```

> **Importante:** cambia `ADMIN_EMAIL` y `ADMIN_PASSWORD` en `.env` **antes**
> del primer arranque en producción. La contraseña debe tener entre 8 y 72
> bytes (límite de bcrypt).

### Crear más administradores

Desde `/dashboard` → **Gestión de Usuarios** → **Crear Admin**.

Por API:

```bash
curl -X POST http://localhost:8000/admin/users/create \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"email":"otro@tallerdb.local","password":"clave-segura","is_admin":true}'
```

> Un administrador no puede quitarse sus propios permisos ni desactivar su
> propia cuenta.

## Mi perfil

En `/profile` cada usuario puede consultar sus datos y cambiar su contraseña.

```bash
curl -X POST http://localhost:8000/profile/password \
  -H "Cookie: session=..." \
  -d "current_password=actual" \
  -d "new_password=nueva-clave" \
  -d "confirm_password=nueva-clave"
```

## Modelos 3D

- Formato: **GLB** (glTF binario v2), hasta 25 MB.
- Guardados en `./uploads/modelos3d`, servidos con `/modelos/{id}/3d`.
- Validación: extensión, content-type, cabecera glTF, versión, chunk JSON.
- `model-viewer` servido localmente (sin CDN).

## Galería de fotos

- Formatos: **JPG, PNG, WebP**. Máx **5MB** por foto, **10 fotos** por anuncio.
- Validación de **magic bytes** para evitar código malicioso.
- Solo el vendedor puede subir/eliminar fotos de sus anuncios.
- Las fotos se sirven públicamente con caché de 24 horas.

## Flujo de compraventa

1. **Publicar**: El vendedor crea un anuncio con datos del auto y fotos.
2. **Contactar**: El comprador envía un mensaje al vendedor desde la página del auto.
3. **Ofertar**: El comprador hace una oferta (requiere mensaje previo).
4. **Negociar**: El vendedor acepta, rechaza o contraoferta. El proceso continúa.
5. **Cerrar trato**: Al aceptar, se crea un trato y el anuncio pasa a "vendido".
6. **Reportar**: Cualquier usuario puede reportar a otro. Solo el admin resuelve.

## Base de datos

La precedencia es: **`.env` > `config.json` > valores por defecto**.

```env
# MariaDB (por defecto)
DATABASE_TYPE=mariadb
MARIADB_HOST=127.0.0.1
MARIADB_PORT=3306
MARIADB_USER=taller
MARIADB_PASSWORD=tallerpass
MARIADB_DATABASE=tallerdb

# SQLite (sin servidor)
DATABASE_TYPE=sqlite
SQLITE_PATH=./dev.db
```

### Tablas de la base de datos

| Tabla | Descripción |
|-------|-------------|
| `users` | Usuarios (email, password hash, rol, estado) |
| `modelos` | Catálogo original de autos con soporte 3D |
| `anuncios` | Autos a la venta (slug, vendedor, estado) |
| `fotos` | Galería de fotos por anuncio |
| `mensajes` | Chat entre usuarios |
| `ofertas` | Ofertas de compra con cadena de negociación |
| `tratos` | Tratos cerrados con monto final |
| `reportes` | Reportes de usuarios (solo visibles por admin) |

### Fail-fast

- Con **SQLite** la app crea el archivo y arranca.
- Con **MySQL/MariaDB/PostgreSQL** se valida la conexión con timeout (5s).
- Si falla, el proceso termina. `/ready` devuelve `503` si la DB deja de responder.

## CLI de comprobaciones

`app/main.py` incluye dos comandos de diagnóstico. Funcionan desde cualquier
directorio y no arrancan el servidor (para eso usa `python run.py`).

```bash
# Verifica conexión y esquema
python app/main.py testdb

# Ejecuta toda la suite pytest
python app/main.py test
```

## Tests

```bash
python app/main.py test
# o
.venv/bin/python -m pytest -p no:cacheprovider -q
```

Las pruebas cubren auth, CRUD, filtros, 3D, permisos, perfil, config y fail-fast.

## Desarrollo

```bash
# Arrancar todo
./startdb.sh
./start.sh

# Detener todo
./stop.sh
./stopdb.sh

# Servidor con recarga automática
python run.py

# Migración manual (opcional)
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

## Credenciales de prueba

| Rol | Email | Contraseña |
|-----|-------|------------|
| Admin | `admin@tallerdb.local` | `admin123` |

> Cambia las credenciales en `.env` antes de usar en producción.
