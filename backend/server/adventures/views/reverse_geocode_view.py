from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from worldtravel.models import Region, City, VisitedRegion, VisitedCity
from adventures.models import Location, Lodging, Transportation
from adventures.serializers import LocationSerializer
from adventures.geocoding import reverse_geocode
from django.conf import settings
from django.db.models import Q
from adventures.geocoding import search_google, search_osm

SEARCH_MODE_SUFFIXES = {
    'airport': ' Airport',
    'train': ' Station',
    'bus': ' Bus Station',
    'location': '',
    'cab': '',
    'vtc': '',
}

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
                # Google returned error dict - fallback to OSM
                if isinstance(results, dict):
                    results = search_osm(query)
            else:
                results = search_osm(query)
            # Final check: if still an error dict, return it as error
            if isinstance(results, dict):
                return Response(results, status=500)
            return Response(results)
        except Exception:
            return Response({"error": "An internal error occurred while processing the request"}, status=500)

    @action(detail=False, methods=['get'])
    def unified_search(self, request):
        """
        Unified search endpoint that combines:
        1. Geocoding results (addresses from Google Maps/OSM)
        2. User's own locations
        3. User's own lodgings
        4. User's transportation departures and arrivals

        The search_mode parameter controls suffix appended to geocoding queries
        (e.g., 'airport' appends ' Airport') without affecting internal entity queries.

        Returns grouped results by source type for intelligent autocomplete.
        """
        query = request.query_params.get('query', '')
        search_mode = request.query_params.get('search_mode', 'location')
        include_geocode = request.query_params.get('include_geocode', 'true').lower() == 'true'
        include_locations = request.query_params.get('include_locations', 'true').lower() == 'true'
        include_lodging = request.query_params.get('include_lodging', 'true').lower() == 'true'
        include_transportation = request.query_params.get('include_transportation', 'true').lower() == 'true'

        if not query or len(query) < 2:
            return Response({"error": "Query parameter must be at least 2 characters"}, status=400)

        results = {
            "addresses": [],
            "locations": [],
            "lodging": [],
            "departures": [],
            "arrivals": []
        }

        # Search user's locations (raw query, no suffix)
        if include_locations:
            locations = Location.objects.filter(
                Q(user=self.request.user) | Q(is_public=True),
                Q(name__icontains=query) | Q(location__icontains=query)
            ).exclude(
                latitude__isnull=True
            ).exclude(
                longitude__isnull=True
            ).order_by('-updated_at')[:10]

            results["locations"] = [
                {
                    "id": str(loc.id),
                    "name": loc.name,
                    "display_name": loc.location or loc.name,
                    "lat": float(loc.latitude),
                    "lon": float(loc.longitude),
                    "type": "location",
                    "category": loc.category.name if loc.category else None,
                    "source": "location"
                }
                for loc in locations
            ]

        # Search user's lodging (raw query, no suffix)
        if include_lodging:
            lodging = Lodging.objects.filter(
                Q(user=self.request.user) | Q(is_public=True),
                Q(name__icontains=query) | Q(location__icontains=query)
            ).exclude(
                latitude__isnull=True
            ).exclude(
                longitude__isnull=True
            ).order_by('-updated_at')[:10]

            results["lodging"] = [
                {
                    "id": str(ldg.id),
                    "name": ldg.name,
                    "display_name": ldg.location or ldg.name,
                    "lat": float(ldg.latitude),
                    "lon": float(ldg.longitude),
                    "type": ldg.type,
                    "category": "lodging",
                    "source": "lodging"
                }
                for ldg in lodging
            ]

        # Search user's transportation departures and arrivals (raw query, no suffix)
        if include_transportation:
            # Search departures (from_location)
            departures = Transportation.objects.filter(
                Q(user=self.request.user) | Q(is_public=True),
                Q(from_location__icontains=query) | Q(name__icontains=query)
            ).exclude(
                origin_latitude__isnull=True
            ).exclude(
                origin_longitude__isnull=True
            ).order_by('-updated_at')[:10]

            # Use a set to deduplicate by coordinates
            seen_departures = set()
            for t in departures:
                key = (float(t.origin_latitude), float(t.origin_longitude))
                if key not in seen_departures:
                    seen_departures.add(key)
                    results["departures"].append({
                        "id": str(t.id),
                        "name": t.from_location or t.name,
                        "display_name": t.from_location or t.name,
                        "lat": float(t.origin_latitude),
                        "lon": float(t.origin_longitude),
                        "type": t.type,
                        "category": "departure",
                        "source": "departure",
                        "code": t.start_code or None
                    })

            # Search arrivals (to_location)
            arrivals = Transportation.objects.filter(
                Q(user=self.request.user) | Q(is_public=True),
                Q(to_location__icontains=query) | Q(name__icontains=query)
            ).exclude(
                destination_latitude__isnull=True
            ).exclude(
                destination_longitude__isnull=True
            ).order_by('-updated_at')[:10]

            # Use a set to deduplicate by coordinates
            seen_arrivals = set()
            for t in arrivals:
                key = (float(t.destination_latitude), float(t.destination_longitude))
                if key not in seen_arrivals:
                    seen_arrivals.add(key)
                    results["arrivals"].append({
                        "id": str(t.id),
                        "name": t.to_location or t.name,
                        "display_name": t.to_location or t.name,
                        "lat": float(t.destination_latitude),
                        "lon": float(t.destination_longitude),
                        "type": t.type,
                        "category": "arrival",
                        "source": "arrival",
                        "code": t.end_code or None
                    })

        # Search addresses via geocoding (suffix applied here only)
        if include_geocode:
            try:
                geocode_query = query + SEARCH_MODE_SUFFIXES.get(search_mode, '')
                geocode_results = None

                if getattr(settings, 'GOOGLE_MAPS_API_KEY', None):
                    geocode_results = search_google(geocode_query)
                    # Google returned error dict - fallback to OSM
                    if isinstance(geocode_results, dict):
                        geocode_results = search_osm(geocode_query)
                else:
                    geocode_results = search_osm(geocode_query)

                if isinstance(geocode_results, list):
                    results["addresses"] = [
                        {
                            **r,
                            "source": "address"
                        }
                        for r in geocode_results[:10]
                    ]
            except Exception:
                # Geocoding failed, but we can still return internal results
                pass

        return Response(results)

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