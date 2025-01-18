
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from adventures.models import Adventure, Collection
from adventures.serializers import AdventureSerializer, CollectionSerializer
from django.db.models import Q
from adventures.utils import pagination
from worldtravel.models import Country, Region, City
from worldtravel.serializers import CountrySerializer, RegionSerializer, CitySerializer
from users.models import CustomUser as User
from users.serializers import CustomUserDetailsSerializer as UserSerializer

class GlobalSearchView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = pagination.StandardResultsSetPagination

    def list(self, request):
        search_term = request.query_params.get('query', '')
        # print(f"Searching for: {search_term}")  # For debugging

        if not search_term:
            return Response({"error": "Search query is required"}, status=400)

        # Search for adventures
        adventures = Adventure.objects.filter(
            (Q(name__icontains=search_term) | Q(description__icontains=search_term) | Q(location__icontains=search_term)) & Q(user_id=request.user.id)
        )

        # Search for collections
        collections = Collection.objects.filter(
            Q(name__icontains=search_term) & Q(user_id=request.user.id)
        )

        # Search for users
        users = User.objects.filter(
            (Q(username__icontains=search_term) | Q(first_name__icontains=search_term) | Q(last_name__icontains=search_term)) & Q(public_profile=True)
        )

        # Search for countries
        countries = Country.objects.filter(
            Q(name__icontains=search_term) | Q(country_code__icontains=search_term)
        )

        # Search for regions
        regions = Region.objects.filter(
            Q(name__icontains=search_term) | Q(country__name__icontains=search_term)
        )

        # Search for cities
        cities = City.objects.filter(
            Q(name__icontains=search_term) | Q(region__name__icontains=search_term) | Q(region__country__name__icontains=search_term)
        )

        # Serialize the results
        adventure_serializer = AdventureSerializer(adventures, many=True)
        collection_serializer = CollectionSerializer(collections, many=True)
        user_serializer = UserSerializer(users, many=True)
        country_serializer = CountrySerializer(countries, many=True)
        region_serializer = RegionSerializer(regions, many=True)
        city_serializer = CitySerializer(cities, many=True)

        return Response({
            "adventures": adventure_serializer.data,
            "collections": collection_serializer.data,
            "users": user_serializer.data,
            "countries": country_serializer.data,
            "regions": region_serializer.data,
            "cities": city_serializer.data
        })
        