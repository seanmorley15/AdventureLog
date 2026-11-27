#!/usr/bin/env bash
# Idempotent app bootstrap: memcached, database migrations, first-boot admin user.
# Works in the dev container (env provided by docker-compose.yml) and on the host
# (env from backend/server/.env). Reuses the production entrypoint helpers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=../docker/shared/entrypoint-common.sh
source "$ROOT/docker/shared/entrypoint-common.sh"

start_memcached() {
	if pgrep -x memcached >/dev/null 2>&1; then
		return 0
	fi
	if ! command -v memcached >/dev/null 2>&1; then
		>&2 echo "WARNING: memcached is not installed; Django's cache will be unavailable."
		return 0
	fi
	local user_args=()
	if [[ "$(id -u)" -eq 0 ]]; then
		user_args=(-u nobody)
	fi
	memcached -d -m 64 -p 11211 -l 127.0.0.1 "${user_args[@]}"
	>&2 echo "memcached started on 127.0.0.1:11211"
}

# The frontend reads PUBLIC_SERVER_URL from frontend/.env when launched from VS Code.
seed_frontend_env() {
	if [[ ! -f "$ROOT/frontend/.env" && -f "$ROOT/frontend/.env.example" ]]; then
		cp "$ROOT/frontend/.env.example" "$ROOT/frontend/.env"
		>&2 echo "Created frontend/.env from frontend/.env.example"
	fi
}

start_memcached
seed_frontend_env

cd "$ROOT/backend/server"
if command -v psql >/dev/null 2>&1; then
	wait_for_postgres
else
	>&2 echo "WARNING: psql not found; skipping the PostgreSQL readiness check."
fi
run_migrations
create_superuser_if_needed

>&2 echo "Bootstrap complete. World data is not imported automatically; run the"
>&2 echo "'Backend: download world data' task if you need countries/regions."
