#!/usr/bin/env bash
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
declare -g TRAEFIK_ENABLED=""
declare -g USE_EMAIL=""
declare -g USE_DOCKER_SECRETS=""
declare -g EMAIL_HOST=""
declare -g EMAIL_USE_TLS=""
declare -g EMAIL_PORT=""
declare -g EMAIL_USE_SSL=""
declare -g EMAIL_HOST_USER=""
declare -g EMAIL_HOST_PASSWORD=""
declare -g FINISHED_CORRECTLY="true"

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

# pause(){
#     read -s -n 1 -p "Press any key to continue . . ."
#     echo ""
# }

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
    for bin in curl docker docker-compose tr sed; do
        if ! command -v "$bin" >/dev/null 2>&1; then
            missing_deps+=("$bin")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        echo ""
        echo "Please install the missing dependencies:"
        for dep in "${missing_deps[@]}"; do
            case $dep in
                "curl")
                    echo "  • curl: apt-get install curl (Ubuntu/Debian) or brew install curl (macOS)"
                    ;;
                "tr")
                    echo "  • curl: apt-get install coreutils (Ubuntu/Debian) and should be installed by default on macOS"
                    ;;
                "sed")
                    echo "  • curl: apt-get install sed (Ubuntu/Debian) or brew install gnu-sed (macOS)"
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
}

prompt_email_configuration() {
    echo ""
    log_header "📧  SMTP Email Configuration"
    echo ""
    echo "Please enter the required SMTP settings for sending emails from AdventureLog."
    echo ""

    # SMTP Host
    while true; do
        read -r -p "📨 SMTP Host: " EMAIL_HOST
        if [[ -n "$EMAIL_HOST" ]]; then
            break
        else
            log_error "SMTP Host cannot be empty."
        fi
    done

    # Use TLS
    while true; do
        read -r -p "🔐 Use TLS? (y/n): " input_tls
        case "${input_tls,,}" in
            y | yes)
                EMAIL_USE_TLS=true
                break
                ;;
            n | no)
                EMAIL_USE_TLS=false
                break
                ;;
            *)
                log_error "Invalid input. Please enter y or n."
                ;;
        esac
    done

    # Use SSL
    while true; do
        read -r -p "🔐 Use SSL? (y/n): " input_ssl
        case "${input_ssl,,}" in
            y | yes)
                EMAIL_USE_SSL=true
                break
                ;;
            n | no)
                EMAIL_USE_SSL=false
                break
                ;;
            *)
                log_error "Invalid input. Please enter y or n."
                ;;
        esac
    done

    # SMTP Port
    while true; do
        read -r -p "🔌 SMTP Port: " EMAIL_PORT
        if [[ "$EMAIL_PORT" =~ ^[0-9]+$ ]]; then
            break
        else
            log_error "Please enter a valid numeric port."
        fi
    done

    # SMTP Username
    while true; do
        read -r -p "👤 SMTP Username: " EMAIL_HOST_USER
        if [[ -n "$EMAIL_HOST_USER" ]]; then
            break
        else
            log_error "SMTP Username cannot be empty."
        fi
    done

    # SMTP Password
    while true; do
        read -r -s -p "🔑 SMTP Password: " EMAIL_HOST_PASSWORD
        echo
        if [[ -n "$EMAIL_HOST_PASSWORD" ]]; then
            break
        else
            log_error "Passwords do not match or are empty. Please try again."
        fi
    done

    log_success "SMTP configuration completed."
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

    while true; do
        read -r -p "🚦 Use SMTP email with AdventureLog? (Y/n): " input_email
        case "${input_email,,}" in
            y | yes | "") 
                USE_EMAIL=true
                prompt_email_configuration
                break
                ;;
            n | no)
                USE_EMAIL=false
                break
                ;;
            *)
                log_error "Invalid input. Please enter Y or N."
                ;;
        esac
    done
    log_success "Using SMTP email with AdventureLog?: $USE_EMAIL"

    while true; do
        read -r -p "🚦 Enable Traefik labels? (Y/n): " input_traefik
        case "${input_traefik,,}" in
            y | yes | "") 
                TRAEFIK_ENABLED=true
                break
                ;;
            n | no)
                TRAEFIK_ENABLED=false
                break
                ;;
            *)
                log_error "Invalid input. Please enter Y or N."
                ;;
        esac
    done
    log_success "Traefik enabled?: $TRAEFIK_ENABLED"

    while true; do
        read -r -p "🚦 Use docker secrets, which is more secure? (Y/n): " input_secrets
        case "${input_secrets,,}" in
            y | yes | "") 
                USE_DOCKER_SECRETS=true
                break
                ;;
            n | no)
                USE_DOCKER_SECRETS=false
                break
                ;;
            *)
                log_error "Invalid input. Please enter Y or N."
                ;;
        esac
    done
    log_success "Using Docker Secrets enabled?: $USE_DOCKER_SECRETS"
    
    echo ""
}

