from django.conf import settings
from django.http import JsonResponse

from cloud.utils import get_or_create_subscription, has_access
from users.models import APIKey


class CloudAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.CLOUD_MODE:
            return self.get_response(request)

        if not request.path.startswith("/api/"):
            return self.get_response(request)

        if request.path.startswith("/api/billing/"):
            return self.get_response(request)

        user = request.user if request.user.is_authenticated else None

        if user is None:
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                auth_header = request.headers.get("Authorization", "")
                if auth_header.lower().startswith("api-key "):
                    api_key = auth_header[8:].strip()

            if api_key:
                api_key_instance = APIKey.authenticate(api_key)
                if api_key_instance:
                    user = api_key_instance.user

        if user is None:
            return self.get_response(request)

        subscription = get_or_create_subscription(user)
        if has_access(user, subscription):
            return self.get_response(request)

        return JsonResponse(
            {"detail": "Subscription required.", "code": "subscription_required"},
            status=402,
        )
