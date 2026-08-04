#!/bin/bash
# Deploy the latest AdventureLog Docker images. Safe for cron/automation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
# shellcheck source=lib/compose-paths.sh
source "${SCRIPTS_DIR}/lib/compose-paths.sh"

COMPOSE_FILE="${COMPOSE_FILE:-}"
ENV_FILE=""
LOG_CONTAINER=""
FOLLOW_LOGS=false
DO_BACKUP=false

for arg in "$@"; do
	case "$arg" in
		--logs) FOLLOW_LOGS=true ;;
		--backup) DO_BACKUP=true ;;
	esac
done

if [[ -z "$COMPOSE_FILE" ]]; then
	COMPOSE_FILE="$(default_compose_file)"
fi

case "$COMPOSE_FILE" in
	*docker-compose.advanced.yml*)
		ENV_FILE=".env.advanced"
		LOG_CONTAINER="adventurelog-backend"
		;;
	*docker-compose.aio.yml*)
		ENV_FILE=".env.aio"
		LOG_CONTAINER="adventurelog"
		;;
	*)
		ENV_FILE=".env"
		LOG_CONTAINER="adventurelog"
		;;
esac

COMPOSE=(docker compose -f "$COMPOSE_FILE")
if [[ -f "$ENV_FILE" ]]; then
	COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
fi

if [[ -f "$ENV_FILE" ]] && [[ -f scripts/validate-env.sh ]]; then
	echo "Validating $ENV_FILE ..."
	bash scripts/validate-env.sh "$ENV_FILE"
fi

if [[ "$DO_BACKUP" == true ]]; then
	if [[ -f scripts/backup.sh ]]; then
		COMPOSE_FILE="$COMPOSE_FILE" bash scripts/backup.sh
	else
		echo "WARNING: scripts/backup.sh not found; skipping backup" >&2
	fi
fi

echo "Deploying latest version of AdventureLog ($COMPOSE_FILE)"
"${COMPOSE[@]}" pull
echo "Starting containers"
"${COMPOSE[@]}" up -d --wait 2>/dev/null || "${COMPOSE[@]}" up -d
echo "All set!"
"${COMPOSE[@]}" ps

if [[ "$FOLLOW_LOGS" == true ]]; then
	docker logs "$LOG_CONTAINER" --follow
fi
