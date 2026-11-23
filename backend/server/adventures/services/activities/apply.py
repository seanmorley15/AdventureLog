"""Turning an uploaded activity file into a stored GPX and the fields it fills."""

from __future__ import annotations

import os

from django.core.files.base import ContentFile

from .analysis import ActivityAnalysis, analyze_track
from .gpx_writer import track_to_gpx
from .reading import read_track


def prepare_activity_file(validated_data: dict, upload) -> ActivityAnalysis:
    """
    Replace ``validated_data['gpx_file']`` with a normalized GPX and fill the fields the client left out.

    Whatever the client sent wins, so a value the user edited, or one an integration supplied,
    is never overwritten by the file. Raises ``UnreadableTrackError`` for a file that is not a track.
    """
    track = read_track(upload)
    analysis = analyze_track(track)
    stem = os.path.splitext(os.path.basename(upload.name or 'activity'))[0] or 'activity'
    validated_data['gpx_file'] = ContentFile(
        track_to_gpx(track, analysis.values.get('sport_type')), name=f'{stem}.gpx'
    )
    for name, value in analysis.values.items():
        if validated_data.get(name) in (None, ''):
            validated_data[name] = value
    return analysis
