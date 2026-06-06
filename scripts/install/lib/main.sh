#!/bin/bash
# Main install orchestration.
set -euo pipefail

choose_setup_type() {
	if [[ "${DRY_RUN:-false}" == true ]]; then
		SETUP_TYPE="aio"
		resolve_compose_settings
		return 0
	fi
	print_step_header 2 7 "Choose setup type"
	local choice
	if ! choice="$(tui_choose "Select installation type" \
		"All-in-One (recommended — single URL, minimal config)" \
		"Standard (advanced — separate frontend and backend)")"; then
		choice="All-in-One (recommended — single URL, minimal config)"
	fi
	case "$choice" in
		Standard*)
			SETUP_TYPE="standard"
			;;
		*)
			SETUP_TYPE="aio"
			;;
	esac
	resolve_compose_settings
	log_info "Selected: $SETUP_TYPE"
}

run_fresh_install() {
	print_screen "Starting installation — $(date)"
	init_tui
	run_preflight

	if [[ -z "${SETUP_TYPE:-}" ]] || [[ "$SETUP_TYPE" == "aio" && -z "${SITE_URL:-}" ]]; then
		choose_setup_type
	fi

	ensure_install_directory

	if [[ "$SETUP_TYPE" == "aio" ]]; then
		download_aio_toolkit
		run_aio_install_wizard
		write_env_aio
	else
		download_standard_toolkit
		run_standard_install_wizard
		write_env_standard
	fi

	trap 'cleanup_on_failure; print_failure_message; exit 1' ERR
	run_deploy_phase
	save_credentials_file

	if [[ "$SETUP_TYPE" == "aio" ]]; then
		print_aio_success
	else
		print_standard_success
	fi
}

run_installer_main() {
	if [[ "$FORCE_INSTALL" != true ]]; then
		if [[ -d "$INSTALL_DIR" ]] && detect_existing_install "$INSTALL_DIR"; then
			init_tui
			if [[ "${ADVENTURELOG_MANAGE:-}" == "1" ]] || tui_confirm "Existing AdventureLog install detected. Open management menu?" "y"; then
				INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
				run_management_menu
				return 0
			fi
		fi
		if [[ "${ADVENTURELOG_MANAGE:-}" == "1" ]]; then
			init_tui
			run_management_menu
			return 0
		fi
	fi

	run_fresh_install
}
