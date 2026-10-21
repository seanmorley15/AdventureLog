"""The one error the day plan raises."""

from __future__ import annotations




from core.errors import ServiceError

# Codes that are not a plain 400.
_STATUS_BY_CODE = {'not_found': 404, 'conflict': 409}


class DayPlanError(ServiceError):
    """A request the day plan cannot apply; ``code`` decides the HTTP status."""

    def __init__(self, message, code='invalid', extra=None):
        super().__init__(message, code=code, status=_STATUS_BY_CODE.get(code, 400), extra=extra)
