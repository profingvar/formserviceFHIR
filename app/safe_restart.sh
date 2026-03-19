#!/usr/bin/env bash
# ============================================================
# sso.pdhc — safe_restart.sh
# Server-side restart script. Stops and restarts all services
# with health verification before declaring success.
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORTS=(9000 9001 9002 9003)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Kill owned ports
info "Stopping existing processes on ports ${PORTS[*]}..."
for port in "${PORTS[@]}"; do
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
done
sleep 2

# Restart via Docker Compose
info "Restarting services via Docker Compose..."
cd "$SCRIPT_DIR"
docker compose down 2>/dev/null || true
docker compose up -d

# Wait for health
info "Waiting for services to become healthy..."
RETRIES=30
for i in $(seq 1 $RETRIES); do
    if curl -sf http://localhost:9000/api/health >/dev/null 2>&1; then
        info "Health check passed. All services running."
        info "  App:  http://localhost:9000"
        info "  DB:   localhost:9003"
        exit 0
    fi
    sleep 2
done

error "Health check failed after ${RETRIES} attempts. Check logs."
docker compose logs --tail=50
exit 1
