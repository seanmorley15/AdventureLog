# Traefik

Run AdventureLog behind [Traefik](https://traefik.io/) with automatic HTTPS from Let's Encrypt. The repository has a ready-made compose file for this. It runs Advanced Deployment (separate frontend and backend) on one domain.

## Requirements

- A domain whose DNS points at your server.
- Ports `80` and `443` open to the internet, for Let's Encrypt.
- The general [requirements](getting_started.md#requirements).

## Steps

1. Download the compose file and the example env file. The compose file reads `../.env.advanced`, so it goes in a `docker/` folder:

   ```bash
   mkdir -p adventurelog/docker && cd adventurelog
   wget -P docker https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/docker/docker-compose.traefik.yaml
   wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/.env.advanced.example
   cp .env.advanced.example .env.advanced
   ```

2. Edit `.env.advanced`. Change `POSTGRES_PASSWORD` and `SECRET_KEY`. Delete or comment out `ORIGIN`, `FRONTEND_URL`, `PUBLIC_URL`, and `CSRF_TRUSTED_ORIGINS`, which are derived from `SITE_URL` only when they aren't set. Then add:

   | Variable | Description | Example |
   | -------- | ----------- | ------- |
   | `SITE_URL` | Your public HTTPS address. AdventureLog derives its other URLs from it. | `https://adventurelog.example.com` |
   | `TRAEFIK_DOMAIN` | The domain Traefik answers on | `adventurelog.example.com` |
   | `ACME_EMAIL` | Your email for Let's Encrypt | `you@example.com` |

3. Start everything:

   ```bash
   docker compose --env-file .env.advanced -f docker/docker-compose.traefik.yaml up -d
   ```

4. Open `https://adventurelog.example.com` and follow [First Steps](first_steps.md).

## How traffic is routed

| Path | Goes to |
| ---- | ------- |
| `/media`, `/admin`, `/accounts`, `/static` | The backend (Django) |
| Everything else | The frontend (SvelteKit) |

To use your own Traefik instead of the bundled one, copy the `traefik.*` labels from the `web` and `server` services into your compose file, and put the containers on Traefik's network.
