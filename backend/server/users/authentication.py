"""
Custom DRF authentication backend for AdventureLog API keys.

Clients may supply their key via either of these headers:

    Authorization: Api-Key al_xxxxxxxxxxxxxxxx...
    X-API-Key: al_xxxxxxxxxxxxxxxx...

Session-based CSRF enforcement is performed by DRF's built-in
``SessionAuthentication`` class only.  Requests authenticated via this
class are never subject to CSRF checks, which is the correct behaviour
for token-based API access.

Native apps sign in through allauth's headless *app* client and send the session token it
returns as ``X-Session-Token``; see ``SessionTokenAuthentication`` below.
"""

import time
from types import SimpleNamespace

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

SESSION_TOUCH_KEY = '_session_touch'  # shared with users.middleware.EfficientSessionMiddleware


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


def user_from_session_token(token):
    """
    The signed-in user behind an allauth app-client session token, or ``None``.

    ``None`` covers every way a token can be unusable: no such session, a session that holds
    no signed-in user (for example one waiting for the second factor), a deactivated user, and
    a session started before the user's last password change. Django's own ``get_user`` makes
    those checks, so this behaves exactly like a cookie session would.

    As a side effect it extends the session's expiry, at most once per
    ``SESSION_TOUCH_INTERVAL_SECONDS``. Allauth's app views only do that for their own routes,
    so without it a token would die 14 days after sign-in however often the app is used.
    """
    from allauth.headless import app_settings
    from django.contrib.auth import get_user

    session = app_settings.TOKEN_STRATEGY.lookup_session(token)
    if session is None:
        return None

    user = get_user(SimpleNamespace(session=session))  # flushes the session on a bad password hash
    if not user.is_authenticated:
        return None

    now = int(time.time())
    interval = int(getattr(settings, 'SESSION_TOUCH_INTERVAL_SECONDS', 60 * 60 * 24))
    last_touch = session.get(SESSION_TOUCH_KEY)
    if not isinstance(last_touch, int) or now - last_touch >= interval:
        session[SESSION_TOUCH_KEY] = now
        session.save()
    return user


class SessionTokenAuthentication(BaseAuthentication):
    """
    Authenticate a request with the ``X-Session-Token`` an allauth *app* client sign-in returns.

    This is a stand-in. django-allauth 65.x ships the same thing as
    ``allauth.headless.contrib.rest_framework.authentication.XSessionTokenAuthentication``
    (plus optional JWT tokens), but this project is on 0.63, whose app client is not accepted by
    DRF at all. When allauth is upgraded, replace this class with the upstream one in
    ``REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`` and the ``users.schema`` extension, and
    swap ``user_from_session_token`` in ``main.views`` and ``cloud.middleware`` for it.

    The token is the Django session key, so signing out (``DELETE /api/auth/app/v1/auth/session``)
    or revoking the session in Settings → Security ends it. It is a header, not a cookie, so a
    browser never sends it on its own and no CSRF check applies.
    """

    HEADER = 'X-Session-Token'

    def authenticate(self, request):
        token = request.META.get('HTTP_X_SESSION_TOKEN')
        if not token:
            return None
        user = user_from_session_token(token)
        if user is None:
            raise AuthenticationFailed('Invalid or expired session token.')
        return (user, token)

    def authenticate_header(self, request):
        return 'X-Session-Token'
