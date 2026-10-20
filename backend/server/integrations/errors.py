class IntegrationError(Exception):
    """A failure talking to an external service, with a message that is safe to show the user."""

    def __init__(self, user_message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.status_code = status_code
        self.code = code


class MfaRequired(IntegrationError):
    def __init__(self, username: str):
        super().__init__('MFA verification required.', code='endurain.mfa_required')
        self.username = username
