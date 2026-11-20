# Advanced Configuration

Optional environment variables for security hardening, performance tuning, and authentication behavior. For the complete reference, see [Environment Variables](environment_variables.md).

## Authentication behavior

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `ACCOUNT_EMAIL_VERIFICATION` | `none` | `none` (no verification), `optional` (send link, allow login), or `mandatory` (block login until verified) |
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
| `RATE_LIMIT_PLACE_PHOTO` | `300/minute` | Google place photos |
| `RATE_LIMIT_IMAGE_IMPORT` | `12/minute` | Image import |
| `RATE_LIMIT_EXTERNAL_GEOCODE` | `120/minute` | External geocoding |
| `RATE_LIMIT_EXTERNAL_RECOMMENDATIONS` | `30/minute` | Recommendations |
| `RATE_LIMIT_EXTERNAL_WIKIPEDIA` | `60/minute` | Wikipedia lookups |
| `RATE_LIMIT_EXTERNAL_SUNRISE_SUNSET` | `30/minute` | Sunrise/sunset API |

## Performance

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `GUNICORN_WORKERS` | `2` | Gunicorn worker count. Use `1` on small VPS instances; `(2 × CPU cores) + 1` on larger servers. |
| `GUNICORN_MAX_REQUESTS` | `10000` | Restart a worker after this many requests (`0` = never). |
| `SKIP_WORLD_DATA` | unset | Set to `1` to skip the first-boot `download_countries` import. Saves RAM on low-memory hosts; world travel data can be imported later. |

The installer offers `SKIP_WORLD_DATA=1` automatically when it detects limited RAM.

## Multi-factor authentication

Multi-factor authentication (TOTP) needs no server settings. Each user turns it on under **Settings → Security**. See [Account and Settings](../usage/settings.md#security).

## Cloud billing (hosted only)

These variables apply only to the hosted AdventureLog cloud service, not self-hosted installs:

| Variable | Description |
| -------- | ----------- |
| `CLOUD_MODE` | Enable cloud billing features |
| `CLOUD_TRIAL_DAYS` | Trial period length |
| `STRIPE_*` | Stripe payment integration keys |
