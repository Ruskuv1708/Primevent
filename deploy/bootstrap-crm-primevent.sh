#!/usr/bin/env bash
set -euo pipefail

: "${CRM_ADMIN_EMAIL:?Set CRM_ADMIN_EMAIL before bootstrapping the CRM workspace}"
: "${CRM_ADMIN_PASSWORD:?Set CRM_ADMIN_PASSWORD before bootstrapping the CRM workspace}"

CRM_WORKSPACE_NAME="${CRM_WORKSPACE_NAME:-Prime Event CRM}"
CRM_WORKSPACE_SUBDOMAIN="${CRM_WORKSPACE_SUBDOMAIN:-crm}"

export CRM_BOOTSTRAP_PASSWORD="$CRM_ADMIN_PASSWORD"
docker compose exec \
  -e CRM_BOOTSTRAP_PASSWORD \
  crm_backend \
  python scripts/bootstrap_workspace_and_admin.py \
    --email "$CRM_ADMIN_EMAIL" \
    --workspace-name "$CRM_WORKSPACE_NAME" \
    --subdomain "$CRM_WORKSPACE_SUBDOMAIN"
