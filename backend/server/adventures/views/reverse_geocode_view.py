from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from worldtravel.models import Region, City, VisitedRegion, VisitedCity
from adventures.models import Location
from adventures.serializers import LocationSerializer
from adventures.geocoding import reverse_geocode
from django.conf import settings
from adventures.geocoding import search_google, search_osm

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
        # searches through all of the users locations, if the serialized data is_visited, is true, runs reverse geocode on the locations and if a region is found, marks it as visited. Use the extractIsoCode function to get the region
        new_region_count = 0
        new_regions = {}
        new_city_count = 0
        new_cities = {}
        locations = Location.objects.filter(user=self.request.user)
        serializer = LocationSerializer(locations, many=True)
        for adventure, serialized_adventure in zip(locations, serializer.data):
            if serialized_adventure['is_visited'] == True:
                lat = adventure.latitude
                lon = adventure.longitude
                if not lat or not lon:
                    continue

                # Use the existing reverse_geocode function which handles both Google and OSM
                data = reverse_geocode(lat, lon, self.request.user)
                if 'error' in data:
                    continue

                # data already contains region_id and city_id
                if 'region_id' in data and data['region_id'] is not None:
                    region = Region.objects.filter(id=data['region_id']).first()
                    visited_region = VisitedRegion.objects.filter(region=region, user=self.request.user).first()
                    if not visited_region:
                        visited_region = VisitedRegion(region=region, user=self.request.user)
                        visited_region.save()
                        new_region_count += 1
                        new_regions[region.id] = region.name

                if 'city_id' in data and data['city_id'] is not None:
                    city = City.objects.filter(id=data['city_id']).first()
                    visited_city = VisitedCity.objects.filter(city=city, user=self.request.user).first()
                    if not visited_city:
                        visited_city = VisitedCity(city=city, user=self.request.user)
                        visited_city.save()
                        new_city_count += 1
                        new_cities[city.id] = city.name
        return Response({"new_regions": new_region_count, "regions": new_regions, "new_cities": new_city_count, "cities": new_cities})