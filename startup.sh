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
# Example: node build/index.js
# Print message
echo "Starting AdventureLog"

# Wait for the database to start up
wait_for_db

# generate the schema
npm run generate

# Run database migration
npm run migrate

# Start the application
node build/index.js
