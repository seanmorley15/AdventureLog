from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from worldtravel.models import Region, City
from worldtravel.services import mark_cities_visited, mark_regions_visited
from adventures.models import Location
from adventures.services.geocoding.reverse import reverse_geocode as reverse_geocode_service
from adventures.services.places.details import get_place_details
from adventures.services.places.search import search_places
from adventures.throttling import ExternalGeocodeThrottle

class ReverseGeocodeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], throttle_classes=[ExternalGeocodeThrottle])
    def reverse_geocode(self, request):
        lat = request.query_params.get('lat', '')
        lon = request.query_params.get('lon', '')
        if not lat or not lon:
            return Response({"error": "Latitude and longitude are required"}, status=400)
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            return Response({"error": "Invalid latitude or longitude"}, status=400)
        selection = reverse_geocode_service(lat, lon, self.request.user)
        data = selection.data
        if 'error' in data:
            return Response({"error": "An internal error occurred while processing the request"}, status=400)
        return Response(data)
    
    @action(detail=False, methods=['get'], throttle_classes=[ExternalGeocodeThrottle])
    def search(self, request):
        query = request.query_params.get('query', '')
        if not query:
            return Response({"error": "Query parameter is required"}, status=400)

        include_meta = request.query_params.get('include_meta', '').lower() in {'1', 'true', 'yes'}

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
            return Response({"error": "An internal error occurred while processing the request"}, status=500)

    @action(detail=False, methods=['post'])
    def mark_visited_region(self, request):
        """
        Marks regions and cities as visited based on user's visited locations.
        Uses the pre-stored region/city data on locations to avoid expensive reverse geocoding.
        """
        new_region_count = 0
        new_regions = {}
        new_city_count = 0
        new_cities = {}
        
        # Get all visited locations with their region and city data
        visited_locations = Location.objects.filter(
            user=self.request.user
        ).select_related('region', 'city')
        
        # Track unique regions and cities to create VisitedRegion/VisitedCity entries
        regions_to_mark = set()
        cities_to_mark = set()
        
        for location in visited_locations:
            # Only process locations that are marked as visited
            if not location.is_visited_status():
                continue
            
            # Collect regions
            if location.region:
                regions_to_mark.add(location.region.id)
            
            # Collect cities
            if location.city:
                cities_to_mark.add(location.city.id)
        
        new_region_ids = mark_regions_visited(self.request.user.id, regions_to_mark)
        new_region_count = len(new_region_ids)
        if new_region_ids:
            new_regions = {r.id: r.name for r in Region.objects.filter(id__in=new_region_ids)}

        new_city_ids = mark_cities_visited(self.request.user.id, cities_to_mark)
        new_city_count = len(new_city_ids)
        if new_city_ids:
            new_cities = {c.id: c.name for c in City.objects.filter(id__in=new_city_ids)}

        return Response({
            "new_regions": new_region_count,
            "regions": new_regions,
            "new_cities": new_city_count,
            "cities": new_cities
        })

    @action(detail=False, methods=['get'], throttle_classes=[ExternalGeocodeThrottle])
    def place_details(self, request):
        place_id = request.query_params.get('place_id', '').strip()
        if not place_id:
            return Response({"error": "place_id parameter is required"}, status=400)

        name = request.query_params.get('name', '')
        language = request.query_params.get('language', 'en')

        details = get_place_details(place_id, fallback_query=name, language=language)
        if 'error' in details and not details.get('description'):
            return Response(details, status=502)
        return Response(details)