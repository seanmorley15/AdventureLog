from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import requests
from geopy.distance import geodesic

class RecommendationsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    BASE_URL = "https://overpass-api.de/api/interpreter"
    HEADERS = {'User-Agent': 'AdventureLog Server'}

    def parse_google_places(self, places, origin):
        locations = []

        for place in places:
            location = place.get('location', {})
            types = place.get('types', [])
            
            # Updated for new API response structure
            formatted_address = place.get("formattedAddress") or place.get("shortFormattedAddress")
            display_name = place.get("displayName", {})
            name = display_name.get("text") if isinstance(display_name, dict) else display_name

            lat = location.get('latitude')
            lon = location.get('longitude')

            if not name or not lat or not lon:
                continue

            distance_km = geodesic(origin, (lat, lon)).km

            adventure = {
                "id": place.get('id'),
                "type": 'place',
                "name": name,
                "description": place.get('businessStatus', None),
                "latitude": lat,
                "longitude": lon,
                "address": formatted_address,
                "tag": types[0] if types else None,
                "distance_km": round(distance_km, 2),
            }

            locations.append(adventure)

        # Sort by distance ascending
        locations.sort(key=lambda x: x["distance_km"])

        return locations
    
    def parse_overpass_response(self, data, request):
        nodes = data.get('elements', [])
        locations = []
        all = request.query_params.get('all', False)

        origin = None
        try:
            origin = (
                float(request.query_params.get('lat')),
                float(request.query_params.get('lon'))
            )
        except(ValueError, TypeError):
            origin = None

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

            locations.append(adventure)

        # Sort by distance if available
        if origin:
            locations.sort(key=lambda x: x.get("distance_km") or float("inf"))

        return locations

    
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

        locations = self.parse_overpass_response(data, request)
        return Response(locations)

    def query_google_nearby(self, lat, lon, radius, category, request):
        """Query Google Places API (New) for nearby places"""
        api_key = settings.GOOGLE_MAPS_API_KEY
        
        # Updated to use new Places API endpoint
        url = "https://places.googleapis.com/v1/places:searchNearby"
        
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': 'places.displayName.text,places.formattedAddress,places.location,places.types,places.rating,places.userRatingCount,places.businessStatus,places.id'
        }
        
        # Map categories to place types for the new API
        type_mapping = {
            'lodging': 'lodging',
            'food': 'restaurant',
            'tourism': 'tourist_attraction',
        }
        
        payload = {
            "includedTypes": [type_mapping[category]],
            "maxResultCount": 20,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": float(lat),
                        "longitude": float(lon)
                    },
                    "radius": float(radius)
                }
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            places = data.get('places', [])
            origin = (float(lat), float(lon))
            locations = self.parse_google_places(places, origin)
            
            return Response(locations)
            
        except requests.exceptions.RequestException as e:
            print(f"Google Places API error: {e}")
            # Fallback to Overpass API
            return self.query_overpass(lat, lon, radius, category, request)
        except Exception as e:
            print(f"Unexpected error with Google Places API: {e}")
            # Fallback to Overpass API
            return self.query_overpass(lat, lon, radius, category, request)

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

        # Use the new Google Places API
        return self.query_google_nearby(lat, lon, radius, category, request)