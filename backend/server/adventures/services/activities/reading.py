"""Reading an uploaded activity file in whichever format it is."""

from __future__ import annotations

from .errors import UnreadableTrackError
from .readers import fit, gpx, kml, tcx
from .track import Track

SUPPORTED_EXTENSIONS = ('.gpx', '.fit', '.tcx', '.kml', '.kmz')
# Even a multi-day recording at one point a second is a few megabytes.
MAX_TRACK_FILE_BYTES = 50 * 1024 * 1024


def _sniff(file) -> str:
    """The format from the file's first bytes, not its name."""
    file.seek(0)
    head = file.read(2048)
    file.seek(0)
    if head[8:12] == b'.FIT':
        return 'fit'
    if head[:2] == b'PK':
        return 'kml'  # KMZ
    text = head.decode('utf-8', errors='ignore').lower()
    if '<gpx' in text:
        return 'gpx'
    if '<trainingcenterdatabase' in text:
        return 'tcx'
    if '<kml' in text:
        return 'kml'
    raise UnreadableTrackError('Upload a GPX, FIT, TCX, KML or KMZ file.')


_READERS = {'fit': fit.read, 'gpx': gpx.read, 'tcx': tcx.read, 'kml': kml.read}


def read_track(file) -> Track:
    """Parse an uploaded file into a ``Track``; raises ``UnreadableTrackError`` for anything else."""
    if (getattr(file, 'size', 0) or 0) > MAX_TRACK_FILE_BYTES:
        raise UnreadableTrackError('This file is too large to read as an activity.')
    return _READERS[_sniff(file)](file)
