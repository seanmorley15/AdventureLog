# Social Auth & OIDC

Let people sign in to AdventureLog with an account they already have, from GitHub or from a self-hosted identity provider such as Authentik, Pocket ID, or Authelia. Users can also link one of these accounts to their existing AdventureLog account.

**Who sets it up:** the server admin, in the identity provider and in the AdventureLog admin panel.

## Providers

| Provider | Type | Guide |
| -------- | ---- | ----- |
| Authentik | Self-hosted OpenID Connect | [Authentik](social_auth/authentik.md) |
| Pocket ID | Self-hosted OpenID Connect | [Pocket ID](social_auth/pocket_id.md) |
| Authelia | Self-hosted OpenID Connect | [Authelia's guide](https://www.authelia.com/integration/openid-connect/adventure-log/) |
| Any other OpenID Connect provider | OpenID Connect | [OpenID Connect](social_auth/oidc.md) |
| GitHub | OAuth | [GitHub](social_auth/github.md) |

## How setup works

Every provider follows the same three steps. The provider guides fill in the details.

1. **Create a client in the provider**, with AdventureLog's callback URL as the redirect URL. The callback URL is on your backend's public address: your `SITE_URL` on Standard Deployment, or `PUBLIC_URL` on Advanced Deployment.
2. **Add a social application in AdventureLog.** Open the [Admin Panel](../guides/admin_panel.md), go to **Social Accounts → Social applications**, and choose **Add**. Enter the client ID and secret from the provider.
3. **Choose the site.** Under **Sites**, move your site (usually `example.com`) to the chosen list, and save.

The provider then appears on the AdventureLog login page.

On Advanced Deployment behind a reverse proxy, the `/accounts` path must reach the backend, or the callback returns 404.

## Sign-in settings

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `SOCIALACCOUNT_ALLOW_SIGNUP` | `False` | Let new people create an account through a provider, even when `DISABLE_REGISTRATION=True` |
| `FORCE_SOCIALACCOUNT_LOGIN` | `False` | Turn off password login, so everyone signs in through a provider |

See [Advanced Settings](advanced_configuration.md#authentication-behavior) for the others.

## Linking an existing account

A user who already has an AdventureLog account signs in as usual, opens **Settings → Security**, and chooses **Launch Account Connections** under **Sign-in Methods**. The providers set up on the server are listed there to link.

## Mobile app

The mobile app signs in through the same providers using the system browser, and the server hands the app a one-time code afterward. Nothing needs to be added to your identity provider: it only ever sees the usual AdventureLog login. The app's redirect address (`adventurelog://auth/callback`) is checked by AdventureLog itself, not by the provider.
