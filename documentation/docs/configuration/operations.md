# Operations

Day-to-day tools for a self-hosted AdventureLog server: the installer's management menu, the helper scripts, and env file validation.

| Task | Page |
| ---- | ---- |
| Back up and restore | [Backups and Restore](backups.md) |
| Update to a new version | [Updating](updating.md) |
| Run maintenance commands | [Management Commands](management_commands.md) |
| Manage users and data in the browser | [Admin Panel](../guides/admin_panel.md) |

## Management menu

If you installed with the [Quick Start Installer](../install/quick_start.md), run it again, or run the script from your install folder:

```bash
bash install_adventurelog.sh --manage
```

| Action | What it does |
| ------ | ------------ |
| **Status** | Shows container health and the `/health` check |
| **Update** | Pulls the latest images and restarts, with an optional backup first |
| **Reconfigure** | Runs the setup questions again |
| **Backup** | Runs `scripts/backup.sh` |
| **Restore** | Runs `scripts/restore.sh` with a backup folder you pick |
| **Logs** | Follows the container logs |
| **Restart** | Restarts the containers |
| **Uninstall** | Stops the containers and deletes their volumes |

## Helper scripts

The installer puts these in `scripts/`. [Backups and Restore](backups.md#back-up) shows how to download them for a manual install.

| Script | What it does |
| ------ | ------------ |
| `deploy.sh` | Validates the env file, optionally backs up, pulls images, and restarts. See [Updating](updating.md). |
| `backup.sh`, `restore.sh` | See [Backups and Restore](backups.md). |
| `validate-env.sh` | Checks an env file for common mistakes. See [below](#validate-your-env-file). |

### Which setup the scripts use

The scripts work out whether you run Standard or Advanced Deployment from the env files in the folder:

| Files present | Compose file | Env file |
| ------------- | ------------ | -------- |
| Only `.env` | `docker-compose.yml` | `.env` |
| Only `.env.advanced` | `docker/docker-compose.advanced.yml` | `.env.advanced` |
| Both, with `ADVENTURELOG_COMPOSE=advanced` set | `docker/docker-compose.advanced.yml` | `.env.advanced` |
| Anything else | `docker-compose.yml` | `.env` |

To choose explicitly, set `COMPOSE_FILE`:

```bash
COMPOSE_FILE=docker/docker-compose.advanced.yml bash scripts/deploy.sh --backup
```

When you run `docker compose` yourself, always pass the env file, for example `docker compose --env-file .env ps`.

## Validate your env file

Run this after editing an env file, and before deploying:

```bash
bash scripts/validate-env.sh               # detects the file
bash scripts/validate-env.sh .env.advanced # or name it
```

It catches common mistakes, such as `PUBLIC_SERVER_URL` pointing at the host's backend port instead of the internal Docker service name.

## Logs

::: code-group

```bash [Standard]
docker compose logs -f app
```

```bash [Advanced]
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml logs -f server web
```

:::

The backend log shows startup, migrations, the background job worker, and errors. For problems, start with [Troubleshooting](../troubleshooting/common_issues.md).
