#!/bin/bash
# Restore AdventureLog from a backup created by scripts/backup.sh.
set -euo pipefail

if [[ $# -lt 1 ]]; then
	echo "Usage: $0 <backup-directory>" >&2
	echo "Example: $0 backups/20260101-120000" >&2
	exit 1
fi

BACKUP_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
# shellcheck source=lib/compose-paths.sh
source "${SCRIPTS_DIR}/lib/compose-paths.sh"

if [[ ! -d "$BACKUP_DIR" ]]; then
	echo "ERROR: Backup directory not found: $BACKUP_DIR" >&2
	exit 1
fi

COMPOSE_FILE="${COMPOSE_FILE:-}"
if [[ -z "$COMPOSE_FILE" ]]; then
	COMPOSE_FILE="$(default_compose_file)"
fi

ENV_FILE="${ENV_FILE:-}"
case "$COMPOSE_FILE" in
	*docker-compose.advanced.yml*)
		ENV_FILE="${ENV_FILE:-.env.advanced}"
		;;
	*docker-compose.aio.yml*)
		ENV_FILE="${ENV_FILE:-.env.aio}"
		;;
	*)
		ENV_FILE="${ENV_FILE:-.env}"
		;;
esac

if [[ -f "$ENV_FILE" ]]; then
	COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
else
	COMPOSE=(docker compose -f "$COMPOSE_FILE")
fi

resolve_compose_volume() {
	local suffix="$1"
	docker volume ls -q | grep "${suffix}$" | head -n 1
}

MEDIA_VOLUME="$(resolve_compose_volume "adventurelog_media")"
if [[ -z "$MEDIA_VOLUME" ]]; then
	MEDIA_VOLUME="$(resolve_compose_volume "media")"
fi

POSTGRES_USER="${POSTGRES_USER:-adventure}"
POSTGRES_DB="${POSTGRES_DB:-database}"

if [[ -f .env.advanced ]]; then
	# shellcheck disable=SC1090
	set -a
	source .env.advanced
	set +a
elif [[ -f .env ]]; then
	# shellcheck disable=SC1090
	set -a
	source .env
	set +a
elif [[ -f .env.aio ]]; then
	# shellcheck disable=SC1090
	set -a
	source .env.aio
	set +a
fi

echo "Stopping AdventureLog containers..."
"${COMPOSE[@]}" down

if [[ -f "$BACKUP_DIR/.env.advanced" ]]; then
	cp "$BACKUP_DIR/.env.advanced" .env.advanced
elif [[ -f "$BACKUP_DIR/.env" ]]; then
	cp "$BACKUP_DIR/.env" .env
elif [[ -f "$BACKUP_DIR/.env.aio" ]]; then
	cp "$BACKUP_DIR/.env.aio" .env.aio
fi

echo "Starting database..."
"${COMPOSE[@]}" up -d db
sleep 5

if [[ -f "$BACKUP_DIR/database.sql" ]]; then
	echo "Restoring database..."
	"${COMPOSE[@]}" exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	cat "$BACKUP_DIR/database.sql" | "${COMPOSE[@]}" exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
fi

if [[ -f "$BACKUP_DIR/media.tar.gz" ]]; then
	if [[ -z "$MEDIA_VOLUME" ]]; then
		echo "ERROR: media volume not found; cannot restore media" >&2
		exit 1
	fi
	echo "Restoring media volume..."
	docker run --rm \
		-v "${MEDIA_VOLUME}:/data" \
		-v "$(realpath "$BACKUP_DIR"):/backup:ro" \
		alpine:3.21 \
		sh -c "rm -rf /data/* && tar xzf /backup/media.tar.gz -C /data"
fi

echo "Starting AdventureLog..."
"${COMPOSE[@]}" up -d

echo "Restore complete."
