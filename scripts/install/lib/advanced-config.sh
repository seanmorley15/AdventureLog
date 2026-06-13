#!/bin/bash
# Advanced Deployment multi-container configuration wizard.
set -euo pipefail

prompt_advanced_core_config() {
	print_step_header 3 "$WIZARD_TOTAL" "Core configuration"
	tui_print_box "Advanced Deployment" "Separate frontend and backend URLs — best for reverse proxies and split deployments."

	local default_frontend="http://localhost:8015"
	while true; do
		FRONTEND_ORIGIN="$(prompt_with_default "Frontend URL" "$default_frontend")"
		if validate_url "$FRONTEND_ORIGIN"; then
			FRONTEND_PORT="$(extract_port_from_url "$FRONTEND_ORIGIN" "8015")"
			break
		fi
		log_error "Invalid frontend URL"
	done

	local default_backend="http://localhost:8016"
	while true; do
		BACKEND_URL="$(prompt_with_default "Backend URL" "$default_backend")"
		if validate_url "$BACKEND_URL"; then
			BACKEND_PORT="$(extract_port_from_url "$BACKEND_URL" "8016")"
			break
		fi
		log_error "Invalid backend URL"
	done

	POSTGRES_PASSWORD="$(generate_secure_password 32)"
	if tui_confirm "Change default admin credentials (admin/admin)?" "y"; then
		DJANGO_ADMIN_USERNAME="$(prompt_with_default "Admin username" "admin")"
		DJANGO_ADMIN_PASSWORD="$(generate_secure_password 24)"
		DJANGO_ADMIN_EMAIL="$(prompt_with_default "Admin email" "admin@example.com")"
	else
		DJANGO_ADMIN_USERNAME="admin"
		DJANGO_ADMIN_PASSWORD="admin"
		DJANGO_ADMIN_EMAIL="admin@example.com"
	fi
	log_success "Frontend: $FRONTEND_ORIGIN  Backend: $BACKEND_URL"
	echo ""
}

write_env_advanced() {
	local target="$ENV_FILE"
	local secret_key
	secret_key="$(generate_secure_password 50)"
	if [[ -f .env.advanced.example ]]; then
		cp .env.advanced.example "$target"
		local tmp="${target}.tmp"
		while IFS= read -r line || [[ -n "$line" ]]; do
			case "$line" in
				POSTGRES_PASSWORD=*) echo "POSTGRES_PASSWORD=$(format_env_value "$POSTGRES_PASSWORD")" ;;
				DJANGO_ADMIN_PASSWORD=*) echo "DJANGO_ADMIN_PASSWORD=$(format_env_value "$DJANGO_ADMIN_PASSWORD")" ;;
				DJANGO_ADMIN_USERNAME=*) echo "DJANGO_ADMIN_USERNAME=$(format_env_value "$DJANGO_ADMIN_USERNAME")" ;;
				DJANGO_ADMIN_EMAIL=*) echo "DJANGO_ADMIN_EMAIL=$(format_env_value "$DJANGO_ADMIN_EMAIL")" ;;
				SECRET_KEY=*) echo "SECRET_KEY=$(format_env_value "$secret_key")" ;;
				ORIGIN=*) echo "ORIGIN=$(format_env_value "$FRONTEND_ORIGIN")" ;;
				PUBLIC_URL=*) echo "PUBLIC_URL=$(format_env_value "$BACKEND_URL")" ;;
				CSRF_TRUSTED_ORIGINS=*) echo "CSRF_TRUSTED_ORIGINS=$(format_env_value "${FRONTEND_ORIGIN},${BACKEND_URL}")" ;;
				FRONTEND_URL=*) echo "FRONTEND_URL=$(format_env_value "$FRONTEND_ORIGIN")" ;;
				FRONTEND_PORT=*) echo "FRONTEND_PORT=$(format_env_value "$FRONTEND_PORT")" ;;
				BACKEND_PORT=*) echo "BACKEND_PORT=$(format_env_value "$BACKEND_PORT")" ;;
				*) echo "$line" ;;
			esac
		done < "$target" > "$tmp"
		mv "$tmp" "$target"
	else
		{
			echo "PUBLIC_SERVER_URL=http://server:8000"
			echo "ORIGIN=$(format_env_value "$FRONTEND_ORIGIN")"
			echo "BODY_SIZE_LIMIT=Infinity"
			echo "FRONTEND_PORT=$(format_env_value "$FRONTEND_PORT")"
			echo "PGHOST=db"
			echo "POSTGRES_DB=database"
			echo "POSTGRES_USER=adventure"
			echo "POSTGRES_PASSWORD=$(format_env_value "$POSTGRES_PASSWORD")"
			echo "SECRET_KEY=$(format_env_value "$secret_key")"
			echo "DJANGO_ADMIN_USERNAME=$(format_env_value "$DJANGO_ADMIN_USERNAME")"
			echo "DJANGO_ADMIN_PASSWORD=$(format_env_value "$DJANGO_ADMIN_PASSWORD")"
			echo "DJANGO_ADMIN_EMAIL=$(format_env_value "$DJANGO_ADMIN_EMAIL")"
			echo "PUBLIC_URL=$(format_env_value "$BACKEND_URL")"
			echo "CSRF_TRUSTED_ORIGINS=$(format_env_value "${FRONTEND_ORIGIN},${BACKEND_URL}")"
			echo "DEBUG=False"
			echo "FRONTEND_URL=$(format_env_value "$FRONTEND_ORIGIN")"
			echo "BACKEND_PORT=$(format_env_value "$BACKEND_PORT")"
		} > "$target"
	fi
	save_optional_env_to_file "$target"
	log_success "Wrote $target"
}

show_advanced_review() {
	print_step_header 5 "$WIZARD_TOTAL" "Review & confirm"
	print_section "Configuration summary"
	print_summary_row "Setup" "Advanced Deployment"
	print_summary_row "Frontend" "$FRONTEND_ORIGIN"
	print_summary_row "Backend" "$BACKEND_URL"
	print_summary_row "PostGIS image" "$POSTGIS_IMAGE"
	echo ""
	tui_confirm "Proceed with installation?" "y" || exit 0
}

print_advanced_success() {
	print_success_banner
	log_success "AdventureLog is installed and ready."
	echo ""
	print_section "Your instance"
	print_summary_row "Frontend" "$FRONTEND_ORIGIN"
	print_summary_row "Backend" "$BACKEND_URL"
	print_summary_row "Admin user" "$DJANGO_ADMIN_USERNAME"
	print_summary_row "Admin password" "$DJANGO_ADMIN_PASSWORD"
	echo ""
	print_next_steps \
		"Open ${FRONTEND_ORIGIN} in your browser" \
		"Update images: bash scripts/deploy.sh --backup" \
		"Re-run the installer for the management console"
	print_footer
}

run_advanced_install_wizard() {
	SETUP_TYPE="advanced"
	resolve_compose_settings
	prompt_advanced_core_config
	run_port_checks
	run_optional_features_wizard
	write_postgis_override
	show_advanced_review
}
