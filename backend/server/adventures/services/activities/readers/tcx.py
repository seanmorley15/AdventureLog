"""TCX (Garmin Training Center): laps with trackpoints, and lap totals as the device summary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from ..errors import UnreadableTrackError
from ..track import DeviceSummary, Track, TrackPoint


def _local(tag) -> str:
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def _children(element, name):
    return [child for child in element if _local(child.tag) == name]


def _child_text(element, name):
    for child in element.iter():
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return None


def _number(text):
    try:
        return float(text) if text is not None else None
    except ValueError:
        return None


def _time(text):
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _trackpoint(element) -> TrackPoint | None:
    position = next((child for child in element if _local(child.tag) == 'Position'), None)
    if position is None:
        return None
    lat, lon = _number(_child_text(position, 'LatitudeDegrees')), _number(_child_text(position, 'LongitudeDegrees'))
    if lat is None or lon is None:
        return None
    heart_rate = next((child for child in element if _local(child.tag) == 'HeartRateBpm'), None)
    return TrackPoint(
        lat=lat,
        lon=lon,
        ele=_number(_child_text(element, 'AltitudeMeters')),
        time=_time(_child_text(element, 'Time')),
        heart_rate=_number(_child_text(heart_rate, 'Value')) if heart_rate is not None else None,
        cadence=_number(_child_text(element, 'Cadence')) or _number(_child_text(element, 'RunCadence')),
    )


def _summary(laps) -> DeviceSummary:
    """Lap totals added up, and maxima taken across laps."""
    def total(name):
        values = [_number(_child_text(lap, name)) for lap in laps]
        values = [value for value in values if value is not None]
        return sum(values) if values else None

    seconds = total('TotalTimeSeconds')
    max_speeds = [_number(_child_text(lap, 'MaximumSpeed')) for lap in laps]
    max_hr = [
        _number(_child_text(element, 'Value'))
        for lap in laps for element in _children(lap, 'MaximumHeartRateBpm')
    ]
    return DeviceSummary(
        distance=total('DistanceMeters'),
        elapsed_time=timedelta(seconds=seconds) if seconds else None,
        max_speed=max([s for s in max_speeds if s is not None], default=None),
        calories=total('Calories'),
        max_heart_rate=max([hr for hr in max_hr if hr is not None], default=None),
    )


def read(file) -> Track:
    try:
        file.seek(0)
        root = ElementTree.parse(file).getroot()
    except (ElementTree.ParseError, DefusedXmlException, ValueError) as error:
        raise UnreadableTrackError('This TCX file is not valid.') from error

    activity = next((el for el in root.iter() if _local(el.tag) == 'Activity'), None)
    if activity is None:
        raise UnreadableTrackError('This TCX file has no activity.')

    laps = _children(activity, 'Lap')
    segments = []
    for lap in laps:
        for track in _children(lap, 'Track'):
            points = [point for point in map(_trackpoint, _children(track, 'Trackpoint')) if point]
            if points:
                segments.append(points)
    if not segments:
        raise UnreadableTrackError('This TCX file has no GPS points.')

    return Track(
        segments=segments,
        name=_child_text(activity, 'Notes'),
        sport=activity.get('Sport'),
        format='tcx',
        summary=_summary(laps),
    )
