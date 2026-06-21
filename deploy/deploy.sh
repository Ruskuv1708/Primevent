#!/bin/bash
set -euo pipefail

echo "Starting deployment for primevent.uz..."

echo "Building and starting Docker containers..."
docker compose up -d --build --remove-orphans

echo "Stack status:"
docker compose ps

echo "Done. The local proxy listens on ports 80 and 443."
