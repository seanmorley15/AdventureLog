# Updating

Updating AdventureLog when using Docker is straightforward. **Back up your instance before updating.**

### Option 1: Re-run the installer (management menu)

```bash
curl -sSL https://get.adventurelog.app | bash
```

Choose **Update to latest images** (optionally with backup).

### Option 2: deploy.sh (cron-safe)

Make sure you are in the same directory as your compose file.

```bash
bash deploy.sh --backup
bash deploy.sh --logs   # optional: follow container logs after deploy
```

For AIO installs, pass the compose file explicitly or rely on auto-detection when only `.env.aio` exists:

```bash
COMPOSE_FILE=docker-compose.aio.yml bash deploy.sh --backup
```

### Option 3: Manual

```bash
bash scripts/backup.sh
docker compose pull
docker compose up -d --wait
```

To restore from a backup directory:

```bash
bash scripts/restore.sh backups/YYYYMMDD-HHMMSS
```

## Updating the Region Data

Region and Country data in AdventureLog is provided by an open source project: [dr5hn/countries-states-cities-database](https://github.com/dr5hn/countries-states-cities-database). If you would like to update the region data in your AdventureLog instance, you can do so by running the following command. This will make sure your database is up to date with the latest region data for your version of AdventureLog. For security reasons, the region data is not automatically updated to the latest and is release version is controlled in the `settings.py` file.

```bash
docker exec -it <container> bash
```

Once you are in the container run the following command to resync the region data.

```bash
python manage.py download-countries --force
```
