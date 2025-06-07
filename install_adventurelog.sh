#!/bin/bash
set -euo pipefail

# =============================================================================
# AdventureLog Installer Script
# (c) 2023-2025 Sean Morley <https://seanmorley.com>
# https://adventurelog.app
# License: GPL-3.0
# =============================================================================

APP_NAME="AdventureLog"
INSTALL_DIR="./adventurelog"
COMPOSE_FILE_URL="https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/docker-compose.yml"
ENV_FILE_URL="https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/.env.example"

# Global configuration variables
declare -g FRONTEND_ORIGIN=""
declare -g BACKEND_URL=""
declare -g ADMIN_PASSWORD=""
declare -g DB_PASSWORD=""
declare -g FRONTEND_PORT=""
declare -g BACKEND_PORT=""

# Color codes for beautiful output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# =============================================================================
# Utility Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo -e "${PURPLE}$1${NC}"
}

print_banner() {
    cat << 'EOF'
╔═════════════════════════════════════════════════════════════════════════╗
║                                                                         ║
║             A D V E N T U R E L O G   I N S T A L L E R                 ║
║                                                                         ║
║                    The Ultimate Travel Companion                        ║
║                                                                         ║
╚═════════════════════════════════════════════════════════════════════════╝
EOF
}

print_header() {
    clear
    echo ""
    print_banner
    echo ""
    log_header "🚀 Starting installation — $(date)"
    echo ""
}

generate_secure_password() {
    # Generate a 24-character password with mixed case, numbers, and safe symbols
    local length=${1:-24}
    
    # Test if /dev/urandom exists
    if [[ ! -r "/dev/urandom" ]]; then
        echo "ERROR: /dev/urandom not readable" >&2
        return 1
    fi
    
    # Try the main approach
    if command -v tr &>/dev/null; then
        LC_ALL=C tr -dc 'A-Za-z0-9!#$%&*+-=?@^_' </dev/urandom 2>/dev/null | head -c "$length" 2>/dev/null
        return 0
    fi
    
    # Fallback approach using od
    if command -v od &>/dev/null; then
        dd if=/dev/urandom bs=1 count=100 2>/dev/null | od -An -tx1 | tr -d ' \n' | cut -c1-"$length"
        return 0
    fi
    
    # Last resort - use openssl if available
    if command -v openssl &>/dev/null; then
        openssl rand -base64 32 | tr -d "=+/" | cut -c1-"$length"
        return 0
    fi
    
    echo "ERROR: No suitable random generation method found" >&2
    return 1
}

check_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# =============================================================================
# Validation Functions
# =============================================================================

validate_url() {
    local url="$1"
    if [[ $url =~ ^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$ ]]; then
        return 0
    else
        return 1
    fi
}

