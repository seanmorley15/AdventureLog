# OIDC Social Authentication

AdventureLog can be configured to use OpenID Connect (OIDC) as an identity provider for social authentication. Users can then log in to AdventureLog using their OIDC account.

The configuration is basically the same as [Authentik](./authentik.md), but you replace the client and secret with the OIDC client and secret provided by your OIDC provider. The `server_url` should be the URL of your OIDC provider where you can find the OIDC configuration.

Each provider has a different configuration, so you will need to check the documentation of your OIDC provider to find the correct configuration.
