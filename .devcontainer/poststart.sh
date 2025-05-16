#!/bin/bash

set -a # Make sure to export vars to the whole environment
source ./.devcontainer/.env
set +a

# Run PostGIS with "docker in docker" on port 5432
docker run --rm --name adventurelog-devdb -e POSTGRES_USER -e POSTGRES_PASSWORD -e POSTGRES_DB -p 5432:5432 -d postgis/postgis:15-3.3

cd ./backend/server

# Function to check PostgreSQL availability
check_postgres() {
  psql -c '\q' >/dev/null 2>&1
}

# Wait for PostgreSQL to become available
until check_postgres; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - continuing..."

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
mkdir media
python manage.py download-countries
if [ $? -eq 137 ]; then
  >&2 echo "WARNING: The download-countries command was interrupted. This is likely due to lack of memory allocated to the container or the host. Please try again with more memory."
  exit 1
fi

# Run backend in dev mode
nohup $SHELL -c "python manage.py runserver 2>&1 | tee -a /tmp/servers.log >> /tmp/backend.log" > /dev/null &

cd ../../frontend

# Run frontend in dev mode
nohup $SHELL -c "npm run dev 2>&1 | tee -a /tmp/servers.log >> /tmp/frontend.log" > /dev/null &