extract_port_from_url() {
    local url="$1"
    local default_port="$2"
    
    # Extract port from URL using regex
    if [[ $url =~ :([0-9]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        # Use default port based on protocol
        if [[ $url =~ ^https:// ]]; then
            echo "443"
        elif [[ $url =~ ^http:// ]]; then
            echo "${default_port:-80}"
        else
            echo "$default_port"
        fi
    fi
}

check_port_availability() {
    local port="$1"
    local service_name="$2"
    
    # Check if port is in use
    if command -v netstat &>/dev/null; then
        if netstat -ln 2>/dev/null | grep -q ":$port "; then
            log_warning "Port $port is already in use"
            echo ""
            read -r -p "Do you want to continue anyway? The $service_name service may fail to start. [y/N]: " confirm
            if [[ ! $confirm =~ ^[Yy]$ ]]; then
                echo "Installation cancelled."
                exit 0
            fi
        fi
    elif command -v ss &>/dev/null; then
        if ss -ln 2>/dev/null | grep -q ":$port "; then
            log_warning "Port $port is already in use"
            echo ""
            read -r -p "Do you want to continue anyway? The $service_name service may fail to start. [y/N]: " confirm
            if [[ ! $confirm =~ ^[Yy]$ ]]; then
                echo "Installation cancelled."
                exit 0
            fi
        fi
    fi
}

check_dependencies() {
    log_info "Checking system dependencies..."
    
    local missing_deps=()
    
    if ! command -v curl &>/dev/null; then
        missing_deps+=("curl")
    fi
    
    if ! command -v docker &>/dev/null; then
        missing_deps+=("docker")
    fi
    
    if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
        missing_deps+=("docker-compose")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        echo ""
        echo "Please install the missing dependencies:"
        for dep in "${missing_deps[@]}"; do
            case $dep in
                "curl")
                    echo "  • curl: apt-get install curl (Ubuntu/Debian) or brew install curl (macOS)"
                    ;;
                "docker")
                    echo "  • Docker: https://docs.docker.com/get-docker/"
                    ;;
                "docker-compose")
                    echo "  • Docker Compose: https://docs.docker.com/compose/install/"
                    ;;
            esac
        done
        exit 1
    fi
    
    log_success "All dependencies are installed"
}

check_docker_status() {
    log_info "Checking Docker daemon status..."
    
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"
        echo ""
        echo "Please start Docker and try again:"
        echo "  • On macOS/Windows: Start Docker Desktop"
        echo "  • On Linux: sudo systemctl start docker"
        exit 1
    fi
    
    log_success "Docker daemon is running"
}

# =============================================================================
# Installation Functions
# =============================================================================

create_directory() {
    log_info "Setting up installation directory: $INSTALL_DIR"
    
    if [ -d "$INSTALL_DIR" ]; then
        log_warning "Directory already exists"
        echo ""
        read -r -p "Do you want to continue and overwrite existing files? [y/N]: " confirm
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            echo "Installation cancelled."
            exit 0
        fi
    else
        mkdir -p "$INSTALL_DIR"
        log_success "Created directory: $INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR" || {
        log_error "Failed to change to directory: $INSTALL_DIR"
        exit 1
    }
}

# Check for AdventureLog running as a docker container
check_running_container() {
    if docker ps -a --filter "name=adventurelog" --format '{{.Names}}' | grep -q "adventurelog"; then
        log_error "AdventureLog is already running as a Docker container (including stopped or restarting states)."
        echo ""
        echo "Running this installer further can break existing installs."
        echo "Please stop and remove the existing AdventureLog container manually before proceeding."
        echo "  • To stop: docker compose down --remove-orphans"
        echo "Installation aborted to prevent data loss."
        exit 1
    fi
}

download_files() {
    log_info "Downloading configuration files..."
    
    # Download with better error handling
    if ! curl -fsSL --connect-timeout 10 --max-time 30 "$COMPOSE_FILE_URL" -o docker-compose.yml; then
        log_error "Failed to download docker-compose.yml"
        exit 1
    fi
    log_success "docker-compose.yml downloaded"
    
    if ! curl -fsSL --connect-timeout 10 --max-time 30 "$ENV_FILE_URL" -o .env; then
        log_error "Failed to download .env template"
        exit 1
    fi
    log_success ".env template downloaded"
}

prompt_configuration() {
    echo ""
    log_header "🛠️  Configuration Setup"
    echo ""
    echo "Configure the URLs where AdventureLog will be accessible."
    echo "Press Enter to use the default values shown in brackets."
    echo ""
    echo "⚠️  Note: The installer will automatically configure Docker ports based on your URLs"
    echo ""
    
    # Frontend URL
    local default_frontend="http://localhost:8015"
    while true; do
        read -r -p "🌐 Frontend URL [$default_frontend]: " input_frontend
        FRONTEND_ORIGIN=${input_frontend:-$default_frontend}
        
        if validate_url "$FRONTEND_ORIGIN"; then
            FRONTEND_PORT=$(extract_port_from_url "$FRONTEND_ORIGIN" "8015")
            break
        else
            log_error "Invalid URL format. Please enter a valid URL (e.g., http://localhost:8015)"
        fi
    done
    log_success "Frontend URL: $FRONTEND_ORIGIN (Port: $FRONTEND_PORT)"
    
    # Backend URL
    local default_backend="http://localhost:8016"
    while true; do
        read -r -p "🔧 Backend URL [$default_backend]: " input_backend
        BACKEND_URL=${input_backend:-$default_backend}
        
        if validate_url "$BACKEND_URL"; then
            BACKEND_PORT=$(extract_port_from_url "$BACKEND_URL" "8016")
            break
        else
            log_error "Invalid URL format. Please enter a valid URL (e.g., http://localhost:8016)"
        fi
    done
    log_success "Backend URL: $BACKEND_URL (Port: $BACKEND_PORT)"
    
    # Check port availability
    check_port_availability "$FRONTEND_PORT" "frontend"
    check_port_availability "$BACKEND_PORT" "backend"
    
    echo ""
}

configure_environment_fallback() {
    log_info "Using simple configuration approach..."
    
    # Generate simple passwords using a basic method
    DB_PASSWORD="$(date +%s | sha256sum | base64 | head -c 32)"
    ADMIN_PASSWORD="$(date +%s | sha256sum | base64 | head -c 24)"
    
    log_info "Generated passwords using fallback method"
    
    # Create backup
    cp .env .env.backup
    
    # Use simple string replacement with perl if available
    if command -v perl &>/dev/null; then
        log_info "Using perl for configuration..."
        # Fix: Update BOTH password variables for database consistency
        perl -pi -e "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$DB_PASSWORD/" .env
        perl -pi -e "s/^DATABASE_PASSWORD=.*/DATABASE_PASSWORD=$DB_PASSWORD/" .env
        perl -pi -e "s/^DJANGO_ADMIN_PASSWORD=.*/DJANGO_ADMIN_PASSWORD=$ADMIN_PASSWORD/" .env
        perl -pi -e "s|^ORIGIN=.*|ORIGIN=$FRONTEND_ORIGIN|" .env
        perl -pi -e "s|^PUBLIC_URL=.*|PUBLIC_URL=$BACKEND_URL|" .env
        perl -pi -e "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=$FRONTEND_ORIGIN,$BACKEND_URL|" .env
        perl -pi -e "s|^FRONTEND_URL=.*|FRONTEND_URL=$FRONTEND_ORIGIN|" .env
        # Add port configuration
        perl -pi -e "s/^FRONTEND_PORT=.*/FRONTEND_PORT=$FRONTEND_PORT/" .env
        perl -pi -e "s/^BACKEND_PORT=.*/BACKEND_PORT=$BACKEND_PORT/" .env
        
        # Add port variables if they don't exist
        if ! grep -q "^FRONTEND_PORT=" .env; then
            echo "FRONTEND_PORT=$FRONTEND_PORT" >> .env
        fi
        if ! grep -q "^BACKEND_PORT=" .env; then
            echo "BACKEND_PORT=$BACKEND_PORT" >> .env
        fi
        
        if grep -q "POSTGRES_PASSWORD=$DB_PASSWORD" .env; then
            log_success "Configuration completed successfully"
            return 0
        fi
    fi
    
    # Manual approach - create .env from scratch with key variables
    log_info "Creating minimal .env configuration..."
    cat > .env << EOF
# Database Configuration
POSTGRES_DB=adventurelog
POSTGRES_USER=adventurelog
POSTGRES_PASSWORD=$DB_PASSWORD
DATABASE_PASSWORD=$DB_PASSWORD

# Django Configuration
DJANGO_ADMIN_USERNAME=admin
DJANGO_ADMIN_PASSWORD=$ADMIN_PASSWORD
SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || echo "change-this-secret-key-$(date +%s)")

# URL Configuration
ORIGIN=$FRONTEND_ORIGIN
PUBLIC_URL=$BACKEND_URL
FRONTEND_URL=$FRONTEND_ORIGIN
CSRF_TRUSTED_ORIGINS=$FRONTEND_ORIGIN,$BACKEND_URL

# Port Configuration
FRONTEND_PORT=$FRONTEND_PORT
BACKEND_PORT=$BACKEND_PORT

# Additional Settings
DEBUG=False
EOF
    
    log_success "Created minimal .env configuration"
    return 0
}

configure_environment() {
    log_info "Generating secure configuration..."
    
    # Debug: Test password generation first
    log_info "Testing password generation..."
    if ! command -v tr &>/dev/null; then
        log_error "tr command not found - required for password generation"
        exit 1
    fi
    
    # Generate secure passwords with error checking
    log_info "Generating database password..."
    DB_PASSWORD=$(generate_secure_password 32)
    if [[ -z "$DB_PASSWORD" ]]; then
        log_error "Failed to generate database password"
        exit 1
    fi
    log_success "Database password generated (${#DB_PASSWORD} characters)"
    
    log_info "Generating admin password..."
    ADMIN_PASSWORD=$(generate_secure_password 24)
    if [[ -z "$ADMIN_PASSWORD" ]]; then
        log_error "Failed to generate admin password"
        exit 1
    fi
    log_success "Admin password generated (${#ADMIN_PASSWORD} characters)"
    
    # Debug: Check if .env file exists and is readable
    log_info "Checking .env file..."
    if [[ ! -f ".env" ]]; then
        log_error ".env file not found"
        exit 1
    fi
    
    if [[ ! -r ".env" ]]; then
        log_error ".env file is not readable"
        exit 1
    fi
    
    log_info "File check passed - .env exists and is readable ($(wc -l < .env) lines)"
    
    # Try fallback method first (simpler and more reliable)
    log_info "Attempting configuration..."
    if configure_environment_fallback; then
        return 0
    fi
    
    log_warning "Fallback method failed, trying advanced processing..."
    
    # Fallback to bash processing
    # Create backup of original .env
    cp .env .env.backup
    
    # Create a new .env file by processing the original line by line
    local temp_file=".env.temp"
    local processed_lines=0
    local updated_lines=0
    
    while IFS= read -r line || [[ -n "$line" ]]; do
        ((processed_lines++))
        case "$line" in
            POSTGRES_PASSWORD=*)
                echo "POSTGRES_PASSWORD=$DB_PASSWORD"
                ((updated_lines++))
                ;;
            DATABASE_PASSWORD=*)
                echo "DATABASE_PASSWORD=$DB_PASSWORD"
                ((updated_lines++))
                ;;
            DJANGO_ADMIN_PASSWORD=*)
                echo "DJANGO_ADMIN_PASSWORD=$ADMIN_PASSWORD"
                ((updated_lines++))
                ;;
            ORIGIN=*)
                echo "ORIGIN=$FRONTEND_ORIGIN"
                ((updated_lines++))
                ;;
            PUBLIC_URL=*)
                echo "PUBLIC_URL=$BACKEND_URL"
                ((updated_lines++))
                ;;
            CSRF_TRUSTED_ORIGINS=*)
                echo "CSRF_TRUSTED_ORIGINS=$FRONTEND_ORIGIN,$BACKEND_URL"
                ((updated_lines++))
                ;;
            FRONTEND_URL=*)
                echo "FRONTEND_URL=$FRONTEND_ORIGIN"
                ((updated_lines++))
                ;;
            FRONTEND_PORT=*)
                echo "FRONTEND_PORT=$FRONTEND_PORT"
                ((updated_lines++))
                ;;
            BACKEND_PORT=*)
                echo "BACKEND_PORT=$BACKEND_PORT"
                ((updated_lines++))
                ;;
            *)
                echo "$line"
                ;;
        esac
    done < .env > "$temp_file"
    
    # Add port variables if they weren't found in the original file
    if ! grep -q "^FRONTEND_PORT=" "$temp_file"; then
        echo "FRONTEND_PORT=$FRONTEND_PORT" >> "$temp_file"
        ((updated_lines++))
    fi
    if ! grep -q "^BACKEND_PORT=" "$temp_file"; then
        echo "BACKEND_PORT=$BACKEND_PORT" >> "$temp_file"
        ((updated_lines++))
    fi
    
    log_info "Processed $processed_lines lines, updated $updated_lines configuration values"
    
    # Check if temp file was created successfully
    if [[ ! -f "$temp_file" ]]; then
        log_error "Failed to create temporary configuration file"
        exit 1
    fi
    
    # Replace the original .env with the configured one
    if mv "$temp_file" .env; then
        log_success "Environment configured with secure passwords and port settings"
    else
        log_error "Failed to replace .env file"
        log_info "Restoring backup and exiting"
        mv .env.backup .env
        rm -f "$temp_file"
        exit 1
    fi
    
    # Verify critical configuration was applied
    if grep -q "POSTGRES_PASSWORD=$DB_PASSWORD" .env && (grep -q "DATABASE_PASSWORD=$DB_PASSWORD" .env || grep -q "POSTGRES_PASSWORD=$DB_PASSWORD" .env); then
        log_success "Configuration verification passed - database password variables set"
    else
        log_error "Configuration verification failed - database passwords not properly configured"
        log_info "Showing database-related lines in .env for debugging:"
        grep -E "(POSTGRES_PASSWORD|DATABASE_PASSWORD)" .env | while read -r line; do
            echo "  $line"
        done
        mv .env.backup .env
        exit 1
    fi
    
    # Verify port configuration
    if grep -q "FRONTEND_PORT=$FRONTEND_PORT" .env && grep -q "BACKEND_PORT=$BACKEND_PORT" .env; then
        log_success "Port configuration verified - frontend: $FRONTEND_PORT, backend: $BACKEND_PORT"
    else
        log_warning "Port configuration may not be complete - check .env file manually"
    fi
}

