# Install AdventureLog

AdventureLog runs in Docker. Most people use **Standard Deployment**: one app container and one database, reached on a single port. Pick a guide below, then follow [First Steps](first_steps.md) once the app is running.

## Requirements

| Requirement | Details |
| ----------- | ------- |
| Docker | Docker Engine with Docker Compose v2, or a platform that runs Docker images |
| Memory | **2 GB RAM** on first boot, while the world geography data is imported; about **1 GB** afterward |
| Host | Linux server, VPS, homelab, NAS, or macOS with Docker Desktop |
| CPU | x86-64 or ARM64. The AdventureLog images are multi-arch. |
| HTTPS (optional) | A domain name and a [reverse proxy](#reverse-proxy) |

On a small host, set `SKIP_WORLD_DATA=1` to skip the geography import on first boot and run it later. See [Advanced Settings](../configuration/advanced_configuration.md#performance).

## Choose your setup

### Docker

| I want… | Guide |
| ------- | ----- |
| One container, one port | <span class="al-rec-badge">Recommended</span> [Standard Deployment](standard.md) |
| A guided installer that sets up Standard Deployment for me | [Quick Start Installer](quick_start.md) |
| Separate frontend, backend, and database containers | [Advanced Deployment](docker.md) |

### Homelab and NAS platforms

| Platform | Guide |
| -------- | ----- |
| Proxmox LXC | [Proxmox LXC](proxmox_lxc.md) |
| Synology NAS | [Synology NAS](synology_nas.md) |
| Unraid | [Unraid](unraid.md) |
| Easypanel | [Easypanel](easypanel.md), official template |
| Umbrel | [Umbrel app store](https://apps.umbrel.com/app/adventurelog), community app |
| TrueNAS SCALE | [TrueNAS app catalog](https://apps.truenas.com/catalog/adventurelog/), community app |
| Kubernetes | [Kubernetes with Kustomize](kustomize.md) |

These all use the same AdventureLog Docker images, adapted for each platform.

### Reverse proxy {#reverse-proxy}

Use one of these to serve AdventureLog over HTTPS on your own domain:

| Proxy | Guide |
| ----- | ----- |
| Nginx Proxy Manager | [Nginx Proxy Manager](nginx_proxy_manager.md) |
| Traefik | [Traefik](traefik.md), with a ready-made compose file |
| Caddy | [Caddy](caddy.md) |

Whichever you use, set `SITE_URL` to your public HTTPS address. See [URL and networking](../configuration/environment_variables.md#url-and-networking).

### Working on AdventureLog itself

To change the code rather than run the app, see [Development Setup](dev_container_wsl.md).

## After installation

1. Follow [First Steps](first_steps.md) to sign in, find the admin password, and set up email and backups.
2. Go through the [Production Checklist](production_checklist.md) before you rely on the server.
3. Learn the app in the [Usage guide](../usage/usage.md).
