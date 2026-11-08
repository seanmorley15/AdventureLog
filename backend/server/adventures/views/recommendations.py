"""Places worth visiting near a point, from Google and OpenStreetMap."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.response import Response

from adventures.serializers.places import RecommendationQuerySerializer, RecommendationResponseSerializer
from adventures.services.places.search import search_places
from adventures.services.recommendations.search import get_recommendations
from adventures.throttling import ExternalRecommendationsThrottle
from adventures.utils.language import resolve_request_language
from core.exceptions import APIError
from core.serializers import validated


class RecommendationsViewSet(viewsets.ViewSet):
    openapi_tags = ['Places']
    throttle_classes = [ExternalRecommendationsThrottle]
    list_returns_object = True

    @extend_schema(
        parameters=[RecommendationQuerySerializer],
        responses={
            200: RecommendationResponseSerializer,
            400: OpenApiResponse(description='Invalid input, or `location` could not be found (`location_not_found`).'),
            503: OpenApiResponse(description='No source could be reached (`upstream_error`) or Google was asked for but is not configured (`not_configured`).'),
        },
    )
    def list(self, request):
        """
        Find recommendations nearby

        Places to see, eat, drink or stay within `radius` meters of a point, ranked by quality and
        distance. Google results are topped up with OpenStreetMap when Google finds few places, and
        the same place from both is merged. Give the point as `lat` and `lon`, or as a `location`
        name to look up first.
        """
        params = validated(RecommendationQuerySerializer, request.query_params)
        lang = resolve_request_language(request)
        lat, lon = params.get('lat'), params.get('lon')
        if lat is None or lon is None:
            selection = search_places(params['location'], language=lang)
            best = selection.results[0] if selection and not selection.error and selection.results else None
            lat = best.get('lat', best.get('latitude')) if best else None
            lon = best.get('lon', best.get('longitude')) if best else None
            if lat is None or lon is None:
                raise APIError('That location could not be found.', code='location_not_found')

        result = get_recommendations(
            lat=float(lat),
            lon=float(lon),
            radius=params['radius'],
            category=params['category'],
            sources=params['sources'],
            limit=params['limit'],
            lang=lang,
        )
        return Response(RecommendationResponseSerializer(result).data)
