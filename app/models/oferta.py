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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OfertaEstado(str, Enum):
    pendiente = "pendiente"
    aceptada = "aceptada"
    rechazada = "rechazada"
    contraoferta = "contraoferta"
    cancelada = "cancelada"


class Oferta(Base):
    """Oferta de compra sobre un anuncio, con soporte para contraofertas.

    Un comprador hace una oferta al vendedor. El vendedor puede aceptar,
    rechazar o hacer una contraoferta. El proceso continúa hasta que
    ambos aceptan o alguien cancela.
    """

    __tablename__ = "ofertas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    anuncio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("anuncios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    comprador_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    oferta_anterior_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ofertas.id", ondelete="SET NULL"), nullable=True
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estado: Mapped[OfertaEstado] = mapped_column(
        SAEnum(OfertaEstado), nullable=False, default=OfertaEstado.pendiente, index=True
    )
    mensaje: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creado_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    actualizado_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relaciones
    anuncio = relationship("Anuncio", back_populates="ofertas")
    comprador = relationship(
        "User", foreign_keys=[comprador_id], backref="ofertas_compra"
    )
    oferta_anterior = relationship(
        "Oferta", remote_side=[id], backref="siguiente_oferta", foreign_keys=[oferta_anterior_id]
    )
    trato = relationship("Trato", back_populates="oferta", uselist=False)

    def __repr__(self) -> str:
        return f"<Oferta(id={self.id}, anuncio={self.anuncio_id}, monto={self.monto})>"
