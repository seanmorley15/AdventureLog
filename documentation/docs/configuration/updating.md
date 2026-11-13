# Updating

Updating pulls new images and restarts AdventureLog. Database changes are applied automatically when the app starts. **Back up before every update.** See [Backups and Restore](backups.md).

Before a major version, read its [changelog](../changelogs/development_timeline.md) for steps that need you.

## Update commands

Pick the tab that matches how you installed. `scripts/deploy.sh` is the easiest: it validates your env file, backs up, pulls images, and waits until the app is healthy.

::: code-group

```bash [deploy.sh]
# From your install folder. Detects Standard or Advanced Deployment.
bash scripts/deploy.sh --backup
bash scripts/deploy.sh --logs   # optional: follow the logs afterward
```

```bash [Compose, Standard]
bash scripts/backup.sh
docker compose --env-file .env pull
docker compose --env-file .env up -d --wait
```

```bash [Compose, Advanced]
bash scripts/backup.sh
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml pull
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml up -d --wait
```

```bash [Quick Start Installer]
# Opens the management menu. Choose "Update".
bash install_adventurelog.sh --manage
```

:::

The deploy and backup scripts come with the [Quick Start Installer](../install/quick_start.md). For a manual install, [download them](backups.md#back-up) or use the Compose commands.

If your platform manages containers for you (Unraid, Synology, TrueNAS, Umbrel, Easypanel), update the AdventureLog images there.

## What happens during an update

1. New images are pulled.
2. The containers restart with your existing env file and volumes.
3. Database migrations run when the backend starts.
4. If a release adds new world data, it is imported once. This takes a few minutes and needs the same RAM as a first boot.
5. The `/health` check confirms the app is ready.

If something goes wrong, [restore the backup](backups.md#restore) you made first.

## World data

Country, region, and city data comes from [dr5hn/countries-states-cities-database](https://github.com/dr5hn/countries-states-cities-database). Each AdventureLog release pins a version of it, so it changes only when you update AdventureLog. To import it again by hand, for example after starting with `SKIP_WORLD_DATA=1`, run `download_countries`. See [Management Commands](management_commands.md#world-data).

Some releases change how the data is linked, such as v0.14, which ties territories like Puerto Rico to the country they are also listed under. The changelog says when a management command is needed afterward.

## Moving between setups

To switch an existing server from Advanced to Standard Deployment, see [Switch to Standard Deployment](../guides/switch_to_standard.md).
