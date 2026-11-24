#!/bin/bash
# Shared startup tasks for backend and Standard Deployment containers.
# Source from entrypoint.sh after environment variables are configured.

get_env() {
	local var value
	for var in "$@"; do
		value="$(printenv "$var" 2>/dev/null || true)"
		if [[ -n "$value" ]]; then
			echo "$value"
			return
		fi
	done
}

check_postgres() {
	local db_host db_user db_name db_pass

	db_host=$(get_env PGHOST)
	db_user=$(get_env POSTGRES_USER PGUSER)
	db_name=$(get_env POSTGRES_DB PGDATABASE)
	db_pass=$(get_env POSTGRES_PASSWORD PGPASSWORD)

	PGPASSWORD="$db_pass" psql -h "$db_host" -U "$db_user" -d "$db_name" -c '\q' >/dev/null 2>&1
}

wait_for_postgres() {
	until check_postgres; do
		>&2 echo "PostgreSQL is unavailable - sleeping"
		sleep 1
	done
	>&2 echo "PostgreSQL is up - continuing..."
}

run_migrations() {
	python manage.py migrate
}

create_superuser_if_needed() {
	# A missing or weak DJANGO_ADMIN_PASSWORD (such as the old admin/admin default) is replaced by
	# a random one, printed once below, so a fresh install never has a guessable superuser.
	# DJANGO_ADMIN_ALLOW_WEAK_PASSWORD=true keeps a weak one for throwaway test stacks.
	if [[ -n "${DJANGO_ADMIN_USERNAME:-}" && -n "${DJANGO_ADMIN_EMAIL:-}" ]]; then
		# Credentials are read from the environment inside Python, never pasted into the code,
		# so quotes or other special characters in a password cannot break startup.
		# Create the env user only on first boot. Later starts must not insert again when
		# the configured username changed but the email is still taken by an existing admin.
		python manage.py shell <<'EOF'
import os
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import get_password_validators, validate_password
from django.core.exceptions import ValidationError
from allauth.account.models import EmailAddress

User = get_user_model()

username = os.environ['DJANGO_ADMIN_USERNAME']
email = os.environ['DJANGO_ADMIN_EMAIL']
password = os.environ.get('DJANGO_ADMIN_PASSWORD', '')
allow_weak = os.environ.get('DJANGO_ADMIN_ALLOW_WEAK_PASSWORD', '').lower() == 'true'

ADMIN_PASSWORD_VALIDATORS = get_password_validators([
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
])


def password_problem(candidate):
    if not candidate:
        return 'DJANGO_ADMIN_PASSWORD is not set'
    try:
        validate_password(candidate, User(username=username, email=email), ADMIN_PASSWORD_VALIDATORS)
    except ValidationError as exc:
        return 'DJANGO_ADMIN_PASSWORD is too weak (' + ' '.join(exc.messages) + ')'
    return None


if User.objects.filter(is_superuser=True).exists():
    print("Superuser already exists.")
else:
    problem = password_problem(password)
    generated = False
    if problem and not (allow_weak and password):
        password = secrets.token_urlsafe(18)
        generated = True
    print("Creating superuser...")
    superuser = User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print("Superuser created successfully.")
    EmailAddress.objects.create(
        user=superuser,
        email=email,
        verified=True,
        primary=True
    )
    print("EmailAddress object created successfully for AllAuth.")
    if generated:
        bar = '=' * 72
        print(bar)
        print(f"{problem}, so a random password was generated.")
        print(f"  Admin username: {username}")
        print(f"  Admin password: {password}")
        print("It is shown only this once. Sign in and change it under Settings.")
        print(bar)
    elif problem:
        print(f"WARNING: {problem}. Kept because DJANGO_ADMIN_ALLOW_WEAK_PASSWORD=true; never use this in production.")
EOF
	fi
}

run_download_countries() {
	if [[ "${SKIP_WORLD_DATA:-}" == "1" ]]; then
		>&2 echo "SKIP_WORLD_DATA=1 — skipping download_countries"
		return 0
	fi

	>&2 echo "Running download_countries (first boot may take several minutes; ensure ~2GB RAM is available)..."
	python manage.py download_countries
	local download_exit=$?
	if [[ "$download_exit" -eq 137 ]]; then
		>&2 echo "WARNING: download_countries was interrupted (likely out of memory). Retry with more RAM or set SKIP_WORLD_DATA=1."
		exit 1
	elif [[ "$download_exit" -ne 0 ]]; then
		>&2 echo "ERROR: download_countries failed."
		exit 1
	fi
}

finalize_startup() {
	if [[ -f /code/adventurelog.txt ]]; then
		cat /code/adventurelog.txt
	fi

}
