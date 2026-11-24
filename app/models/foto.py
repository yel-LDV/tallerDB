from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Foto(Base):
    """Foto de un anuncio, almacenada localmente con validación de cabecera.

    Hasta 10 fotos por anuncio, máx 5MB cada una, formatos JPG/PNG/WebP.
    """

    __tablename__ = "fotos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    anuncio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("anuncios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    archivo_key: Mapped[str] = mapped_column(String(255), nullable=False)
    tamano: Mapped[int] = mapped_column(Integer, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    formato: Mapped[str] = mapped_column(String(10), nullable=False)
    subido_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relaciones
    anuncio = relationship("Anuncio", back_populates="fotos")

    def __repr__(self) -> str:
        return f"<Foto(id={self.id}, anuncio={self.anuncio_id}, orden={self.orden})>"
