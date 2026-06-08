# Operations & Maintenance

Day-to-day tasks for a self-hosted AdventureLog instance: updates, backups, validation, and the installer management menu.

## Management menu

If you installed via the [Quick Start Installer](../install/quick_start.md), re-run it to open the interactive management menu:

```bash
curl -sSL https://get.adventurelog.app | bash
```

Or from your install directory:

```bash
bash install_adventurelog.sh --manage
```

Available actions:

| Action | What it does |
| ------ | ------------ |
| **Status** | Shows container health and `/health` endpoint |
| **Update** | Pulls latest images and redeploys (optional backup first) |
| **Reconfigure** | Re-runs the configuration wizard |
| **Backup** | Runs `scripts/backup.sh` |
| **Restore** | Runs `scripts/restore.sh` from a backup folder |
| **Logs** | Follows container logs |
| **Restart** | Restarts the compose stack |
| **Uninstall** | Stops containers, removes volumes |

## Compose file detection

`scripts/deploy.sh`, `scripts/backup.sh`, and `scripts/restore.sh` auto-detect your setup:

| Condition | Compose file | Env file |
| --------- | ------------ | -------- |
| Only `.env.aio` exists | `docker/docker-compose.aio.yml` | `.env.aio` |
| `ADVENTURELOG_COMPOSE=aio` with both env files | `docker/docker-compose.aio.yml` | `.env.aio` |
| Otherwise | `docker/docker-compose.yml` | `.env` |

Override manually:

```bash
COMPOSE_FILE=docker/docker-compose.aio.yml bash scripts/deploy.sh --backup
```

Always pass `--env-file` when running `docker compose` directly:

```bash
docker compose --env-file .env.aio -f docker/docker-compose.aio.yml ps
```

## Updating

See [Updating](updating.md) for full details. Quick reference:

```bash
# Recommended — validates env, backs up, pulls, and waits for health
bash scripts/deploy.sh --backup

# AIO with explicit compose file
COMPOSE_FILE=docker/docker-compose.aio.yml bash scripts/deploy.sh --backup
```

## Backup

`scripts/backup.sh` creates a timestamped folder under `backups/` containing:

- Your env file (`.env` or `.env.aio`)
- PostgreSQL dump (`database.sql`)
- Media volume archive (`media.tar.gz`)

```bash
bash scripts/backup.sh
# Custom output directory:
BACKUP_DIR=/mnt/backups bash scripts/backup.sh
```

## Restore

```bash
bash scripts/restore.sh backups/20260101-120000
```

This stops the stack, restores env + database + media, and brings containers back up.

## Environment validation

Run before every deploy or after editing env files:

```bash
bash scripts/validate-env.sh
bash scripts/validate-env.sh .env.aio
```

The validator catches common mistakes such as `PUBLIC_SERVER_URL` pointing at the host backend port instead of the internal Docker service name.

## First boot behavior

On first start, the backend container:

1. Runs database migrations
2. Creates the Django superuser from `DJANGO_ADMIN_*` variables
3. Imports world geography data (`download-countries`) unless `SKIP_WORLD_DATA=1`

The geography import needs **~2 GB RAM** on first boot. Steady-state use is typically **~1 GB**. The installer offers `SKIP_WORLD_DATA=1` on low-memory hosts.

## Scheduled tasks

Inside the backend container, a cron job runs nightly (UTC midnight):

```bash
python manage.py sync_visited_regions
```

This keeps world-travel region visit status in sync with location data.

## In-app backup vs shell scripts

AdventureLog also has backup/restore features in **Settings** that operate through the REST API. These are separate from `scripts/backup.sh` and are useful for app-level exports. For full disaster recovery (database + media + env), use the shell scripts.

## Security checklist

- [ ] Change default `POSTGRES_PASSWORD`, `SECRET_KEY`, and admin credentials
- [ ] Set `ENABLE_RATE_LIMITS=True` in production
- [ ] Configure `CSRF_TRUSTED_ORIGINS` / `SITE_URL` for your public domain
- [ ] Use HTTPS via a reverse proxy
- [ ] Review [API Keys](api_keys.md) and revoke unused keys
- [ ] Enable MFA in **Settings → Security** for admin accounts

## Related docs

- [Environment Variables](environment_variables.md)
- [Updating](updating.md)
- [Troubleshooting](../troubleshooting/login_unresponsive.md)
