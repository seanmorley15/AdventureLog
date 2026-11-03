"""
Signing the mobile app in through the providers the server already has (OIDC, GitHub...).

The app never sees the provider. It opens the system browser, the browser signs in the usual
way, and this module turns that browser session into a one-time code the app trades (with a
PKCE verifier) for an app session token. Three steps, one function each:

1. ``begin``: check the request and build the provider login path, with the PKCE challenge,
   state and redirect URI carried in a signed value (allauth signs an already signed-in
   browser out before a provider login, which would wipe anything kept in the session).
2. ``issue_code``: once the browser is signed in, mint the one-time code.
3. ``redeem_code``: check the verifier and open an app session.
"""

import base64
import hashlib
import hmac
import re
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from allauth.headless import app_settings as headless_settings
from allauth.headless.internal import sessionkit
from allauth.socialaccount.models import SocialApp
from allauth.usersessions.models import UserSession
from django.conf import settings
from django.contrib.auth import login as django_login
from django.core import signing
from django.db import transaction
from django.utils import timezone

from core.errors import ServiceError
from users.models import MobileAuthCode

HANDOFF_SALT = 'users.mobile_auth.handoff'
CHALLENGE_PATTERN = re.compile(r'^[A-Za-z0-9_-]{43}$')  # base64url of a SHA-256 digest
MAX_STATE_LENGTH = 256
# Spent codes are kept this long so a replay can still be recognised, then purged.
SPENT_CODE_RETENTION = timedelta(hours=1)


class InvalidStart(ServiceError):
    """The app's request to start a sign-in is not usable."""

    code = 'invalid_request'


class InvalidHandoff(ServiceError):
    """The signed value coming back from the browser is missing, altered or too old."""

    code = 'invalid_handoff'


class InvalidGrant(ServiceError):
    """The code cannot be redeemed (unknown, spent, expired, or the verifier does not match)."""

    code = 'invalid_grant'

    def __init__(self):
        super().__init__('The sign-in code is invalid or has expired.')


def allowed_redirect_uris():
    return list(settings.MOBILE_AUTH_REDIRECT_URIS)


def provider_path(app):
    """The path segment of a provider's login URL, which is also how the app names it."""
    return f'oidc/{app.provider_id}' if app.provider == 'openid_connect' else app.provider


def begin(*, provider, code_challenge, code_challenge_method, state, redirect_uri, signed_in):
    """Check a start request and return the relative URL to send the browser to."""
    if redirect_uri not in allowed_redirect_uris():
        raise InvalidStart('This redirect_uri is not registered for the mobile app.')
    if code_challenge_method != 'S256':
        raise InvalidStart('Only code_challenge_method=S256 is supported.')
    if not CHALLENGE_PATTERN.match(code_challenge or ''):
        raise InvalidStart('code_challenge must be the unpadded base64url SHA-256 of the verifier.')
    if not state or len(state) > MAX_STATE_LENGTH:
        raise InvalidStart('state is required and must be at most 256 characters.')
    if provider not in {provider_path(app) for app in SocialApp.objects.filter(sites=settings.SITE_ID)}:
        raise InvalidStart('This sign-in provider is not configured on the server.')

    handoff = signing.dumps(
        {'c': code_challenge, 's': state, 'r': redirect_uri, 'p': bool(signed_in)}, salt=HANDOFF_SALT
    )
    complete = '/accounts/mobile/complete/?' + urlencode({'h': handoff})
    return f'/accounts/{provider}/login/?' + urlencode({'next': complete})


def load_handoff(value):
    """The details ``begin`` signed, or ``InvalidHandoff``."""
    try:
        data = signing.loads(value, salt=HANDOFF_SALT, max_age=settings.MOBILE_AUTH_HANDOFF_SECONDS)
    except signing.BadSignature:
        raise InvalidHandoff('The sign-in link is invalid or has expired. Start again from the app.')
    if data['r'] not in allowed_redirect_uris():
        raise InvalidHandoff('This redirect_uri is no longer registered for the mobile app.')
    return {'challenge': data['c'], 'state': data['s'], 'redirect_uri': data['r'], 'was_signed_in': data['p']}


def _hash(code):
    return hashlib.sha256(code.encode()).hexdigest()


def issue_code(user, *, challenge, redirect_uri):
    """Mint a one-time code for ``user``. Only its hash is stored."""
    now = timezone.now()
    MobileAuthCode.objects.filter(expires_at__lt=now - SPENT_CODE_RETENTION).delete()
    code = secrets.token_urlsafe(32)
    MobileAuthCode.objects.create(
        code_hash=_hash(code), user=user, code_challenge=challenge, redirect_uri=redirect_uri,
        expires_at=now + timedelta(seconds=settings.MOBILE_AUTH_CODE_SECONDS),
    )
    return code


def _matches_verifier(challenge, verifier):
    digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    return hmac.compare_digest(digest, challenge)


def _revoke_session(session_key):
    if not session_key:
        return
    sessionkit.session_store(session_key).delete()
    UserSession.objects.filter(session_key=session_key).delete()


def redeem_code(request, *, code, code_verifier, redirect_uri):
    """
    Trade a code and its verifier for an app session; returns the session token.

    ``request`` is the Django request, used only to record where the session came from. Every
    failed attempt spends the code. A code that comes back after it was redeemed also ends
    the session it produced.
    """
    revoke = None
    with transaction.atomic():
        row = MobileAuthCode.objects.select_for_update().select_related('user').filter(code_hash=_hash(code)).first()
        if row is None:
            raise InvalidGrant()
        if row.used_at is not None:
            revoke = row.session_key
            outcome = None
        elif (
            row.expires_at <= timezone.now()
            or not row.user.is_active
            or row.redirect_uri != redirect_uri
            or not _matches_verifier(row.code_challenge, code_verifier)
        ):
            row.delete()
            outcome = None
        else:
            # Spend the code while the row lock is still held, so a concurrent redemption
            # sees it as used instead of also passing the checks above.
            row.used_at = timezone.now()
            row.save(update_fields=['used_at'])
            outcome = row
    # Raise outside the transaction, or the deletes above would be rolled back.
    if outcome is None:
        _revoke_session(revoke)
        raise InvalidGrant()

    token = _start_app_session(request, outcome.user)
    MobileAuthCode.objects.filter(pk=outcome.pk).update(session_key=token)
    return token


def _start_app_session(request, user):
    """Sign ``user`` in to a fresh session and return its token, leaving ``request`` as it was."""
    old_session, old_user = request.session, getattr(request, 'user', None)
    request.session = sessionkit.new_session()
    try:
        django_login(request, user)
        request.session.save()
        # allauth lists a session under the user's devices from its own login signal, which
        # Django's login does not send.
        UserSession.objects.create_from_request(request)
        return headless_settings.TOKEN_STRATEGY.create_session_token(request)
    finally:
        request.session = old_session
        if old_user is not None:
            request.user = old_user
