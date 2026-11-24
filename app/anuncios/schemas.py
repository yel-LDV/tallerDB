"""Esquemas Pydantic para anuncios."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


TIPOS_CARROCERIA = [
    "sedan", "suv", "hatchback", "coupe", "convertible",
    "pickup", "wagon", "van", "deportivo", "otro",
]
TRANSMISIONES = ["manual", "automatica", "cvt", "automatica_estructada"]


class AnuncioCreate(BaseModel):
    marca: str = Field(..., min_length=1, max_length=100)
    nombre: str = Field(..., min_length=1, max_length=120)
    anio: int = Field(..., ge=1900, le=2100)
    precio_oferta: Decimal = Field(..., gt=0)
    color: Optional[str] = Field(None, max_length=50)
    tipo: str = Field(default="sedan")
    transmision: str = Field(default="manual")
    descripcion: Optional[str] = None
    kilometraje: Optional[int] = Field(None, ge=0)


class AnuncioUpdate(BaseModel):
    marca: Optional[str] = Field(None, min_length=1, max_length=100)
    nombre: Optional[str] = Field(None, min_length=1, max_length=120)
    anio: Optional[int] = Field(None, ge=1900, le=2100)
    precio_oferta: Optional[Decimal] = Field(None, gt=0)
    color: Optional[str] = Field(None, max_length=50)
    tipo: Optional[str] = None
    transmision: Optional[str] = None
    descripcion: Optional[str] = None
    kilometraje: Optional[int] = Field(None, ge=0)
    estado: Optional[str] = None


class AnuncioOut(BaseModel):
    id: int
    vendedor_id: int
    slug: str
    marca: str
    nombre: str
    anio: int
    precio_oferta: Decimal
    color: Optional[str] = None
    tipo: str
    transmision: str
    descripcion: Optional[str] = None
    kilometraje: Optional[int] = None
    estado: str

    class Config:
        from_attributes = True


class FotoOut(BaseModel):
    id: int
    anuncio_id: int
    orden: int
    formato: str
    tamano: int
    url: str

    class Config:
        from_attributes = True
