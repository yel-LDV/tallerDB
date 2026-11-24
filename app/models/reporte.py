from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReporteEstado(str, Enum):
    pendiente = "pendiente"
    en_revision = "en_revision"
    resuelto = "resuelto"
    descartado = "descartado"


class ReporteMotivo(str, Enum):
    contenido_inapropiado = "contenido_inapropiado"
    fraude = "fraude"
    acoso = "acoso"
    anuncio_falso = "anuncio_falso"
    spam = "spam"
    otro = "otro"


class Reporte(Base):
    """Reporte de un usuario o anuncio, visible solo por administradores.

    Un usuario puede reportar a otro por comportamiento inapropiado, fraude,
    acoso, etc. El administrador revisa y toma la decisión final.
    """

    __tablename__ = "reportes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reportante_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    usuario_reportado_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    anuncio_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anuncios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    motivo: Mapped[ReporteMotivo] = mapped_column(
        SAEnum(ReporteMotivo), nullable=False
    )
    detalles: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[ReporteEstado] = mapped_column(
        SAEnum(ReporteEstado), nullable=False, default=ReporteEstado.pendiente, index=True
    )
    notas_admin: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resuelto_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    creado_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relaciones
    reportante = relationship(
        "User", foreign_keys=[reportante_id], backref="reportes_realizados"
    )
    usuario_reportado = relationship(
        "User", foreign_keys=[usuario_reportado_id], backref="reportes_recibidos"
    )
    anuncio = relationship(
        "Anuncio", backref="reportes_asociados"
    )

    def __repr__(self) -> str:
        return f"<Reporte(id={self.id}, motivo={self.motivo.value})>"
