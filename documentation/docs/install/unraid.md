# Unraid

AdventureLog is in the Unraid Community Applications store as two apps, a frontend and a backend, plus a PostGIS database app. This is an Advanced Deployment, with separate containers.

- [AdventureLog in Community Applications](https://ca.unraid.net/apps?q=adventurelog)
- [PostGIS in Community Applications](https://ca.unraid.net/apps/postgis-0xoswv81175v5s?q=PostGIS)

## Before you start

Install the three apps **in this order**: database, backend, frontend. Put them all on one custom Docker network, so they can reach each other by container name. Create it from the Unraid terminal, replacing `adventurelog` with any name:

```bash
docker network create adventurelog
```

The network then appears when you set up each app. Container names can be anything; the steps below refer to them as the database and backend containers.

## 1. Database

Search Community Applications for **PostGIS**. There is no separate AdventureLog database app.

- **Network type**: your custom network.
- **Repository**: change it to `postgis/postgis:16-3.5`.
- Set these variables. The template has `POSTGRES_PASSWORD`; add the other two.

| Variable | Description |
| -------- | ----------- |
| `POSTGRES_DB` | Database name, for example `adventurelog` |
| `POSTGRES_USER` | Database user, created on first start |
| `POSTGRES_PASSWORD` | That user's password |

The forwarded port `5012` is only needed to reach the database from outside its network.

[![Unraid PostGIS template settings](/unraid-config-2.png)](/unraid-config-2.png)

## 2. Backend

- **Network type**: your custom network.

| Setting | Value |
| ------- | ----- |
| API port | `8016`. This is a port mapping, not a variable. |
| `PGHOST` | The database container's name |
| `PGDATABASE`, `PGUSER`, `PGPASSWORD` | The same as `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` above |
| `SECRET_KEY` | A long random string. Keep it: changing it signs everyone out. |
| `DJANGO_ADMIN_USERNAME` | The first admin's username, for example `admin` |
| `DJANGO_ADMIN_EMAIL` | The first admin's email. Each email can belong to one user only. |
| `DJANGO_ADMIN_PASSWORD` | Optional. Empty or weak: a password is generated and printed once in the container log. See [First Steps](first_steps.md#_2-find-the-admin-password). |
| `PUBLIC_URL` | How your browser reaches the backend, such as `http://192.168.1.20:8016` or your domain. Photo URLs use it. |
| `FRONTEND_URL` | How your browser reaches the frontend, such as `http://192.168.1.20:8015`. Email links use it. |
| `CSRF_TRUSTED_ORIGINS` | Both addresses above, comma-separated |

On a network other than `host`, use the server's IP address in these URLs, not `localhost`.

[![Unraid backend template settings](/unraid-config-1.png)](/unraid-config-1.png)

## 3. Frontend

- **Network type**: your custom network.

| Setting | Value |
| ------- | ----- |
| Web UI port | `8015`. This is a port mapping, not a variable. |
| `PUBLIC_SERVER_URL` | `http://<backend container name>:8000`. The template's default uses `IP_ADDRESS`; replace it with the backend container's name. |
| `ORIGIN` | How your browser reaches the frontend, such as `http://192.168.1.20:8015` or your domain |
| `BODY_SIZE_LIMIT` | Maximum upload size in bytes. The default, `Infinity`, has no limit. |

[![Unraid frontend template settings](/unraid-config-3.png)](/unraid-config-3.png)

## Video walkthrough

AlienTech42 made a video of the whole installation:

<iframe width="560" height="315" src="https://www.youtube.com/embed/hJnoePdAhXg" title="Installing AdventureLog on Unraid" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

## Next steps

- [First Steps](first_steps.md): sign in, secure the admin account, and decide who can join.
- [Updating](../configuration/updating.md): update the three apps from the Docker tab.
