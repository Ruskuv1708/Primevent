#!/usr/bin/env bash
set -euo pipefail

docker compose run --rm certbot renew
docker compose exec proxy nginx -s reload
