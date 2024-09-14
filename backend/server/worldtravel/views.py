from django.shortcuts import render
from .models import Country, Region, VisitedRegion
from .serializers import CountrySerializer, RegionSerializer, VisitedRegionSerializer
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
from adventures.models import Adventure

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
    visits = VisitedRegion.objects.filter(region__country=country, user_id=request.user.id)

    serializer = VisitedRegionSerializer(visits, many=True)
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
        adventures = Adventure.objects.filter(user_id=request.user.id, type='visited')
        count = 0
        for adventure in adventures:
            if adventure.latitude is not None and adventure.longitude is not None:
                try:
                    print(f"Adventure {adventure.id}: lat={adventure.latitude}, lon={adventure.longitude}")
                    point = Point(float(adventure.longitude), float(adventure.latitude), srid=4326)
                    region = Region.objects.filter(geometry__contains=point).first()
                    if region:
                        if not VisitedRegion.objects.filter(user_id=request.user.id, region=region).exists():
                            VisitedRegion.objects.create(user_id=request.user, region=region)
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
        return VisitedRegion.objects.filter(user_id=self.request.user.id)
    
    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user)

    def create(self, request, *args, **kwargs):
        request.data['user_id'] = request.user
        if VisitedRegion.objects.filter(user_id=request.user.id, region=request.data['region']).exists():
            return Response({"error": "Region already visited by user."}, status=400)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class GeoJSONView(viewsets.ViewSet):
    """
    Combine all GeoJSON data from .json files in static/data into a single GeoJSON object.
    """
    def list(self, request):
        combined_geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        # Use Django's static file finder to locate the 'data' directory
        data_dir = finders.find('data')
        
        if not data_dir or not os.path.isdir(data_dir):
            return Response({"error": "Data directory does not exist."}, status=404)

        for filename in os.listdir(data_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(data_dir, filename)
                try:
                    with open(file_path, 'r') as f:
                        json_data = json.load(f)
                        # Check if the JSON data is GeoJSON
                        if isinstance(json_data, dict) and "type" in json_data:
                            if json_data["type"] == "FeatureCollection":
                                combined_geojson["features"].extend(json_data.get("features", []))
                            elif json_data["type"] == "Feature":
                                combined_geojson["features"].append(json_data)
                            # You can add more conditions here for other GeoJSON types if needed
                except (IOError, json.JSONDecodeError) as e:
                    return Response({"error": f"Error reading file {filename}: {str(e)}"}, status=500)

        return Response(combined_geojson)