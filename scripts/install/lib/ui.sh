#!/bin/bash
# UI helpers: colors, banners, logging, step headers.
set -euo pipefail

readonly RED=$'\033[0;31m'
readonly GREEN=$'\033[0;32m'
readonly YELLOW=$'\033[1;33m'
readonly BLUE=$'\033[0;34m'
readonly PURPLE=$'\033[0;35m'
readonly CYAN=$'\033[0;36m'
readonly MAGENTA=$'\033[0;35m'
readonly WHITE=$'\033[0;97m'
readonly BOLD=$'\033[1m'
readonly DIM=$'\033[2m'
readonly NC=$'\033[0m'

INSTALLER_VERSION="${INSTALLER_VERSION:-2.0.0}"
INSTALLER_DOCS="https://adventurelog.app/docs/install/quick_start"
INSTALLER_REPO="https://github.com/seanmorley15/AdventureLog"

log_info() { echo -e "  ${BLUE}●${NC}  $1"; }
log_success() { echo -e "  ${GREEN}✔${NC}  $1"; }
log_warning() { echo -e "  ${YELLOW}◆${NC}  $1"; }
log_error() { echo -e "  ${RED}✖${NC}  $1"; }
log_header() { echo -e "${PURPLE}${BOLD}$1${NC}"; }
log_muted() { echo -e "  ${DIM}$1${NC}"; }

print_banner() {
	if declare -f has_gum &>/dev/null && has_gum && [[ "${GUM_STYLE:-false}" == true ]]; then
		gum style \
			--border rounded \
			--border-foreground 212 \
			--align center \
			--width 58 \
			--padding "1 2" \
			--bold \
			"◆  ADVENTURELOG" \
			"" \
			"Installer v${INSTALLER_VERSION}" \
			"The ultimate travel companion" 2>/dev/null || print_banner_fallback
		return
	fi
	print_banner_fallback
}

print_banner_fallback() {
	cat << EOF
  ${CYAN}╭──────────────────────────────────────────────────────────╮${NC}
  ${CYAN}│${NC}  ${BOLD}${WHITE}◆  ADVENTURELOG${NC}                                      ${CYAN}│${NC}
  ${CYAN}│${NC}     ${DIM}Installer v${INSTALLER_VERSION}${NC}                                   ${CYAN}│${NC}
  ${CYAN}│${NC}     ${DIM}The ultimate travel companion${NC}                      ${CYAN}│${NC}
  ${CYAN}╰──────────────────────────────────────────────────────────╯${NC}
EOF
}

print_manager_banner() {
	if declare -f has_gum &>/dev/null && has_gum && [[ "${GUM_STYLE:-false}" == true ]]; then
		gum style \
			--border rounded \
			--border-foreground 212 \
			--align center \
			--width 58 \
			--padding "1 2" \
			--bold \
			"◆  ADVENTURELOG" \
			"" \
			"Management Console" 2>/dev/null || print_manager_banner_fallback
		return
	fi
	print_manager_banner_fallback
}

print_manager_banner_fallback() {
	cat << EOF
  ${CYAN}╭──────────────────────────────────────────────────────────╮${NC}
  ${CYAN}│${NC}  ${BOLD}${WHITE}◆  ADVENTURELOG${NC}                                      ${CYAN}│${NC}
  ${CYAN}│${NC}     ${DIM}Management Console${NC}                                   ${CYAN}│${NC}
  ${CYAN}╰──────────────────────────────────────────────────────────╯${NC}
EOF
}

print_footer() {
	echo ""
	if [[ "$GUM_STYLE" == true ]] && has_gum; then
		gum style --foreground 245 --align center \
			"${INSTALLER_DOCS}" 2>/dev/null || print_footer_fallback
	else
		print_footer_fallback
	fi
}

print_footer_fallback() {
	echo -e "  ${DIM}${INSTALLER_DOCS}${NC}"
}

