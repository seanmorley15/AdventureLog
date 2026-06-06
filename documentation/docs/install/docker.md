# Docker 🐋

Docker is the preferred way to run AdventureLog on your local machine. It is a lightweight containerization technology that allows you to run applications in isolated environments called containers.

> **Looking for the simplest setup?** See the [All-in-One (AIO)](aio.md) guide — one container, one port, two environment variables.

> **Note**: This guide mainly focuses on installation with a Linux-based host machine, but the steps are similar for other operating systems.

## Prerequisites

- Docker installed on your machine/server. You can learn how to download it [here](https://docs.docker.com/engine/install/).
- **Memory:** allocate at least **2 GB RAM** for the first boot (world geography data import). Steady-state use typically needs about **1 GB**. Optional limits are documented in [`docker-compose.override.example.yml`](https://github.com/seanmorley15/AdventureLog/blob/main/docker-compose.override.example.yml).

## Getting Started

Get the `docker-compose.yml` and `.env.example` files from the AdventureLog repository. You can download them here:

- [Docker Compose](https://github.com/seanmorley15/AdventureLog/blob/main/docker-compose.yml)
- [Environment Variables](https://github.com/seanmorley15/AdventureLog/blob/main/.env.example)

```bash
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/docker-compose.yml
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/.env.example
cp .env.example .env
```

::: tip

If running on an ARM based machine, you will need to use a different PostGIS image. It is recommended to use the `imresamu/postgis:16-3.5-alpine` image or a custom version found [here](https://hub.docker.com/r/imresamu/postgis/tags). The AdventureLog containers are ARM compatible.

:::

## URL mental model

AdventureLog uses several URL-related environment variables. Most installs only need to set the public-facing URLs; keep `PUBLIC_SERVER_URL` at its default.

| Variable | Who uses it | Typical value |
| -------- | ----------- | ------------- |
| `PUBLIC_SERVER_URL` | SvelteKit SSR (container-to-container) | `http://server:8000` — **do not change** for standard Docker installs |
| `ORIGIN` | SvelteKit origin when not using HTTPS | Your frontend URL, e.g. `http://localhost:8015` |
| `PUBLIC_URL` | Django image and OAuth URLs | Your backend URL, e.g. `http://localhost:8016` (or your single domain if using a reverse proxy) |
| `FRONTEND_URL` | Django emails and redirects | Your frontend URL, e.g. `http://localhost:8015` |
| `CSRF_TRUSTED_ORIGINS` | Django CORS and CSRF | Comma-separated list of every browser origin, e.g. `http://localhost:8015,http://localhost:8016` |

When frontend and backend share one domain behind a reverse proxy, you can set `SITE_URL` instead of configuring `ORIGIN`, `FRONTEND_URL`, `PUBLIC_URL`, and `CSRF_TRUSTED_ORIGINS` individually. See `.env.example` for details.

To validate your configuration, run:

```bash
bash scripts/validate-env.sh
```

## Configuration

The `.env` file contains all the configuration settings for your AdventureLog instance. Here’s a breakdown of each section:

### 🌐 Frontend (web)

| Name                | Required  | Description                                                                                                                        | Default Value           |
| ------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| `PUBLIC_SERVER_URL` | Yes       | Used by the frontend SSR server to connect to the backend. Almost every user user will **never have to change this from default**! | `http://server:8000`    |
| `ORIGIN`            | Sometimes | Needed only if not using HTTPS. Set it to the domain or IP you'll use to access the frontend.                                      | `http://localhost:8015` |
| `BODY_SIZE_LIMIT`   | Yes       | Maximum upload size in bytes.                                                                                                      | `Infinity`              |
| `FRONTEND_PORT`     | Yes       | Port that the frontend will run on inside Docker.                                                                                  | `8015`                  |

### 🐘 PostgreSQL Database

| Name                | Required | Description           | Default Value |
| ------------------- | -------- | --------------------- | ------------- |
| `PGHOST`            | Yes      | Internal DB hostname. | `db`          |
| `POSTGRES_DB`       | Yes      | DB name.              | `database`    |
| `POSTGRES_USER`     | Yes      | DB user.              | `adventure`   |
| `POSTGRES_PASSWORD` | Yes      | DB password.          | `changeme123` |

### 🔒 Backend (server)

| Name                    | Required | Description                                                                        | Default Value                                 |
| ----------------------- | -------- | ---------------------------------------------------------------------------------- | --------------------------------------------- |
| `SECRET_KEY`            | Yes      | Django secret key. Change this in production!                                      | `changeme123`                                 |
| `DJANGO_ADMIN_USERNAME` | Yes      | Default Django admin username.                                                     | `admin`                                       |
| `DJANGO_ADMIN_PASSWORD` | Yes      | Default Django admin password.                                                     | `admin`                                       |
| `DJANGO_ADMIN_EMAIL`    | Yes      | Default admin email.                                                               | `admin@example.com`                           |
| `PUBLIC_URL`            | Yes      | Publicly accessible URL of the **backend**. Used for generating image URLs.        | `http://localhost:8016`                       |
| `CSRF_TRUSTED_ORIGINS`  | Yes      | Comma-separated list of frontend/backend URLs that are allowed to submit requests. | `http://localhost:8016,http://localhost:8015` |
| `FRONTEND_URL`          | Yes      | URL to the **frontend**, used for email generation.                                | `http://localhost:8015`                       |
| `BACKEND_PORT`          | Yes      | Port that the backend will run on inside Docker.                                   | `8016`                                        |
| `DEBUG`                 | No       | Should be `False` in production.                                                   | `False`                                       |
| `ENABLE_RATE_LIMITS`    | No       | Enable rate limits on the backend. Should be `True` in production.                 | `False`                                        |

## Optional Configuration

- [Disable Registration](../configuration/disable_registration.md)
- [Google Maps](../configuration/google_maps_integration.md)
- [Email Configuration](../configuration/email.md)
- [Immich Integration](../configuration/immich_integration.md)
- [Umami Analytics](../configuration/analytics.md)

## Running the Containers

Once you've configured `.env`, you can start AdventureLog with:

```bash
docker compose up -d
```

Enjoy using AdventureLog! 🎉
