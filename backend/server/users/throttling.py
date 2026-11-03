from django.conf import settings
from rest_framework.throttling import AnonRateThrottle


class MobileAuthThrottle(AnonRateThrottle):
    """
    Always-on throttle for exchanging a mobile sign-in code, independent of ENABLE_RATE_LIMITS.
    The codes are unguessable; this keeps the endpoint from being a free database hammer.
    """

    scope = 'mobile_auth'

    def get_rate(self):
        rates = getattr(settings, 'RATE_LIMIT_RATES', {}) or {}
        return rates.get(self.scope, '20/minute')
