#!/bin/sh

# Function to check if the database is ready
wait_for_db() {
    echo "Waiting for the database to start up..."
    while ! nc -z db 5432; do
        sleep 1
    done
    echo "Database is now available."
}

# Function to run SQL scripts
run_sql_scripts() {
    echo "Running SQL scripts..."

    # Define the path to your SQL scripts
    SQL_SCRIPTS_PATH="/sql"  # Replace with the path to your SQL scripts

    # Run each SQL script in the directory using the DATABASE_URL
    for sql_script in "$SQL_SCRIPTS_PATH"/*.sql; do
        echo "Running script: $sql_script"
        psql "$DATABASE_URL" -f "$sql_script"
    done
    echo "Finished running SQL scripts."
}

# Start your application here
# Print message
echo "Starting AdventureLog"

# Wait for the database to start up
wait_for_db

# generate the schema
npm run generate

# Run database migration
npm run migrate

# Run SQL scripts
run_sql_scripts

echo "The origin to be set is: $ORIGIN"
# Start the application
ORIGIN=$ORIGIN node build
