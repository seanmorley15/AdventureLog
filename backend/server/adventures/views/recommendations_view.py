from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import requests
from geopy.distance import geodesic
import time


class RecommendationsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    BASE_URL = "https://overpass-api.de/api/interpreter"
    HEADERS = {'User-Agent': 'AdventureLog Server'}

    def parse_google_places(self, places, origin):
        adventures = []

        for place in places:
            location = place.get('geometry', {}).get('location', {})
            types = place.get('types', [])
            formatted_address = place.get("vicinity") or place.get("formatted_address") or place.get("name")

            lat = location.get('lat')
            lon = location.get('lng')

            if not place.get("name") or not lat or not lon:
                continue

            distance_km = geodesic(origin, (lat, lon)).km

            adventure = {
                "id": place.get('place_id'),
                "type": 'place',
                "name": place.get('name', ''),
                "description": place.get('business_status', None),
                "latitude": lat,
                "longitude": lon,
                "address": formatted_address,
                "tag": types[0] if types else None,
                "distance_km": round(distance_km, 2),  # Optional: include in response
            }

            adventures.append(adventure)

        # Sort by distance ascending
        adventures.sort(key=lambda x: x["distance_km"])

        return adventures
    
    def parse_overpass_response(self, data, request):
        nodes = data.get('elements', [])
        adventures = []
        all = request.query_params.get('all', False)

        origin = None
        try:
            origin = (
                float(request.query_params.get('lat')),
                float(request.query_params.get('lon'))
            )
        except:
            pass

        for node in nodes:
            if node.get('type') not in ['node', 'way', 'relation']:
                continue

            tags = node.get('tags', {})
            lat = node.get('lat')
            lon = node.get('lon')
            name = tags.get('name', tags.get('official_name', ''))

            if not name or lat is None or lon is None:
                if not all:
                    continue

            # Flatten address
            address_parts = [tags.get(f'addr:{k}') for k in ['housenumber', 'street', 'suburb', 'city', 'state', 'postcode', 'country']]
            formatted_address = ", ".join(filter(None, address_parts)) or name

            # Calculate distance if possible
            distance_km = None
            if origin:
                distance_km = round(geodesic(origin, (lat, lon)).km, 2)

            # Unified format
            adventure = {
                "id": f"osm:{node.get('id')}",
                "type": "place",
                "name": name,
                "description": tags.get('description'),
                "latitude": lat,
                "longitude": lon,
                "address": formatted_address,
                "tag": next((tags.get(key) for key in ['leisure', 'tourism', 'natural', 'historic', 'amenity'] if key in tags), None),
                "distance_km": distance_km,
                "powered_by": "osm"
            }

            adventures.append(adventure)

        # Sort by distance if available
        if origin:
            adventures.sort(key=lambda x: x.get("distance_km") or float("inf"))

        return adventures

    
    def query_overpass(self, lat, lon, radius, category, request):
        if category == 'tourism':
            query = f"""
                [out:json];
                (
                node(around:{radius},{lat},{lon})["tourism"];
                node(around:{radius},{lat},{lon})["leisure"];
                node(around:{radius},{lat},{lon})["historic"];
                node(around:{radius},{lat},{lon})["sport"];
                node(around:{radius},{lat},{lon})["natural"];
                node(around:{radius},{lat},{lon})["attraction"];
                node(around:{radius},{lat},{lon})["museum"];
                node(around:{radius},{lat},{lon})["zoo"];
                node(around:{radius},{lat},{lon})["aquarium"];
                );
                out;
                """
        elif category == 'lodging':
            query = f"""
                [out:json];
                (
                node(around:{radius},{lat},{lon})["tourism"="hotel"];
                node(around:{radius},{lat},{lon})["tourism"="motel"];
                node(around:{radius},{lat},{lon})["tourism"="guest_house"];
                node(around:{radius},{lat},{lon})["tourism"="hostel"];
                node(around:{radius},{lat},{lon})["tourism"="camp_site"];
                node(around:{radius},{lat},{lon})["tourism"="caravan_site"];
                node(around:{radius},{lat},{lon})["tourism"="chalet"];
                node(around:{radius},{lat},{lon})["tourism"="alpine_hut"];
                node(around:{radius},{lat},{lon})["tourism"="apartment"];
                );
                out;
                """
        elif category == 'food':
            query = f"""
                [out:json];
                (
                node(around:{radius},{lat},{lon})["amenity"="restaurant"];
                node(around:{radius},{lat},{lon})["amenity"="cafe"];
                node(around:{radius},{lat},{lon})["amenity"="fast_food"];
                node(around:{radius},{lat},{lon})["amenity"="pub"];
                node(around:{radius},{lat},{lon})["amenity"="bar"];
                node(around:{radius},{lat},{lon})["amenity"="food_court"];
                node(around:{radius},{lat},{lon})["amenity"="ice_cream"];
                node(around:{radius},{lat},{lon})["amenity"="bakery"];
                node(around:{radius},{lat},{lon})["amenity"="confectionery"];
                );
                out;
                """
        else:
            return Response({"error": "Invalid category."}, status=400)

        overpass_url = f"{self.BASE_URL}?data={query}"
        try:
            response = requests.get(overpass_url, headers=self.HEADERS)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print("Overpass API error:", e)
            return Response({"error": "Failed to retrieve data from Overpass API."}, status=500)

        adventures = self.parse_overpass_response(data, request)
        return Response(adventures)



    @action(detail=False, methods=['get'])
    def query(self, request):
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        radius = request.query_params.get('radius', '1000')
        category = request.query_params.get('category', 'all')

        if not lat or not lon:
            return Response({"error": "Latitude and longitude parameters are required."}, status=400)

        valid_categories = {
            'lodging': 'lodging',
            'food': 'restaurant',
            'tourism': 'tourist_attraction',
        }

        if category not in valid_categories:
            return Response({"error": f"Invalid category. Valid categories: {', '.join(valid_categories)}"}, status=400)

        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)

        # Fallback to Overpass if no API key configured
        if not api_key:
            return self.query_overpass(lat, lon, radius, category, request)

        base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': f"{lat},{lon}",
            'radius': radius,
            'type': valid_categories[category],
            'key': api_key
        }

        all_places = []
        page_token = None

        try:
            for _ in range(3):  # Max 3 pages
                if page_token:
                    params['pagetoken'] = page_token
                    time.sleep(2.5)

                response = requests.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
                all_places.extend(data.get('results', []))
                page_token = data.get('next_page_token')
                if not page_token:
                    break

            origin = (float(lat), float(lon))
            adventures = self.parse_google_places(all_places, origin)
            return Response(adventures)

        except Exception as e:
            print("Google Places API failed, falling back to Overpass:", e)
            return self.query_overpass(lat, lon, radius, category, request)
