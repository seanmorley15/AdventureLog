#!/usr/bin/env bash
# One-time (and idempotent) dependency setup for the dev container.
# Run automatically by devcontainer.json; also used by the "Devcontainer: setup" task.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Named volumes are created root-owned; hand them to the current user.
for dir in "$ROOT/frontend/node_modules" "$HOME/.pnpm-store"; do
	if [[ -d "$dir" && ! -w "$dir" ]]; then
		sudo chown -R "$(id -u):$(id -g)" "$dir"
	fi
done

echo "==> Installing backend dependencies"
pip install --disable-pip-version-check -r "$ROOT/backend/server/requirements.txt"

echo "==> Installing frontend dependencies"
cd "$ROOT/frontend"
pnpm config set store-dir "$HOME/.pnpm-store"
CI=true pnpm install --frozen-lockfile

echo "==> Done. Press F5 and pick 'AdventureLog: Full Stack' to run and debug everything."
