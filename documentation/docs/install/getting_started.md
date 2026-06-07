# Install AdventureLog

AdventureLog runs on Docker in most setups. Pick the guide that matches your environment — from a one-line installer to platform-specific homelab and NAS instructions.

## Quick start

::: tip Fastest install
```bash
curl -sSL https://get.adventurelog.app | bash
```
:::

The [Quick Start Installer](quick_start.md) walks you through setup (AIO by default), writes your env files, and starts AdventureLog. Re-run the same command for updates, backups, and configuration changes.

## Choose your setup

### Docker

| I want to… | Guide |
| ---------- | ----- |
| Guided install on a VPS or homelab | [Quick Start Installer](quick_start.md) |
| One container, one port, minimal config | [All-in-One Docker (AIO)](aio.md) |
| Separate frontend, backend, and database | [Standard Docker](docker.md) |
| HTTPS on a custom domain | [Reverse proxy guides](#reverse-proxy) |

### Homelab & NAS platforms

| Platform | Guide |
| -------- | ----- |
| Proxmox LXC | [Proxmox LXC](proxmox_lxc.md) |
| Synology NAS | [Synology NAS](synology_nas.md) |
| Unraid | [Unraid](unraid.md) |
| Umbrel | [Umbrel](https://apps.umbrel.com/app/adventurelog) — community app |
| TrueNAS SCALE | [TrueNAS](https://apps.truenas.com/catalog/adventurelog/) — community app |

These guides use the same AdventureLog Docker images, adapted for each platform.

### Kubernetes

| Platform | Guide |
| -------- | ----- |
| Kubernetes cluster | [Kubernetes + Kustomize](kustomize.md) |

### Development

| Use case | Guide |
| -------- | ----- |
| Local development on Windows / WSL | [Dev Container + WSL](dev_container_wsl.md) |

### Reverse proxy {#reverse-proxy}

Use these when AdventureLog sits behind HTTPS on a custom domain:

| Proxy | Guide |
| ----- | ----- |
| Nginx Proxy Manager | [Nginx Proxy Manager](nginx_proxy_manager.md) |
| Traefik | [Traefik](traefik.md) — includes `docker-compose-traefik.yaml` |
| Caddy | [Caddy](caddy.md) |

Set `SITE_URL` to your public HTTPS URL so Django CSRF and SvelteKit origins stay correct. See [Environment Variables](../configuration/environment_variables.md#url-and-networking).

## After installation

1. Log in with your admin credentials (default `admin` / `admin` — change immediately)
2. Review [How to Use AdventureLog](../usage/usage.md)
3. Configure optional features in [Configuration](../configuration/environment_variables.md)
4. Set up [backups](../configuration/operations.md#backup) before going to production

## Requirements

- Docker Engine + Docker Compose v2 (for Docker-based installs)
- **2 GB RAM** on first boot (world geography import); ~1 GB afterward
- Linux server, VPS, homelab, or macOS with Docker Desktop
- Optional: domain name and reverse proxy for HTTPS
