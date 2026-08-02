#!/bin/bash
# Validate AdventureLog .env configuration for common self-hosting mistakes.
set -uo pipefail

ENV_FILE="${1:-.env}"
WARNINGS=0
ERRORS=0

warn() {
	echo "WARNING: $1" >&2
	WARNINGS=$((WARNINGS + 1))
}

error() {
	echo "ERROR: $1" >&2
	ERRORS=$((ERRORS + 1))
}

if [[ ! -f "$ENV_FILE" ]]; then
	error "Environment file not found: $ENV_FILE"
	exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

echo "Validating $ENV_FILE ..."

IS_STANDARD_DEPLOYMENT=false
case "$(basename "$ENV_FILE")" in
	.env.aio)
		IS_STANDARD_DEPLOYMENT=true
		;;
esac

# Standard Deployment uses SITE_URL without separate frontend/backend URL vars.
if [[ "$IS_STANDARD_DEPLOYMENT" != true ]] && [[ -z "${ORIGIN:-}" && -z "${PUBLIC_URL:-}" && -z "${FRONTEND_URL:-}" ]]; then
	IS_STANDARD_DEPLOYMENT=true
fi

if [[ "$IS_STANDARD_DEPLOYMENT" == true ]]; then
	if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
		error "POSTGRES_PASSWORD is required in $ENV_FILE"
	fi
	if [[ "${POSTGRES_PASSWORD:-changeme123}" == "changeme123" ]]; then
		warn "Default POSTGRES_PASSWORD detected — change this for production"
	fi
	if [[ -n "${SITE_URL:-}" ]] && [[ "$SITE_URL" != http://* ]] && [[ "$SITE_URL" != https://* ]]; then
		warn "SITE_URL should start with http:// or https://"
	fi
	if [[ "${DJANGO_ADMIN_PASSWORD:-admin}" == "admin" ]] && [[ "${DJANGO_ADMIN_USERNAME:-admin}" == "admin" ]]; then
		warn "Default admin credentials (admin/admin) detected — change for production"
	fi
	if [[ "${MEDIA_STORAGE:-local}" == "s3" ]]; then
		if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]] || [[ -z "${AWS_SECRET_ACCESS_KEY:-}" ]] || [[ -z "${AWS_STORAGE_BUCKET_NAME:-}" ]]; then
			error "MEDIA_STORAGE=s3 requires AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_STORAGE_BUCKET_NAME"
		fi
	fi
	if [[ "${EMAIL_BACKEND:-}" == "email" ]]; then
		if [[ -z "${EMAIL_HOST:-}" ]] || [[ -z "${EMAIL_HOST_USER:-}" ]] || [[ -z "${EMAIL_HOST_PASSWORD:-}" ]]; then
			error "EMAIL_BACKEND=email requires EMAIL_HOST, EMAIL_HOST_USER, and EMAIL_HOST_PASSWORD"
		fi
	fi
	if [[ "${DEBUG:-False}" == "True" ]] || [[ "${DEBUG:-False}" == "true" ]]; then
		warn "DEBUG is enabled — disable for production"
	fi
	echo ""
	if [[ $ERRORS -gt 0 ]]; then
		echo "Validation failed: $ERRORS error(s), $WARNINGS warning(s)"
		exit 1
	fi
	if [[ $WARNINGS -gt 0 ]]; then
		echo "Validation passed with $WARNINGS warning(s)"
		exit 0
	fi
	echo "Validation passed"
	exit 0
fi

if [[ -z "${PUBLIC_SERVER_URL:-}" ]]; then
	warn "PUBLIC_SERVER_URL is not set (default http://server:8000 is expected in Docker)"
elif [[ "$PUBLIC_SERVER_URL" == *"localhost:8016"* ]] || [[ "$PUBLIC_SERVER_URL" == *"127.0.0.1:8016"* ]]; then
	error "PUBLIC_SERVER_URL points at the host-mapped backend port. Use http://server:8000 inside Docker."
