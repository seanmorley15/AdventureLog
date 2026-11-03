"""How API keys appear in the OpenAPI schema (a drf-spectacular extension)."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class APIKeyScheme(OpenApiAuthenticationExtension):
    """``users.authentication.APIKeyAuthentication``: either of two headers carries the key."""

    target_class = 'users.authentication.APIKeyAuthentication'
    name = ['ApiKeyAuth', 'ApiKeyAuthorization']

    def get_security_requirement(self, auto_schema):
        # Either header is enough on its own, so each is a separate alternative.
        return [{'ApiKeyAuth': []}, {'ApiKeyAuthorization': []}]

    def get_security_definition(self, auto_schema):
        return [
            {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API-Key',
                'description': 'An API key from Settings → Security, e.g. `al_xxxxxxxx…`.',
            },
            {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'The same key as `Api-Key al_xxxxxxxx…`.',
            },
        ]
