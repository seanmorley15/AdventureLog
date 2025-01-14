class AppVersionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request (if needed)
        response = self.get_response(request)

        # Add custom header to response
        # Replace with your app version
        response['X-AdventureLog-Version'] = '1.0.0'

        return response

# make a middlewra that prints all of the request cookies
class PrintCookiesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(request.COOKIES)
        response = self.get_response(request)
        return response
    
# middlewares.py

import os
from django.http import HttpRequest

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
