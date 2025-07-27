# ---------------------
# Stage 1: Data builder
# ---------------------
FROM docker.io/python:3.11-slim AS builder

ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown

# Set workdir and environment
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install required Python packages
RUN pip install --no-cache-dir requests osm2geojson

# Copy and run data generation script
COPY main.py /app/main.py
RUN python -u /app/main.py

# ------------------------
# Stage 2: Final Nginx-only
# ------------------------
FROM docker.io/nginx:alpine

ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown

# Optional metadata
LABEL org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}"

# Create destination directory
RUN mkdir -p /var/www/html/data

# Copy generated data and static files
COPY --from=builder /app/data /var/www/html/data
COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/nginx.conf

# Add entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/app/entrypoint.sh"]
