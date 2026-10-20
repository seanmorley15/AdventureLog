"""Calling the Endurain API for the signed-in user's activities."""

import logging
from datetime import date, datetime
from urllib.parse import urlparse
import requests
from integrations.errors import IntegrationError
from integrations.models import EndurainIntegration

from .connection import api_url, assert_host_not_metadata, endurain_request, format_server_url, mobile_headers, normalize_server_url
from .auth import refresh_tokens, refresh_tokens_if_needed

logger = logging.getLogger(__name__)


def api_request(
    integration: EndurainIntegration,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    retry_on_unauthorized: bool = True,
) -> requests.Response:
    # Re-check resolved IPs on each outbound call to mitigate DNS rebinding to metadata.
    hostname = urlparse(format_server_url(integration.server_url)).hostname
    if hostname:
        assert_host_not_metadata(hostname)

    integration = refresh_tokens_if_needed(integration)
    url = api_url(integration.server_url, path)
    try:
        response = endurain_request(
            method.upper(),
            url,
            headers=mobile_headers(integration.access_token),
            params=params,
            timeout=20,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        logger.error('Endurain API request failed %s %s: %s', method, url, exc)
        raise IntegrationError(
            'Unable to communicate with Endurain server.',
            code='endurain.connection_failed',
        ) from exc

    if response.is_redirect:
        raise IntegrationError(
            'Unexpected redirect from Endurain server.',
            code='endurain.connection_failed',
        )

    if response.status_code == 401 and retry_on_unauthorized:
        refresh_tokens(integration)
        return api_request(integration, method, path, params=params, retry_on_unauthorized=False)

    return response


def validate_connection(integration: EndurainIntegration) -> None:
    response = api_request(
        integration,
        'GET',
        f'/activities/user/{integration.endurain_user_id}/page_number/1/num_records/1',
    )
    if response.status_code in (401, 403):
        raise IntegrationError(
            'Endurain rejected the stored credentials.',
            code='endurain.reconnect_required',
            status_code=response.status_code,
        )
    if response.status_code >= 400:
        raise IntegrationError(
            'Could not verify Endurain connection.',
            code='endurain.connection_failed',
            status_code=response.status_code,
        )


def _parse_date_param(value: str | None) -> date | None:
    if not value:
        return None
    try:
        if 'T' in value:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def fetch_user_activities(
    integration: EndurainIntegration,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    page_number: int = 1,
    num_records: int = 50,
) -> list[dict]:
    params = {}
    parsed_start = _parse_date_param(start_date)
    parsed_end = _parse_date_param(end_date)
    if parsed_start:
        params['start_date'] = parsed_start.isoformat()
    if parsed_end:
        params['end_date'] = parsed_end.isoformat()

    response = api_request(
        integration,
        'GET',
        f'/activities/user/{integration.endurain_user_id}/page_number/{page_number}/num_records/{num_records}',
        params=params or None,
    )
    if response.status_code >= 400:
        try:
            detail = response.json().get('detail', 'Failed to fetch activities.')
        except ValueError:
            detail = 'Failed to fetch activities.'
        raise IntegrationError(str(detail), code='endurain.fetch_failed', status_code=response.status_code)

    data = response.json()
    if data is None:
        return []
    if isinstance(data, dict):
        return data.get('records') or data.get('activities') or []
    if isinstance(data, list):
        return data
    return []


def fetch_activity_by_id(integration: EndurainIntegration, activity_id: int) -> dict:
    response = api_request(integration, 'GET', f'/activities/{activity_id}')
    if response.status_code == 404:
        raise IntegrationError('Activity not found.', code='endurain.activity_not_found', status_code=404)
    if response.status_code >= 400:
        raise IntegrationError('Failed to fetch activity.', code='endurain.fetch_failed', status_code=response.status_code)
    data = response.json()
    if not data:
        raise IntegrationError('Activity not found.', code='endurain.activity_not_found', status_code=404)
    return data


def save_integration_from_tokens(
    user,
    server_url: str,
    tokens: dict,
) -> EndurainIntegration:
    normalized_url = normalize_server_url(server_url)
    endurain_user_id = tokens.get('endurain_user_id')
    if not endurain_user_id:
        raise IntegrationError(
            'Could not determine Endurain user id from token.',
            code='endurain.auth_failed',
        )

    integration, _created = EndurainIntegration.objects.update_or_create(
        user=user,
        defaults={
            'server_url': normalized_url,
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'access_token_expires_at': tokens['access_token_expires_at'],
            'refresh_token_expires_at': tokens.get('refresh_token_expires_at'),
            'endurain_user_id': endurain_user_id,
            'username': tokens.get('username', ''),
            'auth_method': EndurainIntegration.AUTH_PASSWORD,
        },
    )
    validate_connection(integration)
    return integration
