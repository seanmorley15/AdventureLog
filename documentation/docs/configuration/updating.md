# Updating AdventureLog

Keep your self-hosted instance current with the latest images and database migrations. **Always back up before updating.**

## Option 1: Installer management menu

```bash
curl -sSL https://get.adventurelog.app | bash
```

Choose **Update to latest images** (with optional backup).

## Option 2: deploy.sh (recommended)

From your install directory (where `deploy.sh` and your compose file live):

```bash
bash deploy.sh --backup
bash deploy.sh --logs   # optional: follow logs after deploy
```

`deploy.sh` validates your env file, creates a backup, pulls images, and runs `docker compose up -d --wait`.

For AIO installs:

```bash
COMPOSE_FILE=docker-compose.aio.yml bash deploy.sh --backup
```

See [Operations & Maintenance](operations.md) for compose auto-detection details.

## Option 3: Manual compose

```bash
bash scripts/backup.sh

# Standard
docker compose --env-file .env -f docker-compose.yml pull
docker compose --env-file .env -f docker-compose.yml up -d --wait

# AIO
docker compose --env-file .env.aio -f docker-compose.aio.yml pull
docker compose --env-file .env.aio -f docker-compose.aio.yml up -d --wait
```

## Restore from backup

```bash
bash scripts/restore.sh backups/YYYYMMDD-HHMMSS
```

## Updating region data

Country and region reference data comes from [dr5hn/countries-states-cities-database](https://github.com/dr5hn/countries-states-cities-database). To refresh it manually:

```bash
docker exec -it <backend-container> bash
python manage.py download-countries --force
```

Region data version is pinned per AdventureLog release in `settings.py` and is not auto-updated on every deploy.

## What happens during an update

1. New container images are pulled
2. Containers restart with your existing env and volumes
3. Database migrations run automatically on backend startup
4. The `/health` endpoint confirms the stack is ready
