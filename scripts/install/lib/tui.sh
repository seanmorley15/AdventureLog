#!/bin/bash
# Cross-distro TUI: gum (real terminals) | styled bash (IDE) | plain fallback.
set -euo pipefail

TUI_BACKEND="bash"
GUM_STYLE=false

has_gum() {
	command -v gum &>/dev/null
}

terminal_supports_gum_interactive() {
	has_gum || return 1
	[[ -t 0 && -t 1 ]] || return 1
	[[ -n "${TERM:-}" && "${TERM:-}" != "dumb" ]] || return 1
	case "${TERM_PROGRAM:-}" in
		vscode|Visual\ Studio\ Code) return 1 ;;
	esac
	[[ -n "${VSCODE_GIT_IPC_HANDLE:-}" ]] && return 1
	[[ -n "${CURSOR_TRACE_ID:-}" ]] && return 1
	[[ -n "${CURSOR_AGENT:-}" ]] && return 1
	return 0
}

detect_tui_backend() {
	if [[ -n "${ADVENTURELOG_TUI:-}" ]]; then
		TUI_BACKEND="$ADVENTURELOG_TUI"
		return 0
	fi
	if terminal_supports_gum_interactive; then
		TUI_BACKEND="gum"
	elif has_gum; then
		TUI_BACKEND="styled"
	elif command -v whiptail &>/dev/null; then
		TUI_BACKEND="whiptail"
	elif command -v dialog &>/dev/null; then
		TUI_BACKEND="dialog"
	else
		TUI_BACKEND="bash"
	fi
}

offer_gum_install() {
	if has_gum; then
		return 0
	fi
	tui_print_box "Enhanced UI" \
		"Install gum for polished menus, spinners, and progress bars.\nhttps://github.com/charmbracelet/gum"
	if ! tui_confirm_bash "Install gum now?" "y"; then
		log_muted "Continuing with built-in styled UI."
		return 1
	fi
	if [[ "$OSTYPE" == "darwin"* ]] && command -v brew &>/dev/null; then
		tui_spinner_bash "Installing gum via Homebrew" brew install gum
	elif command -v apt-get &>/dev/null; then
		tui_spinner_bash "Installing gum via apt" bash -c '
			sudo mkdir -p /etc/apt/keyrings &&
			curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg &&
			echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list >/dev/null &&
			sudo apt-get update -qq &&
			sudo apt-get install -y gum
		'
	else
		log_warning "Automatic gum install is not supported on this OS."
		log_muted "See https://github.com/charmbracelet/gum#installation"
		return 1
	fi
	has_gum
}

init_tui() {
	GUM_STYLE=false
	TUI_BACKEND="bash"
	if has_gum; then
		GUM_STYLE=true
	fi
	if [[ "$DRY_RUN" == true ]] || [[ "${ADVENTURELOG_SKIP_GUM:-}" == "1" ]]; then
		TUI_BACKEND="bash"
		return 0
	fi
	if ! has_gum && [[ "${ADVENTURELOG_SKIP_GUM:-}" != "1" ]]; then
		offer_gum_install && GUM_STYLE=true
	fi
	detect_tui_backend
}

tui_styled() {
	local fg="${1:-212}"
	shift
	if [[ "$GUM_STYLE" == true ]]; then
		gum style --foreground "$fg" "$@"
	else
		echo -e "${PURPLE}${BOLD}$*${NC}"
	fi
}

tui_print_box() {
	local title="$1"
	local body="$2"
	body="$(printf '%b' "$body")"
	echo "" >&2
	if [[ "$GUM_STYLE" == true ]]; then
		gum join --align left --vertical \
			"$(gum style --border rounded --border-foreground 212 --padding "0 1" --bold "$title")" \
			"$(gum style --border rounded --border-foreground 240 --padding "0 1" "$body")" >&2
	else
		local width=54
		echo -e "  ${CYAN}╭$(printf '─%.0s' $(seq 1 "$width"))╮${NC}" >&2
		echo -e "  ${CYAN}│${NC} ${BOLD}${title}${NC}" >&2
		echo -e "  ${CYAN}├$(printf '─%.0s' $(seq 1 "$width"))┤${NC}" >&2
		while IFS= read -r line || [[ -n "$line" ]]; do
			[[ -z "$line" ]] && echo -e "  ${CYAN}│${NC}" >&2 && continue
			echo -e "  ${CYAN}│${NC} ${line}" >&2
		done <<< "$body"
		echo -e "  ${CYAN}╰$(printf '─%.0s' $(seq 1 "$width"))╯${NC}" >&2
	fi
	echo "" >&2
}

