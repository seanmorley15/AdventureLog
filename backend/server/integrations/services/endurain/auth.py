"""Signing in to Endurain: password login, MFA, and keeping tokens fresh."""

import base64
import json
import logging
import secrets
import time
import requests
from django.core.cache import cache
from integrations.errors import IntegrationError, MfaRequired
from integrations.models import EndurainIntegration

from .connection import REQUEST_TIMEOUT_SECONDS, api_url, endurain_post, mobile_headers, normalize_server_url

logger = logging.getLogger(__name__)


TOKEN_REFRESH_BUFFER_SECONDS = 300


MFA_PENDING_TTL_SECONDS = 300


def create_mfa_pending(user_id, server_url: str, username: str) -> str:
    """Store a short-lived MFA challenge bound to the AdventureLog user."""
    token = secrets.token_urlsafe(32)
    cache.set(
        f'endurain:mfa:{user_id}:{token}',
        {
            'server_url': normalize_server_url(server_url),
            'username': username,
        },
        MFA_PENDING_TTL_SECONDS,
    )
    return token


def consume_mfa_pending(user_id, token: str) -> dict:
    """Validate and consume a pending MFA challenge for this user."""
    if not token:
        raise IntegrationError(
            'MFA session expired. Start the connection again.',
            code='endurain.mfa_session_invalid',
            status_code=400,
        )
    key = f'endurain:mfa:{user_id}:{token}'
    data = cache.get(key)
    if not data:
        raise IntegrationError(
            'MFA session expired. Start the connection again.',
            code='endurain.mfa_session_invalid',
            status_code=400,
        )
    cache.delete(key)
    return data


def decode_jwt_sub(access_token: str) -> int | None:
    try:
        payload_segment = access_token.split('.')[1]
        padding = '=' * (-len(payload_segment) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload_segment + padding))
        sub = data.get('sub')
        return int(sub) if sub is not None else None
    except (IndexError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _parse_token_response(data: dict) -> dict:
    if not data.get('access_token') or not data.get('refresh_token'):
        raise IntegrationError(
            'Endurain did not return valid authentication tokens.',
            code='endurain.auth_failed',
        )
    now = int(time.time())
    expires_in = int(data.get('expires_in', 900))
    refresh_expires_in = data.get('refresh_token_expires_in')
    return {
        'access_token': data['access_token'],
        'refresh_token': data['refresh_token'],
        'access_token_expires_at': now + expires_in,
        'refresh_token_expires_at': (
            now + int(refresh_expires_in) if refresh_expires_in is not None else None
        ),
        'endurain_user_id': decode_jwt_sub(data['access_token']),
        'username': data.get('username', ''),
    }


def login_with_password(server_url: str, username: str, password: str) -> dict:
    url = api_url(server_url, '/auth/login')
    try:
        response = endurain_post(
            url,
            headers=mobile_headers(extra={'Content-Type': 'application/x-www-form-urlencoded'}),
            data={'username': username, 'password': password},
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        logger.error('Endurain login request failed: %s', exc)
        raise IntegrationError(
            'Could not connect to Endurain server.',
            code='endurain.connection_failed',
        ) from exc

    if response.is_redirect:
        raise IntegrationError(
            'Unexpected redirect from Endurain server.',
            code='endurain.connection_failed',
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise IntegrationError(
            'Invalid response from Endurain server.',
            code='endurain.connection_failed',
        ) from exc

    if response.status_code in (401, 403):
        detail = data.get('detail', 'Invalid credentials.')
        raise IntegrationError(str(detail), code='endurain.invalid_credentials', status_code=response.status_code)

    if data.get('mfa_required'):
        raise MfaRequired(data.get('username') or username)

    if response.status_code >= 400:
        detail = data.get('detail', 'Authentication failed.')
        raise IntegrationError(str(detail), code='endurain.auth_failed', status_code=response.status_code)

    tokens = _parse_token_response(data)
    tokens['username'] = username
    return tokens


def verify_mfa(server_url: str, username: str, mfa_code: str) -> dict:
    url = api_url(server_url, '/auth/mfa/verify')
    try:
        response = endurain_post(
            url,
            headers=mobile_headers(extra={'Content-Type': 'application/json'}),
            json={'username': username, 'mfa_code': mfa_code},
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        logger.error('Endurain MFA request failed: %s', exc)
        raise IntegrationError(
            'Could not connect to Endurain server.',
            code='endurain.connection_failed',
        ) from exc

    if response.is_redirect:
        raise IntegrationError(
            'Unexpected redirect from Endurain server.',
            code='endurain.connection_failed',
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise IntegrationError(
            'Invalid response from Endurain server.',
            code='endurain.connection_failed',
        ) from exc

    if response.status_code >= 400:
        detail = data.get('detail', 'MFA verification failed.')
        raise IntegrationError(str(detail), code='endurain.mfa_failed', status_code=response.status_code)

    tokens = _parse_token_response(data)
    tokens['username'] = username
    return tokens


def refresh_tokens(integration: EndurainIntegration) -> EndurainIntegration:
    url = api_url(integration.server_url, '/auth/refresh')
    try:
        response = endurain_post(
            url,
            headers=mobile_headers(integration.refresh_token),
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        logger.error('Endurain token refresh failed: %s', exc)
        raise IntegrationError(
            'Could not connect to Endurain for token refresh.',
            code='endurain.connection_failed',
        ) from exc

    if response.is_redirect:
        raise IntegrationError(
            'Unexpected redirect from Endurain during token refresh.',
            code='endurain.refresh_failed',
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise IntegrationError(
            'Invalid response from Endurain during token refresh.',
            code='endurain.refresh_failed',
        ) from exc

    if response.status_code >= 400:
        detail = data.get('detail', 'Token refresh failed.')
        raise IntegrationError(str(detail), code='endurain.reconnect_required', status_code=response.status_code)

    tokens = _parse_token_response(data)
    integration.access_token = tokens['access_token']
    integration.refresh_token = tokens['refresh_token']
    integration.access_token_expires_at = tokens['access_token_expires_at']
    if tokens.get('refresh_token_expires_at'):
        integration.refresh_token_expires_at = tokens['refresh_token_expires_at']
    if tokens.get('endurain_user_id'):
        integration.endurain_user_id = tokens['endurain_user_id']
    integration.save()
    return integration


def refresh_tokens_if_needed(integration: EndurainIntegration) -> EndurainIntegration:
    now = int(time.time())
    if integration.access_token_expires_at - now >= TOKEN_REFRESH_BUFFER_SECONDS:
        return integration
    return refresh_tokens(integration)
