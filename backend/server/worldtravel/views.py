from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from .models import Country, Region, VisitedRegion, City, VisitedCity
from .services import mark_regions_visited
from .serializers import CitySerializer, CountrySerializer, RegionSerializer, VisitedRegionSerializer, VisitedCitySerializer
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def regions_by_country(request, country_code):
    country = get_object_or_404(Country, country_code=country_code)
    regions = (
        Region.objects.filter(country=country)
        .select_related('country')
        .annotate(num_cities_annotated=Count('city', distinct=True))
        .order_by('name')
    )
    serializer = RegionSerializer(regions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visits_by_country(request, country_code):
    country = get_object_or_404(Country, country_code=country_code)
    visits = VisitedRegion.objects.filter(region__country=country, user=request.user.id).select_related('region__country')
    serializer = VisitedRegionSerializer(visits, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cities_by_region(request, region_id):
    region = get_object_or_404(Region, id=region_id)
    cities = City.objects.filter(region=region).select_related('region__country').order_by('name')
    serializer = CitySerializer(cities, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visits_by_region(request, region_id):
    region = get_object_or_404(Region, id=region_id)
    visits = VisitedCity.objects.filter(city__region=region, user=request.user.id).select_related('user', 'city')
    serializer = VisitedCitySerializer(visits, many=True)
    return Response(serializer.data)

# view called spin the globe that return a random country, a random region in that country and a random city in that region
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def globespin(request):
    country = Country.objects.order_by('?').first()
    data = {
        "country": CountrySerializer(country).data,
    }
    
    regions = Region.objects.filter(country=country).select_related('country')
    if regions.exists():
        region = regions.order_by('?').first()
        data["region"] = RegionSerializer(region).data
        
        cities = City.objects.filter(region=region)
        if cities.exists():
            city = cities.order_by('?').first()
            data["city"] = CitySerializer(city).data
    
    return Response(data)

class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.all().order_by('name')
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Region and visit counts come from the same query instead of two per country.
        return Country.objects.annotate(
            num_regions_annotated=Count('region', distinct=True),
            num_visits_annotated=Count(
                'region__visitedregion',
                filter=Q(region__visitedregion__user=self.request.user.id),
                distinct=True,
            ),
        ).order_by('name')

class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.select_related('country').annotate(
        num_cities_annotated=Count('city', distinct=True)
    )
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]

class VisitedRegionViewSet(viewsets.ModelViewSet):
    serializer_class = VisitedRegionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VisitedRegion.objects.filter(user=self.request.user.id).select_related('region__country')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        request.data['user'] = request.user
        if VisitedRegion.objects.filter(user=request.user.id, region=request.data['region']).exists():
            return Response({"error": "Region already visited by user."}, status=400)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, **kwargs):
        region = get_object_or_404(Region, id=kwargs['pk'])
        visited_region = VisitedRegion.objects.filter(user=request.user.id, region=region)
        if visited_region.exists():
            visited_region.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Visited region not found."}, status=status.HTTP_404_NOT_FOUND)
    
class VisitedCityViewSet(viewsets.ModelViewSet):
    serializer_class = VisitedCitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VisitedCity.objects.filter(user=self.request.user.id)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        request.data['user'] = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Ensure a VisitedRegion exists for the city
        region = serializer.validated_data['city'].region
        mark_regions_visited(request.user.id, [region.id])
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, **kwargs):
        city = get_object_or_404(City, id=kwargs['pk'])
        visited_city = VisitedCity.objects.filter(user=request.user.id, city=city)
        if visited_city.exists():
            visited_city.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Visited city not found."}, status=status.HTTP_404_NOT_FOUND)
