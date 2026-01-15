FROM node:22-bullseye-slim AS frontend-builder

LABEL maintainer="Sean Morley"

WORKDIR /app

# Install pnpm and build the frontend
RUN npm install -g pnpm
ENV CI=true
COPY frontend/package.json frontend/pnpm-lock.yaml* frontend/
COPY frontend/ frontend/
WORKDIR /app/frontend
RUN pnpm install --frozen-lockfile --reporter=silent && pnpm run build \
  && rm -rf node_modules \
  && pnpm install --prod --frozen-lockfile --reporter=silent

FROM python:3.13-slim AS backend-builder
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
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/server/requirements.txt /code/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# --- Final stage: runtime with Python 3.13 ---
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /code

# Install runtime packages and NodeJS (for running the built frontend)
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    postgresql-client \
    gdal-bin \
    libgdal-dev \
    nginx \
    memcached \
    supervisor \
    dos2unix \
  && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Copy backend code and aio configs from repo
COPY backend/ /code/backend/
COPY aio/ /code/aio/

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/frontend /code/frontend

# Copy Python packages from backend-builder
COPY --from=backend-builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Ensure folders and permissions
RUN mkdir -p /code/backend/media /code/static /code/media \
  && chmod +x /code/aio/entrypoint.sh || true \
  && dos2unix /code/aio/entrypoint.sh || true

# Copy nginx and supervisord configs into system locations from build context
COPY aio/nginx.conf /etc/nginx/nginx.conf
COPY aio/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Collect static files (best-effort)
RUN python3 /code/backend/server/manage.py collectstatic --noinput --verbosity 1 || true

EXPOSE 80

ENTRYPOINT ["/code/aio/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
