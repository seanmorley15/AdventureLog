# Docker

All production images are built from a **single Dockerfile** with shared stages so frontend, backend, and Standard Deployment stay in sync.

## Build commands (from repository root)

```bash
# Individual images
docker build -f docker/Dockerfile --target frontend -t adventurelog-frontend .
docker build -f docker/Dockerfile --target backend  -t adventurelog-backend .
docker build -f docker/Dockerfile --target aio     -t adventurelog .

# All app images
docker buildx bake -f docker/docker-bake.hcl
```

## Layout

| Path | Purpose |
|------|---------|
| [`Dockerfile`](Dockerfile) | Multi-target build (frontend, backend, Standard Deployment) |
| [`docker-bake.hcl`](docker-bake.hcl) | Optional bake file for all targets |
| [`shared/`](shared/) | nginx, supervisord, and entrypoint scripts shared across images |
| [`aio/`](aio/) | Standard Deployment container entrypoint and env setup scripts |
| [`docker-compose.yml`](docker-compose.yml) | Standard Deployment (single container) |
| [`docker-compose.advanced.yml`](docker-compose.advanced.yml) | Advanced Deployment (frontend, backend, database) |
| [`docker-compose*.yml`](docker-compose.dev.yml) | Development, Traefik, database-only, and CI stacks |

Run compose files from the repository root, for example:

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d
```

Advanced Deployment:

```bash
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml up -d
```

## Shared stages

- **`frontend-build`** — pnpm install, Vite build, production prune (used by `frontend` and Standard Deployment)
- **`backend-builder`** — pip install with GDAL dev headers
- **`backend-runtime`** — Django app, collectstatic, cron scripts (extended by `backend` and Standard Deployment)

Image-specific layers only add nginx/supervisord configs, entrypoints, and (for Standard Deployment) Node + frontend artifacts.

## Slimming

Build context exclusions live in the repository root [`.dockerignore`](../.dockerignore). Never commit local `backend/server/media/`, `.venv/`, or `staticfiles/` — they are mounted or generated at runtime.
