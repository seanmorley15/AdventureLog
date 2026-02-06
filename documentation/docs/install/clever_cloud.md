# Clever Cloud

Clever Cloud is a European PaaS (Platform as a Service) that allows you to deploy applications without managing servers. This guide walks you through deploying AdventureLog on Clever Cloud **without modifying the source code**.

## Prerequisites

- A [Clever Cloud](https://www.clever-cloud.com/) account
- [Clever Cloud CLI](https://www.clever-cloud.com/doc/cli/) installed
- Git installed
- **A custom domain** (required - see note below)

Custom Domain Required

The default `*.cleverapps.io` domains **will not work**. The `cleverapps.io` domain is on the [Public Suffix List](https://publicsuffix.org/), which prevents session cookies from being shared between applications.

You must use a custom domain where both apps share a parent domain:
- `adventurelog.your-domain.com` (frontend)
- `api.adventurelog.your-domain.com` (backend)

## Architecture

| Component | Size | Description |
|-----------|------|-------------|
| Frontend | XS (runtime) / M (build) | SvelteKit application |
| Backend | XS | Django REST API |
| PostgreSQL | S | Database |
| FS Bucket | - | Media storage (persistent) |
| Mailpace | - | Transactional emails (optional) |

## Step 1: Clone the Repository

```bash
git clone https://github.com/seanmorley15/AdventureLog.git
cd AdventureLog
```

## Step 2: Create the Applications

```bash
# Python backend
clever create --type python adventurelog-backend

# Node.js frontend
clever create --type node adventurelog-frontend

# Link applications
clever link adventurelog-backend --alias adventurelog-backend
clever link adventurelog-frontend --alias adventurelog-frontend
```

## Step 3: Create Add-ons

```bash
# PostgreSQL
clever addon create postgresql-addon adventurelog-postgres --plan s_sml --link adventurelog-backend

# FS Bucket for media files
clever addon create fs-bucket adventurelog-media --link adventurelog-backend

# Mailpace for emails (optional)
clever addon create mailpace adventurelog-email --link adventurelog-backend
```

## Step 4: Configure Custom Domains

```bash
# Replace with your domain
clever domain add adventurelog.your-domain.com --alias adventurelog-frontend
clever domain add api.adventurelog.your-domain.com --alias adventurelog-backend
```

Configure CNAME DNS records with your domain registrar.

## Step 5: Configure Instance Sizes

```bash
# Frontend: build on M, runtime on XS
clever scale --alias adventurelog-frontend --flavor XS --build-flavor M

# Backend: XS is sufficient
clever scale --alias adventurelog-backend --flavor XS
```

## Step 6: Backend Environment Variables

### Clever Cloud Configuration

```bash
clever env set --alias adventurelog-backend APP_FOLDER "backend/server"
clever env set --alias adventurelog-backend CC_PYTHON_VERSION "3"
clever env set --alias adventurelog-backend CC_PYTHON_MODULE "main.wsgi:application"
clever env set --alias adventurelog-backend CC_PRE_RUN_HOOK "memcached -u nobody -m 64 -p 11211 -d"
clever env set --alias adventurelog-backend CC_PYTHON_MANAGE_TASKS "collectstatic --noinput, migrate --noinput, download-countries --force"
```

### Django Configuration

```bash
clever env set --alias adventurelog-backend SECRET_KEY "$(openssl rand -base64 32)"
clever env set --alias adventurelog-backend DEBUG "False"
clever env set --alias adventurelog-backend DISABLE_REGISTRATION "False"

# URLs (replace your-domain.com with your domain)
clever env set --alias adventurelog-backend PUBLIC_URL "https://api.your-domain.com"
clever env set --alias adventurelog-backend FRONTEND_URL "https://your-domain.com"
clever env set --alias adventurelog-backend CSRF_TRUSTED_ORIGINS "https://your-domain.com,https://api.your-domain.com"
```

### Automatic Add-on Variable Mapping

These commands automatically retrieve values injected by Clever Cloud add-ons:

```bash
# === PostgreSQL: map addon variables to PG* ===
clever env set --alias adventurelog-backend PGHOST "$(clever env --alias adventurelog-backend --format json | jq -r '.env[] | select(.name=="POSTGRESQL_ADDON_HOST") | .value')"
clever env set --alias adventurelog-backend PGDATABASE "$(clever env --alias adventurelog-backend --format json | jq -r '.env[] | select(.name=="POSTGRESQL_ADDON_DB") | .value')"
clever env set --alias adventurelog-backend PGUSER "$(clever env --alias adventurelog-backend --format json | jq -r '.env[] | select(.name=="POSTGRESQL_ADDON_USER") | .value')"
clever env set --alias adventurelog-backend PGPASSWORD "$(clever env --alias adventurelog-backend --format json | jq -r '.env[] | select(.name=="POSTGRESQL_ADDON_PASSWORD") | .value')"
clever env set --alias adventurelog-backend PGPORT "$(clever env --alias adventurelog-backend --format json | jq -r '.env[] | select(.name=="POSTGRESQL_ADDON_PORT") | .value')"

# === FS Bucket: build CC_FS_BUCKET with BUCKET_HOST ===
clever env set --alias adventurelog-backend CC_FS_BUCKET "backend/server/media:$(clever env --alias adventurelog-backend --format json | jq -r '.env[] | select(.name=="BUCKET_HOST") | .value')"

# === Nginx serves media files directly ===
clever env set --alias adventurelog-backend STATIC_FILES_PATH "backend/server/media"
clever env set --alias adventurelog-backend STATIC_URL_PREFIX "/media"
```

## Step 7: Frontend Environment Variables

```bash
clever env set --alias adventurelog-frontend APP_FOLDER "frontend"
clever env set --alias adventurelog-frontend CC_NODE_BUILD_TOOL "pnpm"
clever env set --alias adventurelog-frontend CC_NODE_DEV_DEPENDENCIES "install"
clever env set --alias adventurelog-frontend CC_POST_BUILD_HOOK "cd frontend && pnpm run build"
clever env set --alias adventurelog-frontend CC_RUN_COMMAND "cd frontend && node build"

# Configuration (replace with your custom domain)
clever env set --alias adventurelog-frontend ORIGIN "https://adventurelog.your-domain.com"
clever env set --alias adventurelog-frontend PUBLIC_SERVER_URL "https://api.adventurelog.your-domain.com"
clever env set --alias adventurelog-frontend BODY_SIZE_LIMIT "Infinity"
```

## Step 8: Email Configuration (Optional)

If you created the Mailpace add-on:

```bash
clever env set --alias adventurelog-backend EMAIL_BACKEND "email"
clever env set --alias adventurelog-backend EMAIL_HOST "smtp.mailpace.com"
clever env set --alias adventurelog-backend EMAIL_PORT "587"
clever env set --alias adventurelog-backend EMAIL_USE_TLS "True"
clever env set --alias adventurelog-backend EMAIL_USE_SSL "False"

# Automatically map Mailpace token
clever env set --alias adventurelog-backend EMAIL_HOST_USER "$(clever env --alias adventurelog-backend --format json | jq -r '.env[] | select(.name=="MAILPACE_API_TOKEN") | .value')"
clever env set --alias adventurelog-backend EMAIL_HOST_PASSWORD "$(clever env --alias adventurelog-backend --format json | jq -r '.env[] | select(.name=="MAILPACE_API_TOKEN") | .value')"

# Replace with your verified domain in Mailpace
clever env set --alias adventurelog-backend DEFAULT_FROM_EMAIL "noreply@your-verified-domain.com"
```

## Step 9: Deploy

```bash
# Backend first
clever deploy --alias adventurelog-backend

# Then frontend
clever deploy --alias adventurelog-frontend
```

## Step 10: Create Superuser

After the first deployment, manually create the admin account:

```bash
clever ssh --alias adventurelog-backend
cd backend/server
python manage.py createsuperuser
```

## Verification

```bash
clever status --alias adventurelog-backend
clever status --alias adventurelog-frontend
```

## Accessing the Application

| URL | Description |
|-----|-------------|
| `https://adventurelog.your-domain.com` | Main application |
| `https://api.adventurelog.your-domain.com/admin` | Django admin panel |

## Updating

To update AdventureLog:

```bash
git pull origin main
clever deploy --alias adventurelog-backend
clever deploy --alias adventurelog-frontend
```

No Git Conflicts

This configuration does not modify the AdventureLog source code. You can update without conflicts.

## Quick Reference - Environment Variables

Two Methods Available
- **CLI (recommended)**: Use the `jq` commands from steps 6-8 to automatically map add-on variables.
- **Web Interface**: Copy the blocks below and manually replace `REPLACE_*` values in the Clever Cloud console.

### Backend (Python)

```bash
# ============================================
# CLEVER CLOUD CONFIGURATION
# ============================================

# Django application folder
APP_FOLDER="backend/server"

# Python version
CC_PYTHON_VERSION="3"

# Django WSGI module
CC_PYTHON_MODULE="main.wsgi:application"

# Start memcached before the app (required by AdventureLog)
CC_PRE_RUN_HOOK="memcached -u nobody -m 64 -p 11211 -d"

# Django commands executed on deployment
CC_PYTHON_MANAGE_TASKS="collectstatic --noinput, migrate --noinput, download-countries"

# ============================================
# MEDIA STORAGE (FS BUCKET)
# ============================================

# Bucket mount for media files
# REPLACE: bucket-xxxxx with your BUCKET_HOST (clever env | grep BUCKET_HOST)
CC_FS_BUCKET="backend/server/media:REPLACE_BUCKET_HOST"

# Nginx serves media files directly (bypasses Django)
STATIC_FILES_PATH="backend/server/media"
STATIC_URL_PREFIX="/media"

# ============================================
# POSTGRESQL DATABASE
# ============================================

# REPLACE: with your PostgreSQL add-on values
# (clever env | grep POSTGRESQL)
PGHOST="REPLACE_HOST"
PGDATABASE="REPLACE_DATABASE"
PGUSER="REPLACE_USER"
PGPASSWORD="REPLACE_PASSWORD"
PGPORT="REPLACE_PORT"

# ============================================
# DJANGO CONFIGURATION
# ============================================

# Django secret key (generate with: openssl rand -base64 32)
SECRET_KEY="REPLACE_GENERATE_SECRET_KEY"

# Debug mode disabled in production
DEBUG="False"

# Allow registrations
DISABLE_REGISTRATION="False"

# ============================================
# URLs (REPLACE WITH YOUR DOMAIN)
# ============================================

# Backend public URL
PUBLIC_URL="https://api.REPLACE_DOMAIN.com"

# Frontend URL
FRONTEND_URL="https://REPLACE_DOMAIN.com"

# Allowed CSRF origins
CSRF_TRUSTED_ORIGINS="https://REPLACE_DOMAIN.com,https://api.REPLACE_DOMAIN.com"

# ============================================
# EMAIL (OPTIONAL - Mailpace)
# ============================================

# Uncomment and configure if using Mailpace
# EMAIL_BACKEND="email"
# EMAIL_HOST="smtp.mailpace.com"
# EMAIL_PORT="587"
# EMAIL_USE_TLS="True"
# EMAIL_USE_SSL="False"
# EMAIL_HOST_USER="REPLACE_MAILPACE_API_TOKEN"
# EMAIL_HOST_PASSWORD="REPLACE_MAILPACE_API_TOKEN"
# DEFAULT_FROM_EMAIL="noreply@REPLACE_VERIFIED_DOMAIN.com"
```

### Frontend (Node.js)

```bash
# ============================================
# CLEVER CLOUD CONFIGURATION
# ============================================

# Frontend application folder
APP_FOLDER="frontend"

# Use pnpm as package manager
CC_NODE_BUILD_TOOL="pnpm"

# Install dev dependencies
CC_NODE_DEV_DEPENDENCIES="install"

# Build command (runs on M instance)
CC_POST_BUILD_HOOK="cd frontend && pnpm run build"

# Start command (runs on XS instance)
CC_RUN_COMMAND="cd frontend && node build"

# ============================================
# SVELTEKIT CONFIGURATION
# ============================================

# Frontend origin URL (REPLACE WITH YOUR DOMAIN)
ORIGIN="https://REPLACE_DOMAIN.com"

# Backend API URL (REPLACE WITH YOUR DOMAIN)
PUBLIC_SERVER_URL="https://api.REPLACE_DOMAIN.com"

# No size limit for uploads
BODY_SIZE_LIMIT="Infinity"
```

---

## Troubleshooting

### Login Not Working

**Cause:** You are using the default `*.cleverapps.io` domains.

**Solution:** Use a custom domain (required).

### Images/Media Not Loading

Verify these variables are set:
```bash
clever env --alias adventurelog-backend | grep -E "(STATIC_FILES_PATH|STATIC_URL_PREFIX|CC_FS_BUCKET)"
```

### Memcached Error

Verify `CC_PRE_RUN_HOOK` is configured:
```bash
clever env --alias adventurelog-backend | grep CC_PRE_RUN_HOOK
# Should display: CC_PRE_RUN_HOOK="memcached -u nobody -m 64 -p 11211 -d"
```

### Missing Country Data

Redeploy to re-run `download-countries`:
```bash
clever restart --alias adventurelog-backend --without-cache
```

## Cost Estimation

| Component | Size | Estimated Cost/Month |
|-----------|------|----------------------|
| Frontend (runtime) | XS | ~5€ |
| Frontend (build) | M (temporary) | ~0.50€ |
| Backend | XS | ~5€ |
| PostgreSQL | S | ~10€ |
| FS Bucket | - | ~2€ |
| Mailpace | - | Free tier |
| **Total** | | **~22.50€/month** |

*Prices are estimates. Check [Clever Cloud pricing](https://www.clever-cloud.com/pricing/) for current rates.*
