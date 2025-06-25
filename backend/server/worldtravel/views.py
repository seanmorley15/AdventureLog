from django.shortcuts import render
from .models import Country, Region, VisitedRegion, City, VisitedCity
from .serializers import CitySerializer, CountrySerializer, RegionSerializer, VisitedRegionSerializer, VisitedCitySerializer
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
import os
import json
from django.http import JsonResponse
from django.contrib.gis.geos import Point
from django.conf import settings
from rest_framework.decorators import action
from django.contrib.staticfiles import finders
from adventures.models import Location

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def regions_by_country(request, country_code):
    # require authentication
    country = get_object_or_404(Country, country_code=country_code)
    regions = Region.objects.filter(country=country).order_by('name')
    serializer = RegionSerializer(regions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visits_by_country(request, country_code):
    country = get_object_or_404(Country, country_code=country_code)
    visits = VisitedRegion.objects.filter(region__country=country, user=request.user.id)

    serializer = VisitedRegionSerializer(visits, many=True)
    return Response(serializer.data)

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
    region = get_object_or_404(Region, id=region_id)
    visits = VisitedCity.objects.filter(city__region=region, user=request.user.id)

    serializer = VisitedCitySerializer(visits, many=True)
    return Response(serializer.data)

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
        
    # make a post action that will get all of the users adventures and check if the point is in any of the regions if so make a visited region object for that user if it does not already exist
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
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, **kwargs):
        # delete by region id
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
        # if the region is not visited, visit it
        region = serializer.validated_data['city'].region
        if not VisitedRegion.objects.filter(user=request.user.id, region=region).exists():
            VisitedRegion.objects.create(user=request.user, region=region)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, **kwargs):
        # delete by city id
        city = get_object_or_404(City, id=kwargs['pk'])
        visited_city = VisitedCity.objects.filter(user=request.user.id, city=city)
        if visited_city.exists():
            visited_city.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Visited city not found."}, status=status.HTTP_404_NOT_FOUND)