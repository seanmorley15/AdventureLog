"""FIT (Garmin and most sports watches): ``record`` samples plus the device's own ``session`` totals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import fitdecode

from ..errors import UnreadableTrackError
from ..track import DeviceSummary, Track, TrackPoint

SEMICIRCLES_TO_DEGREES = 180 / 2**31
# Timer events that pause the recording; the next record starts a new segment.
_STOP_EVENT_TYPES = {'stop', 'stop_all', 'stop_disable', 'stop_disable_all'}


def _utc(value: datetime | None) -> datetime | None:
    """FIT timestamps are UTC but decoded naive."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _value(frame, *names):
    for name in names:
        value = frame.get_value(name, fallback=None)
        if value is not None:
            return value
    return None


def _record_point(frame) -> TrackPoint | None:
    lat, lon = _value(frame, 'position_lat'), _value(frame, 'position_long')
    if lat is None or lon is None:
        return None
    return TrackPoint(
        lat=lat * SEMICIRCLES_TO_DEGREES,
        lon=lon * SEMICIRCLES_TO_DEGREES,
        ele=_value(frame, 'enhanced_altitude', 'altitude'),
        time=_utc(_value(frame, 'timestamp')),
        heart_rate=_value(frame, 'heart_rate'),
        cadence=_value(frame, 'cadence'),
    )


def _seconds(value) -> timedelta | None:
    return timedelta(seconds=value) if value else None


def _summarize(sessions: list) -> DeviceSummary:
    """Totals across the file's sessions (more than one in a multisport recording)."""
    def total(*names):
        values = [_value(session, *names) for session in sessions]
        values = [value for value in values if value is not None]
        return sum(values) if values else None

    def best(*names):
        values = [_value(session, *names) for session in sessions]
        return max((value for value in values if value is not None), default=None)

    timer, elapsed, distance = total('total_timer_time'), total('total_elapsed_time'), total('total_distance')
    return DeviceSummary(
        distance=distance,
        elevation_gain=total('total_ascent'),
        elevation_loss=total('total_descent'),
        moving_time=_seconds(timer),
        elapsed_time=_seconds(elapsed),
        average_speed=(distance / timer) if distance and timer else None,
        max_speed=best('enhanced_max_speed', 'max_speed'),
        calories=total('total_calories'),
        average_cadence=_value(sessions[0], 'avg_cadence') if sessions else None,
        average_heart_rate=_value(sessions[0], 'avg_heart_rate') if sessions else None,
        max_heart_rate=best('max_heart_rate'),
        start_time=_utc(_value(sessions[0], 'start_time')) if sessions else None,
    )


def read(file) -> Track:
    segments: list[list[TrackPoint]] = [[]]
    sessions: list = []
    utc_offset = None
    try:
        file.seek(0)
        with fitdecode.FitReader(
            file, check_crc=fitdecode.CrcCheck.READONLY, error_handling=fitdecode.ErrorHandling.RAISE
        ) as reader:
            for frame in reader:
                if not isinstance(frame, fitdecode.FitDataMessage):
                    continue
                if frame.name == 'record':
                    point = _record_point(frame)
                    if point:
                        segments[-1].append(point)
                elif frame.name == 'event':
                    if _value(frame, 'event') == 'timer' and _value(frame, 'event_type') in _STOP_EVENT_TYPES:
                        if segments[-1]:
                            segments.append([])
                elif frame.name == 'session':
                    sessions.append(frame)
                elif frame.name == 'activity':
                    stamp, local = _value(frame, 'timestamp'), _value(frame, 'local_timestamp')
                    if stamp and local:
                        utc_offset = timedelta(minutes=round((local - stamp).total_seconds() / 60))
    except (fitdecode.FitError, ValueError, OSError, UnicodeDecodeError) as error:
        raise UnreadableTrackError('This FIT file is not valid.') from error

    segments = [segment for segment in segments if segment]
    if not segments:
        raise UnreadableTrackError('This FIT file has no GPS points.')

    summary = _summarize(sessions)
    summary.utc_offset = utc_offset
    return Track(
        segments=segments,
        sport=_value(sessions[0], 'sport') if sessions else None,
        sub_sport=_value(sessions[0], 'sub_sport') if sessions else None,
        format='fit',
        summary=summary,
    )
