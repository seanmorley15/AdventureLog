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
	if [[ -n "${DJANGO_ADMIN_USERNAME:-}" && -n "${DJANGO_ADMIN_PASSWORD:-}" && -n "${DJANGO_ADMIN_EMAIL:-}" ]]; then
		echo "Creating superuser..."
		python manage.py shell <<EOF
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()

if not User.objects.filter(username='$DJANGO_ADMIN_USERNAME').exists():
    superuser = User.objects.create_superuser(
        username='$DJANGO_ADMIN_USERNAME',
        email='$DJANGO_ADMIN_EMAIL',
        password='$DJANGO_ADMIN_PASSWORD'
    )
    print("Superuser created successfully.")
    EmailAddress.objects.create(
        user=superuser,
        email='$DJANGO_ADMIN_EMAIL',
        verified=True,
        primary=True
    )
    print("EmailAddress object created successfully for AllAuth.")
else:
    print("Superuser already exists.")
EOF
	fi
}

run_download_countries() {
	if [[ "${SKIP_WORLD_DATA:-}" == "1" ]]; then
		>&2 echo "SKIP_WORLD_DATA=1 — skipping download-countries"
		return 0
	fi

	>&2 echo "Running download-countries (first boot may take several minutes; ensure ~2GB RAM is available)..."
	python manage.py download-countries
	local download_exit=$?
	if [[ "$download_exit" -eq 137 ]]; then
		>&2 echo "WARNING: download-countries was interrupted (likely out of memory). Retry with more RAM or set SKIP_WORLD_DATA=1."
		exit 1
	elif [[ "$download_exit" -ne 0 ]]; then
		>&2 echo "ERROR: download-countries failed."
		exit 1
	fi
}

finalize_startup() {
	if [[ -f /code/adventurelog.txt ]]; then
		cat /code/adventurelog.txt
	fi

	/code/scripts/write-cron-env.sh
}
