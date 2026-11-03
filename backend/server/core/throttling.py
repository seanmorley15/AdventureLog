from django.conf import settings
from rest_framework.throttling import UserRateThrottle


class ConditionalUserRateThrottle(UserRateThrottle):
    def get_rate(self):
        if not getattr(settings, "ENABLE_RATE_LIMITS", False):
            return None
        return super().get_rate()
