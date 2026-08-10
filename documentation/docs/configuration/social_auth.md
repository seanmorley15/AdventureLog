# Social Authentication

AdventureLog support authentication via 3rd party services and self-hosted identity providers. Once these services are enabled, users can log in to AdventureLog using their accounts from these services and link existing AdventureLog accounts to these services for easier access.

The steps for each service varies so please refer to the specific service's documentation for more information.

## Supported providers

| Provider | Type | Guide |
| -------- | ---- | ----- |
| Authentik | Self-hosted OIDC | [Setup guide](social_auth/authentik.md) |
| GitHub | OAuth | [Setup guide](social_auth/github.md) |
| Pocket ID | Self-hosted OIDC | [Setup guide](social_auth/pocket_id.md) |
| OpenID Connect | Generic OIDC | [Setup guide](social_auth/oidc.md) |
| Authelia | Self-hosted OIDC | [External guide](https://www.authelia.com/integration/openid-connect/adventure-log/) |

Providers are configured in the Django admin panel under **Social applications**. See the [Admin Panel](../guides/admin_panel.md) for access requirements.

## Linking Existing Accounts

If you already have an AdventureLog account and would like to link it to a 3rd party service, you can do so by logging in to AdventureLog and navigating to the `Account Settings` page. From there, scroll down to `Social and OIDC Authentication` and click the `Launch Account Connections` button. If identity providers have been enabled on your instance, you will see a list of available services to link to.
