from django.conf import settings

from core.throttling import ConditionalUserRateThrottle


class ImageProxyThrottle(ConditionalUserRateThrottle):
    scope = "image_proxy"


class ImageImportThrottle(ConditionalUserRateThrottle):
    scope = "image_import"


class PlacePhotoThrottle(ConditionalUserRateThrottle):
    scope = "place_photo"


class ExternalGeocodeThrottle(ConditionalUserRateThrottle):
    scope = "external_geocode"


class ExternalRecommendationsThrottle(ConditionalUserRateThrottle):
    scope = "external_recommendations"


class ExternalWikipediaThrottle(ConditionalUserRateThrottle):
    scope = "external_wikipedia"


class ExternalSunriseSunsetThrottle(ConditionalUserRateThrottle):
    scope = "external_sunrise_sunset"


class SharingPreviewThrottle(ConditionalUserRateThrottle):
    """
    The ``…-preview/`` endpoints of collections and locations (unlink, delete, leave, remove a
    member, add travelers) walk the places and visits involved, so they have their own per-user
    limit when rate limits are on. Read from settings on each request, like the account previews.
    """

    scope = "sharing_preview"

    def get_rate(self):
        if not getattr(settings, "ENABLE_RATE_LIMITS", False):
            return None
        rates = getattr(settings, "RATE_LIMIT_RATES", {}) or {}
        return rates.get(self.scope, "60/minute")
