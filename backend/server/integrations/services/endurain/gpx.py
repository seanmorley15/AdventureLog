"""Building a GPX file from an Endurain activity's streams."""

import re
from datetime import datetime, timezone as dt_timezone

from adventures.services.activities import track_to_gpx
from adventures.services.activities.track import Track, TrackPoint
from integrations.errors import IntegrationError
from integrations.models import EndurainIntegration

from .activities import _sport_type_name
from .client import api_request, fetch_activity_by_id
from .responses import UNUSABLE_BODY, read_json


STREAM_TYPE_ELEVATION = 4


STREAM_TYPE_LAT_LON = 7


def safe_gpx_filename(name: str | None) -> str:
    """Sanitize an activity name for use in Content-Disposition filenames."""
    safe = re.sub(r'[^\w\s-]', '', name or '').strip().replace(' ', '_')
    return (safe[:80] or 'activity') + '.gpx'


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
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed.replace(tzinfo=dt_timezone.utc) if parsed.tzinfo is None else parsed


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


def _pair_elevations(
    points: list[tuple[float, float, datetime | None]],
    elevation_stream: dict | None,
) -> list[float | None]:
    """
    An elevation for each position, or ``None`` where they cannot be matched.

    The two streams are separate lists. They pair by position only when they are the same
    length; otherwise by timestamp. Guessing a pairing would put altitudes on the wrong points.
    """
    elevations = _extract_elevations(elevation_stream)
    if len(elevations) == len(points):
        return elevations
    by_time = {}
    for waypoint, elevation in zip(_stream_waypoints(elevation_stream), elevations):
        moment = _parse_waypoint_time(waypoint.get('time'))
        if moment is not None and elevation is not None:
            by_time[moment] = elevation
    return [by_time.get(moment) for _lat, _lon, moment in points]


def _fetch_activity_stream(
    integration: EndurainIntegration,
    activity_id: int,
    stream_type: int,
) -> dict | None:
    # v0.20 moved streams under the activity. The old path remains for
    # servers that still serve it; a non-JSON body means that path is gone.
    paths = (
        f'/activities/{activity_id}/streams/{stream_type}',
        f'/activities_streams/activity_id/{activity_id}/stream_type/{stream_type}',
    )
    for path in paths:
        response = api_request(integration, 'GET', path)
        data = read_json(response)
        if data is UNUSABLE_BODY or response.status_code == 404:
            continue
        if response.status_code >= 400 or not isinstance(data, dict):
            return None
        return data
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
    elevations = _pair_elevations(points, elevation_stream)

    sport_type = _sport_type_name(activity.get('activity_type'))
    track = Track(
        segments=[[
            TrackPoint(lat=lat, lon=lon, ele=elevation, time=moment)
            for (lat, lon, moment), elevation in zip(points, elevations)
        ]],
        name=activity.get('name') or 'Activity',
        sport=sport_type,
    )
    return track_to_gpx(track, sport_type)
