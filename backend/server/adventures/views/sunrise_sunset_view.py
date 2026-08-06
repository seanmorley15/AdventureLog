from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from adventures.models import Location
from adventures.services.sunrise_sunset.times import get_sunrise_sunset_for_date
from adventures.throttling import ExternalSunriseSunsetThrottle
from adventures.utils.geo import point_to_lat_lon
from adventures.utils.location_access import user_can_access_location


class SunriseSunsetAPI(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], throttle_classes=[ExternalSunriseSunsetThrottle])
    def lookup(self, request):
        location_id = request.query_params.get('location_id', '').strip()
        date_value = request.query_params.get('date', '').strip()

        if not location_id:
            return Response({'error': 'location_id parameter is required'}, status=400)
        if not date_value:
            return Response({'error': 'date parameter is required'}, status=400)

        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            return Response({'error': 'Location not found'}, status=404)

        if not user_can_access_location(location, request.user):
            return Response(
                {'error': 'User does not have permission to access this location'},
                status=403,
            )

        if not location.coordinates:
            return Response({'error': 'Location has no coordinates'}, status=400)

        try:
            latitude, longitude = point_to_lat_lon(location.coordinates)
        except Exception:
            return Response({'error': 'Location coordinates are invalid'}, status=400)

        sunrise_sunset = get_sunrise_sunset_for_date(latitude, longitude, date_value)
        if not sunrise_sunset:
            return Response({'error': 'Sunrise/sunset not available for this date'}, status=404)

        return Response(sunrise_sunset)
