#!/usr/bin/env bash
# stopdb.sh - Apaga la instancia local de MariaDB de TallerDB.
#
# No borra datos: el directorio .mariadb/ se conserva para el próximo arranque.
#
# Uso:
#   ./stopdb.sh
#   ./stopdb.sh --help

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[db]${NC} $*"; }
warn() { echo -e "${YELLOW}[db]${NC} $*"; }
error() { echo -e "${RED}[db]${NC} $*" >&2; }

usage() {
    cat <<'EOF'
Uso: ./stopdb.sh [--help]

Apaga MariaDB local (socket/PID de .mariadb/run) sin borrar los datos.

Rutas (sobrescribibles por entorno):
  MARIADB_LOCAL_DIR   .mariadb
  MARIADB_RUN_DIR     .mariadb/run
EOF
}

# Carga .env solo para variables que no estén ya definidas en el entorno.
load_env() {
    local env_file="$PROJECT_DIR/.env"
    [[ -f "$env_file" ]] || return 0

    local line key value
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" || "$line" == \#* || "$line" != *=* ]] && continue

        key="${line%%=*}"
        value="${line#*=}"
        key="${key//[[:space:]]/}"
        [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue

        if [[ "$value" == \"*\" && "$value" == *\" ]]; then
            value="${value:1:${#value}-2}"
        elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
            value="${value:1:${#value}-2}"
        else
            value="${value%%[[:space:]]#*}"
        fi
        value="${value%"${value##*[![:space:]]}"}"

        if [[ -z "${!key+x}" ]]; then
            export "$key=$value"
        fi
    done < "$env_file"
}

load_env

for arg in "$@"; do
    case "$arg" in
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Opción desconocida: $arg"
            usage
            exit 2
            ;;
    esac
done

DB_DIR="${MARIADB_LOCAL_DIR:-$PROJECT_DIR/.mariadb}"
RUN_DIR="${MARIADB_RUN_DIR:-$DB_DIR/run}"
SOCKET="${MARIADB_SOCKET:-$RUN_DIR/mariadb.sock}"
PID_FILE="${MARIADB_PID_FILE:-$RUN_DIR/mariadb.pid}"

ADMIN_BIN="$(command -v mariadb-admin || command -v mysqladmin || true)"

stopped() {
    rm -f "$PID_FILE" "$SOCKET"
    log "MariaDB está apagado."
    exit 0
}

# 1) Apagado ordenado por socket (root local sin contraseña).
if [[ -n "$ADMIN_BIN" && -S "$SOCKET" ]]; then
    if "$ADMIN_BIN" --protocol=socket --socket="$SOCKET" -u root ping --silent >/dev/null 2>&1; then
        log "Apagando MariaDB por socket ..."
        if ! "$ADMIN_BIN" --protocol=socket --socket="$SOCKET" -u root shutdown >/dev/null 2>&1; then
            warn "El apagado ordenado falló; se intentará por PID."
        fi
    fi
fi

# 2) Espera a que el proceso termine.
if [[ -f "$PID_FILE" ]]; then
    PID="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
        for _ in $(seq 1 40); do
            kill -0 "$PID" 2>/dev/null || break
            sleep 0.25
        done
    fi
else
    PID=""
fi

# 3) Si sigue vivo, terminación forzada.
if [[ -n "${PID:-}" ]] && kill -0 "$PID" 2>/dev/null; then
    warn "MariaDB no terminó por las buenas; enviando SIGTERM al PID $PID."
    kill "$PID" 2>/dev/null || true
    for _ in $(seq 1 20); do
        kill -0 "$PID" 2>/dev/null || break
        sleep 0.25
    done
    if kill -0 "$PID" 2>/dev/null; then
        warn "Enviando SIGKILL al PID $PID."
        kill -9 "$PID" 2>/dev/null || true
    fi
fi

# 4) Sin PID válido: buscar procesos que usen nuestro datadir.
if pgrep -f "mariadbd.*--datadir=$DB_DIR/data" >/dev/null 2>&1 \
    || pgrep -f "mysqld.*--datadir=$DB_DIR/data" >/dev/null 2>&1; then
    warn "Se encontraron procesos de MariaDB usando $DB_DIR/data; terminándolos."
    pkill -f "mariadbd.*--datadir=$DB_DIR/data" 2>/dev/null || true
    pkill -f "mysqld.*--datadir=$DB_DIR/data" 2>/dev/null || true
    sleep 1
fi

if [[ -n "$ADMIN_BIN" && -S "$SOCKET" ]] \
    && "$ADMIN_BIN" --protocol=socket --socket="$SOCKET" -u root ping --silent >/dev/null 2>&1; then
    error "MariaDB sigue respondiendo en $SOCKET."
    error "Revisa los procesos manualmente (pgrep -af mariadbd)."
    exit 1
fi

stopped
