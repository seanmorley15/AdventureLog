# Pocket ID

[Pocket ID](https://pocket-id.org/) is a lightweight, self-hosted OpenID Connect provider that signs people in with passkeys. Once it's set up, people can sign in to AdventureLog with Pocket ID. Read [Social Auth & OIDC](../social_auth.md) first for how setup works.

## In Pocket ID

1. Open the admin interface, go to **OIDC Clients**, and create a client named `AdventureLog`. Make it a confidential client (not public).
2. Copy the **Client ID** and **Client Secret**.
3. Set the **Callback URL**:

   ```
   https://adventurelog.example.com/accounts/oidc/<CLIENT_ID>/login/callback/
   ```

   - Use your backend's public address: `SITE_URL` on Standard Deployment, `PUBLIC_URL` on Advanced.
   - Replace `<CLIENT_ID>` with the client ID from step 2. It must match the **Provider ID** you enter in AdventureLog.

## In AdventureLog

In the [Admin Panel](../../guides/admin_panel.md), go to **Social Accounts → Social applications → Add**:

| Field | Value |
| ----- | ----- |
| Provider | `OpenID Connect` |
| Provider ID | The Pocket ID client ID |
| Name | `Pocket ID` |
| Client ID | The Pocket ID client ID |
| Secret key | The Pocket ID client secret |
| Key | Leave blank |
| Settings | `{"server_url": "https://pocketid.example.com/.well-known/openid-configuration"}`, with your Pocket ID address |
| Sites | Move your site to **Chosen sites** |

The `server_url` must be reachable from the AdventureLog server. `localhost` means the AdventureLog container, so use your Pocket ID domain or LAN IP address.

Save. **Pocket ID** now appears on the login page.

## Troubleshooting

| Problem | Fix |
| ------- | --- |
| 404 after signing in | On Advanced Deployment, route `/accounts` to the backend in your reverse proxy. |
| Invalid redirect URI | The callback URL in Pocket ID must match exactly, including the trailing `/`, and its `<CLIENT_ID>` must equal the Provider ID in AdventureLog. |
| AdventureLog can't reach Pocket ID | Open `https://pocketid.example.com/.well-known/openid-configuration` from the AdventureLog server. If it doesn't load there, fix the address or networking. |
