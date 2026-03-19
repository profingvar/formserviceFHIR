#!/usr/bin/env bash
# ============================================================
# sso.pdhc — server_deploy.sh
# Unpacks tarball and sets up the service on the server.
# Run on the production server (macmini).
#
# Usage:
#   ./server_deploy.sh <tarball>         # first install
#   ./server_deploy.sh <tarball> update  # update existing install
#
# Ports: 9000 (app), 9003 (db) — same as development.
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[DEPLOY]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# --- Arguments ---
TARBALL="${1:-}"
MODE="${2:-install}"

if [ -z "$TARBALL" ]; then
    error "Usage: $0 <tarball> [install|update]"
    exit 1
fi

if [ ! -f "$TARBALL" ]; then
    error "Tarball not found: $TARBALL"
    exit 1
fi

DEPLOY_DIR="/opt/sso_pdhc"
BACKUP_DIR="/opt/sso_pdhc_backups"

# ============================================================
# Pre-flight checks
# ============================================================
info "=== sso.pdhc Server Deployment ==="
info "Tarball: $TARBALL"
info "Mode:    $MODE"
info "Target:  $DEPLOY_DIR"
info ""

# Check Docker
if ! docker info >/dev/null 2>&1; then
    error "Docker is not running. Start Docker first."
    exit 1
fi
info "Docker is running."

# Check Python
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Install Python 3.11+."
    exit 1
fi
PYVER=$(python3 --version 2>&1)
info "Python: $PYVER"

