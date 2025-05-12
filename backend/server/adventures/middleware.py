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

class XSessionTokenMiddleware(MiddlewareMixin):
    def process_request(self, request):
        session_token = request.headers.get('X-Session-Token')
        if session_token:
            request.COOKIES[settings.SESSION_COOKIE_NAME] = session_token

class DisableCSRFForSessionTokenMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if 'X-Session-Token' in request.headers:
            setattr(request, '_dont_enforce_csrf_checks', True)

class DisableCSRFForMobileLoginSignup(MiddlewareMixin):
    def process_request(self, request):
        is_mobile = request.headers.get('X-Is-Mobile', '').lower() == 'true'
        is_login_or_signup = request.path in ['/auth/browser/v1/auth/login', '/auth/browser/v1/auth/signup']
        if is_mobile and is_login_or_signup:
            setattr(request, '_dont_enforce_csrf_checks', True)
       