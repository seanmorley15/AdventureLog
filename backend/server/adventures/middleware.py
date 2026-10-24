from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import os


class OverrideHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        public_url = os.getenv('PUBLIC_URL', None)
        if public_url:
            # Extract host and scheme
            scheme, host = public_url.split("://")
            request.META['HTTP_HOST'] = host
            request.META['wsgi.url_scheme'] = scheme

            # Set X-Forwarded-Proto for Django
            request.META['HTTP_X_FORWARDED_PROTO'] = scheme

        response = self.get_response(request)
        return response


class DisableCSRFForAPIKeyMiddleware(MiddlewareMixin):
    """Exempt requests carrying an AdventureLog API key from CSRF enforcement.

    DRF's own SessionAuthentication is the only built-in class that enforces
    CSRF, so this middleware is mainly a safety net for non-DRF views and to
    ensure the Django CSRF middleware itself doesn't reject API-key requests
    before they reach DRF.
    """

    def process_request(self, request):
        # Never skip CSRF for requests that also include a Django session.
        if settings.SESSION_COOKIE_NAME in request.COOKIES:
            return

        if request.headers.get('X-API-Key'):
            setattr(request, '_dont_enforce_csrf_checks', True)
            return

        auth_header = request.headers.get('Authorization', '')
        if auth_header.lower().startswith('api-key '):
            setattr(request, '_dont_enforce_csrf_checks', True)
