#!/bin/bash
# UI helpers: colors, banners, logging, step headers.
set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ  $1${NC}"; }
log_success() { echo -e "${GREEN}✔  $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠  $1${NC}"; }
log_error() { echo -e "${RED}✖  $1${NC}"; }
log_header() { echo -e "${PURPLE}${BOLD}$1${NC}"; }

print_banner() {
	if declare -f has_gum &>/dev/null && has_gum && [[ "${GUM_STYLE:-false}" == true ]]; then
		gum style \
			--border double \
			--border-foreground 212 \
			--align center \
			--width 65 \
			--padding "1 2" \
			--bold \
			"ADVENTURELOG" \
			"" \
			"Installer & Manager" \
			"The Ultimate Travel Companion" 2>/dev/null || print_banner_fallback
		return
	fi
	print_banner_fallback
}

print_banner_fallback() {
	cat << 'EOF'
╔═════════════════════════════════════════════════════════════════════════╗
║                                                                         ║
║             A D V E N T U R E L O G   I N S T A L L E R                 ║
║                                                                         ║
║                    The Ultimate Travel Companion                        ║
╚═════════════════════════════════════════════════════════════════════════╝
EOF
}

print_manager_banner() {
	cat << 'EOF'
╔═════════════════════════════════════════════════════════════════════════╗
║                                                                         ║
║             A D V E N T U R E L O G   M A N A G E R                     ║
║                                                                         ║
╚═════════════════════════════════════════════════════════════════════════╝
EOF
}

print_screen() {
	local title="${1:-}"
	if [[ -t 1 ]] && [[ -n "${TERM:-}" ]] && [[ "$TERM" != "dumb" ]]; then
		clear 2>/dev/null || true
	fi
	echo ""
	print_banner
	echo ""
	if [[ -n "$title" ]]; then
		log_header "$title"
		echo ""
	fi
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
		echo -e "${DIM}$(printf '─%.0s' {1..60})${NC}"
		echo ""
	fi
}

print_divider() {
	echo -e "${DIM}$(printf '─%.0s' {1..60})${NC}"
}

print_summary_row() {
	local key="$1"
	local value="$2"
	if [[ "${GUM_STYLE:-false}" == true ]] && has_gum; then
		gum join --horizontal \
			"$(gum style --width 22 --bold "$key")" \
			"$(gum style "$value")" 2>/dev/null || \
		printf "  ${BOLD}%-22s${NC} %s\n" "$key" "$value"
	else
		printf "  ${BOLD}%-22s${NC} %s\n" "$key" "$value"
	fi
}

print_success_banner() {
	echo ""
	cat << 'EOF'
╔════════════════════════════════════════════════════════════════════════════╗
║      A D V E N T U R E L O G   I S   R E A D Y   F O R   L A U N C H!      ║
╚════════════════════════════════════════════════════════════════════════════╝
EOF
	echo ""
}

print_failure_message() {
	echo ""
	log_error "Operation failed!"
	echo ""
	echo "Troubleshooting:"
	echo "  1. docker info"
	echo "  2. docker compose -f $COMPOSE_FILE ps"
	echo "  3. docker compose -f $COMPOSE_FILE logs"
	echo "  4. bash scripts/validate-env.sh $ENV_FILE"
	echo ""
	echo "Support: https://github.com/seanmorley15/AdventureLog"
}
