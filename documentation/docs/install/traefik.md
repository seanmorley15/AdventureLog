# Traefik Reverse Proxy

Deploy AdventureLog behind [Traefik](https://traefik.io/) with automatic HTTPS and path-based routing using the official compose file.

## Official compose file

Download [`docker-compose-traefik.yaml`](https://github.com/seanmorley15/AdventureLog/blob/main/docker-compose-traefik.yaml) from the repository. It includes:

- Traefik v2.11 with Let's Encrypt
- Prebuilt `adventurelog-frontend` and `adventurelog-backend` images (no local build required)
- Path-based routing: frontend pages on `/`, backend on `/media`, `/admin`, `/accounts`, `/static`

## Required environment variables

Add these to your `.env` alongside the standard AdventureLog variables:

| Variable | Description | Example |
| -------- | ----------- | ------- |
| `ACME_EMAIL` | Let's Encrypt registration email | `you@example.com` |
| `TRAEFIK_DOMAIN` | Public domain for the router | `adventurelog.example.com` |
| `SITE_URL` | Public HTTPS URL (derives CSRF and frontend origins) | `https://adventurelog.example.com` |

See [Environment Variables](../configuration/environment_variables.md) for the full list.

## Getting started

```bash
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/docker-compose-traefik.yaml
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/.env.example
cp .env.example .env
# Edit .env: set SITE_URL, ACME_EMAIL, TRAEFIK_DOMAIN, POSTGRES_PASSWORD, SECRET_KEY
bash scripts/validate-env.sh
docker compose -f docker-compose-traefik.yaml up -d
```

## Routing overview

Traefik routes traffic to two containers on a single domain:

| Path prefix | Service |
| ----------- | ------- |
| `/`, `/api`, `/auth`, app pages | Frontend (SvelteKit) |
| `/media`, `/admin`, `/accounts`, `/static` | Backend (Django/Gunicorn) |

This matches the internal routing model used by the [All-in-One](aio.md) container, but with separate frontend and backend services.

## Related guides

- [Standard Docker](docker.md) — base configuration without Traefik
- [Environment Variables](../configuration/environment_variables.md) — URL and CSRF settings
- [Nginx Proxy Manager](nginx_proxy_manager.md) — alternative reverse proxy
