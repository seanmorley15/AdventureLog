from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from worldtravel.models import Region, City, VisitedRegion, VisitedCity
from adventures.models import Adventure
from adventures.serializers import AdventureSerializer
import requests

class ReverseGeocodeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def extractIsoCode(self, data):
        """
        Extract the ISO code from the response data.
        Returns a dictionary containing the region name, country name, and ISO code if found.
        """
        iso_code = None
        town_city_or_county = None
        display_name = None
        country_code = None
        city = None
        visited_city = None

        # town = None
        # city = None
        # county = None
        
        if 'address' in data.keys():
            keys = data['address'].keys()
            for key in keys:
                if key.find("ISO") != -1:
                    iso_code = data['address'][key]
            if 'town' in keys:
                town_city_or_county = data['address']['town']
            if 'county' in keys:
                town_city_or_county = data['address']['county']
            if 'city' in keys:
                town_city_or_county = data['address']['city']
        if not iso_code:
            return {"error": "No region found"}
        
        region = Region.objects.filter(id=iso_code).first()
        visited_region = VisitedRegion.objects.filter(region=region, user_id=self.request.user).first()
        
        region_visited = False
        city_visited = False
        country_code = iso_code[:2]
        
        if region:
            if town_city_or_county:
                display_name = f"{town_city_or_county}, {region.name}, {country_code}"
                city = City.objects.filter(name__contains=town_city_or_county, region=region).first()
                visited_city = VisitedCity.objects.filter(city=city, user_id=self.request.user).first()

        if visited_region:
            region_visited = True
        if visited_city:
            city_visited = True
        if region:
            return {"region_id": iso_code, "region": region.name, "country": region.country.name, "region_visited": region_visited, "display_name": display_name, "city": city.name if city else None, "city_id": city.id if city else None, "city_visited": city_visited}
        return {"error": "No region found"}

    @action(detail=False, methods=['get'])
    def reverse_geocode(self, request):
        lat = request.query_params.get('lat', '')
        lon = request.query_params.get('lon', '')
        url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}"
        headers = {'User-Agent': 'AdventureLog Server'}
        response = requests.get(url, headers=headers)
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            return Response({"error": "Invalid response from geocoding service"}, status=400)
        return Response(self.extractIsoCode(data))

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
                extracted_region = self.extractIsoCode(data)
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