elif [[ "$PUBLIC_SERVER_URL" != *":8000"* ]] && [[ "$PUBLIC_SERVER_URL" != "http://server:8000" ]]; then
	warn "PUBLIC_SERVER_URL is '$PUBLIC_SERVER_URL' — Advanced Deployment installs should use http://server:8000"
fi

if [[ -n "${SITE_URL:-}" ]]; then
	echo "SITE_URL is set — individual URL vars will be derived when not explicitly set."
fi

if [[ -z "${CSRF_TRUSTED_ORIGINS:-}" ]] && [[ -z "${SITE_URL:-}" ]]; then
	warn "CSRF_TRUSTED_ORIGINS is not set and SITE_URL is not set"
fi

if [[ -n "${CSRF_TRUSTED_ORIGINS:-}" ]] && [[ -z "${SITE_URL:-}" ]]; then
	IFS=',' read -ra ORIGINS <<< "$CSRF_TRUSTED_ORIGINS"
	if [[ -n "${ORIGIN:-}" ]] && [[ ! "$CSRF_TRUSTED_ORIGINS" == *"$ORIGIN"* ]]; then
		warn "CSRF_TRUSTED_ORIGINS does not include ORIGIN ($ORIGIN)"
	fi
	if [[ -n "${FRONTEND_URL:-}" ]] && [[ ! "$CSRF_TRUSTED_ORIGINS" == *"$FRONTEND_URL"* ]]; then
		warn "CSRF_TRUSTED_ORIGINS does not include FRONTEND_URL ($FRONTEND_URL)"
	fi
	if [[ -n "${PUBLIC_URL:-}" ]] && [[ ! "$CSRF_TRUSTED_ORIGINS" == *"$PUBLIC_URL"* ]]; then
		warn "CSRF_TRUSTED_ORIGINS does not include PUBLIC_URL ($PUBLIC_URL)"
	fi
fi

if [[ -n "${PUBLIC_URL:-}" ]] && [[ -n "${FRONTEND_URL:-}" ]]; then
	public_scheme="${PUBLIC_URL%%://*}"
	frontend_scheme="${FRONTEND_URL%%://*}"
	if [[ "$public_scheme" != "$frontend_scheme" ]]; then
		warn "PUBLIC_URL ($public_scheme) and FRONTEND_URL ($frontend_scheme) use different schemes"
	fi
fi

if [[ -n "${FRONTEND_PORT:-}" ]] && [[ -n "${ORIGIN:-}" ]]; then
	if [[ "$ORIGIN" == *":$FRONTEND_PORT"* ]] || [[ "$ORIGIN" != *":"* && "$FRONTEND_PORT" == "80" ]]; then
		:
	else
		warn "ORIGIN ($ORIGIN) may not match FRONTEND_PORT ($FRONTEND_PORT)"
	fi
fi

if [[ -n "${BACKEND_PORT:-}" ]] && [[ -n "${PUBLIC_URL:-}" ]]; then
	if [[ "$PUBLIC_URL" == *":$BACKEND_PORT"* ]] || [[ "$PUBLIC_URL" != *":"* && "$BACKEND_PORT" == "80" ]]; then
		:
	else
		warn "PUBLIC_URL ($PUBLIC_URL) may not match BACKEND_PORT ($BACKEND_PORT)"
	fi
fi

if [[ "${POSTGRES_PASSWORD:-changeme123}" == "changeme123" ]] || [[ "${SECRET_KEY:-changeme123}" == "changeme123" ]]; then
	warn "Default POSTGRES_PASSWORD or SECRET_KEY detected — change these for production"
fi

echo ""
if [[ $ERRORS -gt 0 ]]; then
	echo "Validation failed: $ERRORS error(s), $WARNINGS warning(s)"
	exit 1
fi

if [[ $WARNINGS -gt 0 ]]; then
	echo "Validation passed with $WARNINGS warning(s)"
	exit 0
fi

echo "Validation passed"
exit 0
