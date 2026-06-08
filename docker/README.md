# Docker

All production images are built from a **single Dockerfile** with shared stages so frontend, backend, and AIO stay in sync.

## Build commands (from repository root)

```bash
# Individual images
docker build -f docker/Dockerfile --target frontend -t adventurelog-frontend .
docker build -f docker/Dockerfile --target backend  -t adventurelog-backend .
docker build -f docker/Dockerfile --target aio     -t adventurelog-aio .

# All app images
docker buildx bake -f docker/docker-bake.hcl
```

## Layout

| Path | Purpose |
|------|---------|
| [`Dockerfile`](Dockerfile) | Multi-target build (frontend, backend, aio) |
| [`docker-bake.hcl`](docker-bake.hcl) | Optional bake file for all targets |
| [`shared/`](shared/) | nginx, supervisord, and entrypoint scripts shared across images |
| [`aio/`](aio/) | AIO container entrypoint and env setup scripts |
| [`docker-compose*.yml`](docker-compose.aio.yml) | Compose stacks for production, development, Traefik, and CI |

Run compose files from the repository root, for example:

```bash
docker compose --env-file .env.aio -f docker/docker-compose.aio.yml up -d
```

## Shared stages

- **`frontend-build`** — pnpm install, Vite build, production prune (used by `frontend` and `aio`)
- **`backend-builder`** — pip install with GDAL dev headers
- **`backend-runtime`** — Django app, collectstatic, cron scripts (extended by `backend` and `aio`)

Image-specific layers only add nginx/supervisord configs, entrypoints, and (for AIO) Node + frontend artifacts.

## Slimming

Build context exclusions live in the repository root [`.dockerignore`](../.dockerignore). Never commit local `backend/server/media/`, `.venv/`, or `staticfiles/` — they are mounted or generated at runtime.