tui_progress_bar() {
	local step="$1"
	local total="$2"
	local label="$3"
	local width=28
	local filled=$(( step * width / total ))
	local empty=$(( width - filled ))
	local bar="" i
	for ((i = 0; i < filled; i++)); do bar+="█"; done
	for ((i = 0; i < empty; i++)); do bar+="░"; done
	local step_text="Step ${step} of ${total}"
	if [[ "$GUM_STYLE" == true ]]; then
		if ! {
			gum style --foreground 212 "$bar" >&2
			gum style --bold "$step_text" >&2
			gum style --foreground 245 "$label" >&2
		} 2>/dev/null; then
			echo -e "  ${CYAN}${bar}${NC}  ${BOLD}${step_text}${NC}" >&2
			echo -e "  ${DIM}${label}${NC}" >&2
		fi
	else
		echo -e "  ${CYAN}${bar}${NC}  ${BOLD}${step_text}${NC}" >&2
		echo -e "  ${DIM}${label}${NC}" >&2
	fi
	echo "" >&2
}

tui_confirm_bash() {
	local prompt="$1"
	local default="${2:-n}"
	local hint="y/N"
	[[ "$default" == "y" ]] && hint="Y/n"
	if [[ "$TUI_BACKEND" == "styled" ]] || [[ "$TUI_BACKEND" == "gum" ]]; then
		tui_print_box "Confirm" "$prompt"
	fi
	echo "" >&2
	read -r -p "$(echo -e "  ${BOLD}?${NC} ${prompt} ${DIM}[${hint}]${NC}: ")" reply
	reply="${reply:-$default}"
	[[ "$reply" =~ ^[Yy] ]]
}

tui_confirm() {
	local prompt="$1"
	local default="${2:-n}"
	if [[ "${DRY_RUN:-false}" == true ]]; then
		[[ "$default" == "y" ]]
		return
	fi
	case "$TUI_BACKEND" in
		gum)
			local gum_rc=0
			if [[ "$default" == "y" ]]; then
				gum confirm "$prompt" --affirmative " Yes " --negative " No " --default=true 2>/dev/null || gum_rc=$?
			else
				gum confirm "$prompt" --affirmative " Yes " --negative " No " --default=false 2>/dev/null || gum_rc=$?
			fi
			if [[ $gum_rc -eq 0 ]]; then return 0; fi
			if [[ $gum_rc -eq 1 ]]; then return 1; fi
			tui_confirm_bash "$prompt" "$default"
			;;
		whiptail)
			if whiptail --yesno "$prompt" 12 70; then return 0; else return 1; fi
			;;
		dialog)
			if dialog --yesno "$prompt" 12 70; then return 0; else return 1; fi
			;;
		*)
			tui_confirm_bash "$prompt" "$default"
			;;
	esac
}

tui_input_bash() {
	local prompt="$1"
	local default="${2:-}"
	local value
	if [[ "$TUI_BACKEND" == "styled" ]]; then
		tui_print_box "Input" "$prompt"
	fi
	echo "" >&2
	if [[ -n "$default" ]]; then
		read -r -p "$(echo -e "  ${BOLD}›${NC} ${prompt} ${DIM}[${default}]${NC}: ")" value
		echo "${value:-$default}"
	else
		read -r -p "$(echo -e "  ${BOLD}›${NC} ${prompt}: ")" value
		echo "$value"
	fi
}

tui_input() {
	local prompt="$1"
	local default="${2:-}"
	if [[ "${DRY_RUN:-false}" == true ]]; then
		echo "$default"
		return 0
	fi
	local value
	case "$TUI_BACKEND" in
		gum)
			if [[ -n "$default" ]]; then
				value="$(gum input --placeholder "$default" --prompt "$prompt " --value "$default" --width 60 2>/dev/null || true)"
			else
				value="$(gum input --prompt "$prompt " --width 60 2>/dev/null || true)"
			fi
			if [[ -n "$value" ]]; then
				echo "$value"
				return 0
			fi
			tui_input_bash "$prompt" "$default"
			;;
		whiptail)
			whiptail --inputbox "$prompt" 10 70 "$default" 3>&1 1>&2 2>&3
			;;
		dialog)
			dialog --inputbox "$prompt" 10 70 "$default" 3>&1 1>&2 2>&3
			;;
		*)
			tui_input_bash "$prompt" "$default"
			;;
	esac
}

tui_password() {
	local prompt="$1"
	if [[ "${DRY_RUN:-false}" == true ]]; then
		echo "dry-run-password"
		return 0
	fi
	local value
	case "$TUI_BACKEND" in
		gum)
			value="$(gum input --password --prompt "$prompt " --width 60 2>/dev/null || true)"
			if [[ -n "$value" ]]; then
				echo "$value"
				return 0
			fi
			;&
		*)
			if [[ "$TUI_BACKEND" == "styled" ]]; then
				tui_print_box "Secret" "$prompt"
			fi
			echo "" >&2
			read -r -s -p "$(echo -e "  ${BOLD}🔒${NC} ${prompt}: ")" value
			echo "" >&2
			echo "$value"
			;;
	esac
}

