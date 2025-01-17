from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import requests

class OverpassViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    BASE_URL = "https://overpass-api.de/api/interpreter"
    HEADERS = {'User-Agent': 'AdventureLog Server'}

    def make_overpass_query(self, query):
        """
        Sends a query to the Overpass API and returns the response data.
        Args:
            query (str): The Overpass QL query string.
        Returns:
            dict: Parsed JSON response from the Overpass API.
        Raises:
            Response: DRF Response object with an error message in case of failure.
        """
        url = f"{self.BASE_URL}?data={query}"
        try:
            response = requests.get(url, headers=self.HEADERS)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()
        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=500)
        except requests.exceptions.JSONDecodeError:
            return Response({"error": "Invalid response from Overpass API"}, status=400)
        
    def parse_overpass_response(self, data, request):
        """
        Parses the JSON response from the Overpass API and extracts relevant data,
        turning it into an adventure-structured object.

        Args:
            response (dict): The JSON response from the Overpass API.

        Returns:
            list: A list of adventure objects with structured data.
        """
        # Extract elements (nodes/ways/relations) from the response
        nodes = data.get('elements', [])
        adventures = []

        # include all entries, even the ones that do not have lat long
        all = request.query_params.get('all', False)

        for node in nodes:
            # Ensure we are working with a "node" type (can also handle "way" or "relation" if needed)
            if node.get('type') not in ['node', 'way', 'relation']:
                continue

            # Extract tags and general data
            tags = node.get('tags', {})
            adventure = {
                "id": node.get('id'),  # Include the unique OSM ID
                "type": node.get('type'),  # Type of element (node, way, relation)
                "name": tags.get('name', tags.get('official_name', '')),  # Fallback to 'official_name'
                "description": tags.get('description', None),  # Additional descriptive information
                "latitude": node.get('lat', None),  # Use None for consistency with missing values
                "longitude": node.get('lon', None),
                "address": {
                    "city": tags.get('addr:city', None),
                    "housenumber": tags.get('addr:housenumber', None),
                    "postcode": tags.get('addr:postcode', None),
                    "state": tags.get('addr:state', None),
                    "street": tags.get('addr:street', None),
                    "country": tags.get('addr:country', None),  # Add 'country' if available
                    "suburb": tags.get('addr:suburb', None),  # Add 'suburb' for more granularity
                },
                "feature_id": tags.get('gnis:feature_id', None),
                "tag": next((tags.get(key, None) for key in ['leisure', 'tourism', 'natural', 'historic', 'amenity'] if key in tags), None),
                "contact": {
                    "phone": tags.get('phone', None),
                    "email": tags.get('contact:email', None),
                    "website": tags.get('website', None),
                    "facebook": tags.get('contact:facebook', None),  # Social media links
                    "twitter": tags.get('contact:twitter', None),
                },
                # "tags": tags,  # Include all raw tags for future use
            }

            # Filter out adventures with no name, latitude, or longitude
            if (adventure["name"] and 
                adventure["latitude"] is not None and -90 <= adventure["latitude"] <= 90 and 
                adventure["longitude"] is not None and -180 <= adventure["longitude"] <= 180) or all:
                adventures.append(adventure)

        return adventures


    @action(detail=False, methods=['get'])
    def query(self, request):
        """
        Radius-based search for tourism-related locations around given coordinates.
        """
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        radius = request.query_params.get('radius', '1000')  # Default radius: 1000 meters

        valid_categories = ['lodging', 'food', 'tourism']
        category = request.query_params.get('category', 'all')
        if category not in valid_categories:
            return Response({"error": f"Invalid category. Valid categories: {', '.join(valid_categories)}"}, status=400)

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
        if category == 'lodging':
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
        if category == 'food':
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

        # Validate required parameters
        if not lat or not lon:
            return Response(
                {"error": "Latitude and longitude parameters are required."}, status=400
            )

        data = self.make_overpass_query(query)
        adventures = self.parse_overpass_response(data, request)
        return Response(adventures)

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Name-based search for nodes with the specified name.
        """
        name = request.query_params.get('name')

        # Validate required parameter
        if not name:
            return Response({"error": "Name parameter is required."}, status=400)

        # Construct Overpass API query
        query = f'[out:json];node["name"~"{name}",i];out;'
        data = self.make_overpass_query(query)

        adventures = self.parse_overpass_response(data, request)
        return Response(adventures)
