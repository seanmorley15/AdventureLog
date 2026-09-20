#!/usr/bin/env bash
# Run the Django test suite the same way CI does.
# Usage: ./scripts/test-backend.sh [extra manage.py test args...]
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

COMPOSE_FILE="docker/docker-compose.database.yml"
SERVER_DIR="backend/server"

export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5432}"
export PGDATABASE="${PGDATABASE:-database}"
export PGUSER="${PGUSER:-adventure}"
export PGPASSWORD="${PGPASSWORD:-changeme123}"
export SECRET_KEY="${SECRET_KEY:-ci-test-secret-key-not-for-production}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-main.settings_test}"
export DJANGO_ADMIN_USERNAME="${DJANGO_ADMIN_USERNAME:-admin}"
export DJANGO_ADMIN_PASSWORD="${DJANGO_ADMIN_PASSWORD:-admin}"
export DJANGO_ADMIN_EMAIL="${DJANGO_ADMIN_EMAIL:-admin@example.com}"
export PUBLIC_URL="${PUBLIC_URL:-http://localhost:8000}"
export CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-http://localhost:3000,http://localhost:8000}"
export DEBUG="${DEBUG:-True}"
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker is required to start PostGIS for tests" >&2
  exit 1
fi

if ! pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" >/dev/null 2>&1; then
  echo "Starting PostGIS via $COMPOSE_FILE ..."
  docker compose -f "$COMPOSE_FILE" up -d

  echo "Waiting for Postgres to become ready ..."
  for _ in $(seq 1 60); do
    if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "$PGUSER" -d "$PGDATABASE" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  if ! docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "$PGUSER" -d "$PGDATABASE" >/dev/null 2>&1; then
    echo "error: PostGIS did not become ready in time" >&2
    docker compose -f "$COMPOSE_FILE" logs db || true
    exit 1
  fi
else
  echo "Postgres already reachable at ${PGHOST}:${PGPORT}"
fi

cd "$SERVER_DIR"

if ! python3 -c "import django" >/dev/null 2>&1; then
  echo "Installing Python test dependencies (requirements-dev.txt) ..."
  python3 -m pip install -r requirements-dev.txt
fi

if ! python3 -c "import coverage" >/dev/null 2>&1; then
  echo "Installing coverage ..."
  python3 -m pip install 'coverage>=7.6.0,<8'
fi

echo "Running Django tests with coverage ..."
python3 -m coverage run --source='.' manage.py test --verbosity=2 "$@"
python3 -m coverage report --show-missing
python3 -m coverage xml

echo "Done. Coverage report: ${SERVER_DIR}/coverage.xml"
