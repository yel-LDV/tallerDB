from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnuncioEstado(str, Enum):
    activo = "activo"
    vendido = "vendido"
    cancelado = "cancelado"


class Anuncio(Base):
    """Anuncio de auto en venta, publicado por un usuario vendedor.

    Cada anuncio tiene un slug único para la URL pública y pertenece a un
    vendedor (User). Las fotos, ofertas y mensajes se vinculan al anuncio.
    """

    __tablename__ = "anuncios"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_anuncio_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendedor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)

    # Datos del auto
    marca: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_oferta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False, default="sedan")
    transmision: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kilometraje: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Estado del anuncio
    estado: Mapped[AnuncioEstado] = mapped_column(
        SAEnum(AnuncioEstado), nullable=False, default=AnuncioEstado.activo, index=True
    )

    creado_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    actualizado_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relaciones
    vendedor = relationship("User", backref="anuncios_vendidos", foreign_keys=[vendedor_id])
    fotos = relationship("Foto", back_populates="anuncio", cascade="all, delete-orphan", order_by="Foto.orden")
    ofertas = relationship("Oferta", back_populates="anuncio", cascade="all, delete-orphan")
    mensajes = relationship("Mensaje", back_populates="anuncio")

    def __repr__(self) -> str:
        return f"<Anuncio(id={self.id}, {self.marca} {self.nombre} {self.anio})>"
