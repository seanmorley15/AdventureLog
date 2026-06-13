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
| Only `.env` exists | `docker/docker-compose.yml` | `.env` |
| Only `.env.advanced` exists | `docker/docker-compose.advanced.yml` | `.env.advanced` |
| `ADVENTURELOG_COMPOSE=advanced` with both env files | `docker/docker-compose.advanced.yml` | `.env.advanced` |
| Otherwise | `docker/docker-compose.yml` | `.env` |

Override manually:

```bash
COMPOSE_FILE=docker/docker-compose.advanced.yml bash scripts/deploy.sh --backup
```

Always pass `--env-file` when running `docker compose` directly:

```bash
docker compose --env-file .env -f docker/docker-compose.yml ps
```

## Updating

See [Updating](updating.md) for full details. Quick reference:

```bash
# Recommended — validates env, backs up, pulls, and waits for health
bash scripts/deploy.sh --backup

# Advanced Deployment with explicit compose file
COMPOSE_FILE=docker/docker-compose.advanced.yml bash scripts/deploy.sh --backup
```

## Backup

`scripts/backup.sh` creates a timestamped folder under `backups/` containing:

- Your env file (`.env` or `.env.advanced`)
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
bash scripts/validate-env.sh .env
bash scripts/validate-env.sh .env.advanced
```

The validator catches common mistakes such as `PUBLIC_SERVER_URL` pointing at the host backend port instead of the internal Docker service name.

## First boot behavior
