# Environment Variables

AdventureLog configuration is driven by environment variables. The file you edit depends on your install type:

| Install type | Env file | Compose file |
| ------------ | -------- | ------------ |
| All-in-One (AIO) | `.env.aio` | `docker-compose.aio.yml` |
| Standard Docker | `.env` | `docker-compose.yml` |
| Traefik | `.env` | `docker-compose-traefik.yaml` |
| Development | `.env` | `docker-compose.dev.yml` |

Validate before deploying:

```bash
bash scripts/validate-env.sh
# or for AIO:
bash scripts/validate-env.sh .env.aio
```

::: tip AIO minimal setup
AIO only requires `POSTGRES_PASSWORD` in `.env.aio`. URLs, `SECRET_KEY`, and admin defaults are derived at container startup. See [All-in-One Docker](../install/aio.md).
:::

## URL and networking

These variables control how the browser, SvelteKit SSR, and Django talk to each other.

| Variable | Required | Used by | Description | Default |
| -------- | -------- | ------- | ----------- | ------- |
| `SITE_URL` | No | Both | Single public URL when frontend and backend share one domain. Derives `ORIGIN`, `FRONTEND_URL`, `PUBLIC_URL`, and `CSRF_TRUSTED_ORIGINS` when those are unset. | — |
| `PUBLIC_SERVER_URL` | Yes | Frontend SSR | Internal backend URL for server-side requests. **Keep `http://server:8000` in standard Docker.** AIO uses `http://127.0.0.1:8000`. | `http://server:8000` |
| `ORIGIN` | Sometimes | Frontend | Public frontend origin (needed without HTTPS). | `http://localhost:8015` |
| `FRONTEND_URL` | Yes | Backend | Public frontend URL for emails and redirects. | `http://localhost:8015` |
| `PUBLIC_URL` | Yes | Backend | Public backend URL for media and OAuth callbacks. | `http://localhost:8016` |
| `CSRF_TRUSTED_ORIGINS` | Yes | Backend | Comma-separated browser origins allowed to submit forms. | `http://localhost:8015,http://localhost:8016` |
| `FRONTEND_PORT` | Yes | Compose | Host port for the frontend container. | `8015` |
| `BACKEND_PORT` | Yes | Compose | Host port for the backend container. | `8016` |
| `HOST_PORT` | No | AIO compose | Host port mapped to the AIO container. | `8015` |
| `BODY_SIZE_LIMIT` | Yes | Frontend | Maximum upload size in bytes. | `Infinity` |

