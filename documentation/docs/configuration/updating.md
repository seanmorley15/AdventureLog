# Updating AdventureLog

Keep your self-hosted instance current with the latest images and database migrations. **Always back up before updating.**

## Option 1: scripts/deploy.sh (recommended)

From your install directory (where `scripts/deploy.sh` and your compose file live):

```bash
bash scripts/deploy.sh --backup
bash scripts/deploy.sh --logs   # optional: follow logs after deploy
```

`scripts/deploy.sh` validates your env file, creates a backup, pulls images, and runs `docker compose up -d --wait`.

For Standard Deployment installs:

```bash
COMPOSE_FILE=docker/docker-compose.advanced.yml bash scripts/deploy.sh --backup
```

See [Operations & Maintenance](operations.md) for compose auto-detection details.

## Option 2: Manual compose

```bash
bash scripts/backup.sh

# Standard Deployment
docker compose --env-file .env pull
docker compose --env-file .env up -d --wait

# Advanced Deployment
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml pull
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml up -d --wait
```

## Option 3: Guided installer menu

If you used the [Quick Start Installer](../install/quick_start.md), re-run it to open the management menu:

```bash
curl -sSL https://get.adventurelog.app | bash
```

Choose **Update to latest images** (with optional backup).

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
