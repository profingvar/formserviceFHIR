#!/usr/bin/env bash
# ============================================================
# sso.pdhc — start.sh
# Single entry point: kills owned ports, starts DB + app.
# Ctrl+C gracefully shuts down all services.
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/app"
VENV_DIR="$APP_DIR/venv"
PORTS=(9000 9001 9002 9003)

# --- Colima Docker socket (macmini server) ---
if [ -S "/Users/miserver/.colima/default/docker.sock" ]; then
    export DOCKER_HOST="unix:///Users/miserver/.colima/default/docker.sock"
fi

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# --- Stop existing services ---
stop_existing() {
    info "Stopping existing services..."
    # Stop our DB container gracefully (port 9003)
    cd "$APP_DIR" && docker-compose down 2>/dev/null || true
    # Kill app processes on ports 9000-9002 (not 9003 — Docker handles that)
    for port in 9000 9001 9002; do
        pids=$(lsof -ti :"$port" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
            info "  Killed process(es) on port $port"
        fi
    done
    # Kill gunicorn by PID file if present
    if [ -f "$APP_DIR/gunicorn.pid" ]; then
        kill "$(cat "$APP_DIR/gunicorn.pid")" 2>/dev/null || true
        rm -f "$APP_DIR/gunicorn.pid"
    fi
    sleep 1
}

# --- Check Docker ---
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    info "Docker is running."
}

# --- Ensure and activate venv ---
activate_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        info "Creating virtual environment at $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
        info "Virtual environment created."
    fi
    source "$VENV_DIR/bin/activate"
    info "Virtual environment activated."
    info "Installing/updating dependencies..."
    pip install --quiet --upgrade pip
    pip install --quiet -r "$APP_DIR/requirements.txt"
    info "Dependencies ready."
}

# --- Graceful shutdown ---
cleanup() {
    echo ""
    info "Shutting down..."
    # Stop Flask dev server if running
    if [ -n "${FLASK_PID:-}" ]; then
        kill "$FLASK_PID" 2>/dev/null || true
        wait "$FLASK_PID" 2>/dev/null || true
        info "Flask stopped."
    fi
    # Stop Docker containers
    info "Stopping Docker containers..."
    cd "$APP_DIR" && docker-compose down 2>/dev/null || true
    info "Docker containers stopped."
    # Deactivate venv
    deactivate 2>/dev/null || true
    info "Virtual environment deactivated."
    info "Goodbye."
    exit 0
}

trap cleanup SIGINT SIGTERM

# ============================================================
# Main
# ============================================================
info "=== sso.pdhc starting ==="

check_docker
stop_existing
activate_venv

# Start DB via Docker Compose
info "Starting PostgreSQL container..."
cd "$APP_DIR"
docker-compose up -d db
info "Waiting for DB to be healthy..."
until docker-compose exec db pg_isready -U sso_user -d sso_db >/dev/null 2>&1; do
    sleep 1
done
info "PostgreSQL is ready on port 9003."

# Create required directories
mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/results"

# Initialise DB tables and bootstrap SU (idempotent)
info "Initialising database (idempotent)..."
cd "$APP_DIR"
python scripts/init_db.py
python scripts/create_su.py
info "Database ready."

# Start Flask app (gunicorn, background)
info "Starting gunicorn on port 9000..."
cd "$APP_DIR"
gunicorn \
    --bind 0.0.0.0:9000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile "$APP_DIR/logs/access.log" \
    --error-logfile "$APP_DIR/logs/error.log" \
    --daemon \
    --pid "$APP_DIR/gunicorn.pid" \
    "src.app:create_app()"

sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/api/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    info "Health check: PASSED (HTTP 200)"
else
    warn "Health check: HTTP $HTTP_CODE — check logs at $APP_DIR/logs/"
fi

info "=== sso.pdhc is running ==="
info "  App:  http://localhost:9000"
info "  DB:   localhost:9003"
info "  PID:  $APP_DIR/gunicorn.pid"
info "  Logs: $APP_DIR/logs/"
