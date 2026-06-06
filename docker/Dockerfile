# syntax=docker/dockerfile:1
#
# Unified AdventureLog image definitions — build from repository root:
#   docker build -f docker/Dockerfile --target frontend -t adventurelog-frontend .
#   docker build -f docker/Dockerfile --target backend  -t adventurelog-backend .
#   docker build -f docker/Dockerfile --target aio     -t adventurelog-aio .
#
# Or: docker buildx bake -f docker/docker-bake.hcl

ARG PNPM_VERSION=10.32.1

# ---------------------------------------------------------------------------
# Shared build stages
# ---------------------------------------------------------------------------

FROM node:22-bookworm-slim AS node-runtime

FROM cgr.dev/chainguard/node:latest-dev@sha256:6eec455f386d097fc57d8aa73bd06c27ab91faa4f02f9103f94b4c56e0f9a80b AS frontend-build
ARG PNPM_VERSION
USER root
WORKDIR /app
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/.npmrc* ./
RUN pnpm install --frozen-lockfile
COPY frontend/ .
RUN rm -f .env && pnpm run build
ENV CI=true
RUN pnpm prune --prod

FROM python:3.13-slim AS backend-builder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /code
RUN apt-get update && apt-get install -y --no-install-recommends \
      git \
      gdal-bin \
      libgdal-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY backend/server/requirements.txt /code/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Shared Django runtime used by backend and AIO images.
FROM python:3.13-slim AS backend-runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /code
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      postgresql-client \
      gdal-bin \
      nginx \
      memcached \
      supervisor \
      cron \
      fonts-noto-core \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY --from=backend-builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin
COPY backend/server /code/
COPY docker/shared/entrypoint-common.sh /code/scripts/entrypoint-common.sh
COPY backend/cron/adventurelog /etc/cron.d/adventurelog
COPY backend/scripts/run-cron-job.sh /code/scripts/run-cron-job.sh
COPY backend/scripts/write-cron-env.sh /code/scripts/write-cron-env.sh
RUN chmod +x /code/scripts/entrypoint-common.sh /code/scripts/run-cron-job.sh /code/scripts/write-cron-env.sh \
    && chmod 0644 /etc/cron.d/adventurelog \
    && mkdir -p /code/static /code/media /var/log/adventurelog /var/lock
RUN python3 manage.py collectstatic --noinput --verbosity 2

# ---------------------------------------------------------------------------
# Production targets
# ---------------------------------------------------------------------------

FROM gcr.io/distroless/nodejs22-debian12:nonroot@sha256:13593b7570658e8477de39e2f4a1dd25db2f836d68a0ba771251572d23bb4f8e AS frontend
LABEL org.opencontainers.image.title="AdventureLog Frontend" \
      org.opencontainers.image.description="AdventureLog SvelteKit frontend (SSR)." \
      org.opencontainers.image.source="https://github.com/seanmorley15/AdventureLog" \
      org.opencontainers.image.licenses="GPL-3.0"
WORKDIR /app
ENV NODE_ENV=production
COPY --from=frontend-build /app/build ./build
COPY --from=frontend-build /app/node_modules ./node_modules
COPY --from=frontend-build /app/package.json ./package.json
COPY frontend/start.js ./start.js
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
CMD ["start.js"]

FROM backend-runtime AS backend
LABEL org.opencontainers.image.title="AdventureLog Backend" \
      org.opencontainers.image.description="AdventureLog Django backend with nginx gateway." \
      org.opencontainers.image.source="https://github.com/seanmorley15/AdventureLog" \
      org.opencontainers.image.licenses="GPL-3.0"
COPY docker/shared/nginx-backend.conf /etc/nginx/nginx.conf
COPY docker/shared/supervisord-backend.conf /etc/supervisor/conf.d/supervisord.conf
COPY backend/entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh
EXPOSE 80 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:80/health/')"
ENTRYPOINT ["/code/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

FROM backend-runtime AS aio
LABEL org.opencontainers.image.title="AdventureLog AIO" \
      org.opencontainers.image.description="All-in-one AdventureLog container with frontend and backend on a single port." \
      org.opencontainers.image.source="https://github.com/seanmorley15/AdventureLog" \
      org.opencontainers.image.licenses="GPL-3.0"
ENV NODE_ENV=production
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
RUN ln -sf /usr/local/bin/node /usr/bin/node
COPY --from=frontend-build /app/build /app/build
COPY --from=frontend-build /app/node_modules /app/node_modules
COPY --from=frontend-build /app/package.json /app/package.json
COPY frontend/start.js /app/start.js
COPY docker/shared/nginx-aio.conf /etc/nginx/nginx.conf
COPY docker/shared/supervisord-aio.conf /aio/supervisord.conf
COPY aio/env-setup.sh /aio/env-setup.sh
COPY aio/entrypoint.sh /aio/entrypoint.sh
RUN chmod +x /aio/env-setup.sh /aio/entrypoint.sh
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=5 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:80/health')"
ENTRYPOINT ["/aio/entrypoint.sh"]
CMD ["supervisord", "-c", "/aio/supervisord.conf"]
