from django.conf import settings
from rest_framework.throttling import AnonRateThrottle

from core.throttling import ConditionalUserRateThrottle


class MobileAuthThrottle(AnonRateThrottle):
    """
    Always-on throttle for exchanging a mobile sign-in code, independent of ENABLE_RATE_LIMITS.
    The codes are unguessable; this keeps the endpoint from being a free database hammer.
    """

    scope = 'mobile_auth'

    def get_rate(self):
        rates = getattr(settings, 'RATE_LIMIT_RATES', {}) or {}
        return rates.get(self.scope, '20/minute')


class AccountPreviewThrottle(ConditionalUserRateThrottle):
    """
    The account deletion and privacy previews walk every shared trip, so they are limited per user
    when rate limits are on (the rest of the account is not: the app loads it on every page).
    """

    scope = 'account_preview'

    def get_rate(self):
        if not getattr(settings, 'ENABLE_RATE_LIMITS', False):
            return None
        rates = getattr(settings, 'RATE_LIMIT_RATES', {}) or {}
        return rates.get(self.scope, '30/minute')
