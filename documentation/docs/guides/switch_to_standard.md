# Switch to Standard Deployment

Move an existing Advanced Deployment (separate `web`, `server`, and `db` containers) to [Standard Deployment](../install/standard.md), with one app container on one port. Your users, locations, collections, and photos come with you.

The steps copy your data into new volumes and leave the old ones untouched, so you can go back if anything is wrong.

## Before you start

- **Update first.** Bring the Advanced Deployment up to the latest version, so both setups run the same database version. See [Updating](../configuration/updating.md).
- **Have a backup.** You'll make a fresh one in step 1. See [Backups and Restore](../configuration/backups.md).
- **Collect your settings.** Open `.env.advanced` and note `POSTGRES_PASSWORD`, `SECRET_KEY`, and any optional settings you use, such as email, S3, Google Maps, or Strava.

Run every command from your install folder, the one with `.env.advanced` and the `docker/` folder.

## 1. Back up and stop

```bash
bash scripts/backup.sh
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml down
```

Note the backup folder it prints, for example `backups/20260101-120000`. Don't add `-v` to `down`: that would delete the old volumes.

## 2. Create the Standard Deployment files

```bash
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/docker-compose.yml
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/.env.example
cp .env.example .env
```

Edit `.env`:

```env
POSTGRES_PASSWORD=<same as in .env.advanced>
SECRET_KEY=<same as in .env.advanced>
SITE_URL=https://adventurelog.example.com
```

Keep `SECRET_KEY`: a new one signs everyone out and stops existing API keys working. Then copy over any optional settings you noted. Leave out `PUBLIC_URL`, `ORIGIN`, `FRONTEND_URL`, `CSRF_TRUSTED_ORIGINS`, and `PUBLIC_SERVER_URL`; Standard Deployment works them out from `SITE_URL`.

## 3. Load the database

Start only the new database, clear it, and load your backup:

```bash
BACKUP=backups/20260101-120000   # your backup folder
docker compose --env-file .env up -d db
docker compose --env-file .env exec -T db psql -U adventure -d database \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose --env-file .env exec -T db psql -U adventure -d database < "$BACKUP/database.sql"
```

If your old setup used a database user other than `adventure`, the load reports errors about that role. They don't affect your data.

## 4. Load the photos and files

```bash
docker compose --env-file .env run --rm --no-deps \
  -v "$PWD/$BACKUP":/backup:ro --entrypoint sh app \
  -c "tar xzf /backup/media.tar.gz -C /code/media"
```

Skip this step if you use [S3 media storage](../configuration/s3_storage.md).

## 5. Start AdventureLog

```bash
docker compose --env-file .env up -d --wait
```

Open your `SITE_URL` and sign in with your usual account.

## 6. Update your reverse proxy

Standard Deployment serves everything on one port, `8015` by default (`HOST_PORT`). Point your proxy at that port for the whole domain, and remove the rules that sent `/media`, `/admin`, `/accounts`, and `/static` to the backend.

## 7. Clean up

Once everything works, remove the old files: `.env.advanced` and `docker/docker-compose.advanced.yml`. The scripts in `scripts/` then use Standard Deployment automatically.

Later, delete the old volumes. List them first, and remove only the ones from the Advanced Deployment (their names start with the old project name, usually `docker_`):

```bash
docker volume ls | grep -E "postgres_data|adventurelog_media"
docker volume rm docker_postgres_data docker_adventurelog_media
```

## Going back

Stop the Standard Deployment with `docker compose --env-file .env down`, then start the Advanced one again with its usual command. Its volumes were never changed.
