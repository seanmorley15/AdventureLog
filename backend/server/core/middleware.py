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
