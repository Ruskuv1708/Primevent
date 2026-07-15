#!/usr/bin/env bash
set -euo pipefail

if ! docker compose exec -T proxy test -f /etc/letsencrypt/live/primevent.uz/fullchain.pem \
  || ! docker compose exec -T proxy test -f /etc/letsencrypt/live/primevent.uz/privkey.pem; then
  echo "Certificate files are missing in /etc/letsencrypt/live/primevent.uz inside the proxy container" >&2
  exit 1
fi

docker compose exec -T proxy nginx -t
docker compose exec -T proxy nginx -s reload

echo "HTTPS configuration validated and reloaded for primevent.uz, www.primevent.uz, crm.primevent.uz, testcrm.primevent.uz, syncvista.uz, www.syncvista.uz, and lms.primevent.uz"
