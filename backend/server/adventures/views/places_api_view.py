from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adventures.services.places.search import search_places
from adventures.services.places.details import get_place_details
from adventures.services.geocoding.reverse import reverse_geocode
from adventures.throttling import ExternalGeocodeThrottle


class PlacesAPI(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], throttle_classes=[ExternalGeocodeThrottle])
    def search(self, request):
        query = request.query_params.get("query", "").strip()
        if not query:
            return Response({"error": "Query parameter is required"}, status=400)

        include_meta = request.query_params.get("include_meta", "").lower() in {"1", "true", "yes"}
        try:
            selection = search_places(query)
            if selection.error:
                if include_meta:
                    return Response({
                        "provider_used": selection.provider_used,
                        "providers_attempted": selection.providers_attempted,
                        "results": [],
                        "error": selection.error,
                    })
                return Response([])

            if include_meta:
                return Response({
                    "provider_used": selection.provider_used,
                    "providers_attempted": selection.providers_attempted,
                    "results": selection.results,
                })
            return Response(selection.results)
        except Exception:
            return Response({"error": "Internal error"}, status=500)

    @action(detail=False, methods=["get"])
    def place_details(self, request):
        place_id = request.query_params.get("place_id", "").strip()
        if not place_id:
            return Response({"error": "place_id parameter is required"}, status=400)

        name = request.query_params.get("name", "")
        language = request.query_params.get("language", "en")

        details = get_place_details(place_id, fallback_query=name, language=language)
        if isinstance(details, dict) and details.get("error"):
            return Response(details, status=502)
        return Response(details)

    @action(detail=False, methods=["get"], throttle_classes=[ExternalGeocodeThrottle])
    def reverse(self, request):
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        if not lat or not lon:
            return Response({"error": "Latitude and longitude are required"}, status=400)
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            return Response({"error": "Invalid latitude or longitude"}, status=400)

        selection = reverse_geocode(lat, lon, request.user)
        data = selection.data if hasattr(selection, "data") else selection
        if isinstance(data, dict) and data.get("error"):
            return Response({"error": "An internal error occurred while processing the request"}, status=400)
        return Response(data)
