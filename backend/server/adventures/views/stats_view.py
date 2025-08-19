from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from adventures.utils.sports_types import SPORT_CATEGORIES
from adventures.utils.get_is_visited import is_location_visited
from django.db.models import Sum, Avg, Max, Count
from worldtravel.models import City, Region, Country, VisitedCity, VisitedRegion
from adventures.models import Location, Collection, Activity
from django.contrib.auth import get_user_model

User = get_user_model()

class StatsViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for listing the stats of a user.
    """

    def _get_visited_locations_count(self, user):
        """Calculate count of visited locations for a user"""
        visited_count = 0
        
        # Get all locations for this user
        user_locations = Location.objects.filter(user=user).prefetch_related('visits')
        
        for location in user_locations:
            if is_location_visited(location):
                visited_count += 1
        
        return visited_count

    def _get_activity_stats_by_category(self, user_activities):
        """Calculate detailed stats for each sport category"""
        category_stats = {}
        
        for category, sports in SPORT_CATEGORIES.items():
            activities = user_activities.filter(sport_type__in=sports)
            
            if activities.exists():
                # Calculate aggregated stats
                stats = activities.aggregate(
                    count=Count('id'),
                    total_distance=Sum('distance'),
                    total_moving_time=Sum('moving_time'),
                    total_elevation_gain=Sum('elevation_gain'),
                    total_elevation_loss=Sum('elevation_loss'),
                    avg_distance=Avg('distance'),
                    max_distance=Max('distance'),
                    avg_elevation_gain=Avg('elevation_gain'),
                    max_elevation_gain=Max('elevation_gain'),
                    avg_speed=Avg('average_speed'),
                    max_speed=Max('max_speed'),
                    total_calories=Sum('calories')
                )
                
                # Convert Duration objects to total seconds for JSON serialization
                total_moving_seconds = 0
                if stats['total_moving_time']:
                    total_moving_seconds = int(stats['total_moving_time'].total_seconds())
                
                # Get sport type breakdown within category
                sport_breakdown = {}
                for sport in sports:
                    sport_activities = activities.filter(sport_type=sport)
                    if sport_activities.exists():
                        sport_stats = sport_activities.aggregate(
                            count=Count('id'),
                            total_distance=Sum('distance'),
                            total_elevation_gain=Sum('elevation_gain')
                        )
                        sport_breakdown[sport] = {
                            'count': sport_stats['count'],
                            'total_distance': round(sport_stats['total_distance'] or 0, 2),
                            'total_elevation_gain': round(sport_stats['total_elevation_gain'] or 0, 2)
                        }
                
                category_stats[category] = {
                    'count': stats['count'],
                    'total_distance': round(stats['total_distance'] or 0, 2),
                    'total_moving_time': total_moving_seconds,
                    'total_elevation_gain': round(stats['total_elevation_gain'] or 0, 2),
                    'total_elevation_loss': round(stats['total_elevation_loss'] or 0, 2),
                    'avg_distance': round(stats['avg_distance'] or 0, 2),
                    'max_distance': round(stats['max_distance'] or 0, 2),
                    'avg_elevation_gain': round(stats['avg_elevation_gain'] or 0, 2),
                    'max_elevation_gain': round(stats['max_elevation_gain'] or 0, 2),
                    'avg_speed': round(stats['avg_speed'] or 0, 2),
                    'max_speed': round(stats['max_speed'] or 0, 2),
                    'total_calories': round(stats['total_calories'] or 0, 2),
                    'sports': sport_breakdown
                }
        
        return category_stats

    def _get_overall_activity_stats(self, user_activities):
        """Calculate overall activity statistics"""
        if not user_activities.exists():
            return {
                'total_count': 0,
                'total_distance': 0,
                'total_moving_time': 0,
                'total_elevation_gain': 0,
                'total_elevation_loss': 0,
                'total_calories': 0
            }
        
        stats = user_activities.aggregate(
            total_count=Count('id'),
            total_distance=Sum('distance'),
            total_moving_time=Sum('moving_time'),
            total_elevation_gain=Sum('elevation_gain'),
            total_elevation_loss=Sum('elevation_loss'),
            total_calories=Sum('calories')
        )
        
        # Convert Duration to seconds
        total_moving_seconds = 0
        if stats['total_moving_time']:
            total_moving_seconds = int(stats['total_moving_time'].total_seconds())
        
        return {
            'total_count': stats['total_count'],
            'total_distance': round(stats['total_distance'] or 0, 2),
            'total_moving_time': total_moving_seconds,
            'total_elevation_gain': round(stats['total_elevation_gain'] or 0, 2),
            'total_elevation_loss': round(stats['total_elevation_loss'] or 0, 2),
            'total_calories': round(stats['total_calories'] or 0, 2)
        }

    @action(detail=False, methods=['get'], url_path=r'counts/(?P<username>[\w.@+-]+)')
    def counts(self, request, username):
        if request.user.username == username:
            user = get_object_or_404(User, username=username)
        else:
            user = get_object_or_404(User, username=username, public_profile=True)
        
        # remove the email address from the response
        user.email = None
        
        # get the counts for the user
        location_count = Location.objects.filter(user=user.id).count()
        visited_location_count = self._get_visited_locations_count(user)
        trips_count = Collection.objects.filter(user=user.id).count()
        visited_city_count = VisitedCity.objects.filter(user=user.id).count()
        total_cities = City.objects.count()
        visited_region_count = VisitedRegion.objects.filter(user=user.id).count()
        total_regions = Region.objects.count()
        visited_country_count = VisitedRegion.objects.filter(
            user=user.id).values('region__country').distinct().count()
        total_countries = Country.objects.count()
        
        # get activity data
        user_activities = Activity.objects.filter(user=user.id)
        
        # Get enhanced activity statistics
        overall_activity_stats = self._get_overall_activity_stats(user_activities)
        activity_stats_by_category = self._get_activity_stats_by_category(user_activities)
        
        return Response({
            # Travel stats
            'location_count': location_count,
            'visited_location_count': visited_location_count,
            'trips_count': trips_count,
            'visited_city_count': visited_city_count,
            'total_cities': total_cities,
            'visited_region_count': visited_region_count,
            'total_regions': total_regions,
            'visited_country_count': visited_country_count,
            'total_countries': total_countries,
            
            # Overall activity stats
            'activities_overall': overall_activity_stats,
            
            # Detailed activity stats by category
            'activities_by_category': activity_stats_by_category,
            
            # Legacy fields (for backward compatibility)
            'activity_distance': overall_activity_stats['total_distance'],
            'activity_moving_time': overall_activity_stats['total_moving_time'],
            'activity_elevation': overall_activity_stats['total_elevation_gain'],
            'activity_count': overall_activity_stats['total_count'],
        })