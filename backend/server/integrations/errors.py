from core.errors import ServiceError


class IntegrationError(ServiceError):
    """
    A failure talking to an external service, with a message that is safe to show the user.

    ``status_code`` is what the outside service answered, when it answered. The API answers with
    ``status``: by default 400 when the service could not be used with the given settings, 404
    when it said the thing does not exist, and 502 when it answered with any other error.
    """

    def __init__(self, user_message: str, *, status_code: int | None = None, code: str | None = None,
                 status: int | None = None):
        if status is None:
            status = 400 if status_code is None else 404 if status_code == 404 else 502
        super().__init__(user_message, code=code or 'integration_error', status=status)
        self.user_message = user_message
        self.status_code = status_code


class MfaRequired(IntegrationError):
    def __init__(self, username: str):
        super().__init__('MFA verification required.', code='endurain.mfa_required')
        self.username = username
