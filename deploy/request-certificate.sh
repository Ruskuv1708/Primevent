#!/usr/bin/env bash
set -euo pipefail

certbot_contact_args=(--register-unsafely-without-email)
if [[ -n "${CERTBOT_EMAIL:-}" ]]; then
  certbot_contact_args=(--email "$CERTBOT_EMAIL" --no-eff-email)
fi

mkdir -p data/certbot/www data/certbot/conf

docker compose run --rm certbot certonly \
  --cert-name primevent.uz \
  --webroot \
  --webroot-path /var/www/certbot \
  "${certbot_contact_args[@]}" \
  --agree-tos \
  --non-interactive \
  --expand \
  -d primevent.uz \
  -d www.primevent.uz \
  -d crm.primevent.uz \
  -d testcrm.primevent.uz \
  -d syncvista.uz \
  -d www.syncvista.uz \
  -d lms.primevent.uz

./deploy/enable-https.sh
