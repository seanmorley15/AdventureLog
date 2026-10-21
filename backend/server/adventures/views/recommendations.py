"""Places worth visiting near a point, from Google and OpenStreetMap."""

import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from adventures.serializers.places import RecommendationQuerySerializer, RecommendationResponseSerializer
from adventures.services.places.search import search_places
from adventures.services.recommendations.search import get_recommendations
from adventures.throttling import ExternalRecommendationsThrottle
from core.exceptions import APIError
from core.serializers import validated

logger = logging.getLogger(__name__)


class RecommendationsViewSet(viewsets.ViewSet):
    openapi_tags = ['Places']
    throttle_classes = [ExternalRecommendationsThrottle]

    @extend_schema(
        parameters=[RecommendationQuerySerializer],
        responses={
            200: RecommendationResponseSerializer,
            400: OpenApiResponse(description='Invalid input, or `location` could not be found (`location_not_found`).'),
            503: OpenApiResponse(description='Only OpenStreetMap was asked for and it is unavailable.'),
        },
    )
    def list(self, request):
        """
        Find recommendations nearby

        Places to stay (`lodging`), eat (`food`) or see (`tourism`) within `radius` meters of a
        point, ranked by quality and distance and de-duplicated across providers. Give the point
        as `lat` and `lon`, or as a `location` name to look up first.
        """
        params = validated(RecommendationQuerySerializer, request.query_params)
        lat, lon = params.get('lat'), params.get('lon')
        if lat is None or lon is None:
            selection = search_places(params['location'])
            best = selection.results[0] if selection and not selection.error and selection.results else None
            lat = best and (best.get('lat') or best.get('latitude'))
            lon = best and (best.get('lon') or best.get('longitude'))
            if lat is None or lon is None:
                raise APIError('That location could not be found.', code='location_not_found')

        result = get_recommendations(
            lat=float(lat), lon=float(lon), radius=params['radius'], category=params['category'],
            sources=params['sources'],
        )
        if params['sources'] == 'osm' and result.get('count', 0) == 0 and result.get('warnings'):
            raise APIError(
                'OpenStreetMap is temporarily unavailable. Please try again later.',
                code='upstream_unavailable',
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(result)
