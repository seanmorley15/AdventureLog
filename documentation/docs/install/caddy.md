# Caddy

[Caddy](https://caddyserver.com/) is a web server that gets HTTPS certificates automatically. Use it to serve AdventureLog on your own domain.

## 1. Add Caddy to your compose file

Add a `caddy` service next to AdventureLog's services, and its volumes:

```yaml
services:
  caddy:
    image: docker.io/library/caddy:2
    container_name: adventurelog-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./caddy:/etc/caddy
      - caddy_data:/data
      - caddy_config:/config

  # ...AdventureLog's services stay as they are

volumes:
  caddy_data:
  caddy_config:
```

All traffic now goes through Caddy, so you can remove the `ports:` from AdventureLog's own services.

## 2. Write the Caddyfile

Create `caddy/Caddyfile`, in the same folder as the compose file, with your domain:

::: code-group

```txt [Standard Deployment]
adventurelog.example.com {
  reverse_proxy app:80
}
```

```txt [Advanced Deployment]
adventurelog.example.com {
  @backend path /media* /admin* /static* /accounts*
  reverse_proxy @backend server:80
  reverse_proxy web:3000
}
```

:::

## 3. Set AdventureLog's address

Set `SITE_URL=https://adventurelog.example.com` in your env file. On Advanced Deployment, also delete or comment out `ORIGIN`, `FRONTEND_URL`, `PUBLIC_URL`, and `CSRF_TRUSTED_ORIGINS`; they are derived from `SITE_URL` only when they aren't set.

## 4. Start

```bash
docker compose --env-file .env up -d
```

For Advanced Deployment, use `--env-file .env.advanced -f docker/docker-compose.advanced.yml`. Open your domain and follow [First Steps](first_steps.md).
