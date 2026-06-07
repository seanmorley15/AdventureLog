# Advanced Configuration

Optional environment variables for security hardening, performance tuning, and authentication behavior. For the complete reference, see [Environment Variables](environment_variables.md).

## Authentication behavior

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `ACCOUNT_EMAIL_VERIFICATION` | `none` | `none`, `optional`, or `mandatory` email verification for new accounts |
| `FORCE_SOCIALACCOUNT_LOGIN` | `False` | When `True`, disables password login — social/OIDC providers only |
| `SOCIALACCOUNT_ALLOW_SIGNUP` | `False` | Allow new accounts via social providers even when `DISABLE_REGISTRATION=True` |

Related: [Social Auth](social_auth.md), [Disable Registration](disable_registration.md), [SMTP Email](email.md).

## Rate limiting

Enable in production to protect against abuse:

```env
ENABLE_RATE_LIMITS=True
```

Per-endpoint overrides (all optional):

| Variable | Default | Endpoint |
| -------- | ------- | -------- |
| `RATE_LIMIT_USER` | `10000/hour` | Authenticated API requests |
| `RATE_LIMIT_IMAGE_PROXY` | `60/minute` | Image proxy |
| `RATE_LIMIT_IMAGE_IMPORT` | `12/minute` | Image import |
| `RATE_LIMIT_EXTERNAL_GEOCODE` | `120/minute` | External geocoding |
| `RATE_LIMIT_EXTERNAL_RECOMMENDATIONS` | `30/minute` | Recommendations |
| `RATE_LIMIT_EXTERNAL_WIKIPEDIA` | `60/minute` | Wikipedia lookups |
| `RATE_LIMIT_EXTERNAL_SUN_TIMES` | `30/minute` | Sun times API |

## Performance

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `GUNICORN_WORKERS` | `2` | Gunicorn worker count. Use `1` on small VPS instances; `(2 × CPU cores) + 1` on larger servers. |
| `SKIP_WORLD_DATA` | unset | Set to `1` to skip the first-boot `download-countries` import. Saves RAM on low-memory hosts; world travel data can be imported later. |

The installer offers `SKIP_WORLD_DATA=1` automatically when it detects limited RAM.

## Multi-factor authentication

MFA (TOTP) is configured per-user in the app, not via environment variables:

1. Log in and open **Settings → Security**
2. Enable **Multi-Factor Authentication**
3. Scan the QR code with an authenticator app

## Mobile QR login

AdventureLog supports QR-based mobile login from **Settings → Security**. No server-side configuration is required.

## Cloud billing (hosted only)

These variables apply only to the hosted AdventureLog cloud service, not self-hosted installs:

| Variable | Description |
| -------- | ----------- |
| `CLOUD_MODE` | Enable cloud billing features |
| `CLOUD_TRIAL_DAYS` | Trial period length |
| `STRIPE_*` | Stripe payment integration keys |
