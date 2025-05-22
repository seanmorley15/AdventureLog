#!/bin/bash

# Function to check PostgreSQL availability
check_postgres() {
  PGPASSWORD=$PGPASSWORD psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -c '\q' >/dev/null 2>&1
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
python manage.py download-countries
if [ $? -eq 137 ]; then
  >&2 echo "WARNING: The download-countries command was interrupted. This is likely due to lack of memory allocated to the container or the host. Please try again with more memory."
  exit 1
fi

# Sync the translations if $COUNTRY_TRANSLATIONS is true
if [ -n "$COUNTRY_TRANSLATIONS" -a "$COUNTRY_TRANSLATIONS" = "true" ]; then
  echo "Syncing translations for countries..."
  # Get the translations for all countries
  python manage.py cities --import=country
  # Get the translations for all alt names
  python manage.py cities --import=alt_name
  # Get the translations for all countries
  python manage.py get-translations
fi

cat /code/adventurelog.txt

# Start Gunicorn in foreground
exec gunicorn main.wsgi:application \
    --bind [::]:8000 \
    --workers 2 \
    --timeout 120
