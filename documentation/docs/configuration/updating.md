# Updating AdventureLog

Keep your self-hosted instance current with the latest images and database migrations. **Always back up before updating.**

## Option 1: scripts/deploy.sh (recommended)

From your install directory (where `scripts/deploy.sh` and your compose file live):

```bash
bash scripts/deploy.sh --backup
bash scripts/deploy.sh --logs   # optional: follow logs after deploy
```

`scripts/deploy.sh` validates your env file, creates a backup, pulls images, and runs `docker compose up -d --wait`.

For Standard Deployment installs:

```bash
COMPOSE_FILE=docker/docker-compose.advanced.yml bash scripts/deploy.sh --backup
```

See [Operations & Maintenance](operations.md) for compose auto-detection details.

## Option 2: Manual compose

```bash
bash scripts/backup.sh

# Standard Deployment
docker compose --env-file .env pull
docker compose --env-file .env up -d --wait

# Advanced Deployment
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml pull
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml up -d --wait
```

## Option 3: Guided installer menu

If you used the [Quick Start Installer](../install/quick_start.md), re-run it to open the management menu:

```bash
curl -sSL https://get.adventurelog.app | bash
```

Choose **Update to latest images** (with optional backup).

## Restore from backup

```bash
bash scripts/restore.sh backups/YYYYMMDD-HHMMSS
```

## Updating region data

Country and region reference data comes from [dr5hn/countries-states-cities-database](https://github.com/dr5hn/countries-states-cities-database). To refresh it manually:

```bash
docker exec -it <backend-container> bash
python manage.py download_countries --force
```

Region data version is pinned per AdventureLog release in `settings.py` and is not auto-updated on every deploy.

### Territories such as Guadeloupe and Puerto Rico

The dataset lists some places twice: as a country and as a region of another country (Guadeloupe as a country and as a region of France, Puerto Rico as a country and as a region of the United States). Geocoders report them under the larger country, so AdventureLog ties each pair together when it imports the data, and files new places under the territory's own country.

Upgrading from an earlier version repeats the world-data import once on the next start, since the links and native-language names are new. It takes a few minutes, needs the same RAM as a first boot, and keeps your visited regions. If you start with `SKIP_WORLD_DATA=1`, run `python manage.py download_countries` once yourself.

Places you saved before the update stay under the larger country. To move them, check what would change and then apply it:

```bash
python manage.py reassign_territory_locations
python manage.py reassign_territory_locations --apply
```

It uses the stored world data only and makes no geocoding requests. Visited regions and cities follow the places that moved.

### Visited places stay in sync

A territory and the region it is also listed as are one place, and a visit counts once. You mark it visited on the territory's own pages, and the region under the larger country mirrors that:

- On the United States page, Puerto Rico shows as visited whenever any region of the Puerto Rico country is. Opening it takes you to the Puerto Rico page, with a fresh search and filter, instead of a second list of the same place.
- The world data lists Puerto Rico's cities twice, 78 under the country and 255 under the United States region. The import merges them onto the country: a city with the same name on both sides is the same town and appears once, and the others move to the nearest Puerto Rico region. The region under the United States keeps no cities of its own.
- The statistics and the country list count a Puerto Rico trip once, for Puerto Rico, and not again for the United States.

This applies to every place the world data lists twice, not just Puerto Rico: the other US territories (Guam, the US Virgin Islands, American Samoa, the Northern Mariana Islands, the US Minor Outlying Islands), the French overseas territories, Hong Kong and Macau under China, and Svalbard under Norway. Only Puerto Rico, Hong Kong and New Caledonia list cities under the larger country, so those are the ones whose cities are merged.

Visits to a merged city move to the city it was merged into, and so do your places that were in it. Visits you marked on the larger country's region before the update stay as they were and are counted once in the statistics. `reassign_territory_locations --apply` tidies up the ones that came from your places.

## What happens during an update

1. New container images are pulled
2. Containers restart with your existing env and volumes
3. Database migrations run automatically on backend startup
4. The `/health` endpoint confirms the stack is ready
