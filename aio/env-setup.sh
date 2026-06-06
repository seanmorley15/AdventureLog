#!/bin/bash
# Derive full AdventureLog configuration from minimal AIO environment variables.
set -euo pipefail

SITE_URL="${SITE_URL:-http://localhost:8015}"
SITE_URL="${SITE_URL%/}"

export SITE_URL
export ORIGIN="${ORIGIN:-$SITE_URL}"
export FRONTEND_URL="${FRONTEND_URL:-$SITE_URL}"
export PUBLIC_URL="${PUBLIC_URL:-$SITE_URL}"
export CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-$SITE_URL}"
export PUBLIC_SERVER_URL="${PUBLIC_SERVER_URL:-http://127.0.0.1:8000}"
export BODY_SIZE_LIMIT="${BODY_SIZE_LIMIT:-Infinity}"
export DEBUG="${DEBUG:-False}"
export PORT=3000

export PGHOST="${PGHOST:-db}"
export POSTGRES_DB="${POSTGRES_DB:-database}"
export POSTGRES_USER="${POSTGRES_USER:-adventure}"
export PGDATABASE="${PGDATABASE:-$POSTGRES_DB}"
export PGUSER="${PGUSER:-$POSTGRES_USER}"

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
	echo "ERROR: POSTGRES_PASSWORD is required for the AIO container." >&2
	exit 1
fi
export PGPASSWORD="${POSTGRES_PASSWORD}"

if [[ -z "${SECRET_KEY:-}" ]]; then
	export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
fi

export DJANGO_ADMIN_USERNAME="${DJANGO_ADMIN_USERNAME:-admin}"
export DJANGO_ADMIN_PASSWORD="${DJANGO_ADMIN_PASSWORD:-admin}"
export DJANGO_ADMIN_EMAIL="${DJANGO_ADMIN_EMAIL:-admin@example.com}"

echo "AIO configuration:"
echo "  SITE_URL=$SITE_URL"
echo "  PUBLIC_SERVER_URL=$PUBLIC_SERVER_URL"
echo "  PGHOST=$PGHOST"
