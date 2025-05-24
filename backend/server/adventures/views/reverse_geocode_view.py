from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from worldtravel.models import Region, City, VisitedRegion, VisitedCity
from adventures.models import Adventure
from adventures.serializers import AdventureSerializer
import requests
from adventures.geocoding import reverse_geocode
from adventures.geocoding import extractIsoCode

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
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=jsonv2"
        headers = {'User-Agent': 'AdventureLog Server'}
        response = requests.get(url, headers=headers)
        try:
            data = response.json()
            parsed_results = []
            for item in data:
                parsed_results.append({
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                    "category": item.get("category"),
                    "type": item.get("type"),
                    "importance": item.get("importance"),
                    "addresstype": item.get("addresstype"),
                    "name": item.get("name"),
                    "display_name": item.get("display_name"),
                })
        except requests.exceptions.JSONDecodeError:
            return Response({"error": "Invalid response from geocoding service"}, status=400)
        return Response(parsed_results)

    @action(detail=False, methods=['post'])
    def mark_visited_region(self, request):
        # searches through all of the users adventures, if the serialized data is_visited, is true, runs reverse geocode on the adventures and if a region is found, marks it as visited. Use the extractIsoCode function to get the region
        new_region_count = 0
        new_regions = {}
        new_city_count = 0
        new_cities = {}
        adventures = Adventure.objects.filter(user_id=self.request.user)
        serializer = AdventureSerializer(adventures, many=True)
        for adventure, serialized_adventure in zip(adventures, serializer.data):
            if serialized_adventure['is_visited'] == True:
                lat = adventure.latitude
                lon = adventure.longitude
                if not lat or not lon:
                    continue
                url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}"
                headers = {'User-Agent': 'AdventureLog Server'}
                response = requests.get(url, headers=headers)
                try:
                    data = response.json()
                except requests.exceptions.JSONDecodeError:
                    return Response({"error": "Invalid response from geocoding service"}, status=400)
                extracted_region = extractIsoCode(self.request.user,data)
                if 'error' not in extracted_region:
                    region = Region.objects.filter(id=extracted_region['region_id']).first()
                    visited_region = VisitedRegion.objects.filter(region=region, user_id=self.request.user).first()
                    if not visited_region:
                        visited_region = VisitedRegion(region=region, user_id=self.request.user)
                        visited_region.save()
                        new_region_count += 1
                        new_regions[region.id] = region.name

                    if extracted_region['city_id'] is not None:
                        city = City.objects.filter(id=extracted_region['city_id']).first()
                        visited_city = VisitedCity.objects.filter(city=city, user_id=self.request.user).first()
                        if not visited_city:
                            visited_city = VisitedCity(city=city, user_id=self.request.user)
                            visited_city.save()
                            new_city_count += 1
                            new_cities[city.id] = city.name
        return Response({"new_regions": new_region_count, "regions": new_regions, "new_cities": new_city_count, "cities": new_cities})