configure_environment() {
    log_info "Verifying required tools..."

    for cmd in tr sed cp grep wc mkdir; do
        if ! command -v "$cmd" &>/dev/null; then
            log_error "$cmd is required but not found."
            exit 1
        fi
    done

    log_info "Generating secure secrets..."
    DB_PASSWORD=$(generate_secure_password 32)
    ADMIN_PASSWORD=$(generate_secure_password 24)
    SECRET_KEY=$(generate_secure_password 50)

    if [[ -z "$DB_PASSWORD" || -z "$ADMIN_PASSWORD" || -z "$SECRET_KEY" ]]; then
        log_error "❌ Failed to generate secure credentials"
        exit 1
    fi

    log_success "✅ Secrets generated: DB(${#DB_PASSWORD}), Admin(${#ADMIN_PASSWORD}), Key(${#SECRET_KEY})"

    FRONTEND_PORT="${FRONTEND_PORT:-8015}"
    BACKEND_PORT="${BACKEND_PORT:-8016}"
    FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-"http://localhost:$FRONTEND_PORT"}"
    BACKEND_URL="${BACKEND_URL:-"http://localhost:$BACKEND_PORT"}"
    CSRF_TRUSTED="$BACKEND_URL,$FRONTEND_ORIGIN"

    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "docker-compose.yml not found"
        exit 1
    fi

    cp docker-compose.yml docker-compose.yml.bak || {
        log_error "Failed to back up docker-compose.yml"
        exit 1
    }

    log_info "Applying configuration to docker-compose.yml..."

    # Handle Docker secrets if enabled
    if [[ "$USE_DOCKER_SECRETS" == "true" ]]; then
        log_info "Enabling Docker secrets..."

        mkdir -p .secrets

        # Save secrets to files
        echo "$DB_PASSWORD" > .secrets/postgres-password.secret || FINISHED_CORRECTLY=false
        echo "$SECRET_KEY" > .secrets/secret-key.secret || FINISHED_CORRECTLY=false
        echo "$ADMIN_PASSWORD" > .secrets/django-admin-password.secret || FINISHED_CORRECTLY=false

        # Uncomment secret references in docker-compose.yml
        sed -i '' -E \
            -e 's/^([[:space:]]*)#[[:space:]]*(secrets:)/\1\2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*( - postgres-password)/\1\2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*( - secret-key)/\1\2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*( - django-admin-password)/\1\2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*#( - email-host-password)/\1# \2/' \
            -e 's/^([[:space:]]*)#[[:space:]](secrets:[[:space:]]*#.*)/\1\2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*(postgres-password:)/\1  \2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*(file: .secrets\/postgres-password\.secret)/\1    \2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*(secret-key:)/\1  \2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*(file: .secrets\/secret-key\.secret)/\1    \2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*#[[:space:]]*(email-host-password:)/\1  # \2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*#[[:space:]]*(file: .secrets\/email-host-password\.secret)/\1  #   \2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*(django-admin-password:)/\1  \2/' \
            -e 's/^([[:space:]]*)#[[:space:]]*(file: .secrets\/django-admin-password\.secret)/\1    \2/' \
            docker-compose.yml || FINISHED_CORRECTLY=false
        # for swapping normal variables to secrets
        awk '
        {
            lines[NR] = $0

            # Match lines like: [whitespace]#[whitespace]VARIABLE_FILE:
            if ($0 ~ /^[[:space:]]*#[[:space:]]*[A-Z0-9_]+_FILE:/) {
                line = $0
                indent = line
                sub(/[^[:space:]]+.*/, "", indent) # Get leading whitespace

                # Remove leading `#` and any spaces after
                sub(/^[[:space:]]*#[[:space:]]*/, "", line)
                split(line, parts, ":")
                split(parts[1], name_parts, "_FILE")
                varname = name_parts[1]

                uncomment_line[NR] = indent line
                comment_var[varname] = 1
            }
        }
        END {
            for (i = 1; i <= NR; i++) {
                line = lines[i]

                # Replace commented *_FILE line with uncommented version (with indent)
                if (i in uncomment_line) {
                    print uncomment_line[i]
                    continue
                }

                # Comment out original VARIABLE: line if a *_FILE was found
                if (line ~ /^[[:space:]]*[A-Z0-9_]+:/) {
                    indent = line
                    sub(/[^[:space:]]+.*/, "", indent)
                    split(line, parts, ":")
                    var = parts[1]
                    gsub(/^[[:space:]]*/, "", var)

                    if (var in comment_var) {
                        print indent "# " substr(line, length(indent)+1)
                        continue
                    }
                }

                # Default: print line as-is
                print line
            }
        }
        ' docker-compose.yml > docker-compose.yml.tmp && {
            mv docker-compose.yml.tmp docker-compose.yml
        } || FINISHED_CORRECTLY=false

        # Handle email password secret comments
        awk '
        {
            lines[NR] = $0
        }

        END {
            for (i = 1; i <= NR; i++) {
                line1 = lines[i]
                line2 = lines[i + 1]

                # Match: line1 = single-commented VAR, line2 = double-commented VAR_FILE
                if (line1 ~ /^[[:space:]]*#[[:space:]]*[A-Z0-9_]+:[[:space:]]*/ &&
                    line2 ~ /^[[:space:]]*#[[:space:]]*#[[:space:]]*[A-Z0-9_]+_FILE:/) {

                    # Extract indent from line1
                    indent1 = line1
                    sub(/[^[:space:]]+.*/, "", indent1)

                    # Clean VAR line for recommenting
                    clean1 = line1
                    gsub(/^[[:space:]]*#[[:space:]]*/, "", clean1)

                    # Print double-commented VAR line
                    print indent1 "# # " clean1

                    # Extract indent from line2
                    indent2 = line2
                    sub(/[^[:space:]]+.*/, "", indent2)

                    # Clean VAR_FILE line to single-comment
                    clean2 = line2
                    gsub(/^[[:space:]]*#[[:space:]]*/, "", clean2) # Remove first #
                    gsub(/^[[:space:]]*#[[:space:]]*/, "", clean2) # Remove second #

                    # Print single-commented VAR_FILE line
                    print indent2 "# " clean2

                    i++ # Skip next line since we just processed it
                    continue
                }

                # Default: print original line
                print lines[i]
            }
        }
        ' docker-compose.yml > docker-compose.yml.tmp && {
            mv docker-compose.yml.tmp docker-compose.yml
        } || FINISHED_CORRECTLY=false

        log_success "Docker secrets configured"
    else
        # Default env var replacements (no secrets)
        sed -i '' -E \
            -e "s|^([[:space:]]*POSTGRES_PASSWORD:).*|\1 $DB_PASSWORD|" \
            -e "s|^([[:space:]]*DJANGO_ADMIN_PASSWORD:).*|\1 $ADMIN_PASSWORD|" \
            -e "s|^([[:space:]]*SECRET_KEY:).*|\1 $SECRET_KEY|" \
            -e "s|^([[:space:]]*EMAIL_HOST_PASSWORD:).*|\1 $EMAIL_HOST_PASSWORD|" \
            docker-compose.yml || FINISHED_CORRECTLY=false

        # if [[ "$USE_EMAIL" == "true" ]]; then
        # fi
    fi
        # Handle email config if enabled
    if [[ "$USE_EMAIL" == "true" ]]; then
        log_info "Enabling email configuration..."
        sed -i '' -E \
            -e "s/^([[:space:]]*)#[[:space:]]*(EMAIL_BACKEND:).*/\1\2 email/" \
            -e "s/^([[:space:]]*)#[[:space:]]*(EMAIL_HOST:).*/\1\2 $EMAIL_HOST/" \
            -e "s/^([[:space:]]*)#[[:space:]]*(EMAIL_USE_TLS:).*/\1\2 $EMAIL_USE_TLS/" \
            -e "s/^([[:space:]]*)#[[:space:]]*(EMAIL_PORT:).*/\1\2 $EMAIL_PORT/" \
            -e "s/^([[:space:]]*)#[[:space:]]*(EMAIL_USE_SSL:).*/\1\2 $EMAIL_USE_SSL/" \
            -e "s/^([[:space:]]*)#[[:space:]]*(EMAIL_HOST_USER:).*/\1\2 $EMAIL_HOST_USER/" \
            docker-compose.yml || FINISHED_CORRECTLY=false
        
        if [[ "$USE_DOCKER_SECRETS" == "true" ]]; then
            sed -i '' -E \
                -e "s/^([[:space:]]*)#[[:space:]]*(# EMAIL_HOST_PASSWORD:).*/\1\2/" \
                -e "s/^([[:space:]]*)#[[:space:]]*(EMAIL_HOST_PASSWORD_FILE:).*/\1\2 \/run\/secrets\/email-host-password/" \
                -e "s/^([[:space:]]*)#[[:space:]]*(- email-host-password)/\1 \2/" \
                -e "s/^([[:space:]]*)#[[:space:]]*(email-host-password:)/\1\2/" \
                -e "s/^([[:space:]]*)#[[:space:]]*(file: .secrets\/email-host-password\.secret)/\1  \2/" \
                docker-compose.yml || FINISHED_CORRECTLY=false
        else
            sed -i '' -E \
                -e "s/^([[:space:]]*)#[[:space:]]*(EMAIL_HOST_PASSWORD:).*/\1\2 $EMAIL_HOST_PASSWORD/" \
                docker-compose.yml || FINISHED_CORRECTLY=false
        fi

        log_success "Email configuration applied"
    fi

    # Replace other standard values
    sed -i '' -E \
        -e "s|^( *BACKEND_PORT:).*|\1 $BACKEND_PORT|" \
        -e "s|^( *FRONTEND_PORT:).*|\1 $FRONTEND_PORT|" \
        -e "s|^( *PUBLIC_URL:).*|\1 $BACKEND_URL|" \
        -e "s|^( *FRONTEND_URL:).*|\1 $FRONTEND_ORIGIN|" \
        -e "s|^( *ORIGIN:).*|\1 $FRONTEND_ORIGIN|" \
        -e "s|^( *CSRF_TRUSTED_ORIGINS:).*|\1 $CSRF_TRUSTED|" \
        -e "s|([[:space:]]+-[[:space:]]*\")([0-9]+)(:3000\")|\1$FRONTEND_PORT\3|" \
        -e "s|([[:space:]]+-[[:space:]]*\")([0-9]+)(:80\")|\1$BACKEND_PORT\3|" \
        docker-compose.yml || FINISHED_CORRECTLY=false

    if [[ "$TRAEFIK_ENABLED" == "true" ]]; then
        sed -i '' -E \
            -e 's/^([[:space:]]*)#([[:space:]]*labels:)/\1 \2/' \
            -e 's/^([[:space:]]*)#([[:space:]]*-?[[:space:]]*"traefik\..*")/\1 \2/' \
            docker-compose.yml || FINISHED_CORRECTLY=false
    fi

    if [[ "$FINISHED_CORRECTLY" == "false" ]]; then
        log_error "configuration failed"
        log_info "Restoring backup..."
        mv docker-compose.yml.bak docker-compose.yml
        exit 1
    fi

    log_success "docker-compose.yml updated"

    log_info "🔍 Verifying updated values in docker-compose.yml:"
    diff -y docker-compose.yml.bak docker-compose.yml || :

    # Basic verification of values present
    if [[ "$USE_DOCKER_SECRETS" == "false" ]]; then
        if grep -q "$DB_PASSWORD" docker-compose.yml && grep -q "$FRONTEND_PORT" docker-compose.yml && grep -q "$BACKEND_PORT" docker-compose.yml; then
            log_success "✅ Configuration verification passed"
        else
            log_warning "⚠️  Some configuration values may not have applied properly"
            log_info "Restoring backup for safety... (renaming auto-configured docker-compose.yml to docker-compose.yml.install)"
            mv docker-compose.yml docker-compose.yml.install
            mv docker-compose.yml.bak docker-compose.yml
            exit 1
        fi
    else
        if grep -q "postgres-password" docker-compose.yml && grep -q "$FRONTEND_PORT" docker-compose.yml && grep -q "$BACKEND_PORT" docker-compose.yml; then
            log_success "✅ Configuration verification passed"
        else
            log_warning "⚠️  Some configuration values may not have applied properly"
            log_info "Restoring backup for safety... (renaming auto-configured docker-compose.yml to docker-compose.yml.install)"
            mv docker-compose.yml docker-compose.yml.install
            mv docker-compose.yml.bak docker-compose.yml
            exit 1
        fi
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
