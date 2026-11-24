"""Esquemas Pydantic para ofertas y tratos."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class OfertaCreate(BaseModel):
    anuncio_id: int = Field(..., gt=0)
    monto: Decimal = Field(..., gt=0)
    mensaje: Optional[str] = None


class OfertaResponder(BaseModel):
    accion: str = Field(..., pattern="^(aceptar|rechazar|contraoferta)$")
    monto: Optional[Decimal] = Field(None, gt=0)
    mensaje: Optional[str] = None


class OfertaOut(BaseModel):
    id: int
    anuncio_id: int
    comprador_id: int
    monto: Decimal
    estado: str
    mensaje: Optional[str] = None
    creado_at: str

    class Config:
        from_attributes = True


class TratoOut(BaseModel):
    id: int
    oferta_id: int
    comprador_id: int
    vendedor_id: int
    monto_final: Decimal
    estado: str

    class Config:
        from_attributes = True
