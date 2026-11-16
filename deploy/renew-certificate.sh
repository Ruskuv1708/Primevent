#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# -T: no TTY, so this also works from cron.
docker compose run --rm -T certbot renew --non-interactive
docker compose exec -T proxy nginx -t
docker compose exec -T proxy nginx -s reload