update_docker_compose_ports() {
    log_info "Updating Docker Compose port configuration..."
    
    # Create backup of docker-compose.yml
    cp docker-compose.yml docker-compose.yml.backup
    
    # Update ports in docker-compose.yml using sed
    if command -v sed &>/dev/null; then
        # For frontend service port mapping
        sed -i.tmp "s/\"[0-9]*:3000\"/\"$FRONTEND_PORT:3000\"/g" docker-compose.yml
        # For backend service port mapping  
        sed -i.tmp "s/\"[0-9]*:8000\"/\"$BACKEND_PORT:8000\"/g" docker-compose.yml
        
        # Clean up temporary files created by sed -i
        rm -f docker-compose.yml.tmp
        
        log_success "Docker Compose ports updated - Frontend: $FRONTEND_PORT, Backend: $BACKEND_PORT"
    else
        log_warning "sed command not available - Docker Compose ports may need manual configuration"
    fi
}

start_services() {
    log_info "Starting AdventureLog services..."
    echo ""
    
    # Use docker compose or docker-compose based on availability
    local compose_cmd
    if docker compose version &>/dev/null; then
        compose_cmd="docker compose"
    else
        compose_cmd="docker-compose"
    fi
    
    # Pull images first for better progress indication
    log_info "Pulling required Docker images..."
    $compose_cmd pull
    
    # Start services
    log_info "Starting containers..."
    if $compose_cmd up -d --remove-orphans; then
        log_success "All services started successfully"
    else
        log_error "Failed to start services"
        echo ""
        log_info "Checking service status..."
        $compose_cmd ps
        exit 1
    fi
}

