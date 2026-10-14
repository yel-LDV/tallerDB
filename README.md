# TallerDB - Sistema de Autenticación Mínimo

Proyecto base con FastAPI + Jinja2 + MySQL + Sessions + Dark Mode

## Características

- **Login / Registro** con validación servidor
- **Sesiones seguras** (HttpOnly, SameSite=Lax, 7 días)
- **Hash de contraseñas** con bcrypt
- **Dark/Light mode** (preferencia del sistema por defecto, persiste en localStorage)
- **Migraciones** con Alembic
- **Arquitectura modular** lista para escalar

## Stack

| Capa | Tecnología |
|------|------------|
| Web | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 (async) |
| DB | MySQL/MariaDB (asyncmy) |
| Templates | Jinja2 |
| Auth | Starlette Sessions + bcrypt |
| Validación | Pydantic 2 |
| Config | pydantic-settings |

## Estructura

```
tallerdbProyect/
├── app/
│   ├── config.py          # Settings (pydantic-settings)
│   ├── database.py        # SQLAlchemy async engine/session
│   ├── main.py            # FastAPI app + middleware
│   ├── models/
│   │   └── user.py        # User model
│   ├── schemas/
│   │   └── auth.py        # Pydantic schemas
│   ├── auth/
│   │   ├── security.py    # Hash/verify passwords
│   │   ├── deps.py        # Auth dependencies
│   │   └── router.py      # Routes: /login, /register, /logout, /dashboard
│   ├── templates/
│   │   ├── base.html      # Layout + theme toggle
│   │   ├── login.html
│   │   ├── register.html
│   │   └── dashboard.html
│   └── static/
│       └── style.css      # CSS con variables CSS para temas
├── alembic/               # Migraciones
├── tests/
├── .env                   # Variables de entorno (no commitear)
├── .env.example
├── requirements.txt
└── run.py                 # Entry point
```

## Instalación

```bash
# 1. Crear venv e instalar deps
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configurar .env
cp .env.example .env
# Editar .env con tus credenciales MySQL y SECRET_KEY

# 3. Crear BD en MySQL
mysql -u root -p -e "CREATE DATABASE tallerdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 4. Ejecutar migraciones
alembic upgrade head

# 5. Levantar servidor
python run.py
# o: uvicorn app.main:app --reload
```

## Uso

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/register` | GET/POST | Registro público |
| `/login` | GET/POST | Inicio de sesión |
| `/logout` | POST | Cerrar sesión |
| `/dashboard` | GET | Panel protegido (requiere auth) |
| `/docs` | GET | Swagger UI (API docs) |

## Dark Mode

- Por defecto usa `prefers-color-scheme` del sistema
- Click en el icono sol/luna en el dashboard para alternar
- Preferencia guardada en `localStorage`

## Desarrollo

```bash
# Nueva migración tras cambiar modelos
alembic revision --autogenerate -m "descripcion"

# Ver migraciones pendientes
alembic history

# Tests
pytest
```

## Variables de entorno (.env)

```env
DATABASE_URL=mysql+asyncmy://user:password@localhost:3306/tallerdb
SECRET_KEY=clave-secreta-muy-larga-y-aleatoria-para-produccion
SESSION_COOKIE_NAME=session
APP_NAME=TallerDB
DEBUG=true
```

## Producción

- `DEBUG=false`
- `SECRET_KEY` fuerte (32+ chars aleatorios)
- `https_only=true` en SessionMiddleware (requiere HTTPS)
- Proxy reverso (nginx) + TLS
- MySQL con usuario dedicado y permisos mínimos