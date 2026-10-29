import logging

from fastapi import APIRouter, Request, Form, Depends, status, HTTPException, Body
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel, EmailStr, ValidationError

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin
from app.auth.security import hash_password, verify_password
from app.auth.deps import require_auth, require_guest
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def base_context(request: Request, **extra):
    return {"request": request, "app_name": settings.app_name, **extra}


def require_admin_user(current_user: User = Depends(require_auth)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )
    return current_user


# ===== Schemas para admin API =====
class ToggleAdminRequest(BaseModel):
    is_admin: bool

class ToggleActiveRequest(BaseModel):
    is_active: bool

class CreateAdminRequest(BaseModel):
    email: EmailStr
    password: str
    is_admin: bool = True


# ===== Public Auth Routes =====
def _render_register(
    request: Request,
    *,
    email: str = "",
    error: str | None = None,
    field_errors: dict[str, str] | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        "register.html",
        base_context(
            request,
            error=error,
            field_errors=field_errors or {},
            email=email,
        ),
        status_code=status_code,
    )


def _errores_validacion_register(exc: ValidationError) -> dict[str, str]:
    """Traduce errores de Pydantic a mensajes de formulario en español."""
    errores: dict[str, str] = {}
    for item in exc.errors():
        campo = str(item["loc"][0]) if item.get("loc") else "general"
        mensaje = item.get("msg", "")
        if campo == "email":
            errores[campo] = "Ingresa un correo electrónico válido."
        elif campo == "password":
            if "72 bytes" in mensaje:
                errores[campo] = "La contraseña no puede superar los 72 bytes."
            else:
                errores[campo] = (
                    "La contraseña debe tener al menos 8 caracteres."
                )
        else:
            errores[campo] = mensaje
    return errores


@router.get("/register", response_class=HTMLResponse)
async def register_get(request: Request, _: None = Depends(require_guest)):
    return _render_register(request)


@router.post("/register", response_class=HTMLResponse)
async def register_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_guest),
):
    email_raw = email.strip()
    errores: dict[str, str] = {}

    if password != confirm_password:
        errores["confirm_password"] = "Las contraseñas no coinciden."

    try:
        data = UserCreate(email=email_raw, password=password)
    except ValidationError as exc:
        errores.update(_errores_validacion_register(exc))
        data = None

    if not errores:
        # Comprobación amable antes de intentar insertar. El índice único
        # sigue siendo la garantía ante carreras entre peticiones.
        result = await db.execute(
            select(User).where(func.lower(User.email) == str(data.email))
        )
        if result.scalar_one_or_none():
            errores["email"] = (
                "Este correo ya está registrado. ¿Quieres iniciar sesión?"
            )

    if errores:
        return _render_register(
            request,
            email=email_raw,
            field_errors=errores,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        hashed = await run_in_threadpool(hash_password, password)
        user = User(
            email=str(data.email),
            hashed_password=hashed,
            is_active=True,
            is_admin=False,
        )
        db.add(user)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return _render_register(
            request,
            email=email_raw,
            field_errors={
                "email": "Este correo ya está registrado. ¿Quieres iniciar sesión?"
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("Error al registrar usuario")
        return _render_register(
            request,
            email=email_raw,
            error="No pudimos crear tu cuenta. Inténtalo de nuevo.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse(
        url="/dashboard?bienvenido=1", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, _: None = Depends(require_guest)):
    return templates.TemplateResponse("login.html", base_context(request, error=None))


@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_guest),
):
    email_normalizado = email.strip().lower()
    result = await db.execute(
        select(User).where(func.lower(User.email) == email_normalizado)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            base_context(
                request,
                error="Email o contraseña incorrectos",
                email=email.strip(),
            ),
            status_code=401,
        )

    if not user.is_active:
        return templates.TemplateResponse(
            "login.html",
            base_context(request, error="Cuenta desactivada", email=email.strip()),
            status_code=403,
        )

    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


# ===== Dashboard =====
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    # Obtener todos los usuarios si es admin
    all_users = None
    if current_user.is_admin:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        all_users = result.scalars().all()

    return templates.TemplateResponse(
        "dashboard.html",
        base_context(request, user=current_user, all_users=all_users),
    )


# ===== Admin API Routes =====
@router.post("/admin/users/create", response_class=JSONResponse)
async def admin_create_user(
    request: Request,
    data: CreateAdminRequest,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear nuevo usuario (admin)."""
    email = data.email.lower().strip()
    
    # Validar contraseña
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
    if len(data.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="La contraseña no puede superar los 72 bytes")

    # Verificar si existe (comparación insensible a mayúsculas)
    result = await db.execute(
        select(User).where(func.lower(User.email) == email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # Crear usuario sin bloquear el event loop con bcrypt
    hashed = await run_in_threadpool(hash_password, data.password)
    user = User(
        email=email,
        hashed_password=hashed,
        is_active=True,
        is_admin=data.is_admin,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Error al crear usuario")

    return {"success": True, "user": {"id": user.id, "email": user.email, "is_admin": user.is_admin}}


@router.post("/admin/users/{user_id}/toggle-admin", response_class=JSONResponse)
async def admin_toggle_admin(
    request: Request,
    user_id: int,
    data: ToggleAdminRequest,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Cambiar estado de administrador."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes modificar tus propios permisos")

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    target_user.is_admin = data.is_admin
    await db.commit()

    return {"success": True, "is_admin": target_user.is_admin}


@router.post("/admin/users/{user_id}/toggle-active", response_class=JSONResponse)
async def admin_toggle_active(
    request: Request,
    user_id: int,
    data: ToggleActiveRequest,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Activar/desactivar usuario."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta")

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    target_user.is_active = data.is_active
    await db.commit()

    return {"success": True, "is_active": target_user.is_active}


@router.get("/admin/users", response_class=JSONResponse)
async def admin_list_users(
    request: Request,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar todos los usuarios (JSON)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]