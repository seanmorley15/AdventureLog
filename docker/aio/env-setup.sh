#!/bin/bash
# Derive full AdventureLog configuration from minimal Standard Deployment environment variables.
set -euo pipefail

SITE_URL="${SITE_URL:-http://localhost:8015}"
SITE_URL="${SITE_URL%/}"

export SITE_URL
export ORIGIN="${ORIGIN:-$SITE_URL}"
export FRONTEND_URL="${FRONTEND_URL:-$SITE_URL}"
export PUBLIC_URL="${PUBLIC_URL:-$SITE_URL}"
export CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-$SITE_URL}"
export PUBLIC_SERVER_URL="${PUBLIC_SERVER_URL:-http://127.0.0.1:8000}"
export BODY_SIZE_LIMIT="${BODY_SIZE_LIMIT:-100M}"
export DEBUG="${DEBUG:-False}"
export PORT=3000

export PGHOST="${PGHOST:-db}"
export POSTGRES_DB="${POSTGRES_DB:-database}"
export POSTGRES_USER="${POSTGRES_USER:-adventure}"
export PGDATABASE="${PGDATABASE:-$POSTGRES_DB}"
export PGUSER="${PGUSER:-$POSTGRES_USER}"

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
	echo "ERROR: POSTGRES_PASSWORD is required for Standard Deployment." >&2
	exit 1
fi
export PGPASSWORD="${POSTGRES_PASSWORD}"

if [[ -z "${SECRET_KEY:-}" ]]; then
	# Generate the key once and reuse it. A new key on every start logs everyone out and
	# stops API keys working. The media volume is the directory every deployment persists.
	secret_key_file="/code/media/.secret_key"
	if [[ -s "$secret_key_file" ]]; then
		SECRET_KEY="$(<"$secret_key_file")"
	else
		SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
		if ! (umask 077 && mkdir -p "$(dirname "$secret_key_file")" && printf '%s' "$SECRET_KEY" >"$secret_key_file") 2>/dev/null; then
			echo "WARNING: could not save a generated SECRET_KEY to $secret_key_file. Set SECRET_KEY to keep sessions and API keys across restarts." >&2
		fi
	fi
	export SECRET_KEY
fi

# nginx sits in front of SvelteKit and has its own body limit, so a BODY_SIZE_LIMIT above it
# was silently capped there ("client intended to send too large body"). Give nginx the same
# limit, parsed the way adapter-node parses it: bytes, or a K/M/G suffix in powers of 1024.
nginx_body_limit() {
	local value="$1"
	if [[ "$value" == "Infinity" ]]; then
		echo 0 # nginx: no limit
	elif [[ "$value" =~ ^([0-9]+(\.[0-9]+)?)([KkMmGg]?)$ ]]; then
		local number="${BASH_REMATCH[1]}" multiplier=1
		case "${BASH_REMATCH[3]}" in
			[Kk]) multiplier=1024 ;;
			[Mm]) multiplier=1048576 ;;
			[Gg]) multiplier=1073741824 ;;
		esac
		awk -v n="$number" -v m="$multiplier" 'BEGIN { b = n * m; c = int(b); if (b > c) c++; printf "%d\n", c }'
	else
		return 1
	fi
}

if nginx_limit="$(nginx_body_limit "$BODY_SIZE_LIMIT")"; then
	sed -i -E "s/^([[:space:]]*client_max_body_size)[[:space:]]+[^;]+;/\1 ${nginx_limit};/" /etc/nginx/nginx.conf
else
	echo "WARNING: BODY_SIZE_LIMIT='$BODY_SIZE_LIMIT' is not bytes, a K/M/G size or Infinity; nginx keeps its built-in upload limit." >&2
fi

export DJANGO_ADMIN_USERNAME="${DJANGO_ADMIN_USERNAME:-admin}"
# Empty means the first start generates a random password and prints it in the logs.
export DJANGO_ADMIN_PASSWORD="${DJANGO_ADMIN_PASSWORD:-}"
export DJANGO_ADMIN_EMAIL="${DJANGO_ADMIN_EMAIL:-admin@example.com}"

echo "Standard Deployment configuration:"
echo "  SITE_URL=$SITE_URL"
echo "  PUBLIC_SERVER_URL=$PUBLIC_SERVER_URL"
echo "  PGHOST=$PGHOST"
echo "  BODY_SIZE_LIMIT=$BODY_SIZE_LIMIT"
