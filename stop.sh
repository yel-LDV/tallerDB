#!/usr/bin/env bash
# stop.sh - Para el proyecto TallerDB
# Uso: ./stop.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PID_FILE="$PROJECT_DIR/.server.pid"
PORT=8000

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[stop]${NC} $*"; }
warn() { echo -e "${YELLOW}[stop]${NC} $*"; }
error() { echo -e "${RED}[stop]${NC} $*" >&2; }

# Matar por PID file
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
        log "Deteniendo servidor (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 1
        # Forzar si no murió
        if kill -0 "$PID" 2>/dev/null; then
            warn "Proceso no terminó, forzando (SIGKILL)..."
            kill -9 "$PID" 2>/dev/null
        fi
        log "Servidor detenido."
    else
        warn "PID $PID no encontrado o ya muerto."
    fi
    rm -f "$PID_FILE"
else
    warn "No hay PID file."
fi

# Matar cualquier proceso en el puerto por si acaso
if lsof -ti:"$PORT" >/dev/null 2>&1; then
    warn "Limpiando procesos restantes en puerto $PORT..."
    lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
    sleep 0.5
fi

# Matar procesos uvicorn/watchfiles huérfanos del proyecto
pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
pkill -f "watchfiles.*tallerdbProyect" 2>/dev/null || true

log "Limpieza completa."