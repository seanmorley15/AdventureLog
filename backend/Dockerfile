# Stage 1: Build stage with dependencies
FROM python:3.13-slim AS builder

# Metadata labels
LABEL maintainer="Sean Morley" \
      version="0.10.0" \
      description="AdventureLog — the ultimate self-hosted travel companion." \
      org.opencontainers.image.title="AdventureLog" \
      org.opencontainers.image.description="AdventureLog helps you plan, track, and share your adventures." \
      org.opencontainers.image.version="0.10.0" \
      org.opencontainers.image.authors="Sean Morley" \
      org.opencontainers.image.source="https://github.com/seanmorley15/AdventureLog" \
      org.opencontainers.image.vendor="Sean Morley" \
      org.opencontainers.image.licenses="GPL-3.0"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies needed for build
RUN apt-get update && apt-get install -y --no-install-recommends \
      git \
      postgresql-client \
      gdal-bin \
      libgdal-dev \
      nginx \
      memcached \
      supervisor \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ./server/requirements.txt /code/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Stage 2: Final image with runtime dependencies
FROM python:3.13-slim
WORKDIR /code
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies (including GDAL)
RUN apt-get update && apt-get install -y --no-install-recommends \
      postgresql-client \
      gdal-bin \
      libgdal-dev \
      nginx \
      memcached \
      supervisor \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project code and configs
COPY ./server /code/
COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY ./entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh \
    && mkdir -p /code/static /code/media

# Collect static files
RUN python3 manage.py collectstatic --noinput --verbosity 2

# Expose ports
EXPOSE 80 8000

# Start Supervisor
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
