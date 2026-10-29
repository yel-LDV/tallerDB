#!/usr/bin/env bash
# startdb.sh - Inicia una instancia local de MariaDB para TallerDB.
#
# Los datos, socket, PID y logs viven en .mariadb/ (ignorado por git).
# Lee la configuración de .env (MARIADB_*) sin sobrescribir variables ya
# exportadas en el entorno.
#
# Uso:
#   ./startdb.sh              # inicia y carga esquema/datos si faltan
#   ./startdb.sh --no-seed    # no inserta los datos de ejemplo
#   ./startdb.sh --help

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
Uso: ./startdb.sh [--no-seed] [--help]

Inicia MariaDB local usando las variables MARIADB_* de .env.
  --no-seed   No carga database/init/02_seed_modelos.sql si el catálogo está vacío.
  --help      Muestra esta ayuda.

Rutas (sobrescribibles por entorno):
  MARIADB_LOCAL_DIR   .mariadb
  MARIADB_DATA_DIR    .mariadb/data
  MARIADB_RUN_DIR     .mariadb/run
  MARIADB_LOG_DIR     .mariadb/log
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

MARIADB_PORT="${MARIADB_PORT:-3306}"
DB_NAME="${MARIADB_DATABASE:-tallerdb}"
DB_USER="${MARIADB_USER:-taller}"
DB_PASSWORD="${MARIADB_PASSWORD:-tallerpass}"

DB_DIR="${MARIADB_LOCAL_DIR:-$PROJECT_DIR/.mariadb}"
DATA_DIR="${MARIADB_DATA_DIR:-$DB_DIR/data}"
RUN_DIR="${MARIADB_RUN_DIR:-$DB_DIR/run}"
LOG_DIR="${MARIADB_LOG_DIR:-$DB_DIR/log}"
SOCKET="${MARIADB_SOCKET:-$RUN_DIR/mariadb.sock}"
PID_FILE="${MARIADB_PID_FILE:-$RUN_DIR/mariadb.pid}"
ERROR_LOG="$LOG_DIR/mariadb.err"

SEED=1
for arg in "$@"; do
    case "$arg" in
        --no-seed) SEED=0 ;;
        --seed) SEED=1 ;;
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

[[ "$MARIADB_PORT" =~ ^[0-9]+$ ]] || {
    error "MARIADB_PORT no es un número válido: $MARIADB_PORT"
    exit 1
}
[[ "$DB_NAME" =~ ^[A-Za-z0-9_]+$ ]] || {
    error "MARIADB_DATABASE solo puede contener letras, números y guion bajo."
    exit 1
}
[[ "$DB_USER" =~ ^[A-Za-z0-9_]+$ ]] || {
    error "MARIADB_USER solo puede contener letras, números y guion bajo."
    exit 1
}

MARIADBD_BIN="$(command -v mariadbd || command -v mysqld || true)"
INSTALL_BIN="$(command -v mariadb-install-db || command -v mysql_install_db || true)"
ADMIN_BIN="$(command -v mariadb-admin || command -v mysqladmin || true)"
CLIENT_BIN="$(command -v mariadb || command -v mysql || true)"

if [[ -z "$MARIADBD_BIN" || -z "$INSTALL_BIN" || -z "$ADMIN_BIN" || -z "$CLIENT_BIN" ]]; then
    error "No se encontraron los binarios de MariaDB (mariadbd, mariadb-install-db, mariadb-admin, mariadb)."
    error "Instala MariaDB/MySQL antes de usar este script."
    exit 1
fi

mkdir -p "$DATA_DIR" "$RUN_DIR" "$LOG_DIR"

# Si ya responde por el socket, no arrancamos otra instancia.
if "$ADMIN_BIN" --protocol=socket --socket="$SOCKET" -u root ping --silent >/dev/null 2>&1; then
    log "MariaDB ya está corriendo en 127.0.0.1:$MARIADB_PORT (socket: $SOCKET)"
    exit 0
fi

if [[ -f "$PID_FILE" ]]; then
    OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
        warn "El proceso $OLD_PID existe pero MariaDB no responde por el socket."
        warn "Revisa $ERROR_LOG o ejecuta ./stopdb.sh."
        exit 1
    fi
    warn "Eliminando PID huérfano: $PID_FILE"
    rm -f "$PID_FILE"
