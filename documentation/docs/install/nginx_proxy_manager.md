# Nginx Proxy Manager

[Nginx Proxy Manager](https://nginxproxymanager.com/) is a web interface for nginx proxy hosts and SSL certificates. Use it to serve AdventureLog over HTTPS on your own domain.

## 1. Put both on one Docker network

Nginx Proxy Manager reaches AdventureLog by container name, so they must share a network. Create one:

```bash
docker network create proxy
```

Add it to the bottom of AdventureLog's compose file, and to Nginx Proxy Manager's:

```yaml
networks:
  default:
    name: proxy
    external: true
```

Restart both.

## 2. Set AdventureLog's address

Set `SITE_URL` to your public HTTPS address, for example `https://adventurelog.example.com`, and restart AdventureLog. On Advanced Deployment, also delete or comment out `ORIGIN`, `FRONTEND_URL`, `PUBLIC_URL`, and `CSRF_TRUSTED_ORIGINS` in `.env.advanced`; they are derived from `SITE_URL` only when they aren't set.

## 3. Add the proxy host

In Nginx Proxy Manager, go to **Hosts → Proxy Hosts → Add Proxy Host**, enter your domain, and request an SSL certificate on the **SSL** tab.

::: code-group

```txt [Standard Deployment]
Details tab
  Scheme:                http
  Forward Hostname / IP: adventurelog
  Forward Port:          80
```

```txt [Advanced Deployment]
Details tab
  Scheme:                http
  Forward Hostname / IP: adventurelog-frontend
  Forward Port:          3000

Custom locations tab: add one for each of
  /media  /admin  /accounts  /static
  Scheme:                http
  Forward Hostname / IP: adventurelog-backend
  Forward Port:          80
```

:::

The ports are the containers' internal ports, so they stay the same whatever host ports you mapped.

Open your domain and follow [First Steps](first_steps.md).
