from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: User = Depends(require_auth),
):
    return templates.TemplateResponse(
        "dashboard.html",
        base_context(request, user=current_user),
    )