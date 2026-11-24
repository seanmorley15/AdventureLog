# SMTP Email

AdventureLog sends email for invitations, password resets, email verification, and `@mention` notifications in comments. Until you set up SMTP, it only writes these emails to the backend log.

## Turn on SMTP

Add these settings to your env file (`.env` for Standard Deployment, `.env.advanced` for Advanced), then restart.

::: code-group

```env [.env]
EMAIL_BACKEND=email
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=adventurelog@example.com
EMAIL_HOST_PASSWORD=your_smtp_password
DEFAULT_FROM_EMAIL=adventurelog@example.com
```

```yaml [docker-compose.yml]
environment:
  - EMAIL_BACKEND=email
  - EMAIL_HOST=smtp.example.com
  - EMAIL_PORT=587
  - EMAIL_USE_TLS=True
  - EMAIL_USE_SSL=False
  - EMAIL_HOST_USER=adventurelog@example.com
  - EMAIL_HOST_PASSWORD=your_smtp_password
  - DEFAULT_FROM_EMAIL=adventurelog@example.com
```

:::

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `EMAIL_BACKEND` | `console` | `console` writes emails to the log. Any other value, such as `email`, sends them over SMTP. |
| `EMAIL_HOST` | none | Your SMTP server |
| `EMAIL_PORT` | `587` | Usually `587` with TLS, or `465` with SSL |
| `EMAIL_USE_TLS` | `True` | Use STARTTLS. Turn off when using SSL. |
| `EMAIL_USE_SSL` | `False` | Use SSL from the start of the connection, usually on port `465` |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | none | SMTP login. Many providers need an app password. |
| `DEFAULT_FROM_EMAIL` | none | The sender address. Many providers only accept an address you own. |

## Set the site name in emails

Emails show the site name in the subject, such as `[example.com]`, until you change it:

1. Open the [Admin Panel](../guides/admin_panel.md).
2. Go to **Sites** and open the first site, usually `example.com`.
3. Set **Domain name** and **Display name**, for example `adventurelog.example.com` and `AdventureLog`.
4. Save.

## Check it works

Invite yourself from the admin panel (see [Invite a User](../guides/invite_user.md)), or use **Forgot password** on the login page. If nothing arrives, look for SMTP errors in the backend log.

## Related

- [Advanced Settings](advanced_configuration.md#authentication-behavior): require email verification with `ACCOUNT_EMAIL_VERIFICATION`.