See [Standard Docker](../install/docker.md#url-mental-model) for a visual explanation of the URL model.

## Database (PostgreSQL / PostGIS)

| Variable | Required | Description | Default |
| -------- | -------- | ----------- | ------- |
| `PGHOST` | Yes | Database hostname inside Docker network. | `db` |
| `POSTGRES_DB` / `PGDATABASE` | Yes | Database name. | `database` |
| `POSTGRES_USER` / `PGUSER` | Yes | Database user. | `adventure` |
| `POSTGRES_PASSWORD` / `PGPASSWORD` | Yes | Database password. Change in production. | `changeme123` |

## Django core

| Variable | Required | Description | Default |
| -------- | -------- | ----------- | ------- |
| `SECRET_KEY` | Yes | Django secret key. Auto-generated on AIO if unset. | `changeme123` |
| `DEBUG` | No | Enable debug mode. Use `False` in production. | `False` |
| `DJANGO_ADMIN_USERNAME` | Yes | First-boot superuser username. | `admin` |
| `DJANGO_ADMIN_PASSWORD` | Yes | First-boot superuser password. | `admin` |
| `DJANGO_ADMIN_EMAIL` | Yes | First-boot superuser email. | `admin@example.com` |
| `GUNICORN_WORKERS` | No | Gunicorn worker processes. Use `1` on small hosts; `(2 × CPU) + 1` on larger servers. | `2` |
| `SKIP_WORLD_DATA` | No | Set to `1` to skip the first-boot `download-countries` import (saves RAM; world travel data loads later). | unset |

## Registration and authentication

| Variable | Required | Description | Default |
| -------- | -------- | ----------- | ------- |
| `DISABLE_REGISTRATION` | No | Block new account signups. | `False` |
| `DISABLE_REGISTRATION_MESSAGE` | No | Message shown when registration is disabled. | Custom message |
| `SOCIALACCOUNT_ALLOW_SIGNUP` | No | Allow new accounts via social providers when registration is disabled. | `False` |
| `FORCE_SOCIALACCOUNT_LOGIN` | No | Disable password login; social/OIDC only. | `False` |
| `ACCOUNT_EMAIL_VERIFICATION` | No | `none`, `optional`, or `mandatory`. | `none` |

Related guides: [Social Auth](social_auth.md), [Disable Registration](disable_registration.md), [API Keys](api_keys.md).

## Rate limiting

| Variable | Required | Description | Default |
| -------- | -------- | ----------- | ------- |
| `ENABLE_RATE_LIMITS` | No | Enable API rate limiting. Recommended in production. | `False` |
| `RATE_LIMIT_USER` | No | Default authenticated user throttle. | `10000/hour` |
| `RATE_LIMIT_IMAGE_PROXY` | No | Image proxy endpoint limit. | `60/minute` |
| `RATE_LIMIT_IMAGE_IMPORT` | No | Image import limit. | `12/minute` |
| `RATE_LIMIT_EXTERNAL_GEOCODE` | No | External geocoding limit. | `120/minute` |
| `RATE_LIMIT_EXTERNAL_RECOMMENDATIONS` | No | Recommendations API limit. | `30/minute` |
| `RATE_LIMIT_EXTERNAL_WIKIPEDIA` | No | Wikipedia lookup limit. | `60/minute` |
| `RATE_LIMIT_EXTERNAL_SUN_TIMES` | No | Sun times API limit. | `30/minute` |

See [Advanced Configuration](advanced_configuration.md) for usage notes.

## Email (SMTP)

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `EMAIL_BACKEND` | No | `console` (logs only) or `email` (SMTP). |
| `EMAIL_HOST` | If SMTP | SMTP server hostname. |
| `EMAIL_PORT` | No | SMTP port. Default `587`. |
| `EMAIL_USE_TLS` | No | Enable TLS. Default `true`. |
| `EMAIL_USE_SSL` | No | Enable SSL. Default `false`. |
| `EMAIL_HOST_USER` | If SMTP | SMTP username. |
| `EMAIL_HOST_PASSWORD` | If SMTP | SMTP password. |
| `DEFAULT_FROM_EMAIL` | If SMTP | Sender address. |

See [SMTP Email](email.md).

## Media storage

| Variable | Required | Description | Default |
| -------- | -------- | ----------- | ------- |
| `MEDIA_STORAGE` | No | `local` or `s3`. | `local` |
| `MEDIA_STORAGE_LIMIT_MB` | No | Per-user storage cap in MB (`0` = unlimited). | `0` |
| `MEDIA_STORAGE_LIMIT_BYTES` | No | Overrides MB limit when set. | `0` |
| `AWS_ACCESS_KEY_ID` | If S3 | S3 access key. | — |
| `AWS_SECRET_ACCESS_KEY` | If S3 | S3 secret key. | — |
| `AWS_STORAGE_BUCKET_NAME` | If S3 | Bucket name. | — |
| `AWS_S3_ENDPOINT_URL` | If non-AWS | Provider endpoint (R2, MinIO, Spaces). | — |
| `AWS_S3_REGION_NAME` | No | Region (`auto` for Cloudflare R2). | — |
| `AWS_S3_CUSTOM_DOMAIN` | No | CDN or custom domain for media URLs. | — |

See [S3 Media Storage](s3_storage.md).

## Integrations

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `GOOGLE_MAPS_API_KEY` | If enabled | Google Maps tiles and place search. |
| `STRAVA_CLIENT_ID` | If enabled | Strava OAuth client ID. |
| `STRAVA_CLIENT_SECRET` | If enabled | Strava OAuth client secret. |
| `PUBLIC_UMAMI_SRC` | If enabled | Umami analytics script URL. |
| `PUBLIC_UMAMI_WEBSITE_ID` | If enabled | Umami website ID. |

## Traefik compose

Used with `docker-compose-traefik.yaml`:

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `ACME_EMAIL` | Yes | Let's Encrypt registration email. |
| `TRAEFIK_DOMAIN` | Yes | Public domain for the Traefik router. |

## Operations

These are not application settings but affect management scripts:

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `COMPOSE_FILE` | Override compose file (`deploy.sh`, backup, restore). | Auto-detected |
| `ADVENTURELOG_COMPOSE` | Set to `aio` to prefer AIO when both env files exist. | unset |
| `BACKUP_DIR` | Backup output directory for `scripts/backup.sh`. | `backups` |
| `ADVENTURELOG_REF` | Git ref for installer downloads. | `main` |

See [Operations & Maintenance](operations.md).

## Source of truth

- Standard env template: [`.env.example`](https://github.com/seanmorley15/AdventureLog/blob/main/.env.example)
- AIO env template: [`.env.aio.example`](https://github.com/seanmorley15/AdventureLog/blob/main/.env.aio.example)
- Django settings: [`backend/server/main/settings.py`](https://github.com/seanmorley15/AdventureLog/blob/main/backend/server/main/settings.py)
- AIO derivation: [`aio/env-setup.sh`](https://github.com/seanmorley15/AdventureLog/blob/main/aio/env-setup.sh)
