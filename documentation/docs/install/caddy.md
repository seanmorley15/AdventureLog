# Installation with Caddy

Caddy is a modern HTTP reverse proxy. It automatically integrates with Let's Encrypt (or other certificate providers) to generate TLS certificates for your site.

As an example, if you want to add Caddy to your Docker compose configuration, add the following service to your `docker-compose-ymö`:

```yaml
services:
  caddy:
    image: docker.io/library/caddy:2
    container_name: adventurelog-caddy
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./caddy:/etc/caddy
      - caddy_data:/data
      - caddy_config:/config

  web: ...
  server: ...
  db: ...

volumes:
  caddy_data:
  caddy_config:
```

Since all ingress traffic to the AdventureLog containsers now travels through Caddy, we can also remove the external ports configuration from those containsers in the `docker-compose.yml`. Just delete this configuration:

```yaml
  web:
    ports:
      - "8016:80"
…
  server:
    ports:
      - "8015:3000"
```

That's it for the Docker compose changes. Of course, there are other methods to run Caddy which are equally valid.

However, we also need to configure Caddy. For this, create a file `./caddy/Caddyfile` in which you configure the requests which are proxied to the frontend and backend respectively and what domain Caddy should request a certificate for:

```
adventurelog.example.com {

  @frontend {
    not path /media* /admin* /static* /accounts*
  }
  reverse_proxy @frontend web:3000

  reverse_proxy server:80
}
```

Once configured, you can start up the containsers:

```bash
docker compose up
```

Your AdventureLog should now be up and running.
