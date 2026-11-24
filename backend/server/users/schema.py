"""How API keys and app session tokens appear in the OpenAPI schema (a drf-spectacular extension)."""

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


class SessionTokenScheme(OpenApiAuthenticationExtension):
    """``users.authentication.SessionTokenAuthentication``: the token a native app signs in with."""

    target_class = 'users.authentication.SessionTokenAuthentication'
    name = 'SessionTokenAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-Session-Token',
            'description': (
                'The `meta.session_token` returned by `POST /api/auth/app/v1/auth/login` '
                '(or by `POST /api/auth/mobile/token/`). Used by the mobile app.'
            ),
        }
