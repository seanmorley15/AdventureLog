import base64
import ipaddress
import json
import logging
import re
import secrets
import socket
import time
from datetime import date, datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlparse

import gpxpy
import gpxpy.gpx
import requests
from django.core.cache import cache

from .models import EndurainIntegration

logger = logging.getLogger(__name__)

ENDURAIN_API_PREFIX = '/api/v1'
ENDURAIN_CLIENT_TYPE = 'mobile'
# CFNetwork suffix lets Endurain's ua-parser treat this as the client name
# (shows as "Other - AdventureLog Integration" in sessions instead of "Python Requests").
ENDURAIN_USER_AGENT = 'AdventureLog Integration/1.0 CFNetwork/1.0'
STREAM_TYPE_ELEVATION = 4
STREAM_TYPE_LAT_LON = 7
TOKEN_REFRESH_BUFFER_SECONDS = 300
MFA_PENDING_TTL_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 15
# Cloud metadata / link-local targets that must never be reachable via server_url.
_BLOCKED_HOSTNAMES = frozenset({
    'metadata.google.internal',
    'metadata.google.com',
    'instance-data',
})
_METADATA_NETWORKS = (
    ipaddress.ip_network('169.254.0.0/16'),  # link-local / cloud metadata
    ipaddress.ip_network('fd00:ec2::/32'),  # AWS IPv6 metadata
)

ACTIVITY_TYPE_MAP = {
    1: 'Run',
    2: 'Run',
    3: 'Run',
    4: 'Ride',
    5: 'Ride',
    6: 'Ride',
    7: 'Ride',
    8: 'Swim',
    9: 'Swim',
    10: 'Workout',
    11: 'Walk',
    12: 'Hike',
    13: 'Rowing',
    14: 'Yoga',
    15: 'AlpineSki',
    16: 'NordicSki',
    17: 'Snowboard',
    18: 'Transition',
    19: 'Workout',
    20: 'Crossfit',
    21: 'Tennis',
    22: 'TableTennis',
    23: 'Badminton',
    24: 'Squash',
    25: 'Racquetball',
    26: 'Pickleball',
    27: 'Ride',
    28: 'Ride',
    29: 'Ride',
    30: 'Windsurf',
    31: 'Walk',
    32: 'StandUpPaddling',
    33: 'Surf',
    34: 'Run',
    35: 'Ride',
    36: 'Ride',
    37: 'IceSkate',
    38: 'Soccer',
    39: 'Padel',
    40: 'Run',
    41: 'Workout',
    42: 'Kayaking',
    43: 'Sailing',
    44: 'Snowshoe',
    45: 'InlineSkate',
    46: 'HIIT',
    47: 'JumpRope',
}


