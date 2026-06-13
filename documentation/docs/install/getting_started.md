# Install AdventureLog

AdventureLog runs on Docker in most setups. Pick the guide that matches your environment — from Standard Deployment to platform-specific homelab and NAS instructions.

## Choose your setup

### Docker

| I want to… | Guide |
| ---------- | ----- |
| One container, one port | <span class="al-rec-badge">Recommended</span> [Standard Deployment](standard.md) |
| Interactive walkthrough that deploys Standard Deployment | [Quick Start Installer](quick_start.md) |
| Separate frontend, backend, and database | [Advanced Deployment](docker.md) |
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
| Traefik | [Traefik](traefik.md) — includes `docker/docker-compose.traefik.yaml` |
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
