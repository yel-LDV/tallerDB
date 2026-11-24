from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Mensaje(Base):
    """Mensaje entre dos usuarios, opcionalmente vinculado a un anuncio.

    Se usa para el chat en tiempo real entre comprador y vendedor.
    """

    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    remitente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    destinatario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    anuncio_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anuncios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    leido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relaciones
    remitente = relationship(
        "User", foreign_keys=[remitente_id], backref="mensajes_enviados"
    )
    destinatario = relationship(
        "User", foreign_keys=[destinatario_id], backref="mensajes_recibidos"
    )
    anuncio = relationship("Anuncio", back_populates="mensajes")

    def __repr__(self) -> str:
        return f"<Mensaje(id={self.id}, de={self.remitente_id}, a={self.destinatario_id})>"
