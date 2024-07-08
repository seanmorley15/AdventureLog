from django.shortcuts import render
from .models import Country, Region, VisitedRegion
from .serializers import CountrySerializer, RegionSerializer, VisitedRegionSerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def regions_by_country(request, country_code):
    # require authentication
    country = get_object_or_404(Country, country_code=country_code)
    regions = Region.objects.filter(country=country)
    serializer = RegionSerializer(regions, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visits_by_country(request, country_code):
    country = get_object_or_404(Country, country_code=country_code)
    visits = VisitedRegion.objects.filter(region__country=country)

    serializer = VisitedRegionSerializer(visits, many=True)
    return Response(serializer.data)


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]

class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]

class VisitedRegionViewSet(viewsets.ModelViewSet):
    queryset = VisitedRegion.objects.all()
    serializer_class = VisitedRegionSerializer
    permission_classes = [IsAuthenticated]