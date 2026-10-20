"""Building a GPX file from an Endurain activity's streams."""

import re
from datetime import datetime, timedelta, timezone as dt_timezone
import gpxpy
import gpxpy.gpx
from integrations.errors import IntegrationError
from integrations.models import EndurainIntegration

from .client import api_request, fetch_activity_by_id


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
    response = api_request(
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
