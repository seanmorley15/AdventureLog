#!/bin/bash
# Resolve Docker Compose file paths (root docker-compose.yml, docker/ variants, legacy locations).
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
	local standard_file advanced_file legacy_file
	standard_file="$(resolve_compose_file "docker-compose.yml")"
	advanced_file="$(resolve_compose_file "docker-compose.advanced.yml")"
	legacy_file="$(resolve_compose_file "docker-compose.aio.yml")"

	if [[ -f .env.advanced ]] && [[ "${ADVENTURELOG_COMPOSE:-}" == "advanced" ]]; then
		printf '%s\n' "$advanced_file"
		return
	fi

	if [[ -f .env.advanced ]] && [[ ! -f .env ]] && [[ ! -f .env.aio ]]; then
		printf '%s\n' "$advanced_file"
		return
	fi

	if [[ -f .env.aio ]] && [[ ! -f .env ]]; then
		if [[ -f "$legacy_file" ]]; then
			printf '%s\n' "$legacy_file"
		else
			printf '%s\n' "$standard_file"
		fi
		return
	fi

	if [[ -f .env.aio ]] && [[ -f "$legacy_file" ]] && [[ "${ADVENTURELOG_COMPOSE:-}" =~ ^(aio|standard)$ ]]; then
		printf '%s\n' "$legacy_file"
		return
	fi

	printf '%s\n' "$standard_file"
}
