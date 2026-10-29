#!/usr/bin/env python3
"""Script para crear el usuario administrador inicial."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from app.auth.security import hash_password
from app.config import settings
from app.database import async_session_maker, init_db
from app.models.user import User


async def create_admin_user() -> None:
    """Crea el usuario admin si no existe, garantizando antes el esquema."""
    await init_db()

    admin_email = settings.admin_email.strip().lower()
    admin_password = settings.admin_password

    if len(admin_password) < 8:
        raise RuntimeError("ADMIN_PASSWORD debe tener al menos 8 caracteres.")
    if len(admin_password.encode("utf-8")) > 72:
        raise RuntimeError("ADMIN_PASSWORD no puede superar los 72 bytes (bcrypt).")

    async with async_session_maker() as db:
        result = await db.execute(
            select(User).where(func.lower(User.email) == admin_email)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Usuario admin ya existe: {existing.email}")
            return

        admin = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            is_active=True,
            is_admin=True,
        )
        db.add(admin)
        await db.commit()
        print(f"Usuario admin creado: {admin_email}")
        if admin_password == "admin123":
            print(
                "ADVERTENCIA: se está usando la contraseña por defecto. "
                "Configura ADMIN_PASSWORD antes de desplegar en producción."
            )


if __name__ == "__main__":
    asyncio.run(create_admin_user())
