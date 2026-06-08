#!/bin/bash
# AdventureLog Installer & Manager
# (c) 2023-2026 Sean Morley — https://adventurelog.app — GPL-3.0
#
# Usage:
#   curl -sSL https://get.adventurelog.app | bash
#   bash install_adventurelog.sh [--dry-run] [--manage] [--force-install]
set -euo pipefail

INSTALLER_VERSION="2.0.0"
ADVENTURELOG_REF="${ADVENTURELOG_REF:-main}"
GITHUB_RAW="https://raw.githubusercontent.com/seanmorley15/AdventureLog/${ADVENTURELOG_REF}"
DRY_RUN=false
FORCE_INSTALL=false
ADVENTURELOG_MANAGE="${ADVENTURELOG_MANAGE:-}"

print_help() {
	cat << EOF
AdventureLog Installer v${INSTALLER_VERSION}

Usage:
  curl -sSL https://get.adventurelog.app | bash
  bash install_adventurelog.sh [options]

Options:
  --dry-run         Preview the wizard without changing your system
  --force-install   Run a fresh install even if one already exists
  --manage          Open the management console for an existing install
  -h, --help        Show this help message

Environment:
  INSTALL_DIR              Target directory (default: ./adventurelog)
  ADVENTURELOG_REF         Git branch/tag for remote files (default: main)
  ADVENTURELOG_SKIP_GUM=1  Disable gum UI (useful for CI and dry runs)

Docs: https://adventurelog.app/docs/install/quick_start
EOF
}

for arg in "$@"; do
	case "$arg" in
		--dry-run) DRY_RUN=true ;;
		--force-install) FORCE_INSTALL=true ;;
		--manage) ADVENTURELOG_MANAGE=1 ;;
		--help|-h)
			print_help
			exit 0
			;;
	esac
done

find_installer_lib_dir() {
	local script_dir=""
	if [[ "${BASH_SOURCE[0]}" != "bash" && "${BASH_SOURCE[0]}" != "-" && -f "${BASH_SOURCE[0]}" ]]; then
		script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
		if [[ -f "$script_dir/scripts/install/lib/ui.sh" ]]; then
			echo "$script_dir/scripts/install/lib"
			return 0
		fi
	fi
	if [[ -f "./scripts/install/lib/ui.sh" ]]; then
		echo "$(cd "./scripts/install/lib" && pwd)"
		return 0
	fi
	return 1
}

bootstrap_and_source_libs() {
	local lib_dir
	if lib_dir="$(find_installer_lib_dir)"; then
		INSTALLER_LIB_DIR="$lib_dir"
		REPO_ROOT="$(cd "$INSTALLER_LIB_DIR/../../.." && pwd)"
	else
		local cache_dir
		cache_dir="$(mktemp -d 2>/dev/null || echo "/tmp/adventurelog-installer-$$")"
		mkdir -p "$cache_dir"
		local files=(
			common.sh ui.sh tui.sh checks.sh download.sh deploy.sh
			aio-config.sh standard-config.sh manage.sh features.sh main.sh
		)
		local f
		for f in "${files[@]}"; do
			curl -fsSL "${GITHUB_RAW}/scripts/install/lib/${f}" -o "${cache_dir}/${f}" || {
				echo "ERROR: Failed to download installer library: ${f}" >&2
				echo "       Check ADVENTURELOG_REF=${ADVENTURELOG_REF} and your network connection." >&2
				exit 1
			}
		done
		INSTALLER_LIB_DIR="$cache_dir"
	fi

	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/common.sh"
	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/ui.sh"
	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/tui.sh"
	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/checks.sh"
	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/download.sh"
	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/features.sh"
	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/aio-config.sh"
	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/standard-config.sh"
	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/deploy.sh"
	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/manage.sh"
	# shellcheck source=/dev/null
	source "$INSTALLER_LIB_DIR/main.sh"
}

run_main() {
	if [[ "$DRY_RUN" == true ]]; then
		export DRY_RUN=true
	fi
	if [[ "$FORCE_INSTALL" == true ]]; then
		export FORCE_INSTALL=true
	fi
	run_installer_main
}

if [[ -t 1 ]] || [[ "$DRY_RUN" == true ]]; then
	if [[ -t 1 ]]; then
		exec < /dev/tty
	fi
	bootstrap_and_source_libs
	run_main "$@"
else
	echo "Error: AdventureLog installer requires an interactive terminal (or use --dry-run)." >&2
	echo "Run: bash install_adventurelog.sh --help" >&2
	exit 1
fi
