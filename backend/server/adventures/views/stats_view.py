from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db import models
from worldtravel.models import City, Region, Country, VisitedCity, VisitedRegion
from adventures.models import Location, Collection, Activity
from django.contrib.auth import get_user_model

User = get_user_model()

class StatsViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for listing the stats of a user.
    """
    @action(detail=False, methods=['get'], url_path=r'counts/(?P<username>[\w.@+-]+)')
    def counts(self, request, username):
        if request.user.username == username:
            user = get_object_or_404(User, username=username)
        else:
            user = get_object_or_404(User, username=username, public_profile=True)
        # serializer = PublicUserSerializer(user)
        
        # remove the email address from the response
        user.email = None

        # get the counts for the user
        location_count = Location.objects.filter(
            user=user.id).count()
        trips_count = Collection.objects.filter(
            user=user.id).count()
        visited_city_count = VisitedCity.objects.filter(
            user=user.id).count()
        total_cities = City.objects.count()
        visited_region_count = VisitedRegion.objects.filter(
            user=user.id).count()
        total_regions = Region.objects.count()
        visited_country_count = VisitedRegion.objects.filter(
            user=user.id).values('region__country').distinct().count()
        total_countries = Country.objects.count()
        
        # get activity counts
        user_activities = Activity.objects.filter(
            user=user.id)
        
        activity_count = user_activities.count()
        activity_distance = user_activities.aggregate(
            total_distance=models.Sum('distance'))['total_distance'] or 0
        activity_moving_time = user_activities.aggregate(
            total_duration=models.Sum('moving_time'))['total_duration'] or 0
        activity_elevation = user_activities.aggregate(
            total_elevation=models.Sum('elevation_gain'))['total_elevation'] or 0
        
        return Response({
            'location_count': location_count,
            'trips_count': trips_count,
            'visited_city_count': visited_city_count,
            'total_cities': total_cities,
            'visited_region_count': visited_region_count,
            'total_regions': total_regions,
            'visited_country_count': visited_country_count,
            'total_countries': total_countries,
            'activity_distance': activity_distance, # measured in meters
            'activity_moving_time': activity_moving_time, # measured in seconds
            'activity_elevation': activity_elevation, # measured in meters
            'activity_count': activity_count,
        }) 