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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TratoEstado(str, Enum):
    activo = "activo"
    cerrado = "cerrado"
    cancelado = "cancelado"


class Trato(Base):
    """Trato cerrado entre comprador y vendedor tras aceptar una oferta.

    Representa el acuerdo final de compra. Ambos pueden cerrarlo
    mutuamente o un administrador puede cancelarlo.
    """

    __tablename__ = "tratos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    oferta_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ofertas.id"), nullable=False, unique=True
    )
    comprador_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    vendedor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    monto_final: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estado: Mapped[TratoEstado] = mapped_column(
        SAEnum(TratoEstado), nullable=False, default=TratoEstado.activo, index=True
    )
    creado_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    cerrado_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Relaciones
    oferta = relationship("Oferta", back_populates="trato")
    comprador = relationship(
        "User", foreign_keys=[comprador_id], backref="tratos_compra"
    )
    vendedor = relationship(
        "User", foreign_keys=[vendedor_id], backref="tratos_venta"
    )

    def __repr__(self) -> str:
        return f"<Trato(id={self.id}, monto={self.monto_final}, estado={self.estado.value})>"
