# Use the official Python slim image as the base image
FROM python:3.13-slim

# Metadata labels for the AdventureLog image
LABEL maintainer="Sean Morley" \
      version="v0.10.0" \
      description="AdventureLog — the ultimate self-hosted travel companion." \
      org.opencontainers.image.title="AdventureLog" \
      org.opencontainers.image.description="AdventureLog is a self-hosted travel companion that helps you plan, track, and share your adventures." \
      org.opencontainers.image.version="v0.10.0" \
      org.opencontainers.image.authors="Sean Morley" \
      org.opencontainers.image.url="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/banner.png" \
      org.opencontainers.image.source="https://github.com/seanmorley15/AdventureLog" \
      org.opencontainers.image.vendor="Sean Morley" \
      org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
      org.opencontainers.image.licenses="GPL-3.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /code

# Install system dependencies (Nginx included)
RUN apt-get update \
    && apt-get install -y git postgresql-client gdal-bin libgdal-dev nginx memcached supervisor \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ./server/requirements.txt /code/
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Create necessary directories
RUN mkdir -p /code/static /code/media
# RUN mkdir -p /code/staticfiles /code/media

# Copy the Django project code into the Docker image
COPY ./server /code/

# Copy Nginx configuration
COPY ./nginx.conf /etc/nginx/nginx.conf

# Copy Supervisor configuration
COPY ./supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Collect static files
RUN python3 manage.py collectstatic --noinput --verbosity 2

# Set the entrypoint script
COPY ./entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh

# Expose ports for NGINX and Gunicorn
EXPOSE 80 8000

# Command to start Supervisor (which starts Nginx and Gunicorn)
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
