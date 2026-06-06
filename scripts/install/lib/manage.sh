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
	log_header "Status"
	$compose ps 2>/dev/null || docker ps -a --filter "name=adventurelog"
	echo ""
	if [[ "$SETUP_TYPE" == "aio" ]]; then
		health_url="${SITE_URL:-http://localhost:8015}/health"
	else
		health_url="${FRONTEND_ORIGIN:-http://localhost:8015}/health"
	fi
	if curl -fsS -o /dev/null "$health_url" 2>/dev/null; then
		log_success "Health OK: $health_url"
	else
		log_warning "Health check failed: $health_url"
	fi
	tui_press_enter
}

mgmt_update() {
	local backup_flag=""
	if tui_confirm "Create backup before update?" "y"; then
		backup_flag="--backup"
	fi
	if [[ -f deploy.sh ]]; then
		# shellcheck disable=SC2086
		COMPOSE_FILE="$COMPOSE_FILE" bash deploy.sh $backup_flag
	else
		local compose
		compose="$(compose_args)"
		$compose pull
		$compose up -d --wait 2>/dev/null || $compose up -d
	fi
	log_success "Update complete"
	tui_press_enter
}

mgmt_reconfigure() {
	log_info "Reconfigure optional features and core settings"
	if [[ -f "$ENV_FILE" ]]; then
		cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d-%H%M%S)"
	fi
	OPTIONAL_ENV_LINES=()
	if [[ "$SETUP_TYPE" == "aio" ]]; then
		prompt_aio_core_config
		run_optional_features_wizard
		write_env_aio
	else
		prompt_standard_core_config
		run_optional_features_wizard
		write_env_standard
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
		log_error "scripts/backup.sh not found"
	fi
	tui_press_enter
}

mgmt_restore() {
	local backups dir choice
	if [[ ! -d backups ]]; then
		log_error "No backups/ directory found"
		tui_press_enter
		return
	fi
	mapfile -t backups < <(find backups -mindepth 1 -maxdepth 1 -type d | sort -r)
	if [[ ${#backups[@]} -eq 0 ]]; then
		log_error "No backups found"
		tui_press_enter
		return
	fi
	echo "Available backups:"
	local i=1
	for dir in "${backups[@]}"; do
		echo "  [$i] $dir"
		((i++)) || true
	done
	read -r -p "Select backup number: " choice
	if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#backups[@]} )); then
		dir="${backups[$((choice - 1))]}"
		if tui_confirm "Restore from $dir? This will overwrite current data." "n"; then
			COMPOSE_FILE="$COMPOSE_FILE" bash scripts/restore.sh "$dir"
		fi
	else
		log_error "Invalid selection"
	fi
	tui_press_enter
}

mgmt_logs() {
	if docker logs "$LOG_CONTAINER" --tail 50 2>/dev/null; then
		echo ""
		if tui_confirm "Follow logs (Ctrl+C to stop)?" "n"; then
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
	$compose restart
	log_success "Services restarted"
	tui_press_enter
}

mgmt_uninstall() {
	if ! tui_confirm "Stop containers and remove volumes? This deletes all data." "n"; then
		return
	fi
	local compose
	compose="$(compose_args)"
	$compose down -v --remove-orphans
	if tui_confirm "Also delete install directory $(pwd)?" "n"; then
		local install_path
		install_path="$(pwd)"
		cd .. || exit 1
		rm -rf "$install_path"
	fi
	log_success "Uninstalled"
}

run_management_menu() {
	enter_install_dir
	print_screen "AdventureLog Manager — $(pwd)"
	log_info "Setup: $SETUP_TYPE | Compose: $COMPOSE_FILE"
	echo ""
	while true; do
		local choice
		choice="$(tui_choose "What would you like to do?" \
			"Check status & health" \
			"Update to latest images" \
			"Edit configuration" \
			"Backup now" \
			"Restore from backup" \
			"View logs" \
			"Restart services" \
			"Uninstall" \
			"Exit")" || break
		case "$choice" in
			"Check status & health") mgmt_check_status ;;
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
	done
}
