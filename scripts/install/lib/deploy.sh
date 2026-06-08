#!/bin/bash
# Deploy containers and wait for health.
set -euo pipefail

validate_env_file() {
	if [[ ! -f "scripts/validate-env.sh" ]]; then
		log_warning "validate-env.sh not found — skipping validation"
		return 0
	fi
	log_info "Validating $ENV_FILE ..."
	if ! bash scripts/validate-env.sh "$ENV_FILE"; then
		log_error "Environment validation failed"
		exit 1
	fi
	log_success "Environment validated"
}

print_pull_failure_help() {
	echo "" >&2
	log_error "Failed to pull Docker images."
	echo "" >&2
	echo "Common fixes:" >&2
	echo "  • Check your internet connection" >&2
	echo "  • If you see 'denied' from ghcr.io, wait a moment and retry" >&2
	echo "  • Try: docker login ghcr.io  (only if using a private registry token)" >&2
	echo "  • Manual pull: docker compose --env-file ${ENV_FILE} -f ${COMPOSE_FILE} pull" >&2
	echo "" >&2
	echo "To build from source instead, clone the full AdventureLog repo and run:" >&2
	echo "  docker compose -f docker/docker-compose.aio.yml build && docker compose -f docker/docker-compose.aio.yml up -d" >&2
	echo "" >&2
}

start_services() {
	if [[ "$DRY_RUN" == true ]]; then
		log_muted "[dry-run] Would pull images and start containers"
		return 0
	fi

	if ! tui_spinner "Pulling Docker images" run_compose pull; then
		print_pull_failure_help
		exit 1
	fi

	log_info "Starting containers — first boot may take a few minutes depending on available memory. Please wait."
	echo "" >&2

	if tui_spinner "Starting containers" run_compose up -d --remove-orphans --wait; then
		:
	elif tui_spinner "Starting containers" run_compose up -d --remove-orphans; then
		log_muted "Started without compose --wait support"
	else
		log_error "Failed to start containers"
		run_compose ps || true
		exit 1
	fi
	log_success "Containers are running"
}

wait_for_health() {
	local url="${1:-$SITE_URL}"
	local max_attempts="${2:-300}"
	local attempt=1
	local health_url="${url%/}/health"

	if [[ "$DRY_RUN" == true ]]; then
		log_info "[dry-run] Would wait for $health_url"
		return 0
	fi

	log_info "Waiting for AdventureLog (up to $((max_attempts / 6)) minutes on first boot)..."
	while (( attempt <= max_attempts )); do
		if curl -fsS -o /dev/null "$health_url" 2>/dev/null; then
			echo "" >&2
			log_success "Health check passed: $health_url"
			return 0
		fi
		local pct=$(( attempt * 100 / max_attempts ))
		local frame='⠋'
		case $(( attempt % 4 )) in
			1) frame='⠙' ;;
			2) frame='⠹' ;;
			3) frame='⠸' ;;
		esac
		printf "\r  ${CYAN}${frame}${NC}  Waiting for ${health_url} ${DIM}(${pct}%%)${NC}  " >&2
		sleep 2
		((attempt++)) || true
	done
	printf "\r\033[K" >&2
	log_warning "Health check timed out — service may still be starting (first boot imports world data)"
	run_compose ps || true
	log_info "Recent logs:"
	docker logs "$LOG_CONTAINER" --tail 30 2>&1 || true
}

cleanup_on_failure() {
	if [[ -f ".env.aio.backup" ]]; then
		mv .env.aio.backup .env.aio 2>/dev/null || true
	fi
	if [[ -f ".env.backup" ]]; then
		mv .env.backup .env 2>/dev/null || true
	fi
	if [[ "$DRY_RUN" != true ]] && command -v docker &>/dev/null; then
		run_compose down --remove-orphans 2>/dev/null || true
	fi
}

run_deploy_phase() {
	print_step_header 6 "$WIZARD_TOTAL" "Deploy containers"
	validate_env_file
	start_services
	print_step_header 7 "$WIZARD_TOTAL" "Health check"
	if [[ "$SETUP_TYPE" == "aio" ]]; then
		wait_for_health "$SITE_URL" 300
	else
		wait_for_health "$FRONTEND_ORIGIN" 300
	fi
}
