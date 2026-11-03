from core.throttling import ConditionalUserRateThrottle


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
