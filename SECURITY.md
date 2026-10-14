# Security Review - TallerDB

## ✅ Implementado

### Autenticación y Sesiones
- **Bcrypt** con 12 rounds (configurable via `security.bcrypt_rounds`)
- **Sesiones seguras**: HttpOnly, SameSite=Lax, Secure en producción
- **Expiración**: 7 días (configurable)
- **Secret key**: Obligatoria, mínima 32 chars en producción

### Headers de Seguridad
| Header | Valor | Propósito |
|--------|-------|-----------|
| `X-Content-Type-Options` | `nosniff` | Previene MIME sniffing |
| `X-Frame-Options` | `DENY` | Previene clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Protección XSS legacy |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control de referrer |
| `Strict-Transport-Security` | `max-age=31536000` | HSTS (solo producción) |

### Validación de Entrada
- **Pydantic v2** en todos los endpoints
- Email validado con `email-validator`
- Contraseña: 8-72 chars, confirmación requerida
- SQLAlchemy ORM previene inyección SQL

### Control de Acceso
- **Middleware `require_auth`** protege rutas
- **Middleware `require_guest`** previene acceso a login/register si autenticado
- Campo `is_admin` en modelo User para futuros permisos

### Base de Datos
- Pool configurable: `NullPool` en producción, pool normal en dev
- `pool_pre_ping=True` para conexiones resilientes
- Migraciones versionadas con Alembic

### Configuración
- **config.json** para parámetros no secretos
- **.env** para secretos (gitignored)
- Prioridad: `.env` > `config.json` > defaults
- Admin user creado automáticamente al iniciar

### Docker
- Multi-stage build (builder + runtime)
- Usuario no-root (`appuser`)
- Health check incluido
- `.dockerignore` completo

## ⚠️ Pendiente / Recomendado para Producción

### Rate Limiting
```python
# Agregar a main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/login")
@limiter.limit("10/hour")
async def login_post(...)
```

### CSRF Protection
```python
# Para formularios HTML, agregar token CSRF
from starlette.middleware.csrf import CSRFMiddleware
app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key)
```

### Audit Logging
- Log de logins fallidos/exitosos
- Log de cambios de contraseña
- Log de acciones admin

### Password Policy
- Verificar contra base de datos de contraseñas comprometidas (haveibeenpwned)
- Expiración de contraseña
- Historial de contraseñas

### 2FA / MFA
- TOTP para usuarios admin
- Códigos de recuperación

### Session Security
- Rotación de session ID en login
- Invalidar sesiones en cambio de contraseña
- Lista de sesiones activas por usuario

### Monitoring
- Métricas Prometheus (`/metrics`)
- Alertas en logins fallidos repetidos
- Health check extendido (DB connectivity)

## 🔧 Configuración de Producción

### .env (ejemplo)
```env
DATABASE_URL=mysql+asyncmy://user:strongpass@db:3306/tallerdb
SECRET_KEY=clave-muy-larga-aleatoria-64-chars-minimo
DEBUG=false
SESSION_COOKIE_NAME=__Host-session
ADMIN_EMAIL=admin@empresa.com
ADMIN_PASSWORD=clave-segura-generada
```

### Nginx (reverse proxy)
```nginx
server {
    listen 443 ssl http2;
    server_name app.empresa.com;

    ssl_certificate /etc/letsencrypt/live/app.empresa.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.empresa.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Docker Compose Production
```bash
docker compose -f docker-compose.yml up -d
```

## 📋 Checklist Pre-Deploy

- [ ] `SECRET_KEY` generada con `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] `DEBUG=false`
- [ ] `SESSION_COOKIE_NAME=__Host-session` (requiere HTTPS)
- [ ] MySQL con usuario dedicado, permisos mínimos
- [ ] Contraseña admin cambiada
- [ ] HTTPS configurado (Let's Encrypt o certificado válido)
- [ ] Backups automáticos de BD
- [ ] Logs centralizados (ELK, Loki, etc.)
- [ ] Rate limiting habilitado
- [ ] CSRF protection habilitado
- [ ] Security headers verificados con `securityheaders.com`
- [ ] Dependency scan: `pip-audit` o `safety check`

## 🐛 Known Issues

1. **bcrypt warning en Python 3.14**: `AttributeError: module 'bcrypt' has no attribute '__about__'`
   - No afecta funcionalidad, solo warning visual
   - Fix: esperar passlib 1.7.5+ o usar `argon2` como alternativa

2. **SQLite en desarrollo**: No apto para producción concurrente
   - Usar MySQL/PostgreSQL en producción

## 📚 Referencias

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Starlette Sessions](https://www.starlette.io/middleware/#sessionmiddleware)