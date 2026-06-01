from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from worldtravel.models import Region, City, VisitedRegion, VisitedCity
from adventures.models import Location
from adventures.serializers import LocationSerializer
from adventures.geocoding import reverse_geocode
from django.conf import settings
from adventures.geocoding import search_google, search_osm, get_place_details

class ReverseGeocodeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
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
        data = reverse_geocode(lat, lon, self.request.user)
        if 'error' in data:
            return Response({"error": "An internal error occurred while processing the request"}, status=400)
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('query', '')
        if not query:
            return Response({"error": "Query parameter is required"}, status=400)

        try:
            if getattr(settings, 'GOOGLE_MAPS_API_KEY', None):
                results = search_google(query)
            else:
                results = search_osm(query)
            return Response(results)
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
        
        # Get existing visited regions for this user
        existing_visited_regions = set(
            VisitedRegion.objects.filter(
                user=self.request.user,
                region_id__in=regions_to_mark
            ).values_list('region_id', flat=True)
        )
        
        # Create new VisitedRegion entries
        new_visited_regions = []
        for region_id in regions_to_mark:
            if region_id not in existing_visited_regions:
                new_visited_regions.append(
                    VisitedRegion(region_id=region_id, user=self.request.user)
                )
        
        if new_visited_regions:
            VisitedRegion.objects.bulk_create(new_visited_regions)
            new_region_count = len(new_visited_regions)
            # Get region names for response
            regions = Region.objects.filter(
                id__in=[vr.region_id for vr in new_visited_regions]
            )
            new_regions = {r.id: r.name for r in regions}
        
        # Get existing visited cities for this user
        existing_visited_cities = set(
            VisitedCity.objects.filter(
                user=self.request.user,
                city_id__in=cities_to_mark
            ).values_list('city_id', flat=True)
        )
        
        # Create new VisitedCity entries
        new_visited_cities = []
        for city_id in cities_to_mark:
            if city_id not in existing_visited_cities:
                new_visited_cities.append(
                    VisitedCity(city_id=city_id, user=self.request.user)
                )
        
        if new_visited_cities:
            VisitedCity.objects.bulk_create(new_visited_cities)
            new_city_count = len(new_visited_cities)
            # Get city names for response
            cities = City.objects.filter(
                id__in=[vc.city_id for vc in new_visited_cities]
            )
            new_cities = {c.id: c.name for c in cities}
        
        return Response({
            "new_regions": new_region_count,
            "regions": new_regions,
            "new_cities": new_city_count,
            "cities": new_cities
        })

    @action(detail=False, methods=['get'])
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