#!/usr/bin/env bash
# ============================================================
# sso.pdhc — pack_deploy.sh
# Creates a deployment tarball for transfer to the server.
# Excludes venv, __pycache__, .git, test results, .env (secrets).
#
# Usage:
#   ./pack_deploy.sh              # creates sso_pdhc_deploy_<timestamp>.tar.gz
#   scp <tarball> user@server:~   # operator transfers manually
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARBALL="sso_pdhc_deploy_${TIMESTAMP}.tar.gz"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[PACK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }

info "Creating deployment tarball: $TARBALL"

cd "$SCRIPT_DIR"

tar czf "$TARBALL" \
    --exclude='./app/venv' \
    --exclude='./app/logs/*' \
    --exclude='./app/results/*' \
    --exclude='./app/.env' \
    --exclude='./app/docs/site' \
    --exclude='./_obs_gateway_repo' \
    --exclude='./.git' \
    --exclude='./.claude' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.DS_Store' \
    --exclude='./results' \
    --exclude='./sso_pdhc_deploy_*.tar.gz' \
    .

SIZE=$(du -h "$TARBALL" | cut -f1)
info "Tarball created: $TARBALL ($SIZE)"
info ""
info "Transfer to server:"
info "  scp $TARBALL user@<server>:~"
info ""
info "Then on the server, run:"
info "  ./server_deploy.sh ~/$TARBALL"
