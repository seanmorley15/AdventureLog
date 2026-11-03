from core.errors import ServiceError


class BackupError(ServiceError):
    """A backup or archive that cannot be read or restored, with a message safe to show the user."""

    def __init__(self, message, status=400, extra=None, code=None):
        if code is None:
            code = 'media_quota_exceeded' if status == 413 else 'invalid_backup'
        super().__init__(message, code=code, status=status, extra=extra)
