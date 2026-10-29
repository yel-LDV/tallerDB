# Dockerfile para TallerDB - Multi-stage build
FROM python:3.12-slim as builder

# Instalar dependencias del sistema para compilar
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN useradd --no-create-home --shell /bin/bash appuser

WORKDIR /app

# Copiar requirements e instalar en virtualenv
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.12-slim

# Instalar solo runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    && rm -rf /var/lib/apt/lists/*

# Copiar virtualenv del builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Crear usuario no-root
RUN useradd --no-create-home --shell /bin/bash appuser

WORKDIR /app

# Copiar código
COPY --chown=appuser:appuser . .

# Directorios de datos: SQLite (dev) y modelos 3D subidos
RUN mkdir -p /app/data /app/uploads && \
    chown -R appuser:appuser /app/data /app/uploads

USER appuser

# Exponer puerto
EXPOSE 8000

# Health check (readiness: comprueba también la base de datos)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready', timeout=2)" || exit 1

# Comando por defecto
CMD ["python", "run.py"]