wait_for_services() {
    log_info "Waiting for services to be ready... (up to 90 seconds, first startup may take longer)"
    
    local max_attempts=45  # 45 attempts * 2 seconds = 90 seconds total
    local attempt=1
    local frontend_ready=false
    local backend_ready=false
    
    while [ $attempt -le $max_attempts ]; do
        # Check frontend
        if [ "$frontend_ready" = false ]; then
            if curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_ORIGIN" | grep -q "200\|404\|302"; then
                log_success "Frontend is responding"
                frontend_ready=true
            fi
        fi
        
        # Check backend
        if [ "$backend_ready" = false ]; then
            if curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL" | grep -q "200\|404\|302"; then
                log_success "Backend is responding"
                backend_ready=true
            fi
        fi
        
        # If both are ready, break the loop
        if [ "$frontend_ready" = true ] && [ "$backend_ready" = true ]; then
            break
        fi
        
        # Check if we've reached max attempts
        if [ $attempt -eq $max_attempts ]; then
            if [ "$frontend_ready" = false ]; then
                log_warning "Frontend may still be starting up (this is normal for first run)"
            fi
            if [ "$backend_ready" = false ]; then
                log_warning "Backend may still be starting up (this is normal for first run)"
            fi
            break
        fi
        
        # Wait and increment counter
        printf "."
        sleep 2
        ((attempt++))
    done
    echo ""
}

