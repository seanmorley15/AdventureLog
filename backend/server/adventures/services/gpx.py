"""Reading elevation and end points from an uploaded GPX track."""

import logging

import gpxpy

logger = logging.getLogger(__name__)


def smooth_elevations(elevations, window_size=3):
    """A simple moving average, to keep GPS noise out of the climb totals."""
    if len(elevations) < window_size:
        return elevations
    half_window = window_size // 2
    smoothed = []
    for i in range(len(elevations)):
        start = max(0, i - half_window)
        end = min(len(elevations), i + half_window + 1)
        smoothed.append(sum(elevations[start:end]) / (end - start))
    return smoothed


def elevation_from_gpx(gpx_file):
    """
    ``(gain, loss, high, low)`` in meters from a GPX file's track points and waypoints.

    All four are ``None`` when the file has no elevation samples or cannot be read.
    """
    try:
        gpx_file.seek(0)
        gpx = gpxpy.parse(gpx_file)
    except Exception:
        logger.warning('Could not parse a GPX file for elevation', exc_info=True)
        return None, None, None, None

    elevations = [
        point.elevation
        for track in gpx.tracks for segment in track.segments for point in segment.points
        if point.elevation is not None
    ]
    elevations += [waypoint.elevation for waypoint in gpx.waypoints if waypoint.elevation is not None]
    if not elevations:
        return None, None, None, None

    gain = loss = 0.0
    smoothed = smooth_elevations(elevations)
    for previous, current in zip(smoothed, smoothed[1:]):
        if current > previous:
            gain += current - previous
        else:
            loss += previous - current
    return gain, loss, max(elevations), min(elevations)


def endpoints_from_gpx(gpx_file):
    """``(start_lat, start_lng, end_lat, end_lng)`` of a GPX track, or four ``None``."""
    try:
        gpx_file.seek(0)
        gpx = gpxpy.parse(gpx_file)
    except Exception:
        logger.warning('Could not parse a GPX file for its end points', exc_info=True)
        return None, None, None, None

    points = [
        (point.latitude, point.longitude)
        for track in gpx.tracks for segment in track.segments for point in segment.points
        if point.latitude is not None and point.longitude is not None
    ]
    if not points:
        return None, None, None, None
    return (*points[0], *points[-1])


def fill_from_gpx(validated_data, gpx_file):
    """
    Fill elevation and start/end coordinates the client left out from the GPX file.

    Values the client sent (for example Strava or Endurain totals) are kept.
    """
    gain, loss, high, low = elevation_from_gpx(gpx_file)
    start_lat, start_lng, end_lat, end_lng = endpoints_from_gpx(gpx_file)
    derived = {
        'elevation_gain': gain, 'elevation_loss': loss, 'elev_high': high, 'elev_low': low,
        'start_lat': start_lat, 'start_lng': start_lng, 'end_lat': end_lat, 'end_lng': end_lng,
    }
    for field, value in derived.items():
        if validated_data.get(field) is None and value is not None:
            validated_data[field] = value
