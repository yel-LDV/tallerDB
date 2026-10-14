from fastapi import APIRouter, Request, Form, Depends, status, HTTPException, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin
from app.auth.security import hash_password, verify_password
from app.auth.deps import require_auth, require_guest
from app.config import settings

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
@router.get("/register", response_class=HTMLResponse)
async def register_get(request: Request, _: None = Depends(require_guest)):
    return templates.TemplateResponse("register.html", base_context(request, error=None))


@router.post("/register", response_class=HTMLResponse)
async def register_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_guest),
):
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            base_context(request, error="Las contraseñas no coinciden"),
            status_code=400,
        )

    if len(password) < 8:
        return templates.TemplateResponse(
            "register.html",
            base_context(request, error="La contraseña debe tener al menos 8 caracteres"),
            status_code=400,
        )

    user = User(email=email.lower(), hashed_password=hash_password(password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return templates.TemplateResponse(
            "register.html",
            base_context(request, error="El email ya está registrado"),
            status_code=400,
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


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
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            base_context(request, error="Email o contraseña incorrectos"),
            status_code=401,
        )

    if not user.is_active:
        return templates.TemplateResponse(
            "login.html",
            base_context(request, error="Cuenta desactivada"),
            status_code=403,
        )

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

    # Verificar si existe
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # Crear usuario
    user = User(
        email=email,
        hashed_password=hash_password(data.password),
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