# =============================================================================
# Output Functions
# =============================================================================

print_success_message() {
    local ip_address
    ip_address=$(hostname -I 2>/dev/null | cut -d' ' -f1 || echo "localhost")

    echo ""
    cat << 'EOF'
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║      A D V E N T U R E L O G   I S   R E A D Y   F O R   L A U N C H!      ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
EOF
    echo ""

    log_success "🎉 Installation completed successfully!"
    echo ""

    echo -e "${BOLD}🌐 Access Points:${NC}"
    echo -e "   🖥️  Frontend:   ${CYAN}$FRONTEND_ORIGIN${NC}"
    echo -e "   ⚙️  Backend:    ${CYAN}$BACKEND_URL${NC}"

    echo ""
    echo -e "${BOLD}🔐 Admin Credentials:${NC}"
    echo -e "   👤 Username:  ${GREEN}admin${NC}"
    echo -e "   🔑 Password:  ${GREEN}$ADMIN_PASSWORD${NC}"

    echo ""
    echo -e "${BOLD}📁 Important Locations:${NC}"
    echo -e "   🛠️  Config:     ${YELLOW}$(pwd)/.env${NC}"
    echo -e "   📦 Media Vol:  ${YELLOW}adventurelog_media${NC}"
    echo -e "   📜 Logs:       ${YELLOW}docker compose logs -f${NC}"

    echo ""
    echo -e "${BOLD}🧰 Management Commands:${NC}"
    echo -e "   ⛔ Stop:       ${CYAN}docker compose down${NC}"
    echo -e "   ▶️  Start:      ${CYAN}docker compose up -d${NC}"
    echo -e "   🔄 Update:     ${CYAN}docker compose pull && docker compose up -d${NC}"
    echo -e "   📖 Logs:       ${CYAN}docker compose logs -f${NC}"

    echo ""
    log_info "💾 Save your admin password in a secure location!"
    echo ""

    # Show port information
    echo -e "${BOLD}🔧 Port Configuration:${NC}"
    echo -e "   🖥️  Frontend Port: ${YELLOW}$FRONTEND_PORT${NC}"
    echo -e "   ⚙️  Backend Port:  ${YELLOW}$BACKEND_PORT${NC}"
    echo ""

    # Optional donation link
    echo -e "${BOLD}❤️  Enjoying AdventureLog?${NC}"
    echo -e "   Support future development: ${MAGENTA}https://seanmorley.com/sponsor${NC}"
    echo ""

    echo -e "${BOLD}🌍 Adventure awaits — your journey starts now with AdventureLog!${NC}"
}

