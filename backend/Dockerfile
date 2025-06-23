# -------------------
# Stage 1: Build Stage
# -------------------
FROM docker.io/python:3.13-alpine AS builder

# Build-time metadata
ARG GIT_SHA=unknown
ARG GIT_TAG=latest
ARG BUILD_DATE=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/install

# Install build dependencies for Alpine
RUN apk add --no-cache \
    build-base \
    libpq \
    libpq-dev \
    gdal \
    gdal-dev \
    geos \
    geos-dev \
    postgresql-dev \
    musl-dev \
    python3-dev \
    linux-headers \
    git

# Set working directory
WORKDIR /build

# Copy entire project into /tmp
COPY . /tmp/

# Install Python dependencies into /install
RUN pip install --upgrade pip && \
    pip install --target=/install -r /tmp/server/requirements.txt && \
    python3 /tmp/server/manage.py collectstatic --noinput --verbosity 2


# -------------------------
# Stage 2: Final Production
# -------------------------
FROM docker.io/python:3.13-alpine AS final

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
      org.opencontainers.image.version="${GIT_TAG}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="GPL-3.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/install:/code" \
    PATH="/install/bin:${PATH}" \
    GDAL_LIBRARY_PATH="/usr/lib/libgdal.so.36.3.10.3" \
    GEOS_LIBRARY_PATH="/usr/lib/libgeos_c.so"

    
    # Copy all from builder, organize in one RUN step
COPY --from=builder /install /install
COPY --from=builder /tmp /tmp

RUN apk add --no-cache \
    nginx\
    supervisor\
    bash\
    curl\
    libpq\
    gdal\
    gdal-dev\
    geos\
    geos-dev\
    postgresql-client && \
    mv /tmp/server /code && \
    mkdir -p /code/static /code/media && \
    mv /tmp/nginx.conf /etc/nginx/nginx.conf && \
    mkdir -p /etc/supervisor/conf.d/ && \
    mv /tmp/supervisord.conf /etc/supervisor/conf.d/supervisord.conf && \
    mv /tmp/entrypoint.sh /code/entrypoint.sh && \
    chmod +x /code/entrypoint.sh && \
    rm -rf /tmp && \
    addgroup -g 349 adventurelog && \
    adduser -D -u 349 -G adventurelog adventurelog && \
    chown -R 349:349 /code
    
WORKDIR /code

EXPOSE 80 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=5 \
  CMD curl --fail --silent --show-error http://localhost:80/ || exit 1