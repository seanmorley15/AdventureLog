#!/bin/bash

# Install dependencies for backend and poststart.sh
sudo apt update && sudo apt install -y python3-gdal postgresql-client
pip install -r ./backend/server/requirements.txt
cd ./backend/server
# Create static files on backend
python manage.py collectstatic --noinput
cd ../../frontend
# Install frontend dependencies
npm install