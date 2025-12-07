from django.shortcuts import render, get_object_or_404
from .models import Country, Region, VisitedRegion, City, VisitedCity
from .serializers import CitySerializer, CountrySerializer, RegionSerializer, VisitedRegionSerializer, VisitedCitySerializer
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from adventures.models import Location

# Cache TTL
CACHE_TTL = 60 * 60 * 24  # 1 day


def invalidate_visit_caches_for_region_and_user(region, user):
    """Invalidate cached visit lists for a given region and user.

    Removes both the per-region and per-country per-user cache keys so
    UI calls will refetch updated visited lists.
    """
    try:
        if region is None or user is None:
            return
        # per-region cache
        cache.delete(f"visits_by_region_{region.id}_{user.id}")
        # per-country cache (region -> country -> country_code)
        country_code = getattr(region.country, 'country_code', None)
        if country_code:
            cache.delete(f"visits_by_country_{country_code}_{user.id}")
    except Exception:
        # Avoid raising cache-related exceptions; best-effort invalidation
        pass

@cache_page(CACHE_TTL)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def regions_by_country(request, country_code):
    country = get_object_or_404(Country, country_code=country_code)
    regions = Region.objects.filter(country=country).order_by('name')
    serializer = RegionSerializer(regions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visits_by_country(request, country_code):
    cache_key = f"visits_by_country_{country_code}_{request.user.id}"
    data = cache.get(cache_key)
    if data is not None:
        return Response(data)
    country = get_object_or_404(Country, country_code=country_code)
    visits = VisitedRegion.objects.filter(region__country=country, user=request.user.id)
    serializer = VisitedRegionSerializer(visits, many=True)
    cache.set(cache_key, serializer.data, CACHE_TTL)
    return Response(serializer.data)

@cache_page(CACHE_TTL)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cities_by_region(request, region_id):
    region = get_object_or_404(Region, id=region_id)
    cities = City.objects.filter(region=region).order_by('name')
    serializer = CitySerializer(cities, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visits_by_region(request, region_id):
    cache_key = f"visits_by_region_{region_id}_{request.user.id}"
    data = cache.get(cache_key)
    if data is not None:
        return Response(data)
    region = get_object_or_404(Region, id=region_id)
    visits = VisitedCity.objects.filter(city__region=region, user=request.user.id)
    serializer = VisitedCitySerializer(visits, many=True)
    cache.set(cache_key, serializer.data, CACHE_TTL)
    return Response(serializer.data)

# view called spin the globe that return a random country, a random region in that country and a random city in that region
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def globespin(request):
    country = Country.objects.order_by('?').first()
    data = {
        "country": CountrySerializer(country).data,
    }
    
    regions = Region.objects.filter(country=country)
    if regions.exists():
        region = regions.order_by('?').first()
        data["region"] = RegionSerializer(region).data
        
        cities = City.objects.filter(region=region)
        if cities.exists():
            city = cities.order_by('?').first()
            data["city"] = CitySerializer(city).data
    
    return Response(data)

@method_decorator(cache_page(CACHE_TTL), name='list')
class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.all().order_by('name')
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def check_point_in_region(self, request):
        lat = float(request.query_params.get('lat'))
        lon = float(request.query_params.get('lon'))
        point = Point(lon, lat, srid=4326)
        region = Region.objects.filter(geometry__contains=point).first()
        if region:
            return Response({'in_region': True, 'region_name': region.name, 'region_id': region.id})
        else:
            return Response({'in_region': False})

    @action(detail=False, methods=['post'])
    def region_check_all_adventures(self, request):
        adventures = Location.objects.filter(user=request.user.id, type='visited')
        count = 0
        for adventure in adventures:
            if adventure.latitude is not None and adventure.longitude is not None:
                try:
                    point = Point(float(adventure.longitude), float(adventure.latitude), srid=4326)
                    region = Region.objects.filter(geometry__contains=point).first()
                    if region:
                        if not VisitedRegion.objects.filter(user=request.user.id, region=region).exists():
                            VisitedRegion.objects.create(user=request.user, region=region)
                            count += 1
                except Exception as e:
                    print(f"Error processing adventure {adventure.id}: {e}")
                    continue
        return Response({'regions_visited': count})

@method_decorator(cache_page(CACHE_TTL), name='list')
class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]

class VisitedRegionViewSet(viewsets.ModelViewSet):
    serializer_class = VisitedRegionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VisitedRegion.objects.filter(user=self.request.user.id)
    
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
        # Invalidate caches for this region and its country for the user
        try:
            region = serializer.validated_data.get('region')
            invalidate_visit_caches_for_region_and_user(region, request.user)
        except Exception:
            pass
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, **kwargs):
        region = get_object_or_404(Region, id=kwargs['pk'])
        visited_region = VisitedRegion.objects.filter(user=request.user.id, region=region)
        if visited_region.exists():
            # capture region before deleting so we can invalidate caches
            affected_region = visited_region.first().region
            visited_region.delete()
            invalidate_visit_caches_for_region_and_user(affected_region, request.user)
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
        # Ensure a VisitedRegion exists for the city and invalidate caches
        region = serializer.validated_data['city'].region
        if not VisitedRegion.objects.filter(user=request.user.id, region=region).exists():
            VisitedRegion.objects.create(user=request.user, region=region)
        try:
            invalidate_visit_caches_for_region_and_user(region, request.user)
        except Exception:
            pass
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, **kwargs):
        city = get_object_or_404(City, id=kwargs['pk'])
        visited_city = VisitedCity.objects.filter(user=request.user.id, city=city)
        if visited_city.exists():
            region = city.region
            visited_city.delete()
            invalidate_visit_caches_for_region_and_user(region, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Visited city not found."}, status=status.HTTP_404_NOT_FOUND)
