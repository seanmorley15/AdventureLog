# Authentik

[Authentik](https://goauthentik.io/) is a self-hosted identity provider. Once it's set up, people can sign in to AdventureLog with their Authentik account. Read [Social Auth & OIDC](../social_auth.md) first for how setup works.

## In Authentik

1. Go to **Providers** and create an **OAuth2/OpenID Provider**. Name it `AdventureLog`.
2. Add a **Redirect URI** of type **Regex**:

   ```
   ^https://adventurelog.example.com/accounts/oidc/.*$
   ```

   Use your backend's public address: `SITE_URL` on Standard Deployment, `PUBLIC_URL` on Advanced. Use `http://` if you don't have HTTPS.

3. Copy the **Client ID** and **Client Secret**.
4. Create an **Application**, assign the provider to it, and set its slug, for example `adventurelog`. The [AdventureLog logo](https://adventurelog.app/adventurelog.png) is available for the application icon.

## In AdventureLog

In the [Admin Panel](../../guides/admin_panel.md), go to **Social Accounts → Social applications → Add**:

| Field | Value |
| ----- | ----- |
| Provider | `OpenID Connect` |
| Provider ID | The Authentik client ID |
| Name | `Authentik` |
| Client ID | The Authentik client ID |
| Secret key | The Authentik client secret |
| Key | Leave blank |
| Settings | `{"server_url": "https://authentik.example.com/application/o/adventurelog/"}`, with your Authentik address and slug |
| Sites | Move your site to **Chosen sites** |

The `server_url` must be reachable from the AdventureLog server. `localhost` means the AdventureLog container, so use your Authentik domain or IP address.

![Authentik social application settings in the AdventureLog admin panel](/authentik_settings.png)

Save. **Authentik** now appears on the login page.

## Troubleshooting

| Problem | Fix |
| ------- | --- |
| 404 after signing in | On Advanced Deployment, route `/accounts` to the backend in your reverse proxy. |
| Authentik says the user has no permission | In Authentik, open the application and use **Check access** for that user. Add a policy that gives the user or their group access. |
| Redirect URI error | Check that the regex matches your backend address, including `http` or `https`. |
