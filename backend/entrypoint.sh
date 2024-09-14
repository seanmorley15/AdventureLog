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
if [ -n "$DJANGO_ADMIN_USERNAME" ] && [ -n "$DJANGO_ADMIN_PASSWORD" ]; then
  echo "Creating superuser..."
  python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if User.objects.count() == 0:
    User.objects.create_superuser('$DJANGO_ADMIN_USERNAME', '$DJANGO_ADMIN_EMAIL', '$DJANGO_ADMIN_PASSWORD')
    print("Superuser created successfully.")
else:
    print("Superuser already exists.")
EOF
fi

# Sync the countries and world travel regions
python manage.py download-countries

# Start Django server
python manage.py runserver 0.0.0.0:8000
