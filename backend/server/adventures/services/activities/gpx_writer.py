"""Writing a ``Track`` back out as GPX: the one format every activity is stored in."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import gpxpy.gpx

from .track import Track

GPXTPX_NS = 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'


def _extension(point) -> ET.Element | None:
    """Heart rate and cadence in Garmin's TrackPointExtension, which readers like Strava understand."""
    if point.heart_rate is None and point.cadence is None:
        return None
    extension = ET.Element(f'{{{GPXTPX_NS}}}TrackPointExtension')
    if point.heart_rate is not None:
        ET.SubElement(extension, f'{{{GPXTPX_NS}}}hr').text = str(int(round(point.heart_rate)))
    if point.cadence is not None:
        ET.SubElement(extension, f'{{{GPXTPX_NS}}}cad').text = str(int(round(point.cadence)))
    return extension


def track_to_gpx(track: Track, sport_type: str | None = None) -> bytes:
    """A single-track GPX with elevation, time and heart rate/cadence for every point that has them."""
    gpx = gpxpy.gpx.GPX()
    gpx.nsmap['gpxtpx'] = GPXTPX_NS
    gpx.creator = 'AdventureLog'
    gpx_track = gpxpy.gpx.GPXTrack(name=track.name)
    gpx_track.type = sport_type or track.sport
    gpx.tracks.append(gpx_track)
    for segment in track.segments:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        for point in segment:
            gpx_point = gpxpy.gpx.GPXTrackPoint(
                latitude=point.lat, longitude=point.lon, elevation=point.ele, time=point.time
            )
            extension = _extension(point)
            if extension is not None:
                gpx_point.extensions.append(extension)
            gpx_segment.points.append(gpx_point)
        gpx_track.segments.append(gpx_segment)
    return gpx.to_xml().encode('utf-8')
