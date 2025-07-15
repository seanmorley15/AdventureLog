#!/bin/bash

# Function to check PostgreSQL availability
# Helper to get the first non-empty environment variable
get_env() {
  for var in "$@"; do
    value="${!var}"
    if [ -n "$value" ]; then
      echo "$value"
      return
    fi
  done
}

check_postgres() {
  local db_host
  local db_user
  local db_name
  local db_pass

  db_host=$(get_env PGHOST)
  db_user=$(get_env PGUSER POSTGRES_USER)
  db_name=$(get_env PGDATABASE POSTGRES_DB)
  db_pass=$(get_env PGPASSWORD POSTGRES_PASSWORD)

  PGPASSWORD="$db_pass" psql -h "$db_host" -U "$db_user" -d "$db_name" -c '\q' >/dev/null 2>&1
}


# Wait for PostgreSQL to become available
until check_postgres; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - continuing..."

# run sql commands
# psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -f /app/backend/init-postgis.sql

# Apply Django migrations
python manage.py migrate

# Create superuser if environment variables are set and there are no users present at all.
if [ -n "$DJANGO_ADMIN_USERNAME" ] && [ -n "$DJANGO_ADMIN_PASSWORD" ] && [ -n "$DJANGO_ADMIN_EMAIL" ]; then
  echo "Creating superuser..."
  python manage.py shell << EOF
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()

# Check if the user already exists
if not User.objects.filter(username='$DJANGO_ADMIN_USERNAME').exists():
    # Create the superuser
    superuser = User.objects.create_superuser(
        username='$DJANGO_ADMIN_USERNAME',
        email='$DJANGO_ADMIN_EMAIL',
        password='$DJANGO_ADMIN_PASSWORD'
    )
    print("Superuser created successfully.")

    # Create the EmailAddress object for AllAuth
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


# Sync the countries and world travel regions
# Sync the countries and world travel regions
python manage.py download-countries
if [ $? -eq 137 ]; then
  >&2 echo "WARNING: The download-countries command was interrupted. This is likely due to lack of memory allocated to the container or the host. Please try again with more memory."
  exit 1
fi

cat /code/adventurelog.txt

# Start Gunicorn in foreground
exec gunicorn main.wsgi:application \
    --bind [::]:8000 \
    --workers 2 \
    --timeout 120
