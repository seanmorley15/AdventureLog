import time

from django.conf import settings


class EfficientSessionMiddleware:
    """
    Keep session auth efficient while preserving sliding expiry and allauth session tracking.

    - Does not write the session on every request (SESSION_SAVE_EVERY_REQUEST stays False).
    - Refreshes expiry at most once per SESSION_TOUCH_INTERVAL_SECONDS.
    - Records the current browser session in allauth.usersessions once per Django session
      so users can list/revoke devices without USERSESSIONS_TRACK_ACTIVITY (per-request writes).
    """

    SESSION_TRACKED_KEY = '_al_us'
    SESSION_TOUCH_KEY = '_session_touch'

    def __init__(self, get_response):
        self.get_response = get_response
        self.touch_interval = int(
            getattr(settings, 'SESSION_TOUCH_INTERVAL_SECONDS', 60 * 60 * 24)
        )

    def __call__(self, request):
        self._maybe_maintain_session(request)
        return self.get_response(request)

    def _maybe_maintain_session(self, request):
        user = getattr(request, 'user', None)
        session = getattr(request, 'session', None)
        if user is None or session is None:
            return
        if not getattr(user, 'is_authenticated', False):
            return
        # Only act on existing cookie sessions — never create sessions for API-key auth.
        if not session.session_key:
            return

        if not session.get(self.SESSION_TRACKED_KEY):
            from allauth.usersessions.models import UserSession

            UserSession.objects.create_from_request(request)
            session[self.SESSION_TRACKED_KEY] = True

        now = int(time.time())
        last_touch = session.get(self.SESSION_TOUCH_KEY)
        if not isinstance(last_touch, int) or (now - last_touch) >= self.touch_interval:
            session[self.SESSION_TOUCH_KEY] = now
            # Mark modified so Django extends expire_date without saving every request.
            session.modified = True
