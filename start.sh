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

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# --- Kill owned ports ---
kill_ports() {
    info "Killing processes on ports ${PORTS[*]}..."
    for port in "${PORTS[@]}"; do
        pids=$(lsof -ti :"$port" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
            info "  Killed process(es) on port $port"
        fi
    done
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

# --- Activate venv ---
activate_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        error "Virtual environment not found at $VENV_DIR. Run: python3 -m venv $VENV_DIR"
        exit 1
    fi
    source "$VENV_DIR/bin/activate"
    info "Virtual environment activated."
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
    cd "$APP_DIR" && docker compose down 2>/dev/null || true
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

kill_ports
check_docker
activate_venv

# Start DB via Docker Compose
info "Starting PostgreSQL container..."
cd "$APP_DIR"
docker compose up -d db
info "Waiting for DB to be healthy..."
until docker compose exec db pg_isready -U sso_user -d sso_db >/dev/null 2>&1; do
    sleep 1
done
info "PostgreSQL is ready on port 9003."

# Create logs directory
mkdir -p "$APP_DIR/logs"

# Start Flask app (development mode)
info "Starting Flask app on port 9000..."
cd "$APP_DIR"
FLASK_APP=src.app:create_app FLASK_ENV=development python -m flask run --host=0.0.0.0 --port=9000 &
FLASK_PID=$!

info "=== sso.pdhc is running ==="
info "  App:  http://localhost:9000"
info "  DB:   localhost:9003"
info "  Press Ctrl+C to stop."

# Wait for Flask process
wait "$FLASK_PID"
