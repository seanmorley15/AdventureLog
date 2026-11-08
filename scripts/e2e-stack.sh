#!/usr/bin/env bash
# Boots the production (AIO) image plus Postgres for the Playwright suite.
#
#   scripts/e2e-stack.sh up        build the image (unless E2E_SKIP_BUILD=1) and start the stack
#   scripts/e2e-stack.sh logs      follow the app logs
#   scripts/e2e-stack.sh down      stop the stack and delete its volumes
#
# Then run the tests:  cd frontend && pnpm test:e2e
#
# Uses its own compose project (adventurelog-e2e) and port, so it never touches a stack you
# run for development. Override with E2E_PORT / E2E_IMAGE.
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${E2E_PORT:-8015}"
IMAGE="${E2E_IMAGE:-adventurelog-e2e}"
WORKDIR=".e2e"
PROJECT="adventurelog-e2e"

mkdir -p "$WORKDIR"

write_files() {
	# Every setting the tests depend on is pinned here, so the suite behaves the same on a
	# laptop and in CI whatever defaults change later.
	printf '%s\n' 'POSTGRES_PASSWORD=e2e-test-pass' "SITE_URL=http://localhost:${PORT}" "HOST_PORT=${PORT}" \
		'DJANGO_ADMIN_USERNAME=admin' 'DJANGO_ADMIN_PASSWORD=admin' 'DJANGO_ADMIN_EMAIL=admin@example.com' \
		'ACCOUNT_EMAIL_VERIFICATION=none' 'DISABLE_REGISTRATION=False' 'ENABLE_RATE_LIMITS=False' \
		'ALLOW_PUBLIC_COLLECTION_LINKS=True' 'FORCE_SOCIALACCOUNT_LOGIN=False' \
		>"$WORKDIR/.env"
	cat >"$WORKDIR/override.yml" <<YML
services:
  app:
    image: ${IMAGE}
    pull_policy: never
    container_name: ${PROJECT}-app
    # Replace (not extend) the base file's env_file, so a developer's own .env is never read.
    env_file: !override
      - .e2e/.env
    environment:
      # Nothing in the suite needs world data, so skip the large first-boot geography import.
      SKIP_WORLD_DATA: "1"
  db:
    container_name: ${PROJECT}-db
YML
}

compose() {
	docker compose -p "$PROJECT" --env-file "$WORKDIR/.env" \
		-f docker-compose.yml -f "$WORKDIR/override.yml" "$@"
}

case "${1:-}" in
up)
	write_files
	if [[ "${E2E_SKIP_BUILD:-}" != "1" ]]; then
		docker build -f docker/Dockerfile --target aio -t "$IMAGE" .
	fi
	if ! compose up -d --wait; then
		compose ps || true
		compose logs || true
		exit 1
	fi
	echo "AdventureLog is up at http://localhost:${PORT}"
	;;
logs)
	write_files
	compose logs -f app
	;;
logs-dump)
	write_files
	compose logs --no-color
	;;
down)
	write_files
	compose down -v
	;;
*)
	sed -n '2,12p' "$0"
	exit 1
	;;
esac