class IntegrationError(Exception):
    def __init__(self, user_message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.status_code = status_code
        self.code = code


class MfaRequired(IntegrationError):
    def __init__(self, username: str):
        super().__init__('MFA verification required.', code='endurain.mfa_required')
        self.username = username


def _format_server_url(server_url: str) -> str:
    """Strip and structurally validate a server URL without DNS lookups."""
    url = (server_url or '').strip().rstrip('/')
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise IntegrationError(
            'Server URL must be a valid http or https URL.',
            code='endurain.invalid_server_url',
        )
    if parsed.username is not None or parsed.password is not None:
        raise IntegrationError(
            'Server URL must not include username or password.',
            code='endurain.invalid_server_url',
        )
    if parsed.query or parsed.fragment:
        raise IntegrationError(
            'Server URL must not include query parameters or fragments.',
            code='endurain.invalid_server_url',
        )
    if not parsed.hostname:
        raise IntegrationError(
            'Server URL must be a valid http or https URL.',
            code='endurain.invalid_server_url',
        )
    path = parsed.path.rstrip('/') if parsed.path else ''
    return f'{parsed.scheme}://{parsed.netloc}{path}'


def _assert_host_not_metadata(hostname: str) -> None:
    """Reject cloud-metadata / link-local targets (SSRF hardening)."""
    hostname_lower = hostname.lower().rstrip('.')
    if hostname_lower in _BLOCKED_HOSTNAMES or hostname_lower.endswith('.metadata.google.internal'):
        raise IntegrationError(
            'Server URL host is not allowed.',
            code='endurain.invalid_server_url',
        )

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise IntegrationError(
            'Could not resolve Endurain server hostname.',
            code='endurain.invalid_server_url',
        ) from exc

    if not addr_infos:
        raise IntegrationError(
            'Could not resolve Endurain server hostname.',
            code='endurain.invalid_server_url',
        )

    for addr_info in addr_infos:
        try:
            ip = ipaddress.ip_address(addr_info[4][0])
        except ValueError as exc:
            raise IntegrationError(
                'Server URL resolved to an invalid IP address.',
                code='endurain.invalid_server_url',
            ) from exc
        if ip.is_multicast or ip.is_unspecified:
            raise IntegrationError(
                'Server URL host is not allowed.',
                code='endurain.invalid_server_url',
            )
        for network in _METADATA_NETWORKS:
            if ip in network:
                raise IntegrationError(
                    'Server URL host is not allowed.',
                    code='endurain.invalid_server_url',
                )


def normalize_server_url(server_url: str) -> str:
    """
    Normalize and validate an Endurain base URL.

    Private/loopback hosts are allowed so self-hosted LAN Endurain works.
    Link-local / cloud-metadata targets and credentialed URLs are rejected.
    """
    url = _format_server_url(server_url)
    hostname = urlparse(url).hostname
    if hostname:
        _assert_host_not_metadata(hostname)
    return url


def safe_gpx_filename(name: str | None) -> str:
    """Sanitize an activity name for use in Content-Disposition filenames."""
    safe = re.sub(r'[^\w\s-]', '', name or '').strip().replace(' ', '_')
    return (safe[:80] or 'activity') + '.gpx'


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


def _api_url(server_url: str, path: str) -> str:
    # Stored URLs were validated at connect time; avoid DNS on every API call.
    base = _format_server_url(server_url)
    if not path.startswith('/'):
        path = f'/{path}'
    return f'{base}{ENDURAIN_API_PREFIX}{path}'


def _mobile_headers(access_token: str | None = None, extra: dict | None = None) -> dict:
    headers = {
        'X-Client-Type': ENDURAIN_CLIENT_TYPE,
        'User-Agent': ENDURAIN_USER_AGENT,
    }
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
    if extra:
        headers.update(extra)
    return headers


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
    url = _api_url(server_url, '/auth/login')
    try:
        response = requests.post(
            url,
            headers=_mobile_headers(extra={'Content-Type': 'application/x-www-form-urlencoded'}),
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
    url = _api_url(server_url, '/auth/mfa/verify')
    try:
        response = requests.post(
            url,
            headers=_mobile_headers(extra={'Content-Type': 'application/json'}),
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
    url = _api_url(integration.server_url, '/auth/refresh')
    try:
        response = requests.post(
            url,
            headers=_mobile_headers(integration.refresh_token),
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


def _request(
    integration: EndurainIntegration,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    retry_on_unauthorized: bool = True,
) -> requests.Response:
    # Re-check resolved IPs on each outbound call to mitigate DNS rebinding to metadata.
    hostname = urlparse(_format_server_url(integration.server_url)).hostname
    if hostname:
        _assert_host_not_metadata(hostname)

    integration = refresh_tokens_if_needed(integration)
    url = _api_url(integration.server_url, path)
    try:
        response = requests.request(
            method.upper(),
            url,
            headers=_mobile_headers(integration.access_token),
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
        return _request(integration, method, path, params=params, retry_on_unauthorized=False)

    return response


def validate_connection(integration: EndurainIntegration) -> None:
    response = _request(
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

    response = _request(
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
    response = _request(integration, 'GET', f'/activities/{activity_id}')
    if response.status_code == 404:
        raise IntegrationError('Activity not found.', code='endurain.activity_not_found', status_code=404)
    if response.status_code >= 400:
        raise IntegrationError('Failed to fetch activity.', code='endurain.fetch_failed', status_code=response.status_code)
    data = response.json()
    if not data:
        raise IntegrationError('Activity not found.', code='endurain.activity_not_found', status_code=404)
    return data


def _sport_type_name(activity_type: int | None) -> str:
    if activity_type is None:
        return 'Activity'
    return ACTIVITY_TYPE_MAP.get(int(activity_type), 'Activity')


def normalize_activity(activity: dict, server_url: str) -> dict:
    activity_id = activity.get('id')
    distance = float(activity.get('distance') or 0)
    moving_time = activity.get('total_timer_time') or activity.get('total_elapsed_time') or 0
    elapsed_time = activity.get('total_elapsed_time') or moving_time or 0
    moving_time = int(moving_time) if moving_time else 0
    elapsed_time = int(elapsed_time) if elapsed_time else 0
    rest_time = max(0, elapsed_time - moving_time) if elapsed_time and moving_time else 0

    avg_speed = activity.get('average_speed')
    max_speed = activity.get('max_speed')
    elevation_gain = activity.get('elevation_gain')
    elevation_loss = activity.get('elevation_loss')
    if elevation_gain is not None:
        elevation_gain = float(elevation_gain)
    if elevation_loss is not None:
        elevation_loss = float(elevation_loss)
    activity_type = activity.get('activity_type')
    sport_type = _sport_type_name(activity_type)

    start_date = activity.get('start_time') or activity.get('start_time_tz_applied') or ''
    start_date_local = activity.get('start_time_tz_applied') or start_date

    pace_per_km = None
    pace_per_mile = None
    if moving_time and distance > 0:
        pace_per_km = moving_time / (distance / 1000)
        pace_per_mile = moving_time / (distance / 1609.34)

    base_url = _format_server_url(server_url)
    export_gpx = f'/api/integrations/endurain/activities/{activity_id}/gpx/'

    return {
        'id': activity_id,
        'name': activity.get('name') or 'Activity',
        'type': sport_type,
        'sport_type': sport_type,
        'distance': distance,
        'distance_km': round(distance / 1000, 2) if distance else None,
        'distance_miles': round(distance / 1609.34, 2) if distance else None,
        'moving_time': moving_time,
        'elapsed_time': elapsed_time,
        'rest_time': rest_time,
        'total_elevation_gain': elevation_gain,
        'estimated_elevation_loss': elevation_loss,
        'elev_high': None,
        'elev_low': None,
        'total_elevation_range': None,
        'start_date': start_date,
        'start_date_local': start_date_local,
        'timezone': activity.get('timezone') or '',
        'timezone_raw': activity.get('timezone') or '',
        'average_speed': avg_speed,
        'average_speed_kmh': round(avg_speed * 3.6, 2) if avg_speed else None,
        'average_speed_mph': round(avg_speed * 2.237, 2) if avg_speed else None,
        'max_speed': max_speed,
        'max_speed_kmh': round(max_speed * 3.6, 2) if max_speed else None,
        'max_speed_mph': round(max_speed * 2.237, 2) if max_speed else None,
        'pace_per_km_seconds': pace_per_km,
        'pace_per_mile_seconds': pace_per_mile,
        'grade_adjusted_average_speed': None,
        'average_cadence': activity.get('average_cad'),
        'average_watts': activity.get('average_power'),
        'max_watts': activity.get('max_power'),
        'kilojoules': None,
        'calories': activity.get('calories'),
        'achievement_count': 0,
        'kudos_count': 0,
        'comment_count': 0,
        'pr_count': 0,
        'gear_id': str(activity.get('gear_id')) if activity.get('gear_id') else None,
        'device_name': activity.get('tracker_model') or activity.get('tracker_manufacturer'),
        'trainer': False,
        'manual': False,
        'start_latlng': None,
        'end_latlng': None,
        'export_original': f'{base_url}/activity/{activity_id}',
        'export_gpx': export_gpx,
        'visibility': str(activity.get('visibility', '')),
        'photo_count': 0,
        'has_heartrate': activity.get('average_hr') is not None,
        'flagged': False,
        'commute': False,
        'provider': 'endurain',
    }


def _stream_waypoints(stream_data: dict | None) -> list[dict]:
    if not stream_data:
        return []
    waypoints = stream_data.get('stream_waypoints') or stream_data.get('data') or []
    return [wp for wp in waypoints if isinstance(wp, dict)]


def _parse_waypoint_time(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Endurain may store unix timestamps in seconds or milliseconds
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=dt_timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None


def _extract_lat_lon_points(
    stream_data: dict | None,
) -> list[tuple[float, float, datetime | None]]:
    points: list[tuple[float, float, datetime | None]] = []
    for wp in _stream_waypoints(stream_data):
        lat = wp.get('lat') if wp.get('lat') is not None else wp.get('latitude')
        lon = wp.get('lon') if wp.get('lon') is not None else wp.get('lng')
        if lon is None:
            lon = wp.get('longitude')
        if lat is None or lon is None:
            continue
        points.append((float(lat), float(lon), _parse_waypoint_time(wp.get('time'))))
    return points


def _extract_elevations(stream_data: dict | None) -> list[float | None]:
    elevations: list[float | None] = []
    for wp in _stream_waypoints(stream_data):
        elev = wp.get('ele')
        if elev is None:
            elev = wp.get('elevation')
        if elev is None:
            elev = wp.get('altitude')
        elevations.append(float(elev) if elev is not None else None)
    return elevations


def _fetch_activity_stream(
    integration: EndurainIntegration,
    activity_id: int,
    stream_type: int,
) -> dict | None:
    response = _request(
        integration,
        'GET',
        f'/activities_streams/activity_id/{activity_id}/stream_type/{stream_type}',
    )
    if response.status_code >= 400:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def export_activity_gpx(integration: EndurainIntegration, activity_id: int) -> bytes:
    activity = fetch_activity_by_id(integration, activity_id)
    lat_lon_stream = _fetch_activity_stream(integration, activity_id, STREAM_TYPE_LAT_LON)
    if lat_lon_stream is None:
        raise IntegrationError(
            'Could not fetch GPS data for this activity.',
            code='endurain.gpx_unavailable',
            status_code=404,
        )

    points = _extract_lat_lon_points(lat_lon_stream)
    if len(points) < 2:
        raise IntegrationError(
            'This activity does not have enough GPS points to export GPX.',
            code='endurain.gpx_unavailable',
        )

    elevation_stream = _fetch_activity_stream(integration, activity_id, STREAM_TYPE_ELEVATION)
    elevations = _extract_elevations(elevation_stream) if elevation_stream else []

    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack(name=activity.get('name') or 'Activity')
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    start_time = activity.get('start_time')
    track_time = None
    if start_time:
        try:
            track_time = datetime.fromisoformat(str(start_time).replace('Z', '+00:00'))
            if track_time.tzinfo is None:
                track_time = track_time.replace(tzinfo=dt_timezone.utc)
        except ValueError:
            track_time = None

    for index, (lat, lon, point_time) in enumerate(points):
        if point_time is None and track_time is not None:
            point_time = track_time + timedelta(seconds=index)

        elevation = None
        if index < len(elevations):
            elevation = elevations[index]

        gpx_segment.points.append(
            gpxpy.gpx.GPXTrackPoint(
                latitude=lat,
                longitude=lon,
                elevation=elevation,
                time=point_time,
            )
        )

    return gpx.to_xml().encode('utf-8')


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
