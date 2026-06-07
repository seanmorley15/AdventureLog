# Admin Panel

The AdventureLog admin panel is powered by Django and is available at `/admin` on your backend URL. In AIO installs, that is the same domain as the frontend (for example `https://adventurelog.example.com/admin`).

## Access requirements

Only users with the **staff** flag (`is_staff=True`) can access the admin panel. The first-boot superuser created from `DJANGO_ADMIN_*` environment variables has staff access by default.

## What you can manage

| Section | Description |
| ------- | ----------- |
| **Users** | Create, edit, and deactivate user accounts |
| **Locations** | View and manage location records in the database |
| **Social applications** | Configure OAuth/OIDC providers (GitHub, OIDC, etc.) |
| **Invitations** | Send invite links for private instances |
| **World data** | Countries, regions, and cities reference data |

## CSRF configuration

If the admin panel loads but form submissions fail, verify `CSRF_TRUSTED_ORIGINS` in your `.env` or `.env.aio` includes your public domain:

```env
CSRF_TRUSTED_ORIGINS=https://adventurelog.example.com
```

When using a single domain, set `SITE_URL` instead and the origins are derived automatically. See [Environment Variables](../configuration/environment_variables.md#url-and-networking).

## Social auth setup

OAuth and OIDC providers are configured in the admin panel under **Social applications** and **Social accounts**. Step-by-step guides:

- [Social Auth overview](../configuration/social_auth.md)
- [GitHub](../configuration/social_auth/github.md)
- [Authentik](../configuration/social_auth/authentik.md)
- [Pocket ID](../configuration/social_auth/pocket_id.md)
- [OpenID Connect](../configuration/social_auth/oidc.md)

## Related guides

- [Invite a User](invite_user.md)
- [Disable Registration](../configuration/disable_registration.md)
