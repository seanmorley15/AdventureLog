from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import logging

from adventures.services.places.search import search_places as search_places_service
from adventures.services.recommendations.search import get_recommendations
from adventures.throttling import ExternalRecommendationsThrottle

logger = logging.getLogger(__name__)


class RecommendationsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], throttle_classes=[ExternalRecommendationsThrottle])
    def query(self, request):
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        location_param = request.query_params.get('location')
        radius = request.query_params.get('radius', '5000')
        category = request.query_params.get('category')
        sources = request.query_params.get('sources', 'both').lower()

        # If lat/lon not provided, attempt provider-based free-text geocoding
        if (not lat or not lon) and location_param:
            try:
                selection = search_places_service(location_param)
                if selection and not selection.error and selection.results:
                    best = selection.results[0]
                    lat = best.get('lat') or best.get('latitude')
                    lon = best.get('lon') or best.get('longitude')
                    location_param = best.get('display_name') or best.get('name') or location_param
                else:
                    return Response({"error": "Could not geocode provided location."}, status=400)
            except Exception:
                logger.warning("Provider-based geocoding failed")
                return Response({"error": "Geocoding failed. Please try a different location."}, status=400)

        if not lat or not lon:
            return Response({"error": "Latitude and longitude parameters are required (or provide a 'location' parameter to geocode)."}, status=400)

        try:
            lat = float(lat)
            lon = float(lon)
            radius = min(float(radius), 50000)
        except ValueError:
            return Response({"error": "Invalid latitude, longitude, or radius value."}, status=400)

        valid_categories = ['lodging', 'food', 'tourism']
        if category not in valid_categories:
            return Response({"error": f"Invalid category. Valid categories: {', '.join(valid_categories)}"}, status=400)

        valid_sources = ['google', 'osm', 'both']
        if sources not in valid_sources:
            return Response({"error": f"Invalid sources. Valid options: {', '.join(valid_sources)}"}, status=400)

        result = get_recommendations(lat=lat, lon=lon, radius=radius, category=category, sources=sources)

        # If OSM-only requested and provider returned a warning, surface a 503 when empty
        if sources == 'osm' and result.get('count', 0) == 0 and result.get('warnings'):
            return Response({"error": "OpenStreetMap service temporarily unavailable. Please try again later.", "count": 0, "results": [], "sources_used": result.get('sources_used')}, status=503)

        return Response(result)