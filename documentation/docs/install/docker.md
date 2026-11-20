# Advanced Deployment

Run AdventureLog as three containers: the SvelteKit frontend (`web`), the Django backend (`server`), and the PostGIS database (`db`). Use it when you need separate frontend and backend URLs or full control over every setting.

::: tip Looking for the simplest setup?
[Standard Deployment](standard.md) runs one app container on one port with one required setting. Check the [requirements](getting_started.md#requirements) for either setup.
:::

## Steps

1. Download the compose file and the example env file. The compose file reads `../.env.advanced`, so it goes in a `docker/` folder next to the env file:

   ```bash
   mkdir -p adventurelog/docker && cd adventurelog
   wget -P docker https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/docker/docker-compose.advanced.yml
   wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/.env.advanced.example
   cp .env.advanced.example .env.advanced
   ```

2. Edit `.env.advanced`. At minimum, change `POSTGRES_PASSWORD` and `SECRET_KEY`, and set the URLs described [below](#urls).

3. Start the containers:

   ```bash
   docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml up -d --wait
   ```

4. Open **http://localhost:8015**, or your `ORIGIN` / `SITE_URL`. The admin password is generated on first start and printed once in the backend log. [First Steps](first_steps.md) shows how to find it.

::: tip ARM hosts
The AdventureLog images are multi-arch. If the `postgis/postgis` image doesn't run on your ARM host, use `imresamu/postgis:16-3.5-alpine` for the `db` service.
:::

## URLs {#urls}

Advanced Deployment has several URL settings. If the frontend and backend share one domain behind a reverse proxy, set `SITE_URL` instead, and delete or comment out `ORIGIN`, `FRONTEND_URL`, `PUBLIC_URL`, and `CSRF_TRUSTED_ORIGINS`: they are derived from `SITE_URL` only when they aren't set.

| Variable | Used by | Typical value |
| -------- | ------- | ------------- |
| `PUBLIC_SERVER_URL` | The frontend server, to reach the backend inside Docker | `http://server:8000`. Leave it as is. |
| `ORIGIN` | The frontend, when not using HTTPS | Your frontend URL, e.g. `http://localhost:8015` |
| `PUBLIC_URL` | The backend, for image and sign-in URLs | Your backend URL, e.g. `http://localhost:8016` |
| `FRONTEND_URL` | The backend, for links in emails and redirects | Your frontend URL, e.g. `http://localhost:8015` |
| `CSRF_TRUSTED_ORIGINS` | The backend, to accept browser requests | Every browser origin, comma-separated, e.g. `http://localhost:8015,http://localhost:8016` |

If you have a checkout of the repository, `bash scripts/validate-env.sh .env.advanced` catches common mistakes, such as `PUBLIC_SERVER_URL` pointing at the host port.

## Required settings

These must be set in `.env.advanced`. Every other setting is optional; see [Environment Variables](../configuration/environment_variables.md).

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `POSTGRES_DB`, `POSTGRES_USER` | Database name and user | `database`, `adventure` |
| `POSTGRES_PASSWORD` | Database password. Change it. | `changeme123` |
| `PGHOST` | Database hostname inside Docker | `db` |
| `SECRET_KEY` | Django secret key. Change it, and keep it: a new key signs everyone out and stops API keys working. | `changeme123` |
| `DJANGO_ADMIN_USERNAME`, `DJANGO_ADMIN_EMAIL` | The first admin account | `admin`, `admin@example.com` |
| `BODY_SIZE_LIMIT` | Maximum upload size in bytes | `Infinity` |

## Next steps

- [First Steps](first_steps.md): sign in, secure the admin account, and decide who can join.
- [Reverse proxy guides](getting_started.md#reverse-proxy): HTTPS on your own domain.
- [Backups and Restore](../configuration/backups.md) and [Updating](../configuration/updating.md).
