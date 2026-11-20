# First Steps

What to do once AdventureLog is running: sign in as the admin, secure the account, and decide who can join. This page applies to every install method.

## 1. Open AdventureLog

Go to `http://localhost:8015`, or to your `SITE_URL` if you set one. The first start takes a few minutes while the database is created and the world geography data is imported. Until then the page may not load.

## 2. Find the admin password

On first start, AdventureLog creates an admin account from these variables:

| Variable | Default |
| -------- | ------- |
| `DJANGO_ADMIN_USERNAME` | `admin` |
| `DJANGO_ADMIN_EMAIL` | `admin@example.com` |
| `DJANGO_ADMIN_PASSWORD` | empty |

If `DJANGO_ADMIN_PASSWORD` is empty or weak, AdventureLog generates a random password instead and **prints it once** in the container log. Weak means shorter than 12 characters, common, all numbers, or too close to the username. So `admin` / `admin` does not work.

Read the generated password from the log:

::: code-group

```bash [Standard]
docker compose logs app | grep -A3 "Admin username"
```

```bash [Advanced]
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml logs server | grep -A3 "Admin username"
```

```bash [Quick Start Installer]
# The installer shows the password at the end, and can save it here
cat adventurelog/credentials.txt
```

:::

The admin account is only created once. Changing `DJANGO_ADMIN_PASSWORD` later has no effect.

::::: details Lost the password, or the log has rotated?
Set a new one from the command line:

::: code-group

```bash [Standard]
docker compose exec app python3 manage.py changepassword admin
```

```bash [Advanced]
docker compose --env-file .env.advanced -f docker/docker-compose.advanced.yml exec server python3 manage.py changepassword admin
```

:::

:::::

## 3. Secure the admin account

Sign in, then open **Settings**:

1. **Profile**: set your name and username.
2. **Emails**: replace `admin@example.com` with your real address and make it primary.
3. **Security**: change the password if you used a generated one, and turn on **Multi-Factor Authentication**.

See [Account and Settings](../usage/settings.md) for everything on these tabs.

## 4. Decide who can join

Out of the box, **anyone who can reach your server can create an account**. Choose one:

| You want | Do this |
| -------- | ------- |
| Only you, or people you invite | Set `DISABLE_REGISTRATION=True`, then [invite users](../guides/invite_user.md) from the admin panel |
| People from your identity provider | Set up [Social Auth & OIDC](../configuration/social_auth.md) |
| Nothing visible without signing in | Set `ALLOW_PUBLIC_ACCESS=False`. See [Public Access](../configuration/public_access.md). |
| Open sign-up | Leave the defaults |

## 5. Set up email

Without email, AdventureLog can't send invitations, password resets, or `@mention` notifications. It only writes them to the container log. See [SMTP Email](../configuration/email.md).

## 6. Set up backups

Back up the database and the media volume before you add anything you'd miss. See [Backups and Restore](../configuration/backups.md).

## 7. Optional extras

- Connect photos, activities, and trails in **Settings → Integrations**. See [All Integrations](../configuration/integrations.md).
- Store uploads in S3 instead of on the server. Decide this now, since moving later is hard. See [S3 Media Storage](../configuration/s3_storage.md).

## Next

- Go through the [Production Checklist](production_checklist.md) if other people will use the server.
- Start using the app with the [Usage guide](../usage/usage.md).
