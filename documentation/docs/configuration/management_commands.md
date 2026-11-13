# Management Commands

AdventureLog includes command-line tools for maintenance that the app doesn't do on its own. Run them inside the backend container:

::: code-group

```bash [Standard]
docker compose exec app python3 manage.py <command> [options]
```

```bash [Advanced]
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml exec server python3 manage.py <command> [options]
```

:::

Commands that change data have a dry run. Use it first, and [back up](backups.md) before applying changes.

## Accounts

| Command | What it does |
| ------- | ------------ |
| `changepassword <username>` | Sets a new password for a user, such as a locked-out admin |
| `createsuperuser` | Creates another admin account |

## World data {#world-data}

| Command | What it does |
| ------- | ------------ |
| `download_countries` | Imports the country, region, and city data. Runs on first boot unless `SKIP_WORLD_DATA=1`. Needs about 2 GB of RAM. |
| `download_countries --force` | Downloads the data again even if it's already there |
| `sync_visited_regions` | Marks the regions and cities of everyone's visited locations as visited. This also runs every night. |

`sync_visited_regions` takes `--dry-run`, `--user-id ID`, `--batch-size N`, and `--verbose`. Staff can also run it for their own account under **Settings → Admin → Update Visited Regions**.

### Territories

Since v0.14, places that the world data lists twice (Puerto Rico as a country and as a US region, for example) are filed under the territory's own country. See [World Travel](../usage/world_travel.md#territories). Two commands tidy up locations saved before then:

| Command | What it does |
| ------- | ------------ |
| `reassign_territory_locations` | Lists locations filed under the larger country that belong to a territory. Add `--apply` to move them. Visited regions and cities follow. |
| `fix_location_countries` | Lists locations whose country disagrees with their region or city, which older backup imports could cause. Add `--apply` to fix them. |

Both use the stored world data only and make no geocoding requests. Without `--apply` they change nothing.

## Photos and files

| Command | What it does |
| ------- | ------------ |
| `backfill_image_coordinates` | Stores GPS coordinates for photos uploaded before AdventureLog read them, so they appear on maps with **Photo locations** turned on |
| `image_cleanup` | Lists stored files that no location or collection uses, and asks before deleting them. `--dry-run` only lists them. |

`backfill_image_coordinates` reads each photo's EXIF data, then falls back to the linked Immich photo if there is one. Photos converted to WEBP may have lost their EXIF data. Options:

| Option | Purpose |
| ------ | ------- |
| `--dry-run` | Show what would be updated without saving |
| `--user-id ID` | Only one user's photos |
| `--batch-size N` | How often to log progress (default 100) |
| `--force` | Read coordinates again even when they're already stored |
| `--verbose` | Log each photo |

## Activities

| Command | What it does |
| ------- | ------------ |
| `activity_elevation_fix` | Recalculates elevation for activities that have a GPX file. Takes `--dry-run`, `--activity-id ID`, and `--batch-size N`. |
