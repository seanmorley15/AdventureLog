# Backups and Restore

An AdventureLog server keeps its data in two places: the **PostgreSQL database** and the **media volume** with uploaded photos and files. A backup needs both, plus your env file.

There are two kinds of backup, for different jobs:

| | Server backup | Account backup |
| --- | --- | --- |
| Made by | The server admin, from the command line | Any user, under **Settings → Data & Storage** |
| Contains | Every user, the database, all media, the env file | One account: locations, visits, collections, media, and settings |
| Use it to | Recover the whole server, or move it to another host | Move one account to another server, or keep a personal copy |

This page covers server backups. For account backups, see [Account and Settings](../usage/settings.md#data-and-storage).

::: tip S3 storage
If you use [S3 media storage](s3_storage.md), the media volume holds no uploads. Back up the bucket with your storage provider's tools as well.
:::

## Back up

The backup script creates a timestamped folder under `backups/` with `database.sql`, `media.tar.gz`, and a copy of your env file. It detects whether you run Standard or Advanced Deployment.

```bash
bash scripts/backup.sh

# Write somewhere else
BACKUP_DIR=/mnt/backups bash scripts/backup.sh
```

The [Quick Start Installer](../install/quick_start.md) puts the scripts in `scripts/`. If you installed by hand, download them into your install folder:

```bash
mkdir -p scripts/lib
for f in backup.sh restore.sh deploy.sh validate-env.sh lib/compose-paths.sh; do
  wget -q -O "scripts/$f" "https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/scripts/$f"
done
```

::: details Back up without the script
These commands do the same thing for Standard Deployment. For Advanced Deployment, add `--env-file .env.advanced -f docker/docker-compose.advanced.yml` to each `docker compose` command.

```bash
mkdir -p backups/manual
cp .env backups/manual/
docker compose exec -T db pg_dump -U adventure database > backups/manual/database.sql
docker run --rm -v "$(docker volume ls -q | grep 'adventurelog_media$')":/data:ro \
  -v "$PWD/backups/manual":/backup alpine tar czf /backup/media.tar.gz -C /data .
```
:::

### Back up on a schedule

Run the script from cron. For example, every night at 03:00:

```txt
0 3 * * * cd /path/to/adventurelog && bash scripts/backup.sh >> backups/backup.log 2>&1
```

Copy the `backups/` folder off the server too. A backup on the same disk doesn't survive that disk failing.

## Restore

```bash
bash scripts/restore.sh backups/20260101-120000
```

The script stops AdventureLog, restores the env file, database, and media, and starts it again.

To move to a new host, install the same AdventureLog version there, copy the backup folder over, and run the restore script. Keep `SECRET_KEY` the same: a new one signs everyone out and stops existing API keys working. Standard Deployment stores a generated key in the media volume, so it moves with the media backup.

## Related

- [Updating](updating.md): the deploy script can back up before every update.
- [Operations](operations.md): the installer's management menu has backup and restore.
