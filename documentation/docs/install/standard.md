# Standard Deployment

Standard Deployment runs AdventureLog as **one app container** and a PostGIS database, reached on a **single port**. There is no separate backend URL, and no reverse proxy is needed for basic use.

The [Advanced Deployment](docker.md) remains available for users who prefer separate frontend/backend services or custom integrations.

## When to use Standard Deployment

| Standard Deployment | Advanced Deployment |
|-----|------------------|
| One URL, one port | Two ports (frontend + backend) |
| One required env var | Full `.env` configuration |
| Good for homelabs and quick installs | Good for reverse proxies and split deployments |

## Quick start

Use Docker Compose directly, or let the guided installer do the same steps for you:

::: code-group

```bash [Docker Compose]
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/docker-compose.yml
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/.env.example
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, then:
docker compose --env-file .env up -d
```

```bash [Guided installer]
# Walks you through the same Standard Deployment setup interactively
curl -sSL https://get.adventurelog.app | bash
```

:::

The [Quick Start Installer](quick_start.md) page explains what the guided installer does.

Open **http://localhost:8015** (or your configured `SITE_URL`). The first start takes a few minutes. Check the [requirements](getting_started.md#requirements) first; the first boot needs about 2 GB of RAM.

The admin password is generated on first start and printed once in the log. [First Steps](first_steps.md) shows how to find it and what to set up next.

## Configuration

Only `POSTGRES_PASSWORD` is required in `.env`:

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Yes | Database password | none |
| `SITE_URL` | No | Public URL for the app | `http://localhost:8015` |
| `HOST_PORT` | No | Host port mapped to the container | `8015` |
| `DJANGO_ADMIN_USERNAME` | No | Username of the first admin | `admin` |
| `DJANGO_ADMIN_PASSWORD` | No | First admin's password. Empty or weak: one is generated and printed in the log. | empty |
| `DJANGO_ADMIN_EMAIL` | No | Email of the first admin | `admin@example.com` |

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

Back up first. See [Updating](../configuration/updating.md) for the other ways to update.

## Image

Prebuilt image: `ghcr.io/seanmorley15/adventurelog:latest`

To build locally from source:

::: code-group

```bash [docker build]
docker build -f docker/Dockerfile --target aio -t adventurelog .
```

```bash [docker compose]
docker compose --env-file .env build
```

:::

See [`docker/README.md`](https://github.com/seanmorley15/AdventureLog/blob/main/docker/README.md) for all build targets.

## Next steps

- [First Steps](first_steps.md): sign in, secure the admin account, and decide who can join.
- [Backups and Restore](../configuration/backups.md): set these up before you rely on the server.
- [Environment Variables](../configuration/environment_variables.md): every optional setting. Add them to `.env`.
