# Standard Deployment

The Standard Deployment bundles the SvelteKit frontend and Django backend into **one container** on a **single port**. No separate backend URL, no reverse proxy required for basic use.

The [Advanced Deployment](docker.md) remains available for users who prefer separate frontend/backend services or custom integrations.

## When to use Standard Deployment

| Standard Deployment | Advanced Deployment |
|-----|------------------|
| One URL, one port | Two ports (frontend + backend) |
| Two env vars to start | Full `.env` configuration |
| Good for homelabs and quick installs | Good for reverse proxies and split deployments |

## Quick start

Most installs use Docker Compose directly:

```bash
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/docker-compose.yml
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/.env.example
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, then:
docker compose --env-file .env up -d
```

### Guided installer (optional)

Prefer a walkthrough? The [Quick Start Installer](quick_start.md) deploys this same Standard Deployment stack interactively:

```bash
curl -sSL https://get.adventurelog.app | bash
```

Open **http://localhost:8015** (or your configured `SITE_URL`).

**Memory:** allocate at least **2 GB RAM** on first boot; about **1 GB** is usually enough afterward.

Default admin login: `admin` / `admin` — change this after first login.

## Configuration

Only **two variables** are required in `.env`:

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Yes | Database password | — |
| `SITE_URL` | No | Public URL for the app | `http://localhost:8015` |

Optional:

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST_PORT` | Host port mapped to the container | `8015` |

Everything else (Django `SECRET_KEY`, `CSRF_TRUSTED_ORIGINS`, `PUBLIC_URL`, `FRONTEND_URL`, `ORIGIN`, internal `PUBLIC_SERVER_URL`, etc.) is derived automatically at startup.

::: tip Image size
The Standard Deployment image is ~1 GB (PostGIS/GDAL + Python + Node). It must **not** include local dev folders such as `backend/server/media/` or `.venv` — those are excluded via [`.dockerignore`](https://github.com/seanmorley15/AdventureLog/blob/main/.dockerignore). If your built image is ~3 GB, rebuild from a clean checkout without baking in local media.
:::

### Example `.env`

```env
POSTGRES_PASSWORD=my-secure-db-password
SITE_URL=https://adventurelog.example.com
HOST_PORT=443
```

When using HTTPS behind an external reverse proxy, set `SITE_URL` to your public HTTPS URL and proxy traffic to the container port.

## Updating

```bash
docker compose --env-file .env pull
docker compose --env-file .env up -d --wait
```

## Image

Prebuilt image: `ghcr.io/seanmorley15/adventurelog:latest`

To build locally from source:

```bash
docker build -f docker/Dockerfile --target aio -t adventurelog .
# or
docker compose --env-file .env build
```

See [`docker/README.md`](https://github.com/seanmorley15/AdventureLog/blob/main/docker/README.md) for all build targets.

## Operations

- [Operations & Maintenance](../configuration/operations.md) — backups, updates, management menu
- [Environment Variables](../configuration/environment_variables.md) — full reference including optional S3, OAuth, and email settings

Additional options can be added to `.env` or the `environment` block in `docker-compose.yml`.
