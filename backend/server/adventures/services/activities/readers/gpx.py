"""GPX: tracks first, routes when there are none. Waypoints are places, not a recording."""

from __future__ import annotations

from datetime import timezone

import gpxpy

from ..errors import UnreadableTrackError
from ..track import Track, TrackPoint

# Heart rate and cadence live in Garmin's TrackPointExtension (and the older gpxtpx/ns3 variants).
_EXTENSION_FIELDS = {'hr': 'heart_rate', 'heartrate': 'heart_rate', 'cad': 'cadence', 'cadence': 'cadence'}


def _utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _extension_values(point) -> dict:
    values = {}
    for extension in point.extensions or []:
        for element in extension.iter():
            tag = element.tag if isinstance(element.tag, str) else ''
            name = tag.rsplit('}', 1)[-1].lower()
            if name in _EXTENSION_FIELDS and element.text:
                try:
                    values[_EXTENSION_FIELDS[name]] = float(element.text)
                except ValueError:
                    continue
    return values


def _point(gpx_point) -> TrackPoint:
    return TrackPoint(
        lat=gpx_point.latitude,
        lon=gpx_point.longitude,
        ele=gpx_point.elevation,
        time=_utc(gpx_point.time),
        **_extension_values(gpx_point),
    )


def read(file) -> Track:
    try:
        file.seek(0)
        gpx = gpxpy.parse(file)
    except Exception as error:
        raise UnreadableTrackError('This GPX file is not valid.') from error

    segments = [
        [_point(point) for point in segment.points]
        for track in gpx.tracks
        for segment in track.segments
        if segment.points
    ]
    if not segments:
        segments = [[_point(point) for point in route.points] for route in gpx.routes if route.points]
    if not segments:
        raise UnreadableTrackError('This GPX file has no track or route points.')

    first_track = gpx.tracks[0] if gpx.tracks else None
    first_route = gpx.routes[0] if gpx.routes else None
    source = first_track or first_route
    return Track(
        segments=segments,
        name=(source.name if source else None) or gpx.name,
        sport=getattr(first_track, 'type', None),
        format='gpx',
    )
