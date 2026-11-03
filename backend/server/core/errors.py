"""The base for errors a service raises when a request cannot be carried out."""


class ServiceError(Exception):
    """
    A refusal a service can explain to the user.

    Services raise it (or a subclass) without knowing about HTTP frameworks. The API's
    exception handler (``core.exceptions``) turns it into the standard error body:
    ``message`` becomes ``detail``, ``code`` stays machine readable, ``status`` is the HTTP
    status, and ``extra`` adds context keys next to them.
    """

    status = 400
    code = 'invalid'

    def __init__(self, message, code=None, status=None, extra=None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status
        self.extra = extra or {}
