# Background Jobs

Slow work does not run while you wait. AdventureLog queues it in the database and a **worker** process picks it up. The worker runs **inside the same container** as the app, started by supervisord next to nginx and gunicorn. There is nothing to add to your compose file, no Redis, and no extra container.

## What runs in the background

| Work | What you see |
| ---- | ------------ |
| Looking up the country, region and city of a place you saved | The place appears at once; its region fills in a moment later. If OpenStreetMap does not answer, it is tried again for several minutes. |
| E-mails about `@mentions` in a comment | Sent when the worker gets to them; a mail server that is down is retried. |
| Deleting the files of a deleted photo or attachment | Removed shortly after, and retried if storage fails. |
| Account backups, collection archives and PDFs | The button shows "Preparing…" and the download starts when the file is ready. Files are kept for 24 hours. |
| Restoring a backup, importing a collection, importing images from web addresses | Progress is shown on the page; the result opens when it finishes. |

## Scheduled tasks

These replace the cron jobs older versions ran inside the container. Times are UTC.

| When | Task |
| ---- | ---- |
| Every day at 00:00 | Mark the regions and cities of your visited places as visited |
| Every hour | Delete expired exports and old job records |
| Every 10 minutes | Start again any job whose worker was killed part-way |
| Every day at 04:30 | Trim the queue's own history (7 days) |
| Sundays at 03:15 | Delete expired login sessions |

## Seeing and managing jobs

Staff can open **Admin → Jobs → Background jobs** for what users started (exports, imports) and **Admin → Procrastinate → Procrastinate jobs** for every task, with its event history. Both lists let you retry failed jobs; the second can also cancel, abort and run a task again.

## Settings

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `WORKER_ENABLED` | `true` | Set to `false` to idle the worker in this container, for example when you run one in its own container. |
| `WORKER_CONCURRENCY` | `3` | Jobs the worker runs at the same time. Each running export holds memory; lower it on small hosts. |
| `JOB_RESULT_TTL_HOURS` | `24` | How long a finished export stays downloadable. |
| `JOBS_RUN_INLINE` | `false` | Run jobs during the request instead of queueing them. For development without a worker. |

## Updating

The first start after the update creates the queue tables as part of the normal migration. If the worker restarts, it first waits up to 60 seconds for running jobs to finish. A job that was cut off is started again automatically within ten minutes.

## Running the worker separately

To give the worker its own resources, start another container from the backend image with `command: python3 manage.py procrastinate worker --concurrency 3` and set `WORKER_ENABLED=false` on the main one. The worker needs a direct connection to PostgreSQL: it does not work through a transaction-pooling proxy such as PgBouncer in transaction mode.

## Troubleshooting

- **A job stays "queued"**: the worker is not running. Check `docker logs adventurelog` for lines that start with `worker`, and that `WORKER_ENABLED` is not `false`.
- **A job failed**: its page in the admin shows the reason. Failed exports and imports can be retried from the list; uploads are kept for 24 hours for that.
