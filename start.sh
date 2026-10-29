#!/usr/bin/env bash
# start.sh - Levanta el proyecto TallerDB (FastAPI + base de datos configurable)
# Uso: ./start.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/.venv"
PID_FILE="$PROJECT_DIR/.server.pid"
LOG_FILE="$PROJECT_DIR/server.log"
PORT=8000

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[start]${NC} $*"; }
warn() { echo -e "${YELLOW}[start]${NC} $*"; }
error() { echo -e "${RED}[start]${NC} $*" >&2; }

# Verificar si ya está corriendo
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
        warn "El servidor ya está corriendo (PID: $OLD_PID) en http://localhost:$PORT"
        exit 0
    else
        warn "PID file huérfano encontrado, limpiando..."
        rm -f "$PID_FILE"
    fi
fi

# Verificar puerto ocupado por otro proceso
if lsof -ti:"$PORT" >/dev/null 2>&1; then
    warn "Puerto $PORT ocupado por otro proceso. Intentando liberar..."
    lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Verificar/crear venv
if [[ ! -d "$VENV_DIR" ]]; then
    log "Creando entorno virtual en $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Usar python -m pip del venv (funciona con uv venv también)
VENV_PYTHON="$VENV_DIR/bin/python"

# Instalar/actualizar dependencias
log "Instalando dependencias..."
"$VENV_PYTHON" -m pip install -q --upgrade pip
"$VENV_PYTHON" -m pip install -q -r requirements.txt

# Verificar .env
if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    log "Creando .env desde .env.example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    warn "¡Edita .env con tus credenciales antes de usar en producción!"
fi

# Crear el esquema si falta y el usuario admin si no existe
log "Verificando esquema y usuario administrador..."
"$VENV_PYTHON" scripts/create_admin.py

# Levantar servidor en background
log "Iniciando servidor en http://localhost:$PORT ..."
nohup "$VENV_PYTHON" run.py >> "$LOG_FILE" 2>&1 &
SERVER_PID=$!

# Guardar PID
echo "$SERVER_PID" > "$PID_FILE"

# Esperar a que esté listo
log "Esperando a que el servidor responda..."
for i in {1..30}; do
    if curl -sf "http://localhost:$PORT/login" >/dev/null 2>&1; then
        log "¡Servidor listo!"
        echo
        echo "  URL:        http://localhost:$PORT"
        echo "  Login:      http://localhost:$PORT/login"
        echo "  Dashboard:  http://localhost:$PORT/dashboard"
        echo "  API Docs:   http://localhost:$PORT/docs"
        echo "  Logs:       tail -f $LOG_FILE"
        echo "  Parar:      ./stop.sh"
        echo
        exit 0
    fi
    sleep 0.5
done

error "El servidor no respondió a tiempo. Revisa $LOG_FILE"
cat "$LOG_FILE"
exit 1