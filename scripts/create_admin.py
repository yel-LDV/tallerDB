#!/usr/bin/env python3
"""Script para crear usuario administrador por defecto."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.config import settings
from app.models.user import User
from app.auth.security import hash_password


async def create_admin_user() -> None:
    """Crea usuario admin si no existe."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    admin_email = getattr(settings, 'admin_email', 'admin@tallerdb.local')
    admin_password = getattr(settings, 'admin_password', 'admin123')

    async with async_session() as db:
        # Verificar si ya existe
        result = await db.execute(select(User).where(User.email == admin_email))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Usuario admin ya existe: {admin_email}")
            return

        # Crear admin
        admin = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            is_active=True,
            is_admin=True,
        )
        db.add(admin)
        await db.commit()
        print(f"Usuario admin creado:")
        print(f"  Email:    {admin_email}")
        print(f"  Password: {admin_password}")
        if admin_password == "admin123":
            print(f"  ADVERTENCIA: Usando contraseña por defecto. Cambiala en produccion!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin_user())