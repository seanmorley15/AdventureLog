# 🚀 Install Options for AdventureLog

AdventureLog can be installed in a variety of ways, depending on your platform or preference.

## Which setup should I use?

| Your situation | Recommended path |
| -------------- | ---------------- |
| New homelab / quick install | [Quick start installer](quick_start.md) — AIO by default, interactive setup |
| Full env control, split containers, or custom integrations | [Standard Docker](docker.md) — full `.env.example` (also available in installer advanced mode) |
| Split domains or path-based reverse proxy (Traefik, NPM, Caddy) | Standard Docker + [reverse proxy docs](#advanced--alternative-setups) |
| Kubernetes cluster | [Kubernetes + Kustomize](kustomize.md) — see `k8s/base/` |

## 📦 Docker Quick Start

::: tip Quick Start Script
**The fastest way to get started:**  
[Install AdventureLog with a single command →](quick_start.md)  
Perfect for Docker beginners.
:::

## 🐳 Popular Installation Methods

- [All-in-One Docker (AIO)](aio.md) — Single container, one port, minimal config
- [Docker](docker.md) — Standard multi-container setup
- [Proxmox LXC](proxmox_lxc.md) — Lightweight virtual environment
- [Synology NAS](synology_nas.md) — Self-host on your home NAS
- [Kubernetes + Kustomize](kustomize.md) — Advanced, scalable deployment
- [Unraid](unraid.md) — Easy integration for homelabbers
- [Umbrel](https://apps.umbrel.com/app/adventurelog) — Home server app store
- [TrueNAS](https://apps.truenas.com/catalog/adventurelog/) — TrueNAS app catalog

## ⚙️ Advanced & Alternative Setups

- [Nginx Proxy Manager](nginx_proxy_manager.md) - Easy reverse proxy config
- [Traefik](traefik.md) — Dynamic reverse proxy with automation
- [Caddy](caddy.md) — Automatic HTTPS with a clean config
- [Dev Container + WSL](dev_container_wsl.md) - Windows dev environment with WSL 2 + Dev Containers
