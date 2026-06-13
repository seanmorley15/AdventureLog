#!/bin/bash
# Download installer files from GitHub.
set -euo pipefail

INSTALLER_LIB_FILES=(
	common.sh ui.sh tui.sh checks.sh download.sh deploy.sh
	standard-config.sh advanced-config.sh manage.sh features.sh
)

download_file() {
	local url="$1"
	local dest="$2"
	local relpath="${url#*AdventureLog/${ADVENTURELOG_REF}/}"
	if [[ -n "${REPO_ROOT:-}" && -f "${REPO_ROOT}/${relpath}" ]]; then
		mkdir -p "$(dirname "$dest")"
		cp "${REPO_ROOT}/${relpath}" "$dest"
		return 0
	fi
	if [[ "$DRY_RUN" == true ]]; then
		log_info "[dry-run] Would download $url -> $dest"
		return 0
	fi
	mkdir -p "$(dirname "$dest")"
	if ! curl -fsSL --connect-timeout 15 --max-time 60 "$url" -o "$dest"; then
		log_error "Failed to download $url"
		return 1
	fi
}

bootstrap_installer_libs() {
	local dest_dir="$1"
	log_info "Downloading installer libraries..."
	mkdir -p "$dest_dir"
	local f
	for f in "${INSTALLER_LIB_FILES[@]}"; do
		download_file "${GITHUB_RAW}/scripts/install/lib/${f}" "${dest_dir}/${f}"
	done
	log_success "Installer libraries ready"
}

copy_local_installer_libs() {
	local src="$1"
	local dest="$2"
	if [[ "$DRY_RUN" == true ]]; then
		log_info "[dry-run] Would copy installer libs to $dest"
		return 0
	fi
	mkdir -p "$dest"
	local f
	for f in "${INSTALLER_LIB_FILES[@]}"; do
		if [[ -f "$src/$f" ]]; then
			cp "$src/$f" "$dest/$f"
			chmod +x "$dest/$f" 2>/dev/null || true
		fi
	done
}

download_standard_toolkit() {
	log_info "Fetching Standard Deployment files"
	mkdir -p docker
	download_file "${GITHUB_RAW}/docker/docker-compose.yml" "docker/docker-compose.yml"
	download_file "${GITHUB_RAW}/.env.example" ".env.example"
	download_file "${GITHUB_RAW}/scripts/deploy.sh" "scripts/deploy.sh"
	download_file "${GITHUB_RAW}/scripts/validate-env.sh" "scripts/validate-env.sh"
	download_file "${GITHUB_RAW}/scripts/backup.sh" "scripts/backup.sh"
	download_file "${GITHUB_RAW}/scripts/restore.sh" "scripts/restore.sh"
	chmod +x scripts/deploy.sh scripts/validate-env.sh scripts/backup.sh scripts/restore.sh 2>/dev/null || true
	if [[ -d "$(dirname "${BASH_SOURCE[0]}")" ]]; then
		copy_local_installer_libs "$(dirname "${BASH_SOURCE[0]}")" "scripts/install/lib"
	fi
	log_success "Deployment toolkit ready"
}

download_advanced_toolkit() {
	log_info "Fetching Advanced Deployment files"
	mkdir -p docker
	download_file "${GITHUB_RAW}/docker/docker-compose.advanced.yml" "docker/docker-compose.advanced.yml"
	download_file "${GITHUB_RAW}/.env.advanced.example" ".env.advanced.example"
	download_file "${GITHUB_RAW}/scripts/deploy.sh" "scripts/deploy.sh"
	download_file "${GITHUB_RAW}/scripts/validate-env.sh" "scripts/validate-env.sh"
	download_file "${GITHUB_RAW}/scripts/backup.sh" "scripts/backup.sh"
	download_file "${GITHUB_RAW}/scripts/restore.sh" "scripts/restore.sh"
	chmod +x scripts/deploy.sh scripts/validate-env.sh scripts/backup.sh scripts/restore.sh 2>/dev/null || true
	if [[ -d "$(dirname "${BASH_SOURCE[0]}")" ]]; then
		copy_local_installer_libs "$(dirname "${BASH_SOURCE[0]}")" "scripts/install/lib"
	fi
	log_success "Deployment toolkit ready"
}

ensure_install_directory() {
	local dir="$INSTALL_DIR"
	log_info "Install directory: $dir"
	if [[ -d "$dir" ]] && [[ "$FORCE_INSTALL" != true ]]; then
		if detect_existing_install "$dir"; then
			return 0
		fi
		log_warning "Directory exists"
		tui_confirm "Continue and update files in existing directory?" "y" || exit 0
	fi
	if [[ "$DRY_RUN" != true ]] || [[ ! -d "$dir" ]]; then
		mkdir -p "$dir"
	fi
	cd "$dir" || exit 1
}
