from django.conf import settings
from rest_framework.throttling import UserRateThrottle


class ConditionalUserRateThrottle(UserRateThrottle):
    def get_rate(self):
        if not getattr(settings, "ENABLE_RATE_LIMITS", False):
            return None
        return super().get_rate()


class ImageProxyThrottle(ConditionalUserRateThrottle):
    scope = "image_proxy"


class ImageImportThrottle(ConditionalUserRateThrottle):
    scope = "image_import"


class ExternalGeocodeThrottle(ConditionalUserRateThrottle):
    scope = "external_geocode"


class ExternalRecommendationsThrottle(ConditionalUserRateThrottle):
    scope = "external_recommendations"


class ExternalWikipediaThrottle(ConditionalUserRateThrottle):
    scope = "external_wikipedia"


class ExternalSunriseSunsetThrottle(ConditionalUserRateThrottle):
    scope = "external_sunrise_sunset"


class EndurainAuthThrottle(UserRateThrottle):
    """
    Always-on throttle for Endurain connect/MFA credential proxying.
    Independent of ENABLE_RATE_LIMITS so auth guessing cannot use AdventureLog as a relay.
    """

    scope = "endurain_auth"

    def get_rate(self):
        rates = getattr(settings, "RATE_LIMIT_RATES", {}) or {}
        return rates.get(self.scope, "10/minute")
