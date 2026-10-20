"""The one error the day plan raises."""

from __future__ import annotations




class DayPlanError(Exception):
    """A request the day plan cannot apply; ``code`` maps to an HTTP status."""

    def __init__(self, message, code='invalid', extra=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.extra = extra or {}