tui_choose_styled() {
	local prompt="$1"
	shift
	local options=("$@")
	local choice i default="${TUI_CHOOSE_DEFAULT_INDEX:-1}"

	tui_print_box "$prompt" "Enter the number for your choice."
	echo "" >&2
	i=1
	for opt in "${options[@]}"; do
		if (( i == default )); then
			if [[ "$GUM_STYLE" == true ]]; then
				echo -e "    $(gum style --foreground 212 --bold "❯ ${i}")  $(gum style --bold "$opt")" >&2
			else
				echo -e "    ${CYAN}${BOLD}❯ ${i}${NC}  ${BOLD}${opt}${NC}" >&2
			fi
		else
			echo -e "      ${DIM}${i}${NC}  ${opt}" >&2
		fi
		((i++)) || true
	done
	echo "" >&2
	read -r -p "$(echo -e "  ${BOLD}›${NC} Choice ${DIM}[${default}]${NC}: ")" choice
	choice="${choice:-$default}"
	if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#options[@]} )); then
		echo "${options[$((choice - 1))]}"
		return 0
	fi
	return 1
}

tui_choose() {
	local prompt="$1"
	shift
	local options=("$@")
	local choice result default_idx="${TUI_CHOOSE_DEFAULT_INDEX:-}"
	if [[ "${DRY_RUN:-false}" == true ]]; then
		if [[ -n "$default_idx" ]]; then
			echo "${options[$((default_idx - 1))]}"
		else
			echo "${options[0]}"
		fi
		return 0
	fi
	case "$TUI_BACKEND" in
		gum)
			if [[ -z "$default_idx" ]] && result="$(gum choose --header "$prompt" --cursor "❯ " --selected.foreground "212" --height 12 "${options[@]}" 2>/dev/null)" && [[ -n "$result" ]]; then
				echo "$result"
				return 0
			fi
			tui_choose_styled "$prompt" "${options[@]}"
			;;
		styled|bash)
			tui_choose_styled "$prompt" "${options[@]}"
			;;
		whiptail|dialog)
			local menu_args=()
			local idx=1
			for opt in "${options[@]}"; do
				menu_args+=("$idx" "$opt")
				((idx++)) || true
			done
			local cmd="whiptail"
			[[ "$TUI_BACKEND" == "dialog" ]] && cmd="dialog"
			choice=$($cmd --menu "$prompt" 20 78 12 "${menu_args[@]}" 3>&1 1>&2 2>&3) || return 1
			echo "${options[$((choice - 1))]}"
			;;
	esac
}

tui_spinner_bash() {
	local title="$1"
	shift
	local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
	local i=0
	local tmp_out tmp_err
	tmp_out="$(mktemp)"
	tmp_err="$(mktemp)"
	("$@" >"$tmp_out" 2>"$tmp_err") &
	local pid=$!
	while kill -0 "$pid" 2>/dev/null; do
		printf '\r  %b%s%b  %s' "$CYAN" "${frames[$i]}" "$NC" "$title" >&2
		i=$(( (i + 1) % ${#frames[@]} ))
		sleep 0.08
	done
	wait "$pid"
	local rc=$?
	printf "\r\033[K" >&2
	if [[ $rc -eq 0 ]]; then
		log_success "$title" >&2
	else
		log_error "$title failed" >&2
		cat "$tmp_err" >&2
	fi
	cat "$tmp_out"
	rm -f "$tmp_out" "$tmp_err"
	return $rc
}

tui_spinner() {
	local title="$1"
	shift
	case "$TUI_BACKEND" in
		gum)
			gum spin --spinner dot --spinner.foreground "212" --title "$title" -- "$@" 2>/dev/null || {
				tui_spinner_bash "$title" "$@"
			}
			;;
		styled|bash)
			tui_spinner_bash "$title" "$@"
			;;
		*)
			log_info "$title"
			"$@"
			;;
	esac
}

tui_press_enter() {
	local msg="${1:-Press Enter to continue}"
	echo "" >&2
	if [[ "$GUM_STYLE" == true ]]; then
		gum style --foreground 245 "  ${msg}…" >&2
	else
		echo -e "  ${DIM}${msg}…${NC}" >&2
	fi
	read -r -p "" _
}

prompt_with_default() {
	local prompt="$1"
	local default="$2"
	local validator="${3:-}"
	local value
	while true; do
		value="$(tui_input "$prompt" "$default")"
		value="${value:-$default}"
		if [[ -z "$validator" ]] || "$validator" "$value"; then
			echo "$value"
			return 0
		fi
		log_error "Invalid value — please try again."
	done
}

prompt_yes_no() {
	local prompt="$1"
	local default="${2:-n}"
	tui_confirm "$prompt" "$default"
}
