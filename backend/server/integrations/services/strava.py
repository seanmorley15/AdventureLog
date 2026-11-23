"""Turning a Strava activity and its streams into a track."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from adventures.services.activities import normalize_sport_type
from adventures.services.activities.track import Track, TrackPoint
from integrations.errors import IntegrationError

# The streams that make a recording, asked for in one request.
STREAM_KEYS = ('latlng', 'altitude', 'time', 'heartrate', 'cadence')


def _stream(streams: dict, key: str) -> list:
    data = (streams.get(key) or {}).get('data')
    return data if isinstance(data, list) else []


def _start_time(activity: dict) -> datetime | None:
    raw = activity.get('start_date')
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def build_track(activity: dict, streams: dict) -> Track:
    """
    A ``Track`` from Strava's ``/activities/{id}`` and ``/streams?key_by_type=true`` answers.

    Strava returns every stream at the same resolution, so values pair up by position.
    Raises ``IntegrationError`` when the activity has no GPS stream (indoor and manual activities).
    """
    positions = _stream(streams, 'latlng')
    if len(positions) < 2:
        raise IntegrationError(
            'This Strava activity has no GPS data to import.', code='strava.gpx_unavailable', status_code=404
        )

    altitude, seconds = _stream(streams, 'altitude'), _stream(streams, 'time')
    heart_rate, cadence = _stream(streams, 'heartrate'), _stream(streams, 'cadence')
    start = _start_time(activity)

    def at(values, index):
        return values[index] if len(values) == len(positions) else None

    points = []
    for index, (lat, lon) in enumerate(positions):
        offset = at(seconds, index)
        points.append(TrackPoint(
            lat=lat,
            lon=lon,
            ele=at(altitude, index),
            time=start + timedelta(seconds=offset) if start is not None and offset is not None else None,
            heart_rate=at(heart_rate, index),
            cadence=at(cadence, index),
        ))
    return Track(
        segments=[points],
        name=activity.get('name'),
        sport=normalize_sport_type(activity.get('sport_type'), activity.get('type')),
        format='gpx',
    )
