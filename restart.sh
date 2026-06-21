#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting Party Show stack (db + backend + frontend + proxy)"
docker compose up -d --build --remove-orphans

log "Stack status:"
docker compose ps
