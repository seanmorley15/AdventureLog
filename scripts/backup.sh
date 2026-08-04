#!/bin/bash
# Backup AdventureLog database, media volume, and environment file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
# shellcheck source=lib/compose-paths.sh
source "${SCRIPTS_DIR}/lib/compose-paths.sh"

COMPOSE_FILE="${COMPOSE_FILE:-}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

if [[ -z "$COMPOSE_FILE" ]]; then
	COMPOSE_FILE="$(default_compose_file)"
fi

case "$COMPOSE_FILE" in
	*docker-compose.advanced.yml*)
		ENV_FILE=".env.advanced"
		;;
	*docker-compose.aio.yml*)
		ENV_FILE=".env.aio"
		;;
	*)
		ENV_FILE=".env"
		;;
esac

COMPOSE=(docker compose -f "$COMPOSE_FILE")
if [[ -f "$ENV_FILE" ]]; then
	COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
fi
DEST="$BACKUP_DIR/$TIMESTAMP"
mkdir -p "$DEST"

resolve_compose_volume() {
	local suffix="$1"
	docker volume ls -q | grep "${suffix}$" | head -n 1
}

MEDIA_VOLUME="$(resolve_compose_volume "adventurelog_media")"
if [[ -z "$MEDIA_VOLUME" ]]; then
	MEDIA_VOLUME="$(resolve_compose_volume "media")"
fi

echo "Backing up AdventureLog to $DEST"

if [[ -f "$ENV_FILE" ]]; then
	cp "$ENV_FILE" "$DEST/"
fi

POSTGRES_USER="${POSTGRES_USER:-adventure}"
POSTGRES_DB="${POSTGRES_DB:-database}"

if [[ -f "$ENV_FILE" ]]; then
	# shellcheck disable=SC1090
	set -a
	source "$ENV_FILE"
	set +a
fi

echo "Dumping database..."
"${COMPOSE[@]}" exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$DEST/database.sql"

echo "Archiving media volume..."
if [[ -z "$MEDIA_VOLUME" ]]; then
	echo "WARNING: media volume not found; skipping media backup" >&2
else
	docker run --rm \
		-v "${MEDIA_VOLUME}:/data:ro" \
		-v "$(cd "$DEST" && pwd):/backup" \
		alpine:3.21 \
		tar czf /backup/media.tar.gz -C /data .
fi

echo "Backup complete: $DEST"
