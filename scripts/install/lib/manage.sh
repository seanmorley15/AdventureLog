#!/bin/bash
# Management mode for existing installs.
set -euo pipefail

enter_install_dir() {
	if [[ -d "$INSTALL_DIR" ]]; then
		cd "$INSTALL_DIR" || exit 1
	fi
	detect_setup_type_from_install "."
	resolve_compose_settings
	load_existing_env "$ENV_FILE"
}

mgmt_check_status() {
	local compose health_url
	compose="$(compose_args)"
	echo ""
	print_section "Container status"
	$compose ps 2>/dev/null || docker ps -a --filter "name=adventurelog"
	echo ""
	if [[ "$SETUP_TYPE" == "standard" ]]; then
		health_url="${SITE_URL:-http://localhost:8015}/health"
	else
		health_url="${FRONTEND_ORIGIN:-http://localhost:8015}/health"
	fi
	if curl -fsS -o /dev/null "$health_url" 2>/dev/null; then
		log_success "Health check passed — ${health_url}"
	else
		log_warning "Health check failed — ${health_url}"
	fi
	tui_press_enter
}

mgmt_update() {
	local backup_flag=""
	if tui_confirm "Create a backup before updating?" "y"; then
		backup_flag="--backup"
	fi
	if [[ -f scripts/deploy.sh ]]; then
		# shellcheck disable=SC2086
		COMPOSE_FILE="$COMPOSE_FILE" bash scripts/deploy.sh $backup_flag
	else
		local compose
		compose="$(compose_args)"
		tui_spinner "Pulling latest images" bash -c "$compose pull"
		tui_spinner "Restarting services" bash -c "$compose up -d --wait 2>/dev/null || $compose up -d"
	fi
	log_success "Update complete"
	tui_press_enter
}

mgmt_reconfigure() {
	log_info "Reconfigure site settings and optional features"
	if [[ -f "$ENV_FILE" ]]; then
		cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d-%H%M%S)"
	fi
	# shellcheck disable=SC2034
	OPTIONAL_ENV_LINES=()
	if [[ "$SETUP_TYPE" == "standard" ]]; then
		prompt_standard_core_config
		run_optional_features_wizard
		write_env_standard
	else
		prompt_advanced_core_config
		run_optional_features_wizard
		write_env_advanced
	fi
	validate_env_file
	if tui_confirm "Restart services to apply changes?" "y"; then
		local compose
		compose="$(compose_args)"
		$compose up -d --remove-orphans
	fi
	log_success "Configuration updated"
	tui_press_enter
}

mgmt_backup() {
	if [[ -f scripts/backup.sh ]]; then
		COMPOSE_FILE="$COMPOSE_FILE" bash scripts/backup.sh
	else
		log_error "scripts/backup.sh not found — run the installer from your install directory"
	fi
	tui_press_enter
}

mgmt_restore() {
	local backups dir choice labels=()
	if [[ ! -d backups ]]; then
		log_error "No backups/ directory found"
		tui_press_enter
		return
	fi
	mapfile -t backups < <(find backups -mindepth 1 -maxdepth 1 -type d | sort -r)
	if [[ ${#backups[@]} -eq 0 ]]; then
		log_error "No backups found in backups/"
		tui_press_enter
		return
	fi
	local i=1
	for dir in "${backups[@]}"; do
		labels+=("$(basename "$dir")")
		((i++)) || true
	done
	if ! choice="$(tui_choose "Select a backup to restore" "${labels[@]}")"; then
		tui_press_enter
		return
	fi
	for dir in "${backups[@]}"; do
		if [[ "$(basename "$dir")" == "$choice" ]]; then
			if tui_confirm "Restore from $dir? This overwrites current data." "n"; then
				COMPOSE_FILE="$COMPOSE_FILE" bash scripts/restore.sh "$dir"
			fi
			tui_press_enter
			return
		fi
	done
	log_error "Backup not found"
	tui_press_enter
}

mgmt_logs() {
	print_section "Recent logs (${LOG_CONTAINER})"
	if docker logs "$LOG_CONTAINER" --tail 50 2>/dev/null; then
		echo ""
		if tui_confirm "Follow logs live? (Ctrl+C to stop)" "n"; then
			docker logs "$LOG_CONTAINER" --follow
		fi
	else
		local compose
		compose="$(compose_args)"
		$compose logs --tail 50
	fi
}

mgmt_restart() {
	local compose
	compose="$(compose_args)"
	tui_spinner "Restarting services" bash -c "$compose restart"
	log_success "Services restarted"
	tui_press_enter
}

mgmt_uninstall() {
	if ! tui_confirm "Stop containers and remove volumes? This deletes all AdventureLog data." "n"; then
		return
	fi
	local compose
	compose="$(compose_args)"
	tui_spinner "Removing containers and volumes" bash -c "$compose down -v --remove-orphans"
	if tui_confirm "Also delete install directory $(pwd)?" "n"; then
		local install_path
		install_path="$(pwd)"
		cd .. || exit 1
		rm -rf "$install_path"
	fi
	log_success "AdventureLog has been uninstalled"
}

run_management_menu() {
	enter_install_dir
	print_screen "AdventureLog Manager — $(pwd)"
	log_muted "Setup: $SETUP_TYPE · Compose: $COMPOSE_FILE · Env: $ENV_FILE"
	echo ""
	while true; do
		local choice
		choice="$(tui_choose "What would you like to do?" \
			"Status & health check" \
			"Update to latest images" \
			"Edit configuration" \
			"Backup now" \
			"Restore from backup" \
			"View logs" \
			"Restart services" \
			"Uninstall" \
			"Exit")" || break
		case "$choice" in
			"Status & health check") mgmt_check_status ;;
			"Update to latest images") mgmt_update ;;
			"Edit configuration") mgmt_reconfigure ;;
			"Backup now") mgmt_backup ;;
			"Restore from backup") mgmt_restore ;;
			"View logs") mgmt_logs ;;
			"Restart services") mgmt_restart ;;
			"Uninstall") mgmt_uninstall; break ;;
			"Exit"|*) break ;;
		esac
		print_screen "AdventureLog Manager"
		log_muted "$(pwd) · $SETUP_TYPE"
		echo ""
	done
}
