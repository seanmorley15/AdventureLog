#!/bin/bash
# Optional feature configuration wizard modules.
set -euo pipefail

feature_section_header() {
	local name="$1"
	local doc_slug="$2"
	if declare -f tui_print_box &>/dev/null; then
		tui_print_box "Configure: ${name}" "Documentation: ${DOCS_BASE}/${doc_slug}.html"
	else
		echo ""
		log_header "Configure: $name"
		log_info "Docs: ${DOCS_BASE}/${doc_slug}.html"
		echo ""
	fi
}

configure_registration_auth() {
	feature_section_header "Registration & Auth" "disable_registration"
	if tui_confirm "Disable new user registration?" "n"; then
		append_env_line "DISABLE_REGISTRATION=True"
		local msg
		msg="$(tui_input "Registration disabled message (optional)" "Registration is disabled for this instance of AdventureLog.")"
		[[ -n "$msg" ]] && append_env_line "DISABLE_REGISTRATION_MESSAGE=${msg}"
	fi
	if tui_confirm "Allow social signup when registration is disabled?" "n"; then
		append_env_line "SOCIALACCOUNT_ALLOW_SIGNUP=True"
	fi
	log_warning "Social-only login: do not enable unless SSO is already configured."
	log_info "SSO can be set up after AdventureLog starts — Django admin → Social applications."
	if tui_confirm "Force social-only login (disable password login)?" "n"; then
		append_env_line "FORCE_SOCIALACCOUNT_LOGIN=True"
	fi
	if tui_confirm "Configure email verification for new accounts?" "n"; then
		local verify
		if ! verify="$(tui_choose "Email verification level" "optional" "mandatory")"; then
			verify="optional"
		fi
		append_env_line "ACCOUNT_EMAIL_VERIFICATION=${verify}"
	fi
}

configure_email() {
	feature_section_header "Email" "email"
	append_env_line "EMAIL_BACKEND=email"
	append_env_line "EMAIL_HOST=$(prompt_with_default "SMTP host" "smtp.gmail.com")"
	if tui_confirm "Use TLS?" "y"; then
		append_env_line "EMAIL_USE_TLS=True"
		append_env_line "EMAIL_PORT=587"
	else
		append_env_line "EMAIL_USE_TLS=False"
		append_env_line "EMAIL_USE_SSL=True"
		append_env_line "EMAIL_PORT=465"
	fi
	append_env_line "EMAIL_HOST_USER=$(prompt_with_default "SMTP username" "")"
	append_env_line "EMAIL_HOST_PASSWORD=$(tui_password "SMTP password")"
	append_env_line "DEFAULT_FROM_EMAIL=$(prompt_with_default "From email" "noreply@example.com")"
}

configure_s3() {
	feature_section_header "S3 Media Storage" "s3_storage"
	log_warning "Choose storage at install time — migrating later is difficult."
	append_env_line "MEDIA_STORAGE=s3"
	append_env_line "AWS_ACCESS_KEY_ID=$(prompt_with_default "AWS access key ID" "")"
	append_env_line "AWS_SECRET_ACCESS_KEY=$(tui_password "AWS secret access key")"
	append_env_line "AWS_STORAGE_BUCKET_NAME=$(prompt_with_default "Bucket name" "")"
	local endpoint
	endpoint="$(tui_input "S3 endpoint URL (empty for AWS)" "")"
	[[ -n "$endpoint" ]] && append_env_line "AWS_S3_ENDPOINT_URL=${endpoint}"
	append_env_line "AWS_S3_REGION_NAME=$(prompt_with_default "Region" "auto")"
	append_env_line "AWS_S3_ADDRESSING_STYLE=path"
	append_env_line "AWS_S3_SIGNATURE_VERSION=s3v4"
	local custom_domain
	custom_domain="$(tui_input "Custom CDN domain (optional)" "")"
	[[ -n "$custom_domain" ]] && append_env_line "AWS_S3_CUSTOM_DOMAIN=${custom_domain}"
}

configure_google_maps() {
	feature_section_header "Google Maps" "google_maps_integration"
	local key
	key="$(prompt_with_default "Google Maps API key" "")"
	[[ -n "$key" ]] && append_env_line "GOOGLE_MAPS_API_KEY=${key}"
}

configure_strava() {
	feature_section_header "Strava Integration" "strava_integration"
	append_env_line "STRAVA_CLIENT_ID=$(prompt_with_default "Strava client ID" "")"
	append_env_line "STRAVA_CLIENT_SECRET=$(tui_password "Strava client secret")"
}

configure_analytics() {
	feature_section_header "Umami Analytics" "analytics"
	append_env_line "PUBLIC_UMAMI_SRC=$(prompt_with_default "Umami script URL" "https://cloud.umami.is/script.js")"
	append_env_line "PUBLIC_UMAMI_WEBSITE_ID=$(prompt_with_default "Umami website ID" "")"
}

configure_performance() {
	feature_section_header "Performance & Rate Limits" "advanced_configuration"
	local workers
	workers="$(prompt_with_default "Gunicorn workers (1 for small hosts)" "2")"
	append_env_line "GUNICORN_WORKERS=${workers}"
	if tui_confirm "Enable rate limits (recommended for production)?" "n"; then
		append_env_line "ENABLE_RATE_LIMITS=True"
	fi
}

configure_debug() {
	feature_section_header "Debug mode" "advanced_configuration"
	if tui_confirm "Enable DEBUG mode? (not for production)" "n"; then
		append_env_line "DEBUG=True"
	fi
}

run_optional_features_wizard() {
	print_step_header 4 "$WIZARD_TOTAL" "Optional features"
	if [[ "${DRY_RUN:-false}" == true ]]; then
		log_info "[dry-run] Skipping optional features"
		return 0
	fi
	log_info "Configure optional integrations, or pick Done when finished."
	echo ""
	local groups=(
		"Registration & Auth"
		"Email"
		"S3 Media Storage"
		"Google Maps"
		"Strava"
		"Umami Analytics"
		"Performance"
		"Debug mode"
		"Done — continue"
	)
	local choice
	while true; do
		if ! choice="$(tui_choose "Optional features" "${groups[@]}")"; then
			break
		fi
		case "$choice" in
			"Registration & Auth") configure_registration_auth ;;
			"Email") configure_email ;;
			"S3 Media Storage") configure_s3 ;;
			"Google Maps") configure_google_maps ;;
			"Strava") configure_strava ;;
			"Umami Analytics") configure_analytics ;;
			"Performance") configure_performance ;;
			"Debug mode") configure_debug ;;
			"Done — continue"|*) break ;;
		esac
	done
	if [[ -n "$SKIP_WORLD_DATA" ]]; then
		append_env_line "SKIP_WORLD_DATA=1"
	fi
}
