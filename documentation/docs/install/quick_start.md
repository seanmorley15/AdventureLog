# Quick Start Installer

The guided installer sets up [Standard Deployment](standard.md) for you. It asks a few questions, writes your env file, starts AdventureLog, and installs a management menu for updates and backups.

## Install

Check the [requirements](getting_started.md#requirements), then run:

```bash
curl -sSL https://get.adventurelog.app | bash
```

When it finishes, follow [First Steps](first_steps.md).

## What the installer does

1. Checks for Docker, Compose v2, enough RAM, and your CPU architecture. On a low-memory host it offers to skip the world data import.
2. On ARM hosts, picks a compatible PostGIS image.
3. Creates the `./adventurelog` folder. Set `INSTALL_DIR` to use another one.
4. Downloads the compose file, env file, and the management scripts (`scripts/deploy.sh`, `backup.sh`, `restore.sh`, `validate-env.sh`).
5. Asks for your site URL, admin account, and optional features such as S3, email, and integrations.
6. Starts the containers and waits until AdventureLog answers on `/health`.
7. Shows the admin password if it generated one, and offers to save it to `credentials.txt`.

During setup you can choose **Advanced Deployment** instead. It uses `docker/docker-compose.advanced.yml` and `.env.advanced`. See [Advanced Deployment](docker.md).

## Manage an existing install

Run the installer again in the same place, or run the script from your install folder:

```bash
bash install_adventurelog.sh --manage
```

The menu can show status, update, reconfigure, back up, restore, follow logs, restart, and uninstall. See [Operations](../configuration/operations.md#management-menu).

## Preview without installing

```bash
curl -sSL https://get.adventurelog.app | bash -s -- --dry-run --force-install
```

## Uninstall

Choose **Uninstall** in the management menu, or remove everything by hand. This deletes your data, so [back up](../configuration/backups.md) first.

```bash
cd adventurelog
docker compose --env-file .env down -v
cd .. && rm -rf adventurelog
```
