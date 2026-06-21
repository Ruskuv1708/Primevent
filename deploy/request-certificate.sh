#!/usr/bin/env bash
set -euo pipefail

: "${CERTBOT_EMAIL:?Set CERTBOT_EMAIL before requesting a certificate}"

mkdir -p data/certbot/www data/certbot/conf

docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email "$CERTBOT_EMAIL" \
  --agree-tos \
  --no-eff-email \
  --non-interactive \
  --expand \
  -d primevent.uz \
  -d www.primevent.uz \
  -d crm.primevent.uz \
  -d testcrm.primevent.uz

./deploy/enable-https.sh