# ============================================================
# Backup existing installation (update mode)
# ============================================================
if [ "$MODE" = "update" ] && [ -d "$DEPLOY_DIR" ]; then
    BACKUP_TS="$(date -u +%Y%m%dT%H%M%SZ)"
    mkdir -p "$BACKUP_DIR"

    info "Backing up existing .env..."
    cp "$DEPLOY_DIR/app/.env" "$BACKUP_DIR/env_backup_${BACKUP_TS}" 2>/dev/null || true

    info "Backing up database..."
    docker exec sso_db pg_dump -U sso_user sso_db > "$BACKUP_DIR/db_backup_${BACKUP_TS}.sql" 2>/dev/null || warn "DB backup skipped (container not running)"

    info "Backing up oath_overview.csv..."
    cp "$DEPLOY_DIR/app/oath_overview.csv" "$BACKUP_DIR/oath_overview_${BACKUP_TS}.csv" 2>/dev/null || true

    info "Stopping existing services..."
    cd "$DEPLOY_DIR/app" && docker compose down 2>/dev/null || true
    # Kill any flask dev processes on our ports
    for port in 9000 9001 9002 9003; do
        pids=$(lsof -ti :"$port" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
        fi
    done
    sleep 1

    info "Backup complete: $BACKUP_DIR/*_${BACKUP_TS}*"
fi

# ============================================================
# Unpack
# ============================================================
info "Creating deploy directory: $DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

info "Unpacking tarball..."
tar xzf "$TARBALL" -C "$DEPLOY_DIR"

info "Files unpacked to $DEPLOY_DIR"

# ============================================================
# Restore .env (update mode) or check .env exists (install mode)
# ============================================================
if [ "$MODE" = "update" ] && [ -f "$BACKUP_DIR/env_backup_${BACKUP_TS}" ]; then
    info "Restoring .env from backup..."
    cp "$BACKUP_DIR/env_backup_${BACKUP_TS}" "$DEPLOY_DIR/app/.env"
    info ".env restored. Review for any new variables in .env.example."
elif [ ! -f "$DEPLOY_DIR/app/.env" ]; then
    warn "No .env file found. Creating from .env.example..."
    cp "$DEPLOY_DIR/app/.env.example" "$DEPLOY_DIR/app/.env"
    warn ""
    warn "  *** IMPORTANT: Edit $DEPLOY_DIR/app/.env before proceeding! ***"
    warn "  *** See pre-deployment-checklist.md for all required changes. ***"
    warn ""
fi

# Secure .env permissions
chmod 600 "$DEPLOY_DIR/app/.env"

# ============================================================
# Restore oath_overview.csv (update mode)
# ============================================================
if [ "$MODE" = "update" ] && [ -f "$BACKUP_DIR/oath_overview_${BACKUP_TS}.csv" ]; then
    info "Restoring oath_overview.csv from backup..."
    cp "$BACKUP_DIR/oath_overview_${BACKUP_TS}.csv" "$DEPLOY_DIR/app/oath_overview.csv"
fi

# ============================================================
# Create virtual environment and install dependencies
# ============================================================
info "Setting up Python virtual environment..."
cd "$DEPLOY_DIR"
if [ ! -d "$DEPLOY_DIR/app/venv" ]; then
    python3 -m venv "$DEPLOY_DIR/app/venv"
    info "Virtual environment created."
else
    info "Virtual environment already exists."
fi

info "Installing dependencies..."
"$DEPLOY_DIR/app/venv/bin/pip" install --quiet --upgrade pip
"$DEPLOY_DIR/app/venv/bin/pip" install --quiet -r "$DEPLOY_DIR/app/requirements.txt"
info "Dependencies installed."

# ============================================================
# Create required directories
# ============================================================
mkdir -p "$DEPLOY_DIR/app/logs"
mkdir -p "$DEPLOY_DIR/app/results"

# ============================================================
# Set script permissions
# ============================================================
chmod +x "$DEPLOY_DIR/start.sh"
chmod +x "$DEPLOY_DIR/app/safe_restart.sh" 2>/dev/null || true
chmod +x "$DEPLOY_DIR/app/scripts/test_endpoints.sh" 2>/dev/null || true

# ============================================================
# Build documentation site
# ============================================================
info "Building documentation site..."
cd "$DEPLOY_DIR/app/docs"
"$DEPLOY_DIR/app/venv/bin/mkdocs" build --quiet 2>/dev/null || warn "mkdocs build skipped (non-critical)"

# ============================================================
# Start services
# ============================================================
info "Starting PostgreSQL container..."
cd "$DEPLOY_DIR/app"
docker compose up -d db

info "Waiting for database to be healthy..."
until docker compose exec db pg_isready -U sso_user -d sso_db >/dev/null 2>&1; do
    sleep 1
done
info "PostgreSQL is ready on port 9003."

# ============================================================
# Database initialisation (install mode only)
# ============================================================
if [ "$MODE" = "install" ]; then
    info "Initialising database tables..."
    cd "$DEPLOY_DIR/app"
    "$DEPLOY_DIR/app/venv/bin/python" scripts/init_db.py
    info "Database tables created."

    info "Creating bootstrap superuser..."
    "$DEPLOY_DIR/app/venv/bin/python" scripts/create_su.py
    info "Bootstrap superuser created."
fi

# ============================================================
# Start the application
# ============================================================
info "Starting application on port 9000..."
cd "$DEPLOY_DIR/app"

# Use gunicorn in production
source "$DEPLOY_DIR/app/venv/bin/activate"
FLASK_ENV=production gunicorn \
    --bind 0.0.0.0:9000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile "$DEPLOY_DIR/app/logs/access.log" \
    --error-logfile "$DEPLOY_DIR/app/logs/error.log" \
    --daemon \
    --pid "$DEPLOY_DIR/app/gunicorn.pid" \
    "src.app:create_app()"

info ""
info "=== sso.pdhc deployment complete ==="
info ""
info "  App:  http://localhost:9000"
info "  DB:   localhost:9003"
info "  Logs: $DEPLOY_DIR/app/logs/"
info "  PID:  $DEPLOY_DIR/app/gunicorn.pid"
info ""

if [ "$MODE" = "install" ]; then
    info "=== FIRST-TIME SETUP REMAINING ==="
    info ""
    info "  1. Verify .env is configured (see pre-deployment-checklist.md)"
    info "  2. Open http://localhost:9000 and login with bootstrap SU"
    info "  3. Change the bootstrap password immediately"
    info "  4. Configure nginx reverse proxy for HTTPS"
    info "  5. Register downstream services"
    info ""
fi

# Health check
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/api/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    info "Health check: PASSED (HTTP 200)"
else
    warn "Health check: returned HTTP $HTTP_CODE — check logs at $DEPLOY_DIR/app/logs/"
fi
