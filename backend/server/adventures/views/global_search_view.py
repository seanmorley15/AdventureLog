from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.contrib.postgres.search import SearchVector, SearchQuery
from adventures.models import Location, Collection
from adventures.serializers import LocationSerializer, CollectionSerializer
from worldtravel.models import Country, Region, City, VisitedCity, VisitedRegion
from worldtravel.serializers import CountrySerializer, RegionSerializer, CitySerializer, VisitedCitySerializer, VisitedRegionSerializer
from users.models import CustomUser as User
from users.serializers import CustomUserDetailsSerializer as UserSerializer

class GlobalSearchView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        search_term = request.query_params.get('query', '').strip()
        if not search_term:
            return Response({"error": "Search query is required"}, status=400)

        # Initialize empty results
        results = {
            "locations": [],
            "collections": [],
            "users": [],
            "countries": [],
            "regions": [],
            "cities": [],
            "visited_regions": [],
            "visited_cities": []
        }

        # Locations: Full-Text Search
        locations = Location.objects.annotate(
            search=SearchVector('name', 'description', 'location')
        ).filter(search=SearchQuery(search_term), user=request.user)
        results["locations"] = LocationSerializer(locations, many=True).data

        # Collections: Partial Match Search
        collections = Collection.objects.filter(
            Q(name__icontains=search_term) & Q(user=request.user)
        )
        results["collections"] = CollectionSerializer(collections, many=True).data

        # Users: Public Profiles Only
        users = User.objects.filter(
            (Q(username__icontains=search_term) |
             Q(first_name__icontains=search_term) |
             Q(last_name__icontains=search_term)) & Q(public_profile=True)
        )
        results["users"] = UserSerializer(users, many=True).data

        # Countries: Full-Text Search
        countries = Country.objects.annotate(
            search=SearchVector('name', 'country_code')
        ).filter(search=SearchQuery(search_term))
        results["countries"] = CountrySerializer(countries, many=True).data

        # Regions and Cities: Partial Match Search
        regions = Region.objects.filter(Q(name__icontains=search_term))
        results["regions"] = RegionSerializer(regions, many=True).data

        cities = City.objects.filter(Q(name__icontains=search_term))
        results["cities"] = CitySerializer(cities, many=True).data

        # Visited Regions and Cities
        visited_regions = VisitedRegion.objects.filter(user=request.user)
        results["visited_regions"] = VisitedRegionSerializer(visited_regions, many=True).data

        visited_cities = VisitedCity.objects.filter(user=request.user)
        results["visited_cities"] = VisitedCitySerializer(visited_cities, many=True).data

        return Response(results)
