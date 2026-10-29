"""Esquemas Pydantic para la categoría Modelos (autos)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Tipos de carrocería soportados (categorías del catálogo)
TIPOS_CARROCERIA = [
    "sedan",
    "hatchback",
    "suv",
    "pickup",
    "deportivo",
    "coupe",
    "van",
]

TRANSMISIONES = ["manual", "automatica", "cvt"]


class ModeloBase(BaseModel):
    marca: str = Field(min_length=1, max_length=100, description="Fabricante")
    nombre: str = Field(min_length=1, max_length=120, description="Nombre del modelo")
    anio: int = Field(ge=1900, le=2100, description="Año del modelo")
    precio: Decimal = Field(ge=0, le=99_999_999.99, description="Precio de lista")
    color: Optional[str] = Field(default=None, max_length=50)
    tipo: str = Field(default="sedan", max_length=40)
    transmision: str = Field(default="manual", max_length=30)
    disponible: bool = True
    descripcion: Optional[str] = Field(default=None, max_length=1000)
    imagen_url: Optional[str] = Field(default=None, max_length=500)


class ModeloCreate(ModeloBase):
    pass


class ModeloUpdate(BaseModel):
    """Actualización parcial: todos los campos son opcionales."""

    marca: Optional[str] = Field(default=None, min_length=1, max_length=100)
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=120)
    anio: Optional[int] = Field(default=None, ge=1900, le=2100)
    precio: Optional[Decimal] = Field(default=None, ge=0, le=99_999_999.99)
    color: Optional[str] = Field(default=None, max_length=50)
    tipo: Optional[str] = Field(default=None, max_length=40)
    transmision: Optional[str] = Field(default=None, max_length=30)
    disponible: Optional[bool] = None
    descripcion: Optional[str] = Field(default=None, max_length=1000)
    imagen_url: Optional[str] = Field(default=None, max_length=500)


class ModeloOut(ModeloBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # La URL 3D solo la gestionan los endpoints de carga/borrado de GLB.
    modelo_3d_url: Optional[str] = None
    modelo_3d_formato: Optional[str] = None
    modelo_3d_tamano: Optional[int] = None
    modelo_3d_subido_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
