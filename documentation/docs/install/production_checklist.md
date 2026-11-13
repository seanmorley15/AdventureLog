# Production Checklist

Go through this list before other people rely on your server. Each item links to the page that explains it.

## Access

- **HTTPS.** Serve AdventureLog over HTTPS through a [reverse proxy](getting_started.md#reverse-proxy), and set `SITE_URL` to the `https://` address.
- **Admin account.** Change the generated admin password, use a real email address, and turn on multi-factor authentication. See [First Steps](first_steps.md#_3-secure-the-admin-account).
- **Who can sign up.** Registration is open by default. Set `DISABLE_REGISTRATION=True` for an invite-only server. See [Disable Registration](../configuration/disable_registration.md).
- **Public content.** Decide whether visitors who aren't signed in can see public collections and profiles. See [Public Access](../configuration/public_access.md).

## Settings

- **Secrets.** Use a strong `POSTGRES_PASSWORD`. On Advanced Deployment, set your own `SECRET_KEY` and keep it; Standard Deployment generates one and stores it in the media volume.
- **Debug off.** `DEBUG` is `False` unless you set it. Never turn it on for a public server.
- **Rate limits.** Set `ENABLE_RATE_LIMITS=True`. See [Advanced Settings](../configuration/advanced_configuration.md#rate-limiting).
- **Upload size.** Cap single uploads with `BODY_SIZE_LIMIT` (bytes, or a `K`/`M`/`G` suffix; `100M` by default on Standard Deployment, unlimited on Advanced), and each user's total storage with `MEDIA_STORAGE_LIMIT_MB` (unlimited by default).
- **Email.** Set up SMTP so invitations and password resets reach people. See [SMTP Email](../configuration/email.md).

## Data

- **Storage.** Choose local or S3 storage now. Moving later is hard. See [S3 Media Storage](../configuration/s3_storage.md).
- **Backups.** Schedule backups and copy them off the server. Restore one once, to know it works. See [Backups and Restore](../configuration/backups.md).
- **Updates.** Know how you'll update, and watch the [changelogs](../changelogs/development_timeline.md). See [Updating](../configuration/updating.md).

## Resources

- **Memory.** Give the server at least 2 GB of RAM for the first boot, and 1 GB afterward. On a small host, lower `GUNICORN_WORKERS` and `WORKER_CONCURRENCY`. See [Advanced Settings](../configuration/advanced_configuration.md#performance) and [Background Jobs](../configuration/background_jobs.md#settings).
