#!/bin/bash
# Resolve Docker Compose file paths (supports docker/ layout and legacy locations).
COMPOSE_DIR="${COMPOSE_DIR:-docker}"

resolve_compose_file() {
	local filename="$1"
	if [[ -f "$filename" ]]; then
		printf '%s\n' "$filename"
	elif [[ -f "${COMPOSE_DIR}/${filename}" ]]; then
		printf '%s\n' "${COMPOSE_DIR}/${filename}"
	elif [[ -f "compose/${filename}" ]]; then
		printf '%s\n' "compose/${filename}"
	else
		printf '%s\n' "${COMPOSE_DIR}/${filename}"
	fi
}

default_compose_file() {
	local aio_file
	aio_file="$(resolve_compose_file "docker-compose.aio.yml")"
	if [[ -f .env.aio ]] && [[ ! -f .env ]]; then
		printf '%s\n' "$aio_file"
	elif [[ -f .env.aio ]] && [[ -f "$aio_file" ]] && [[ "${ADVENTURELOG_COMPOSE:-}" == "aio" ]]; then
		printf '%s\n' "$aio_file"
	else
		resolve_compose_file "docker-compose.yml"
	fi
}
