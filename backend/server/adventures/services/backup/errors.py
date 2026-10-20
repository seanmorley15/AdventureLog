class BackupError(Exception):
    """A backup or archive that cannot be read or restored, with a message safe to show the user."""

    def __init__(self, message, status=400, extra=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra or {}
