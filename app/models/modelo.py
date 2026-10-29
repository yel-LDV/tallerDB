from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Modelo(Base):
    """Catálogo de modelos de autos.

    Esta es la categoría principal de la aplicación: cada registro representa
    un modelo de automóvil que se muestra en el catálogo.
    """

    __tablename__ = "modelos"
    __table_args__ = (
        UniqueConstraint("marca", "nombre", "anio", name="uq_modelo_marca_nombre_anio"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    marca: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False, default="sedan")
    transmision: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    disponible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    imagen_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Modelo 3D (GLB). ``modelo_3d_key`` es el nombre interno en disco y
    # ``modelo_3d_url`` la URL pública que consume el visor.
    modelo_3d_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    modelo_3d_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    modelo_3d_formato: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    modelo_3d_tamano: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    modelo_3d_subido_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Modelo(id={self.id}, {self.marca} {self.nombre} {self.anio})>"
