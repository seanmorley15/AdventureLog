from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from adventures.utils.sports_types import SPORT_CATEGORIES
from adventures.utils.get_is_visited import is_location_visited
from django.db.models import Sum, Avg, Max, Count
from worldtravel.models import City, Region, Country, VisitedCity, VisitedRegion
from adventures.models import Location, Collection, Activity, Transportation, Lodging, Visit
from django.contrib.auth import get_user_model
from math import radians, sin, cos, sqrt, atan2

User = get_user_model()

class StatsViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for listing the stats of a user.
    """

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the great circle distance between two points in km"""
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return 0

        R = 6371  # Radius of the earth in km

        lat1_rad = radians(float(lat1))
        lat2_rad = radians(float(lat2))
        dlat = radians(float(lat2) - float(lat1))
        dlon = radians(float(lon2) - float(lon1))

        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    def _get_total_transportation_distance(self, user):
        """Calculate total distance traveled via transportation in km (based on visits)"""
        # Get all transportation visits for this user
        transport_visits = Visit.objects.filter(
            user=user,
            transportation__isnull=False
        ).select_related('transportation')

        total_distance = 0
        for visit in transport_visits:
            transport = visit.transportation
            distance = self._haversine_distance(
                transport.origin_latitude, transport.origin_longitude,
                transport.destination_latitude, transport.destination_longitude
            )
            total_distance += distance

        return round(total_distance, 2)

    def _get_total_lodging_nights(self, user):
        """Calculate total nights stayed in lodging (based on visits)"""
        # Get all lodging visits for this user
        lodging_visits = Visit.objects.filter(
            user=user,
            lodging__isnull=False
        )

        total_nights = 0
        for visit in lodging_visits:
            if visit.start_date and visit.end_date:
                delta = visit.end_date - visit.start_date
                nights = delta.days
                if nights > 0:
                    total_nights += nights

        return total_nights

    def _get_visited_locations_count(self, user):
        """Calculate count of distinct locations visited by user (based on visits)"""
        # Count distinct locations that have at least one visit by this user
        visited_count = Visit.objects.filter(
            user=user,
            location__isnull=False
        ).values('location').distinct().count()

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

        # Transportation and lodging stats
        transportation_count = Transportation.objects.filter(user=user.id).count()
        lodging_count = Lodging.objects.filter(user=user.id).count()
        total_transportation_km = self._get_total_transportation_distance(user)
        total_lodging_nights = self._get_total_lodging_nights(user)

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

            # Transportation and lodging stats
            'transportation_count': transportation_count,
            'lodging_count': lodging_count,
            'total_transportation_km': total_transportation_km,
            'total_lodging_nights': total_lodging_nights,

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