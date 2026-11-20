# OpenID Connect

AdventureLog works with any provider that supports OpenID Connect (OIDC), such as Keycloak, Zitadel, or Kanidm. Read [Social Auth & OIDC](../social_auth.md) first for how setup works. The [Authentik](authentik.md) and [Pocket ID](pocket_id.md) guides are worked examples.

## In your provider

Create a confidential client for AdventureLog and set its redirect, or callback, URL to:

```
https://adventurelog.example.com/accounts/oidc/<PROVIDER_ID>/login/callback/
```

- Use your backend's public address: `SITE_URL` on Standard Deployment, `PUBLIC_URL` on Advanced.
- `<PROVIDER_ID>` is the **Provider ID** you enter in AdventureLog below. Using the client ID for both keeps it simple.

Copy the client ID and client secret.

## In AdventureLog

In the [Admin Panel](../../guides/admin_panel.md), go to **Social Accounts → Social applications → Add**:

| Field | Value |
| ----- | ----- |
| Provider | `OpenID Connect` |
| Provider ID | The ID used in the callback URL, such as the client ID |
| Name | The name shown on the login button |
| Client ID, Secret key | From your provider |
| Key | Leave blank |
| Settings | `{"server_url": "https://idp.example.com/realms/main"}`: your provider's issuer address, where `/.well-known/openid-configuration` can be found |
| Sites | Move your site to **Chosen sites** |

The `server_url` must be reachable from the AdventureLog server, so don't use `localhost`. Check your provider's documentation for its issuer address.
