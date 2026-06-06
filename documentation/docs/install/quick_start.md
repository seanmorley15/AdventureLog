# 🚀 Quick Start Install

Install **AdventureLog** in seconds using our automated installer. The script defaults to the **All-in-One (AIO)** setup — one URL, one port, minimal configuration.

## 🧪 One-Liner Install

```bash
curl -sSL https://get.adventurelog.app | bash
```

This will:

- Check dependencies (Docker, Docker Compose, RAM, architecture)
- Detect ARM hosts and configure a compatible PostGIS image automatically
- Set up the `./adventurelog` project directory
- Download `docker-compose.aio.yml`, `.env.aio`, and management scripts
- Walk you through core and optional configuration (S3, email, integrations, etc.)
- Start AdventureLog and wait for the health check

## ✅ Requirements

- Docker + Docker Compose v2
- **2 GB RAM** recommended on first boot (world geography import); ~1 GB afterward
- Linux server, VPS, or macOS with Docker Desktop
- Optional: domain name for HTTPS (set `SITE_URL` to your public URL)

::: tip ARM / Apple Silicon
The installer automatically uses `imresamu/postgis:16-3.5-alpine` on ARM hosts. AdventureLog AIO images are multi-arch.
:::

## 🔍 What It Does

The script automatically:

1. Verifies Docker is installed and running
2. Offers **All-in-One** (recommended) or **Standard** (separate frontend/backend) setup
3. Downloads compose files, `.env.aio` or `.env`, `deploy.sh`, and backup scripts
4. Prompts for site URL, admin credentials, and optional features
5. Waits for `/health` (first boot may take several minutes)
6. Saves optional credentials to `credentials.txt`

## 🔄 Management (Re-run the installer)

Re-run the same command to open the **management menu** when an install already exists:

```bash
curl -sSL https://get.adventurelog.app | bash
# or from the install directory:
bash install_adventurelog.sh --manage
```

Management options include:

- Check status and health
- Update to latest images (`deploy.sh --backup`)
- Edit configuration
- Backup and restore
- View logs, restart, or uninstall

## 🧼 Uninstall

From the management menu, choose **Uninstall**, or manually:

```bash
cd adventurelog
docker compose -f docker-compose.aio.yml down -v
rm -rf adventurelog
```

Need more control? See [All-in-One Docker](aio.md), [Standard Docker](docker.md), or other [install options](getting_started.md).
