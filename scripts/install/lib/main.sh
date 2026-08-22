#!/bin/bash
# Main install orchestration.
set -euo pipefail

WIZARD_TOTAL=7

choose_setup_type() {
	if [[ "${DRY_RUN:-false}" == true ]]; then
		SETUP_TYPE="standard"
		resolve_compose_settings
		return 0
	fi
	print_step_header 2 "$WIZARD_TOTAL" "Choose setup type"
	tui_print_box "Installation mode" \
		"Standard Deployment is recommended for homelabs and quick installs.\nAdvanced Deployment gives separate frontend and backend services."
	local choice
	if ! choice="$(tui_choose "Which setup do you want?" \
		"Standard Deployment — single URL, one port (recommended)" \
		"Advanced Deployment — separate frontend and backend")"; then
		choice="Standard Deployment — single URL, one port (recommended)"
	fi
	case "$choice" in
		Advanced*)
			SETUP_TYPE="advanced"
			;;
		*)
			SETUP_TYPE="standard"
			;;
	esac
	resolve_compose_settings
	log_success "Selected $( [[ "$SETUP_TYPE" == "standard" ]] && echo "Standard Deployment" || echo "Advanced Deployment" ) setup"
}

run_fresh_install() {
	init_tui
	print_welcome
	if [[ "${DRY_RUN:-false}" != true ]]; then
		tui_press_enter "Press Enter to begin"
	fi

	print_screen "Installing AdventureLog"
	run_preflight

	if [[ -z "${SETUP_TYPE:-}" ]] || [[ "$SETUP_TYPE" == "standard" && -z "${SITE_URL:-}" ]]; then
		choose_setup_type
	fi

	ensure_install_directory

	if [[ "$SETUP_TYPE" == "standard" ]]; then
		download_standard_toolkit
		run_standard_install_wizard
		write_env_standard
	else
		download_advanced_toolkit
		run_advanced_install_wizard
		write_env_advanced
	fi

	trap 'cleanup_on_failure; print_failure_message; exit 1' ERR
	run_deploy_phase
	save_credentials_file

	if [[ "$SETUP_TYPE" == "standard" ]]; then
		print_standard_success
	else
		print_advanced_success
	fi
}

run_installer_main() {
	if [[ "$FORCE_INSTALL" != true ]]; then
		if [[ -d "$INSTALL_DIR" ]] && detect_existing_install "$INSTALL_DIR"; then
			init_tui
			if [[ "${ADVENTURELOG_MANAGE:-}" == "1" ]] || tui_confirm "Existing AdventureLog install detected. Open the management console?" "y"; then
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
