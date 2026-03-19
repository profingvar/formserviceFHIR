#!/usr/bin/env bash
# ============================================================
# server_backup.sh — Full backup of sso.pdhc service
#
# Creates: ~/backups/sso.pdhc_backup_<datetime>.tar.gz
# Contains: all application files + PostgreSQL database dump
# ============================================================
set -euo pipefail

# --- Configuration ---
SERVICE_NAME="sso.pdhc"
DEPLOY_DIR="/opt/sso_pdhc"
APP_DIR="$DEPLOY_DIR/app"
BACKUP_BASE="$HOME/backups"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
BACKUP_NAME="${SERVICE_NAME}_backup_${TIMESTAMP}"
BACKUP_DIR="$BACKUP_BASE/$BACKUP_NAME"
BACKUP_FILE="$BACKUP_BASE/${BACKUP_NAME}.tar.gz"

# DB connection (must match docker-compose.yml / .env)
DB_CONTAINER="sso_db"
DB_USER="sso_user"
DB_NAME="sso_db"
DB_PORT="9003"

# --- Colima Docker socket (macmini server) ---
if [ -S "$HOME/.colima/default/docker.sock" ]; then
    export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
fi

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# --- Pre-flight ---
info "=== $SERVICE_NAME full backup ==="
info "Timestamp: $TIMESTAMP"

if [ ! -d "$DEPLOY_DIR" ]; then
    error "Deploy directory not found: $DEPLOY_DIR"
    exit 1
fi

mkdir -p "$BACKUP_DIR"
info "Backup staging: $BACKUP_DIR"

# --- 1. Database dump ---
info "Dumping PostgreSQL database..."
if docker exec "$DB_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom \
        > "$BACKUP_DIR/db_dump.pgdump"
    # Also create a plain SQL dump for portability
    docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --format=plain \
        > "$BACKUP_DIR/db_dump.sql"
    info "  Database dump: OK (custom + plain SQL)"
else
    warn "  Database container not running — skipping DB dump"
    warn "  If the DB is critical, start it first: cd $APP_DIR && docker-compose up -d db"
fi

# --- 2. Copy application files ---
info "Copying application files..."

# Copy everything except venv, __pycache__, logs contents, .git
rsync -a \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='logs/*.log*' \
    --exclude='docs/site/' \
    --exclude='.DS_Store' \
    "$DEPLOY_DIR/" "$BACKUP_DIR/files/"

info "  Application files: OK"

# --- 3. Preserve .env separately (double safety) ---
if [ -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env" "$BACKUP_DIR/env_backup"
    chmod 600 "$BACKUP_DIR/env_backup"
    info "  .env backup: OK"
else
    warn "  No .env file found"
fi

# --- 4. Preserve docker-compose.yml separately ---
if [ -f "$APP_DIR/docker-compose.yml" ]; then
    cp "$APP_DIR/docker-compose.yml" "$BACKUP_DIR/docker-compose.yml.bak"
    info "  docker-compose.yml backup: OK"
fi

# --- 5. Preserve oath_overview.csv if present ---
if [ -f "$APP_DIR/oath_overview.csv" ]; then
    cp "$APP_DIR/oath_overview.csv" "$BACKUP_DIR/oath_overview.csv.bak"
    info "  oath_overview.csv backup: OK"
fi

# --- 6. Record metadata ---
cat > "$BACKUP_DIR/BACKUP_INFO.txt" <<HEREDOC
Service:    $SERVICE_NAME
Timestamp:  $TIMESTAMP
Source:      $DEPLOY_DIR
Host:        $(hostname)
User:        $(whoami)
Docker:      $(docker --version 2>/dev/null || echo "N/A")
PostgreSQL:  $(docker exec "$DB_CONTAINER" psql --version 2>/dev/null || echo "N/A")

Contents:
  db_dump.pgdump        — PostgreSQL custom-format dump (use pg_restore)
  db_dump.sql           — PostgreSQL plain SQL dump (human readable)
  files/                — Full application tree (excluding venv, caches, logs)
  env_backup            — Copy of .env at backup time
  docker-compose.yml.bak— Copy of docker-compose.yml at backup time

Restore DB:
  pg_restore -h localhost -p $DB_PORT -U $DB_USER -d $DB_NAME db_dump.pgdump
  — or —
  psql -h localhost -p $DB_PORT -U $DB_USER -d $DB_NAME < db_dump.sql
HEREDOC
info "  Metadata: OK"

# --- 7. Create tarball ---
info "Compressing to tarball..."
cd "$BACKUP_BASE"
tar -czf "$BACKUP_FILE" "$BACKUP_NAME/"

# Remove staging directory
rm -rf "$BACKUP_DIR"

# --- Done ---
SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
info "=== Backup complete ==="
info "  File: $BACKUP_FILE"
info "  Size: $SIZE"
