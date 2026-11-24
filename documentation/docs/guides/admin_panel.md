# Admin Panel

The admin panel is where server admins manage users, sign-in providers, invitations, and the data behind the app. Open it from **Settings → Admin → Launch Administration Panel**, or go to `/admin` on your backend address. On Standard Deployment that's the same domain as the app, for example `https://adventurelog.example.com/admin`.

## Who can open it

Users with **staff** status. The first admin account, created on first start, is a staff superuser. See [First Steps](../install/first_steps.md).

## What you can manage

| Section | What it's for |
| ------- | ------------- |
| **Users** | Edit or deactivate accounts. Tick **Staff status** to let someone open the admin panel, and **Superuser status** to give them every permission. |
| **Invitations** | Invite people by email. See [Invite a User](invite_user.md). |
| **Social applications** | Set up sign-in providers such as Authentik or GitHub. See [Social Auth & OIDC](../configuration/social_auth.md). |
| **Sites** | The domain and name shown in emails. See [SMTP Email](../configuration/email.md#set-the-site-name-in-emails). |
| **Jobs** and **Procrastinate** | Background exports and imports, and every queued task, with retry. See [Background Jobs](../configuration/background_jobs.md#seeing-and-managing-jobs). |
| **Locations**, **Collections**, and their parts | Every user's data, for support and repairs. Edit with care. |
| **World travel** | Countries, regions, and cities, and what users have visited |
| **Integrations** | Each user's Immich, Strava, Wanderer, and Endurain connections |
| **API keys**, **Sessions** | Revoke a user's API keys or sign them out everywhere |

## If saving fails

If pages load but saving a form fails with a CSRF error, the admin panel isn't accepting your address. Set `SITE_URL` to the address you use (Standard Deployment), or add it to `CSRF_TRUSTED_ORIGINS` (Advanced Deployment). See [Login and Registration Unresponsive](../troubleshooting/login_unresponsive.md).
