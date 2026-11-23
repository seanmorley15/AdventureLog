"""
Distance, elevation, time and speed worked out from recorded track points.

Every function is pure and takes the point segments of a ``Track``. The constants below are
the tuning knobs; they follow common practice for GPS recordings (the same ideas Strava and
Garmin Connect use) so the numbers land close to what those services report.
"""

from __future__ import annotations

import math
from datetime import timedelta
from statistics import median

from .track import TrackPoint

EARTH_RADIUS_M = 6_371_008.8
# A step shorter than this from the last kept point is GPS jitter while standing still.
MIN_STEP_M = 1.0
# No outing here goes faster than this (m/s, about 250 km/h), so a faster jump is a GPS glitch.
MAX_PLAUSIBLE_SPEED = 70.0
# A position that keeps "jumping" this many points in a row is where we really are now.
MAX_CONSECUTIVE_GLITCHES = 3
# Altitude must move this far from the last counted level before it adds to gain or loss.
ELEVATION_THRESHOLD_M = 3.0
# Odd window for the median filter that removes single-sample altitude spikes.
ELEVATION_MEDIAN_WINDOW = 5
# A gap between two points longer than this is a pause, whatever the distance.
MAX_MOVING_GAP = timedelta(seconds=60)
# Max speed is the best average over this long, so one GPS spike cannot set it.
MAX_SPEED_WINDOW = timedelta(seconds=10)


def haversine(a: TrackPoint, b: TrackPoint) -> float:
    """Great-circle distance in meters between two points."""
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    d_lat = lat2 - lat1
    d_lon = math.radians(b.lon - a.lon)
    h = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def _cleaned(segment: list[TrackPoint]) -> list[TrackPoint]:
    """
    The points worth measuring between: no jitter while standing still, no impossible jumps.

    A point is dropped when it is within ``MIN_STEP_M`` of the last kept point, or (when both
    have times) when reaching it would take more than ``MAX_PLAUSIBLE_SPEED``. After a few
    such jumps in a row the new position is accepted, so a bad first point cannot hide the rest.
    """
    kept: list[TrackPoint] = []
    glitches = 0
    for point in segment:
        if not kept:
            kept.append(point)
            continue
        step = haversine(kept[-1], point)
        if step < MIN_STEP_M:
            continue
        if kept[-1].time and point.time and glitches < MAX_CONSECUTIVE_GLITCHES:
            seconds = (point.time - kept[-1].time).total_seconds()
            if seconds > 0 and step / seconds > MAX_PLAUSIBLE_SPEED:
                glitches += 1
                continue
        glitches = 0
        kept.append(point)
    return kept


def distance(segments: list[list[TrackPoint]]) -> float:
    """Total distance in meters. Each segment is measured alone, so a gap between them adds nothing."""
    total = 0.0
    for segment in segments:
        kept = _cleaned(segment)
        total += sum(haversine(a, b) for a, b in zip(kept, kept[1:]))
    return total


def _median_filter(values: list[float], window: int) -> list[float]:
    half = window // 2
    return [median(values[max(0, i - half):i + half + 1]) for i in range(len(values))]


def _climb_and_descent(values: list[float], threshold: float) -> tuple[float, float]:
    """Gain and loss counted only once altitude has moved ``threshold`` from the last anchor."""
    gain = loss = 0.0
    anchor = values[0]
    for value in values[1:]:
        if value - anchor >= threshold:
            gain += value - anchor
            anchor = value
        elif anchor - value >= threshold:
            loss += anchor - value
            anchor = value
    return gain, loss


def elevation(segments: list[list[TrackPoint]]) -> tuple[float, float, float, float] | None:
    """
    ``(gain, loss, high, low)`` in meters, or ``None`` when the points carry no altitude.

    Altitude is median-filtered per segment to drop spikes, then summed with hysteresis so
    sensor noise on flat ground does not add up to phantom climbing. High and low come from
    the filtered values for the same reason.
    """
    gain = loss = 0.0
    filtered_all: list[float] = []
    for segment in segments:
        values = [point.ele for point in segment if point.ele is not None]
        if not values:
            continue
        filtered = _median_filter(values, ELEVATION_MEDIAN_WINDOW)
        segment_gain, segment_loss = _climb_and_descent(filtered, ELEVATION_THRESHOLD_M)
        gain += segment_gain
        loss += segment_loss
        filtered_all.extend(filtered)
    if not filtered_all:
        return None
    return gain, loss, max(filtered_all), min(filtered_all)


def has_timestamps(segments: list[list[TrackPoint]]) -> bool:
    return sum(1 for segment in segments for point in segment if point.time is not None) >= 2


def elapsed_time(segments: list[list[TrackPoint]]) -> timedelta | None:
    """First to last timestamp."""
    times = [point.time for segment in segments for point in segment if point.time is not None]
    if len(times) < 2:
        return None
    return max(times) - min(times)


def start_time(segments: list[list[TrackPoint]]):
    times = [point.time for segment in segments for point in segment if point.time is not None]
    return min(times) if times else None


def moving_time(segments: list[list[TrackPoint]], stopped_speed: float) -> timedelta | None:
    """
    Time spent moving faster than ``stopped_speed`` (m/s), ignoring pauses longer than a minute.

    ``None`` when the points have no timestamps.
    """
    if not has_timestamps(segments):
        return None
    total = timedelta()
    for segment in segments:
        kept = [point for point in _cleaned(segment) if point.time is not None]
        for a, b in zip(kept, kept[1:]):
            interval = b.time - a.time
            seconds = interval.total_seconds()
            if seconds <= 0 or interval > MAX_MOVING_GAP:
                continue
            if haversine(a, b) / seconds >= stopped_speed:
                total += interval
    return total


def max_speed(segments: list[list[TrackPoint]]) -> float | None:
    """Best speed in m/s averaged over ``MAX_SPEED_WINDOW``; ``None`` without timestamps."""
    if not has_timestamps(segments):
        return None
    best = 0.0
    window = MAX_SPEED_WINDOW.total_seconds()
    for segment in segments:
        kept = [point for point in _cleaned(segment) if point.time is not None]
        if len(kept) < 2:
            continue
        cumulative = [0.0]
        for a, b in zip(kept, kept[1:]):
            cumulative.append(cumulative[-1] + haversine(a, b))
        start = 0
        for end in range(1, len(kept)):
            # Move the window start up to the latest point still at least one window behind.
            while start + 1 < end and (kept[end].time - kept[start + 1].time).total_seconds() >= window:
                start += 1
            seconds = (kept[end].time - kept[start].time).total_seconds()
            if seconds >= window:
                best = max(best, (cumulative[end] - cumulative[start]) / seconds)
    return best or None
