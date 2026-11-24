"""Generación de slugs únicos para anuncios.

Un slug se construye a partir de marca + nombre + año + un sufijo aleatorio
para garantizar unicidad: `toyota-corolla-2023-a1b2c3`.
"""

import re
import uuid


def _slugify(text: str) -> str:
    """Convierte texto en un segmento de URL seguro."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def generate_slug(marca: str, nombre: str, anio: int) -> str:
    """Genera un slug único para un anuncio."""
    base = f"{_slugify(marca)}-{_slugify(nombre)}-{anio}"
    suffix = uuid.uuid4().hex[:6]
    return f"{base}-{suffix}"