print_screen() {
	local title="${1:-}"
	if [[ -t 1 ]] && [[ -n "${TERM:-}" ]] && [[ "$TERM" != "dumb" ]]; then
		clear 2>/dev/null || true
	fi
	echo ""
	if [[ "$title" == *"Manager"* ]]; then
		print_manager_banner
	else
		print_banner
	fi
	echo ""
	if [[ -n "$title" ]]; then
		log_header "$title"
		echo ""
	fi
}

print_welcome() {
	print_screen "Welcome"
	cat << EOF
  This wizard installs AdventureLog with Docker in a few minutes.

  ${BOLD}What happens next${NC}
    ${DIM}1.${NC} Verify Docker and system resources
    ${DIM}2.${NC} Choose Standard or Advanced Deployment
    ${DIM}3.${NC} Configure your site URL and admin account
    ${DIM}4.${NC} Optionally enable email, S3, integrations
    ${DIM}5.${NC} Deploy containers and wait for health check

EOF
	print_footer
	echo ""
}

print_step_header() {
	local step="$1"
	local total="$2"
	local label="$3"
	WIZARD_STEP="$step"
	WIZARD_TOTAL="$total"
	echo "" >&2
	if declare -f tui_progress_bar &>/dev/null; then
		tui_progress_bar "$step" "$total" "$label"
	else
		log_header "Step ${step}/${total}: ${label}"
		print_divider
		echo ""
	fi
}

print_divider() {
	echo -e "  ${DIM}$(printf '─%.0s' {1..56})${NC}"
}

print_section() {
	local title="$1"
	echo ""
	echo -e "  ${BOLD}${title}${NC}"
	print_divider
}

print_summary_row() {
	local key="$1"
	local value="$2"
	local width=20
	if [[ "${GUM_STYLE:-false}" == true ]] && has_gum; then
		gum join --horizontal \
			"$(gum style --width "$width" --foreground 245 "$key")" \
			"$(gum style --bold "$value")" 2>/dev/null || \
		printf "  ${DIM}%-${width}s${NC} ${BOLD}%s${NC}\n" "$key" "$value"
	else
		printf "  ${DIM}%-${width}s${NC} ${BOLD}%s${NC}\n" "$key" "$value"
	fi
}

print_success_banner() {
	echo ""
	if [[ "$GUM_STYLE" == true ]] && has_gum; then
		gum style \
			--border double \
			--border-foreground 82 \
			--align center \
			--width 58 \
			--padding "0 2" \
			--bold \
			--foreground 82 \
			"Ready for launch!" 2>/dev/null || print_success_banner_fallback
	else
		print_success_banner_fallback
	fi
	echo ""
}

print_success_banner_fallback() {
	cat << EOF
  ${GREEN}╭──────────────────────────────────────────────────────────╮${NC}
  ${GREEN}│${NC}              ${BOLD}${GREEN}Ready for launch!${NC}                        ${GREEN}│${NC}
  ${GREEN}╰──────────────────────────────────────────────────────────╯${NC}
EOF
}

print_next_steps() {
	local lines=("$@")
	echo ""
	print_section "Next steps"
	local line
	for line in "${lines[@]}"; do
		echo -e "  ${CYAN}→${NC}  $line"
	done
	echo ""
}

print_failure_message() {
	echo ""
	log_error "Installation did not complete."
	echo ""
	print_section "Troubleshooting"
	echo -e "  ${DIM}1.${NC} docker info"
	echo -e "  ${DIM}2.${NC} docker compose -f ${COMPOSE_FILE} ps"
	echo -e "  ${DIM}3.${NC} docker compose -f ${COMPOSE_FILE} logs"
	if [[ -f scripts/validate-env.sh ]]; then
		echo -e "  ${DIM}4.${NC} bash scripts/validate-env.sh ${ENV_FILE}"
	fi
	echo ""
	log_muted "Support: ${INSTALLER_REPO}/issues"
	echo ""
}
