from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from worldtravel.models import City, Region, Country, VisitedCity, VisitedRegion
from adventures.models import Adventure, Collection

class StatsViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for listing the stats of a user.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def counts(self, request):
        adventure_count = Adventure.objects.filter(
            user_id=request.user.id).count()
        trips_count = Collection.objects.filter(
            user_id=request.user.id).count()
        visited_city_count = VisitedCity.objects.filter(
            user_id=request.user.id).count()
        total_cities = City.objects.count()
        visited_region_count = VisitedRegion.objects.filter(
            user_id=request.user.id).count()
        total_regions = Region.objects.count()
        visited_country_count = VisitedRegion.objects.filter(
            user_id=request.user.id).values('region__country').distinct().count()
        total_countries = Country.objects.count()
        return Response({
            'adventure_count': adventure_count,
            'trips_count': trips_count,
            'visited_city_count': visited_city_count,
            'total_cities': total_cities,
            'visited_region_count': visited_region_count,
            'total_regions': total_regions,
            'visited_country_count': visited_country_count,
            'total_countries': total_countries
        })