fi
rm -f "$SOCKET"

if [[ ! -d "$DATA_DIR/mysql" ]]; then
    log "Inicializando el directorio de datos en $DATA_DIR ..."
    if ! "$INSTALL_BIN" \
        --datadir="$DATA_DIR" \
        --auth-root-authentication-method=normal \
        --skip-test-db \
        --user="$(id -un)" >"$LOG_DIR/install.log" 2>&1; then
        error "No se pudo inicializar MariaDB. Revisa $LOG_DIR/install.log"
        tail -n 25 "$LOG_DIR/install.log" 2>/dev/null || true
        exit 1
    fi
fi

log "Iniciando MariaDB en 127.0.0.1:$MARIADB_PORT ..."
nohup "$MARIADBD_BIN" \
    --datadir="$DATA_DIR" \
    --socket="$SOCKET" \
    --port="$MARIADB_PORT" \
    --bind-address=127.0.0.1 \
    --pid-file="$PID_FILE" \
    --log-error="$ERROR_LOG" \
    --user="$(id -un)" \
    --skip-name-resolve \
    >"$LOG_DIR/stdout.log" 2>&1 &
START_PID=$!

READY=0
for _ in $(seq 1 60); do
    if "$ADMIN_BIN" --protocol=socket --socket="$SOCKET" -u root ping --silent >/dev/null 2>&1; then
        READY=1
        break
    fi
    if ! kill -0 "$START_PID" 2>/dev/null; then
        break
    fi
    sleep 0.5
done

if [[ "$READY" -ne 1 ]]; then
    error "MariaDB no respondió a tiempo."
    tail -n 30 "$ERROR_LOG" 2>/dev/null || true
    kill "$START_PID" 2>/dev/null || true
    wait "$START_PID" 2>/dev/null || true
    rm -f "$PID_FILE" "$SOCKET"
    exit 1
fi

DB_PASSWORD_SQL="${DB_PASSWORD//\\/\\\\}"
DB_PASSWORD_SQL="${DB_PASSWORD_SQL//\'/\'\'}"

log "Creando base de datos '$DB_NAME' y usuario '$DB_USER' ..."
"$CLIENT_BIN" --protocol=socket --socket="$SOCKET" -u root <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'127.0.0.1' IDENTIFIED BY '$DB_PASSWORD_SQL';
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD_SQL';
ALTER USER '$DB_USER'@'127.0.0.1' IDENTIFIED BY '$DB_PASSWORD_SQL';
ALTER USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD_SQL';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'127.0.0.1';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL

TABLE_EXISTS="$(
    "$CLIENT_BIN" --protocol=socket --socket="$SOCKET" -u root -N -B -e \
        "SELECT COUNT(*) FROM information_schema.tables \
         WHERE table_schema='$DB_NAME' AND table_name='modelos';" \
    | tr -d '[:space:]'
)"

if [[ "$TABLE_EXISTS" == "0" ]]; then
    log "Creando el esquema de TallerDB ..."
    "$CLIENT_BIN" --protocol=socket --socket="$SOCKET" -u root "$DB_NAME" \
        < "$PROJECT_DIR/database/init/01_schema.sql"
fi

if [[ "$SEED" == "1" ]]; then
    ROW_COUNT="$(
        "$CLIENT_BIN" --protocol=socket --socket="$SOCKET" -u root -N -B "$DB_NAME" \
            -e "SELECT COUNT(*) FROM modelos;" | tr -d '[:space:]'
    )"
    if [[ "$ROW_COUNT" == "0" ]]; then
        log "Cargando datos de ejemplo del catálogo ..."
        "$CLIENT_BIN" --protocol=socket --socket="$SOCKET" -u root "$DB_NAME" \
            < "$PROJECT_DIR/database/init/02_seed_modelos.sql"
    fi
fi

log "MariaDB listo."
echo "  Host:      127.0.0.1:$MARIADB_PORT"
echo "  Socket:    $SOCKET"
echo "  Base:      $DB_NAME"
echo "  Usuario:   $DB_USER"
echo "  Datos:     $DATA_DIR"
echo "  Log:       $ERROR_LOG"
echo "  Verificar: python app/main.py testdb"
echo "  Apagar:    ./stopdb.sh"
