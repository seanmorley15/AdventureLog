"""Calling the Endurain API for the signed-in user's activities."""

import logging
from datetime import date, datetime
from urllib.parse import urlparse
import requests
from integrations.errors import IntegrationError
from integrations.models import EndurainIntegration

from .connection import api_url, assert_host_not_metadata, endurain_request, format_server_url, mobile_headers, normalize_server_url
from .auth import refresh_tokens, refresh_tokens_if_needed
from .responses import UNUSABLE_BODY, problem_message, read_json

logger = logging.getLogger(__name__)

# Endurain v0.20 caps page size at 200 and rejects larger num_records values.
MAX_ACTIVITY_PAGE_SIZE = 200


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
    """Confirm the stored token can read this user's activities.

    A removed route on Endurain v0.20+ is answered with the web app's HTML and
    a 200, so a status check alone reports a healthy connection. Require a
    parseable activity list instead.
    """
    try:
        fetch_user_activities(integration, page_number=1, num_records=1)
    except IntegrationError as exc:
        if exc.status_code in (401, 403):
            raise IntegrationError(
                'Endurain rejected the stored credentials.',
                code='endurain.reconnect_required',
                status_code=exc.status_code,
            ) from exc
        if exc.code == 'endurain.invalid_response':
            raise IntegrationError(
                'Could not verify Endurain connection.',
                code='endurain.connection_failed',
                status_code=exc.status_code,
            ) from exc
        raise


def _parse_date_param(value: str | None) -> date | None:
    if not value:
        return None
    try:
        if 'T' in value:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _extract_activities(data) -> list[dict] | None:
    """Pull activity records out of the shapes Endurain has returned.

    v0.20+ list routes return ``{"items": [...], "total", "page", ...}``.
    Older routes returned a bare list or a dict keyed by ``records`` / ``activities``.
    """
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('items', 'records', 'activities'):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return None


def _activity_list_attempts(
    integration: EndurainIntegration,
    *,
    page_number: int,
    num_records: int,
    date_params: dict,
) -> list[tuple[str, dict | None]]:
    """Current Endurain list route, then the pre-v0.20 path.

    v0.20 replaced ``/activities/user/{id}/page_number/{n}/num_records/{m}``
    with ``/activities/users/{id}`` and moved paging into the query string.
    The previous path is tried only when the new one is missing: the web app
    answers an unknown route with HTML, and older servers answer it with 404.
    """
    user_id = integration.endurain_user_id
    current_params = {
        'page_number': page_number,
        'num_records': num_records,
        **date_params,
    }
    legacy_path = (
        f'/activities/user/{user_id}/page_number/{page_number}/num_records/{num_records}'
    )
    return [
        (f'/activities/users/{user_id}', current_params),
        (legacy_path, date_params or None),
    ]


def fetch_user_activities(
    integration: EndurainIntegration,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    page_number: int = 1,
    num_records: int = 50,
) -> list[dict]:
    page_number = max(1, int(page_number))
    num_records = min(MAX_ACTIVITY_PAGE_SIZE, max(1, int(num_records)))
    date_params = {}
    parsed_start = _parse_date_param(start_date)
    parsed_end = _parse_date_param(end_date)
    if parsed_start:
        date_params['start_date'] = parsed_start.isoformat()
    if parsed_end:
        date_params['end_date'] = parsed_end.isoformat()

    attempts = _activity_list_attempts(
        integration,
        page_number=page_number,
        num_records=num_records,
        date_params=date_params,
    )
    for index, (path, params) in enumerate(attempts):
        response = api_request(integration, 'GET', path, params=params)
        data = read_json(response)
        route_missing = data is UNUSABLE_BODY or response.status_code == 404
        if route_missing and index < len(attempts) - 1:
            continue
        if data is UNUSABLE_BODY:
            break
        if response.status_code >= 400:
            raise IntegrationError(
                problem_message(data, 'Failed to fetch activities.'),
                code='endurain.fetch_failed',
                status_code=response.status_code,
            )
        activities = _extract_activities(data)
        if activities is None and index < len(attempts) - 1:
            continue
        if activities is not None:
            return activities

    raise IntegrationError(
        'Endurain returned an invalid response.',
        code='endurain.invalid_response',
        status_code=502,
    )


def fetch_activity_by_id(integration: EndurainIntegration, activity_id: int) -> dict:
    response = api_request(integration, 'GET', f'/activities/{activity_id}')
    data = read_json(response)
    if data is UNUSABLE_BODY:
        raise IntegrationError(
            'Endurain returned an invalid response.',
            code='endurain.invalid_response',
            status_code=502,
        )
    if response.status_code == 404:
        raise IntegrationError('Activity not found.', code='endurain.activity_not_found', status_code=404)
    if response.status_code >= 400:
        raise IntegrationError(
            problem_message(data, 'Failed to fetch activity.'),
            code='endurain.fetch_failed',
            status_code=response.status_code,
        )
    if not isinstance(data, dict) or not data:
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
