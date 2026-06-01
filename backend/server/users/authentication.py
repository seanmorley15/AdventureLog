"""
Custom DRF authentication backend for AdventureLog API keys.

Clients may supply their key via either of these headers:

    Authorization: Api-Key al_xxxxxxxxxxxxxxxx...
    X-API-Key: al_xxxxxxxxxxxxxxxx...

Session-based CSRF enforcement is performed by DRF's built-in
``SessionAuthentication`` class only.  Requests authenticated via this
class are never subject to CSRF checks, which is the correct behaviour
for token-based API access.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class APIKeyAuthentication(BaseAuthentication):
    """Authenticate a request using an AdventureLog API key."""

    def authenticate(self, request):
        raw_key = self._extract_key(request)
        if raw_key is None:
            # Signal to DRF that this scheme was not attempted so other
            # authenticators can still run.
            return None

        from .models import APIKey

        api_key = APIKey.authenticate(raw_key)
        if api_key is None:
            raise AuthenticationFailed("Invalid or expired API key.")

        return (api_key.user, api_key)

    def authenticate_header(self, request):
        return "Api-Key"

    @staticmethod
    def _extract_key(request) -> str | None:
        # Prefer X-API-Key header for simplicity.
        key = request.META.get("HTTP_X_API_KEY")
        if key:
            return key.strip()

        # Also accept "Authorization: Api-Key <token>"
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.lower().startswith("api-key "):
            return auth_header[8:].strip()

        return None
