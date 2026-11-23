"""The one error reading an activity file raises."""

from core.errors import ServiceError


class UnreadableTrackError(ServiceError):
    """An uploaded activity file that is not a GPX, FIT, TCX, KML or KMZ track we can read."""

    def __init__(self, message='This file could not be read as an activity track.'):
        super().__init__(message, code='activity.unreadable_track', status=400)
