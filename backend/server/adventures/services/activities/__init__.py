"""
Reading activity files (GPX, FIT, TCX, KML, KMZ) and working out an activity from them.

Layout, from the bottom up: ``track`` is the format-neutral shape; ``readers`` turn each file
format into a ``Track`` and ``reading`` picks the right one; ``metrics`` computes distance,
elevation, time and speed from the points; ``sports`` maps sport names onto our choices;
``analysis`` merges a device's own totals over the computed metrics; ``gpx_writer`` stores any
track as GPX; ``apply`` fills an activity's fields from an upload.

Nothing here touches the database or imports DRF.
"""

from .analysis import ActivityAnalysis, analyze_track
from .apply import prepare_activity_file
from .errors import UnreadableTrackError
from .gpx_writer import track_to_gpx
from .reading import SUPPORTED_EXTENSIONS, read_track
from .sports import normalize_sport_type

__all__ = [
    'ActivityAnalysis',
    'SUPPORTED_EXTENSIONS',
    'UnreadableTrackError',
    'analyze_track',
    'normalize_sport_type',
    'prepare_activity_file',
    'read_track',
    'track_to_gpx',
]
