"""KML and KMZ (zipped KML): ``LineString`` paths and Google Earth ``gx:Track`` recordings."""

from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from io import BytesIO

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from ..errors import UnreadableTrackError
from ..track import Track, TrackPoint

# A KMZ is a zip, so cap what it may expand to.
MAX_KML_BYTES = 50 * 1024 * 1024


def _local(tag) -> str:
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def _time(text):
    try:
        parsed = datetime.fromisoformat(text.strip().replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _floats(text):
    try:
        return [float(part) for part in text.replace(',', ' ').split()]
    except ValueError:
        return None


def _line_string(element) -> list[TrackPoint]:
    """``lon,lat[,ele]`` tuples separated by whitespace."""
    points = []
    for chunk in (element.text or '').split():
        values = _floats(chunk)
        if values and len(values) >= 2:
            points.append(TrackPoint(lat=values[1], lon=values[0], ele=values[2] if len(values) > 2 else None))
    return points


def _gx_track(element) -> list[TrackPoint]:
    """``when`` timestamps paired by position with ``gx:coord`` ``lon lat ele`` entries."""
    times = [_time(child.text) for child in element if _local(child.tag) == 'when' and child.text]
    coords = [child for child in element if _local(child.tag) == 'coord' and child.text]
    points = []
    for index, coord in enumerate(coords):
        values = _floats(coord.text)
        if not values or len(values) < 2:
            continue
        points.append(TrackPoint(
            lat=values[1], lon=values[0], ele=values[2] if len(values) > 2 else None,
            time=times[index] if len(times) == len(coords) else None,
        ))
    return points


def _kml_bytes(file) -> bytes:
    file.seek(0)
    data = file.read(MAX_KML_BYTES + 1)
    if data[:2] != b'PK':
        return data
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = [info for info in archive.infolist() if info.filename.lower().endswith('.kml')]
            if not names:
                raise UnreadableTrackError('This KMZ file has no KML inside.')
            chosen = next((info for info in names if info.filename.lower() == 'doc.kml'), names[0])
            if chosen.file_size > MAX_KML_BYTES:
                raise UnreadableTrackError('This KMZ file is too large to read.')
            return archive.read(chosen)
    except zipfile.BadZipFile as error:
        raise UnreadableTrackError('This KMZ file is not valid.') from error


def read(file) -> Track:
    data = _kml_bytes(file)
    if len(data) > MAX_KML_BYTES:
        raise UnreadableTrackError('This KML file is too large to read.')
    try:
        root = ElementTree.fromstring(data)
    except (ElementTree.ParseError, DefusedXmlException, ValueError) as error:
        raise UnreadableTrackError('This KML file is not valid.') from error

    segments, name = [], None
    for element in root.iter():
        tag = _local(element.tag)
        if tag == 'LineString':
            points = _line_string(next((c for c in element if _local(c.tag) == 'coordinates'), element))
        elif tag == 'Track':
            points = _gx_track(element)
        else:
            continue
        if points:
            segments.append(points)
    if not segments:
        raise UnreadableTrackError('This KML file has no path or track.')
    for element in root.iter():
        if _local(element.tag) == 'name' and element.text and element.text.strip():
            name = element.text.strip()
            break
    return Track(segments=segments, name=name, format='kml')
