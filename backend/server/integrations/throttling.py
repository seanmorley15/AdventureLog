from django.conf import settings
from rest_framework.throttling import UserRateThrottle


class EndurainAuthThrottle(UserRateThrottle):
    """
    Always-on throttle for Endurain connect/MFA credential proxying.
    Independent of ENABLE_RATE_LIMITS so auth guessing cannot use AdventureLog as a relay.
    """

    scope = "endurain_auth"

    def get_rate(self):
        rates = getattr(settings, "RATE_LIMIT_RATES", {}) or {}
        return rates.get(self.scope, "10/minute")
