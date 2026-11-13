# Common Issues

Find your symptom, then follow the fix. Most problems come from a URL setting that doesn't match the address in your browser, so check that first.

## First, read the log

The backend log usually names the problem.

::: code-group

```bash [Standard]
docker compose logs --tail 200 app
```

```bash [Advanced]
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml logs --tail 200 server web
```

:::

## Symptoms

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| `admin` / `admin` doesn't work | The admin password is generated on first start | [Find the admin password](../install/first_steps.md#_2-find-the-admin-password) |
| The page doesn't load right after the first start | The world data is still importing | Wait a few minutes and watch the log. With less than 2 GB of RAM the import can be killed; see [below](#the-container-keeps-restarting-on-first-start). |
| Login or sign-up does nothing, or returns 403 | URL or CSRF settings don't match your address | [Login and Registration Unresponsive](login_unresponsive.md) |
| Photos don't show | The public URL is wrong or not reachable | [Images Not Displaying](no_images.md) |
| A reverse proxy returns 502 | The proxy points at the wrong container or port | [The proxy returns 502](#the-proxy-returns-502) |
| Social or OIDC sign-in returns 404 | `/accounts` isn't routed to the backend | [Social sign-in returns 404](#social-sign-in-returns-404) |
| The World Travel country list is empty | The world data was skipped or didn't finish | Run `download_countries`. See [Management Commands](../configuration/management_commands.md#world-data). |
| An export or import stays "Preparing…" | The background worker isn't running | [Background Jobs](../configuration/background_jobs.md#troubleshooting) |
| An integration can't connect | `localhost` means the AdventureLog container, not your server | [An integration can't connect](#an-integration-can-t-connect) |
| Emails never arrive | Email is set to print to the log | [SMTP Email](../configuration/email.md) |
| Uploads fail for large files | The upload size limit | Raise `BODY_SIZE_LIMIT`. See [Environment Variables](../configuration/environment_variables.md). |
| Backend restarts with `nginx failed!` | An old Advanced Deployment with a renamed service | [Nginx Failed to Start](nginx_failed.md) |

## The container keeps restarting on first start

The first start imports the world geography data, which needs about 2 GB of RAM. If the log shows `download_countries was interrupted (likely out of memory)`, give the container more memory, or set `SKIP_WORLD_DATA=1` to skip the import and [run it later](../configuration/management_commands.md#world-data).

## The proxy returns 502

- **Standard Deployment**: proxy the whole domain to the app container on port `80`, or to the host on `HOST_PORT` (`8015` by default).
- **Advanced Deployment**: proxy pages to the `web` container on port `3000`, and `/media`, `/admin`, `/accounts`, and `/static` to the `server` container on port `80`.
- If the proxy runs in Docker, it must share a Docker network with AdventureLog.

See the [reverse proxy guides](../install/getting_started.md#reverse-proxy).

## Social sign-in returns 404

On Advanced Deployment, your reverse proxy must send `/accounts/*` to the backend. Standard Deployment handles this itself. Also check that the redirect URL at your identity provider uses your backend's public address. See [Social Auth & OIDC](../configuration/social_auth.md).

## An integration can't connect

Immich, Wanderer, Endurain, and OIDC providers are called **from the AdventureLog server**, not from your browser. Inside a container, `localhost` and `127.0.0.1` mean the container itself. Use your server's LAN IP address, a hostname, or a shared Docker network instead.

## Still stuck?

Ask in the [Discord server](https://discord.gg/wRbQ9Egr8C) or open a [GitHub issue](https://github.com/seanmorley15/AdventureLog/issues). Include your install method, the AdventureLog version from **Settings → About**, and the relevant log lines with secrets removed.
