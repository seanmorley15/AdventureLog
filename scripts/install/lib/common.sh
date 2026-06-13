#!/bin/bash
# Shared globals and utilities for AdventureLog installer.
set -euo pipefail

_COMPOSE_PATHS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/compose-paths.sh"
if [[ -f "$_COMPOSE_PATHS" ]]; then
	# shellcheck source=../../lib/compose-paths.sh
	source "$_COMPOSE_PATHS"
fi

APP_NAME="AdventureLog"
INSTALL_DIR="${INSTALL_DIR:-./adventurelog}"
INSTALLER_VERSION="${INSTALLER_VERSION:-2.0.0}"
ADVENTURELOG_REF="${ADVENTURELOG_REF:-main}"
GITHUB_RAW="https://raw.githubusercontent.com/seanmorley15/AdventureLog/${ADVENTURELOG_REF}"
DOCS_BASE="https://adventurelog.app/docs/configuration"

# Setup type: standard | advanced
SETUP_TYPE="${SETUP_TYPE:-standard}"
DRY_RUN="${DRY_RUN:-false}"
FORCE_INSTALL="${FORCE_INSTALL:-false}"

# Standard Deployment configuration
declare -g SITE_URL=""
declare -g HOST_PORT=""
declare -g POSTGRES_PASSWORD=""
declare -g DJANGO_ADMIN_USERNAME="admin"
declare -g DJANGO_ADMIN_PASSWORD=""
declare -g DJANGO_ADMIN_EMAIL="admin@example.com"
declare -g SKIP_WORLD_DATA=""

# Advanced Deployment configuration
declare -g FRONTEND_ORIGIN=""
declare -g BACKEND_URL=""
declare -g FRONTEND_PORT=""
declare -g BACKEND_PORT=""

# Platform
declare -g SYSTEM_ARCH=""
declare -g POSTGIS_IMAGE=""
declare -g USE_ARM_POSTGIS=false

# Wizard state
declare -g WIZARD_STEP=0
declare -g WIZARD_TOTAL=7
declare -g REPO_ROOT="${REPO_ROOT:-}"

# Compose
declare -g COMPOSE_FILE=""
declare -g ENV_FILE=""
declare -g LOG_CONTAINER=""

resolve_compose_settings() {
	if [[ "$SETUP_TYPE" == "standard" ]]; then
		COMPOSE_FILE="$(resolve_compose_file "docker-compose.yml")"
		ENV_FILE=".env"
		LOG_CONTAINER="adventurelog"
	else
		COMPOSE_FILE="$(resolve_compose_file "docker-compose.advanced.yml")"
		ENV_FILE=".env.advanced"
		LOG_CONTAINER="adventurelog-backend"
	fi
}

generate_secure_password() {
	local length=${1:-24}
	if [[ ! -r "/dev/urandom" ]]; then
		echo "ERROR: /dev/urandom not readable" >&2
		return 1
	fi
	if command -v tr &>/dev/null; then
		LC_ALL=C tr -dc 'A-Za-z0-9!#$%&*+-=?@^_' </dev/urandom 2>/dev/null | head -c "$length" 2>/dev/null
		return 0
	fi
	if command -v openssl &>/dev/null; then
		openssl rand -base64 32 | tr -d "=+/" | cut -c1-"$length"
		return 0
	fi
	echo "ERROR: No suitable random generation method found" >&2
	return 1
}

validate_url() {
	local url="$1"
	[[ $url =~ ^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$ ]]
}

extract_port_from_url() {
	local url="$1"
	local default_port="$2"
	if [[ $url =~ :([0-9]+)(/|$) ]]; then
		echo "${BASH_REMATCH[1]}"
	elif [[ $url =~ ^https:// ]]; then
		echo "443"
	elif [[ $url =~ ^http:// ]]; then
		echo "${default_port:-80}"
	else
		echo "$default_port"
	fi
}

get_compose_cmd() {
	if docker compose version &>/dev/null 2>&1; then
		echo "docker compose"
	else
		echo "docker-compose"
	fi
}

format_env_value() {
	local val="$1"
	if [[ "$val" =~ ^[A-Za-z0-9_.,/@^+-]+$ ]]; then
		printf '%s' "$val"
	else
		local escaped="${val//\\/\\\\}"
		escaped="${escaped//\"/\\\"}"
		printf '"%s"' "$escaped"
	fi
}

compose_args() {
	local cmd
	cmd="$(get_compose_cmd)"
	if [[ -f "$ENV_FILE" ]]; then
		# shellcheck disable=SC2086
		echo $cmd --env-file "$ENV_FILE" -f "$COMPOSE_FILE"
	else
		# shellcheck disable=SC2086
		echo $cmd -f "$COMPOSE_FILE"
	fi
}

run_compose() {
	local cmd
	cmd="$(get_compose_cmd)"
	if [[ -f "$ENV_FILE" ]]; then
		# shellcheck disable=SC2086
		$cmd --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
	else
		# shellcheck disable=SC2086
		$cmd -f "$COMPOSE_FILE" "$@"
	fi
}

detect_install_lib_dir() {
	local script_path="${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}"
	local candidate
	if [[ -n "${INSTALLER_LIB_DIR:-}" && -f "${INSTALLER_LIB_DIR}/ui.sh" ]]; then
		echo "$INSTALLER_LIB_DIR"
		return 0
	fi
	candidate="$(cd "$(dirname "$script_path")" && pwd)"
	if [[ -f "$candidate/ui.sh" ]]; then
		echo "$candidate"
		return 0
	fi
	candidate="$(cd "$(dirname "$script_path")/../.." && pwd)/scripts/install/lib"
	if [[ -f "$candidate/ui.sh" ]]; then
		echo "$candidate"
		return 0
	fi
	return 1
}

append_env_line() {
	local line="$1"
	local key="${line%%=*}"
	local value="${line#*=}"
	if [[ "$key" != "$line" ]]; then
		OPTIONAL_ENV_LINES+=("${key}=$(format_env_value "$value")")
	else
		OPTIONAL_ENV_LINES+=("$line")
	fi
}

save_optional_env_to_file() {
	local target="$1"
	local count=0
	[[ -v OPTIONAL_ENV_LINES ]] && count="${#OPTIONAL_ENV_LINES[@]}"
	if (( count == 0 )); then
		return 0
	fi
	{
		echo ""
		echo "# Optional features configured by AdventureLog installer"
		for line in "${OPTIONAL_ENV_LINES[@]}"; do
			echo "$line"
		done
	} >> "$target"
}

load_existing_env() {
	local file="$1"
	if [[ ! -f "$file" ]]; then
		return 0
	fi
	# shellcheck disable=SC1090
	set -a
	source "$file"
	set +a
	SITE_URL="${SITE_URL:-}"
	HOST_PORT="${HOST_PORT:-}"
	POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
	DJANGO_ADMIN_USERNAME="${DJANGO_ADMIN_USERNAME:-admin}"
	DJANGO_ADMIN_PASSWORD="${DJANGO_ADMIN_PASSWORD:-admin}"
	DJANGO_ADMIN_EMAIL="${DJANGO_ADMIN_EMAIL:-admin@example.com}"
}
