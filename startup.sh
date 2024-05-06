#!/bin/sh

# Function to check if the database is ready
wait_for_db() {
    echo "Waiting for the database to start up..."
    while ! nc -z db 5432; do
        sleep 1
    done
    echo "Database is now available."
}

# Start your application here
# Print message
echo "Starting AdventureLog"

# Wait for the database to start up
if [ -z "$SKIP_DB_WAIT" ] || [ "$SKIP_DB_WAIT" = "false" ]; then
    wait_for_db
fi

# Run database migration
npm run migrate

echo "The origin to be set is: $ORIGIN"
# Start the application
ORIGIN=$ORIGIN node build