print_failure_message() {
    echo ""
    log_error "Installation failed!"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check Docker is running: docker info"
    echo "2. Check available ports: netstat -an | grep :$FRONTEND_PORT"
    echo "3. Check available ports: netstat -an | grep :$BACKEND_PORT"
    echo "4. View logs: docker compose logs"
    echo "5. Check .env configuration: cat .env"
    echo "6. Check docker-compose.yml ports: grep -A5 ports docker-compose.yml"
    echo ""
    echo "For support, visit: https://github.com/seanmorley15/AdventureLog"
}

cleanup_on_failure() {
    log_info "Cleaning up after failure..."
    
    if [ -f ".env.backup" ]; then
        mv .env.backup .env
        log_info "Restored original .env file"
    fi
    
    if [ -f "docker-compose.yml.backup" ]; then
        mv docker-compose.yml.backup docker-compose.yml
        log_info "Restored original docker-compose.yml file"
    fi
    
    if command -v docker &>/dev/null; then
        docker compose down --remove-orphans 2>/dev/null || true
    fi
}

# =============================================================================
# Main Installation Flow
# =============================================================================

main() {
    # Set up error handling
    trap 'cleanup_on_failure; print_failure_message; exit 1' ERR
    
    # Installation steps
    print_header
    check_dependencies
    check_docker_status
    check_running_container
    create_directory
    download_files
    prompt_configuration
    configure_environment
    update_docker_compose_ports
    start_services
    wait_for_services
    print_success_message
    
    # Clean up backup files on success
    rm -f .env.backup
    rm -f docker-compose.yml.backup
}

# Script entry point
# Allow interactive install even when piped
if [[ -t 1 ]]; then
    # stdout is a terminal → likely interactive
    exec < /dev/tty  # reconnect stdin to terminal for user input
    main "$@"
else
    echo "Error: This script needs an interactive terminal." >&2
    exit 1
fi
