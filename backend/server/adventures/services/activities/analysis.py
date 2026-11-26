"""Working out every activity field a track file can give."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from statistics import fmean

from . import metrics
from .sports import normalize_sport_type, stopped_speed_for
from .track import Track

DEVICE = 'device'
COMPUTED = 'computed'


@dataclass
class ActivityAnalysis:
    """
    Suggested activity fields, where each one came from, and facts about the file.

    ``values`` uses the ``Activity`` field names. ``sources`` says ``'device'`` for a total the
    recording device or provider reported, and ``'computed'`` for one worked out from the points.
    ``warnings`` are codes the UI turns into messages.
    """

    values: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    format: str = 'gpx'
    point_count: int = 0
    has_timestamps: bool = False
    has_elevation: bool = False
    utc_offset_minutes: int | None = None
    warnings: list[str] = field(default_factory=list)


def _first(*candidates):
    """The first candidate that is not ``None``, as ``(value, source)``."""
    for value, source in candidates:
        if value is not None:
            return value, source
    return None, None


def _mean(values) -> float | None:
    values = [value for value in values if value is not None]
    return fmean(values) if values else None


def analyze_track(track: Track) -> ActivityAnalysis:
    """Merge the device's own totals over what the points say; the device wins where it has a value."""
    segments, summary = track.segments, track.summary
    points = track.points
    sport_type = normalize_sport_type(track.sub_sport, track.sport)

    climb = metrics.elevation(segments)
    computed_distance = metrics.distance(segments)
    computed_moving = metrics.moving_time(segments, stopped_speed_for(sport_type))
    computed_elapsed = metrics.elapsed_time(segments)

    distance, distance_source = _first((summary.distance, DEVICE), (computed_distance or None, COMPUTED))
    moving, moving_source = _first((summary.moving_time, DEVICE), (computed_moving, COMPUTED))
    elapsed, elapsed_source = _first((summary.elapsed_time, DEVICE), (computed_elapsed, COMPUTED))
    if moving is not None and elapsed is not None and moving > elapsed:
        elapsed, elapsed_source = moving, moving_source
    gain, gain_source = _first(
        (summary.elevation_gain, DEVICE), (climb[0] if climb else None, COMPUTED)
    )
    loss, loss_source = _first(
        (summary.elevation_loss, DEVICE), (climb[1] if climb else None, COMPUTED)
    )
    average_speed, speed_source = _first(
        (summary.average_speed, DEVICE),
        ((distance / moving.total_seconds()) if distance and moving else None, COMPUTED),
    )
    max_speed, max_speed_source = _first((summary.max_speed, DEVICE), (metrics.max_speed(segments), COMPUTED))
    cadence, cadence_source = _first(
        (summary.average_cadence, DEVICE), (_mean(p.cadence for p in points), COMPUTED)
    )
    heart_rates = [p.heart_rate for p in points if p.heart_rate is not None]
    average_hr, average_hr_source = _first(
        (summary.average_heart_rate, DEVICE), (_mean(heart_rates), COMPUTED)
    )
    max_hr, max_hr_source = _first(
        (summary.max_heart_rate, DEVICE), (max(heart_rates) if heart_rates else None, COMPUTED)
    )
    start, start_source = _first((summary.start_time, DEVICE), (metrics.start_time(segments), COMPUTED))
    first, last = points[0], points[-1]

    entries = {
        'name': (track.name, COMPUTED),
        'sport_type': (sport_type, COMPUTED),
        'distance': (distance, distance_source),
        'moving_time': (moving, moving_source),
        'elapsed_time': (elapsed, elapsed_source),
        'rest_time': ((elapsed - moving) if moving is not None and elapsed is not None else None, COMPUTED),
        'elevation_gain': (gain, gain_source),
        'elevation_loss': (loss, loss_source),
        'elev_high': (climb[2] if climb else None, COMPUTED),
        'elev_low': (climb[3] if climb else None, COMPUTED),
        'start_date': (start, start_source),
        'average_speed': (average_speed, speed_source),
        'max_speed': (max_speed, max_speed_source),
        'average_cadence': (cadence, cadence_source),
        'average_heart_rate': (average_hr, average_hr_source),
        'max_heart_rate': (max_hr, max_hr_source),
        'calories': (summary.calories, DEVICE),
        'start_lat': (first.lat, COMPUTED),
        'start_lng': (first.lon, COMPUTED),
        'end_lat': (last.lat, COMPUTED),
        'end_lng': (last.lon, COMPUTED),
    }
    analysis = ActivityAnalysis(
        format=track.format,
        point_count=len(points),
        has_timestamps=metrics.has_timestamps(segments),
        has_elevation=climb is not None,
        utc_offset_minutes=(
            int(summary.utc_offset.total_seconds() // 60) if isinstance(summary.utc_offset, timedelta) else None
        ),
    )
    for name, (value, source) in entries.items():
        if value is not None:
            analysis.values[name] = value
            analysis.sources[name] = source
    if not analysis.has_timestamps:
        analysis.warnings.append('no_timestamps')
    if not analysis.has_elevation:
        analysis.warnings.append('no_elevation')
    return analysis
