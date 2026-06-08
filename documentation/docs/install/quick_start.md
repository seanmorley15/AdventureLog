# Quick Start Installer

The guided installer is an optional way to deploy **All-in-One (AIO) Docker** — the setup most people use. It walks you through configuration interactively, writes your env files, and includes a management menu for updates and backups.

For manual AIO setup with Docker Compose, see [All-in-One Docker](aio.md).

## One-line install

```bash
curl -sSL https://get.adventurelog.app | bash
```

## What the installer does

1. Checks dependencies (Docker, Compose v2, RAM, CPU architecture)
2. Detects ARM hosts and configures a compatible PostGIS image automatically
3. Creates the `./adventurelog` project directory (configurable via `INSTALL_DIR`)
4. Downloads compose files, env files, and management scripts
5. Walks you through site URL, admin credentials, and optional features (S3, email, integrations)
6. Starts containers and waits for the `/health` endpoint
7. Saves credentials to `credentials.txt` when generated

## Requirements

| Requirement | Details |
| ----------- | ------- |
| Docker + Compose v2 | Required |
| RAM | 2 GB recommended on first boot; ~1 GB afterward |
| OS | Linux server, VPS, or macOS with Docker Desktop |
| Domain | Optional — set `SITE_URL` for HTTPS behind a reverse proxy |

::: tip ARM / Apple Silicon
The installer automatically uses `imresamu/postgis:16-3.5-alpine` on ARM hosts. AdventureLog images are multi-arch.
:::

## Setup modes

During installation you can choose:

| Mode | Compose file | Env file | When to use |
| ---- | ------------ | -------- | ----------- |
| **All-in-One** (default) | `docker/docker-compose.aio.yml` | `.env.aio` | Simplest — one port, auto-derived URLs |
| **Standard** | `docker/docker-compose.yml` | `.env` | Full env control, separate frontend/backend ports |

## Management menu

Re-run the installer when an install already exists:

```bash
curl -sSL https://get.adventurelog.app | bash
# or from the install directory:
bash install_adventurelog.sh --manage
```

Options include status, update, reconfigure, backup, restore, logs, restart, and uninstall. See [Operations & Maintenance](../configuration/operations.md).

## Dry run

Preview what the installer would do without making changes:

```bash
ADVENTURELOG_SKIP_GUM=1 bash install_adventurelog.sh --dry-run --force-install
```

## Uninstall

From the management menu, choose **Uninstall**, or manually:

```bash
cd adventurelog
docker compose --env-file .env.aio -f docker/docker-compose.aio.yml down -v
rm -rf adventurelog
```

## Next steps

- [All-in-One Docker](aio.md) — how the AIO container works
- [Standard Docker](docker.md) — multi-container configuration
- [Environment Variables](../configuration/environment_variables.md) — full reference
- [Other install options](getting_started.md)
