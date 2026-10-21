from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import requests
import logging
import time
import re
from datetime import datetime
from urllib.parse import quote
from django.core import signing
from django.shortcuts import redirect
from django.conf import settings
from integrations.models import StravaToken
from core.exceptions import APIError
from core.serializers import validated
from core.timezones import TIMEZONES

logger = logging.getLogger(__name__)

# Seconds to wait on Strava before giving up.
STRAVA_REQUEST_TIMEOUT = 15

# The OAuth state sent to Strava must come back within this many seconds.
STRAVA_STATE_SALT = 'integrations.strava.oauth-state'
STRAVA_STATE_MAX_AGE = 600

class StravaActivitiesQuerySerializer(serializers.Serializer):
    start_date = serializers.CharField(required=False, help_text='ISO 8601 date or date-time; activities after it.')
    end_date = serializers.CharField(required=False, help_text='ISO 8601 date or date-time; activities before it.')
    page = serializers.IntegerField(default=1, min_value=1)
    per_page = serializers.IntegerField(default=30, min_value=1, max_value=200)


STRAVA_ACTIVITY = {
    'type': 'object',
    'description': 'An activity normalized from Strava: distances in meters, times in seconds, speeds in m/s, '
    'plus `export_gpx`, `timezone` (IANA) and convenience units (`distance_km`, `average_speed_kmh`, ...).',
}
_NOT_CONNECTED = OpenApiResponse(description='You have not connected Strava (`strava.not_authorized`).')
_UPSTREAM = OpenApiResponse(description='Strava failed (`strava.fetch_failed`, `strava.connection_failed`).')


class StravaViewSet(viewsets.GenericViewSet):
    """
    Your connection to Strava, for importing activities. The server needs a Strava app
    (`STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`). Routed as a singleton.
    """

    openapi_tags = ['Integrations']
    queryset = StravaToken.objects.none()

    def extract_timezone_from_strava(self, strava_timezone):
        """
        Extract IANA timezone from Strava's GMT offset format
        Input: "(GMT-05:00) America/New_York" or "(GMT+01:00) Europe/Zurich"
        Output: "America/New_York" if it exists in TIMEZONES, otherwise None
        """
        if not strava_timezone:
            return None
            
        # Use regex to extract the IANA timezone identifier
        # Pattern matches: (GMT±XX:XX) Timezone/Name
        match = re.search(r'\(GMT[+-]\d{2}:\d{2}\)\s*(.+)', strava_timezone)
        if match:
            timezone_name = match.group(1).strip()
            # Check if this timezone exists in our TIMEZONES list
            if timezone_name in TIMEZONES:
                return timezone_name
            
        # If no match or timezone not in our list, try to find a close match
        # This handles cases where Strava might use slightly different names
        if match:
            timezone_name = match.group(1).strip()
            # Try some common variations
            variations = [
                timezone_name,
                timezone_name.replace('_', '/'),
                timezone_name.replace('/', '_'),
            ]
            
            for variation in variations:
                if variation in TIMEZONES:
                    return variation
        
        return None

    @extend_schema(responses=inline_serializer('StravaAuthorize', fields={
        'auth_url': serializers.URLField(help_text="Send the browser here to approve access on Strava's site."),
    }))
    @action(detail=False, methods=['get'], url_path='authorize')
    def authorize(self, request):
        """
        Start connecting Strava

        Returns the Strava page where you approve access. Strava then sends the browser to
        `callback/`, which finishes the connection.
        """
        client_id = settings.STRAVA_CLIENT_ID
        redirect_uri = f"{settings.PUBLIC_URL}/api/integrations/strava/callback/"
        scope = 'activity:read_all'
        # Ties the round trip to this user, so a link carrying someone else's code cannot
        # connect their Strava account to this one.
        state = signing.dumps({'user': request.user.pk}, salt=STRAVA_STATE_SALT)

        auth_url = (
            f'https://www.strava.com/oauth/authorize?client_id={client_id}'
            f'&response_type=code'
            f'&redirect_uri={redirect_uri}'
            f'&approval_prompt=auto'
            f'&scope={scope}'
            f'&state={quote(state, safe="")}'
        )

        return Response({'auth_url': auth_url}, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[
            OpenApiParameter('code', str, required=True, description='From Strava.'),
            OpenApiParameter('state', str, required=True, description='From `authorize/`, passed back by Strava.'),
        ],
        responses={
            302: OpenApiResponse(description='Connected; redirects to the settings page of the app.'),
            400: OpenApiResponse(description='Missing code, or the approval expired or started elsewhere '
                                 '(`strava.invalid_state`).'),
            502: _UPSTREAM,
        },
    )
    @action(detail=False, methods=['get'], url_path='callback')
    def callback(self, request):
        """
        Finish connecting Strava

        Strava sends the browser here after you approve access. Not called by API clients.
        """
        code = request.query_params.get('code')
        if not code:
            raise APIError('Missing authorization code from Strava.', code='strava.missing_code', status=status.HTTP_400_BAD_REQUEST)

        try:
            state = signing.loads(
                request.query_params.get('state', ''), salt=STRAVA_STATE_SALT, max_age=STRAVA_STATE_MAX_AGE
            )
        except signing.BadSignature:
            state = None
        if not state or state.get('user') != request.user.pk:
            raise APIError('The Strava authorization expired or did not start here. Try connecting again.', code='strava.invalid_state', status=status.HTTP_400_BAD_REQUEST)

        token_url = 'https://www.strava.com/oauth/token'
        payload = {
            'client_id': int(settings.STRAVA_CLIENT_ID),
            'client_secret': settings.STRAVA_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code'
        }

        try:
            response = requests.post(token_url, data=payload, timeout=STRAVA_REQUEST_TIMEOUT)
            response_data = response.json()

            if response.status_code != 200:
                logger.warning("Strava token exchange failed: %s", response_data)
                raise APIError('Failed to exchange code for access token.', code='strava.exchange_failed', status=status.HTTP_502_BAD_GATEWAY, details=response_data.get('message', 'Unknown error'))

            logger.info("Strava token exchange successful for user %s", request.user.username)

            # Save or update tokens in DB
            strava_token, created = StravaToken.objects.update_or_create(
                user=request.user,
                defaults={
                    'access_token': response_data.get('access_token'),
                    'refresh_token': response_data.get('refresh_token'),
                    'expires_at': response_data.get('expires_at'),
                    'athlete_id': response_data.get('athlete', {}).get('id'),
                    'scope': response_data.get('scope'),
                }
            )

            # redirect to frontend url / settings
            frontend_url = settings.FRONTEND_URL
            if not frontend_url.endswith('/'):
                frontend_url += '/'
            return redirect(f"{frontend_url}settings?tab=integrations")

        except requests.RequestException as e:
            logger.error("Error during Strava OAuth token exchange: %s", str(e))
            raise APIError('Failed to connect to Strava.', code='strava.connection_failed', status=status.HTTP_502_BAD_GATEWAY)
        
    @extend_schema(responses={204: OpenApiResponse(description='Disconnected.'), 404: _NOT_CONNECTED})
    def destroy(self, request):
        """Disconnect Strava"""
        strava_token = StravaToken.objects.filter(user=request.user).first()
        if not strava_token:
            raise APIError('Strava integration is not enabled for this user.', code='strava.not_enabled', status=status.HTTP_404_NOT_FOUND)

        strava_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    def refresh_strava_token_if_needed(self, user):
        strava_token = StravaToken.objects.filter(user=user).first()
        if not strava_token:
            raise APIError('You need to authorize Strava first.', code='strava.not_authorized', status=status.HTTP_404_NOT_FOUND)

        now = int(time.time())
        # If token expires in less than 5 minutes, refresh it
        if strava_token.expires_at - now < 300:
            logger.info(f"Refreshing Strava token for user {user.username}")
            refresh_url = 'https://www.strava.com/oauth/token'
            payload = {
                'client_id': int(settings.STRAVA_CLIENT_ID),
                'client_secret': settings.STRAVA_CLIENT_SECRET,
                'grant_type': 'refresh_token',
                'refresh_token': strava_token.refresh_token,
            }
            try:
                response = requests.post(refresh_url, data=payload, timeout=STRAVA_REQUEST_TIMEOUT)
                data = response.json()
                if response.status_code == 200:
                    # Update token info
                    strava_token.access_token = data['access_token']
                    strava_token.refresh_token = data['refresh_token']
                    strava_token.expires_at = data['expires_at']
                    strava_token.save()
                    return strava_token
                else:
                    logger.error(f"Failed to refresh Strava token: {data}")
                    raise APIError('Failed to refresh Strava token.', code='strava.refresh_failed', status=status.HTTP_502_BAD_GATEWAY, details=data.get('message', 'Unknown error'))
            except requests.RequestException as e:
                logger.error(f"Error refreshing Strava token: {str(e)}")
                raise APIError('Failed to connect to Strava for token refresh.', code='strava.connection_failed', status=status.HTTP_502_BAD_GATEWAY)

        return strava_token

    def extract_essential_activity_info(self, activity):
        """
        Extract essential fields from a single activity dict with enhanced metrics
        """
        # Calculate additional elevation metrics
        elev_high = activity.get("elev_high")
        elev_low = activity.get("elev_low")
        total_elevation_gain = activity.get("total_elevation_gain", 0)
        
        # Calculate total elevation loss (approximate)
        total_elevation_range = None
        estimated_elevation_loss = None
        if elev_high is not None and elev_low is not None:
            total_elevation_range = elev_high - elev_low
            estimated_elevation_loss = max(0, total_elevation_range - total_elevation_gain)
        
        # Calculate pace metrics
        moving_time = activity.get("moving_time")
        distance = activity.get("distance")
        pace_per_km = None
        pace_per_mile = None
        if moving_time and distance and distance > 0:
            pace_per_km = moving_time / (distance / 1000)
            pace_per_mile = moving_time / (distance / 1609.34)
        
        # Calculate efficiency metrics
        grade_adjusted_speed = None
        if activity.get("splits_metric") and len(activity.get("splits_metric", [])) > 0:
            splits = activity.get("splits_metric", [])
            grade_speeds = [split.get("average_grade_adjusted_speed") for split in splits if split.get("average_grade_adjusted_speed")]
            if grade_speeds:
                grade_adjusted_speed = sum(grade_speeds) / len(grade_speeds)
        
        # Calculate time metrics
        elapsed_time = activity.get("elapsed_time")
        moving_time = activity.get("moving_time")
        rest_time = None
        if elapsed_time and moving_time:
            rest_time = elapsed_time - moving_time
        
        # Extract and normalize timezone
        strava_timezone = activity.get("timezone")
        normalized_timezone = self.extract_timezone_from_strava(strava_timezone)
        
        return {
            # Basic activity info
            "id": activity.get("id"),
            "name": activity.get("name"),
            "type": activity.get("type"),
            "sport_type": activity.get("sport_type"),
            
            # Distance and time
            "distance": activity.get("distance"),  # meters
            "distance_km": round(activity.get("distance", 0) / 1000, 2) if activity.get("distance") else None,
            "distance_miles": round(activity.get("distance", 0) / 1609.34, 2) if activity.get("distance") else None,
            "moving_time": activity.get("moving_time"),  # seconds
            "elapsed_time": activity.get("elapsed_time"),  # seconds
            "rest_time": rest_time,  # seconds of non-moving time
            
            # Enhanced elevation metrics
            "total_elevation_gain": activity.get("total_elevation_gain"),  # meters
            "estimated_elevation_loss": estimated_elevation_loss,  # meters (estimated)
            "elev_high": activity.get("elev_high"),  # highest point in meters
            "elev_low": activity.get("elev_low"),  # lowest point in meters
            "total_elevation_range": total_elevation_range,  # difference between high and low
            
            # Date and location
            "start_date": activity.get("start_date"),
            "start_date_local": activity.get("start_date_local"),
            "timezone": normalized_timezone,  # Normalized IANA timezone
            "timezone_raw": strava_timezone,  # Original Strava format for reference
            
            # Speed and pace metrics
            "average_speed": activity.get("average_speed"),  # m/s
            "average_speed_kmh": round(activity.get("average_speed", 0) * 3.6, 2) if activity.get("average_speed") else None,
            "average_speed_mph": round(activity.get("average_speed", 0) * 2.237, 2) if activity.get("average_speed") else None,
            "max_speed": activity.get("max_speed"),  # m/s
            "max_speed_kmh": round(activity.get("max_speed", 0) * 3.6, 2) if activity.get("max_speed") else None,
            "max_speed_mph": round(activity.get("max_speed", 0) * 2.237, 2) if activity.get("max_speed") else None,
            "pace_per_km_seconds": pace_per_km,  # seconds per km
            "pace_per_mile_seconds": pace_per_mile,  # seconds per mile
            "grade_adjusted_average_speed": grade_adjusted_speed,  # m/s accounting for elevation
            
            # Performance metrics
            "average_cadence": activity.get("average_cadence"),
            "average_watts": activity.get("average_watts"),
            "max_watts": activity.get("max_watts"),
            "kilojoules": activity.get("kilojoules"),
            "calories": activity.get("calories"),
            
            # Achievement metrics
            "achievement_count": activity.get("achievement_count"),
            "kudos_count": activity.get("kudos_count"),
            "comment_count": activity.get("comment_count"),
            "pr_count": activity.get("pr_count"),  # personal records achieved
            
            # Equipment and technical
            "gear_id": activity.get("gear_id"),
            "device_name": activity.get("device_name"),
            "trainer": activity.get("trainer"),  # indoor trainer activity
            "manual": activity.get("manual"),  # manually entered
            
            # GPS coordinates
            "start_latlng": activity.get("start_latlng"),
            "end_latlng": activity.get("end_latlng"),
            
            # Export links
            'export_original': f'https://www.strava.com/activities/{activity.get("id")}/export_original',
            'export_gpx': f'https://www.strava.com/activities/{activity.get("id")}/export_gpx',
            
            # Additional useful fields
            "visibility": activity.get("visibility"),
            "photo_count": activity.get("photo_count"),
            "has_heartrate": activity.get("has_heartrate"),
            "flagged": activity.get("flagged"),
            "commute": activity.get("commute"),
        }

    @staticmethod
    def format_pace_readable(pace_seconds):
        """
        Helper function to convert pace in seconds to readable format (MM:SS)
        """
        if pace_seconds is None:
            return None
        minutes = int(pace_seconds // 60)
        seconds = int(pace_seconds % 60)
        return f"{minutes}:{seconds:02d}"

    @staticmethod
    def format_time_readable(time_seconds):
        """
        Helper function to convert time in seconds to readable format (HH:MM:SS)
        """
        if time_seconds is None:
            return None
        hours = int(time_seconds // 3600)
        minutes = int((time_seconds % 3600) // 60)
        seconds = int(time_seconds % 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    @extend_schema(
        parameters=[StravaActivitiesQuerySerializer],
        responses={
            200: inline_serializer('StravaActivityList', fields={
                'activities': serializers.ListField(child=serializers.DictField()),
                'count': serializers.IntegerField(help_text='Activities on this page.'),
                'page': serializers.IntegerField(),
                'per_page': serializers.IntegerField(),
            }),
            404: _NOT_CONNECTED,
            502: _UPSTREAM,
        },
    )
    @action(detail=False, methods=['get'], url_path='activities')
    def activities(self, request):
        """
        List your Strava activities

        Newest first, a page at a time, optionally between two dates. Strava's own paging:
        there is no total count.
        """
        query = validated(StravaActivitiesQuerySerializer, request.query_params)
        strava_token = self.refresh_strava_token_if_needed(request.user)
        start_date, end_date = query.get('start_date'), query.get('end_date')
        page, per_page = query['page'], query['per_page']
        params = {'per_page': per_page, 'page': page}
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                params['after'] = int(start_dt.timestamp())
            except ValueError:
                raise APIError('Invalid start_date format. Use ISO format (e.g., 2024-01-01T00:00:00Z)', code='strava.invalid_start_date', status=status.HTTP_400_BAD_REQUEST)
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                params['before'] = int(end_dt.timestamp())
            except ValueError:
                raise APIError('Invalid end_date format. Use ISO format (e.g., 2024-12-31T23:59:59Z)', code='strava.invalid_end_date', status=status.HTTP_400_BAD_REQUEST)

        headers = {'Authorization': f'Bearer {strava_token.access_token}'}
        try:
            response = requests.get('https://www.strava.com/api/v3/athlete/activities', 
                                headers=headers, params=params, timeout=STRAVA_REQUEST_TIMEOUT)
            if response.status_code != 200:
                raise APIError('Failed to fetch activities from Strava.', code='strava.fetch_failed', status=status.HTTP_502_BAD_GATEWAY, details=response.json().get('message', 'Unknown error'))

            activities = response.json()
            essential_activities = [self.extract_essential_activity_info(act) for act in activities]

            return Response({
                'activities': essential_activities,
                'count': len(essential_activities),
                'page': page,
                'per_page': per_page,
            })

        except requests.RequestException as e:
            logger.error(f"Error fetching Strava activities: {str(e)}")
            raise APIError('Failed to connect to Strava.', code='strava.connection_failed', status=status.HTTP_502_BAD_GATEWAY)

    @extend_schema(
        parameters=[OpenApiParameter('activity_id', str, OpenApiParameter.PATH, description='The Strava activity id.')],
        responses={200: STRAVA_ACTIVITY, 404: _NOT_CONNECTED, 502: _UPSTREAM},
    )
    @action(detail=False, methods=['get'], url_path='activities/(?P<activity_id>[^/.]+)')
    def activity(self, request, activity_id=None):
        """Get a Strava activity"""

        strava_token = self.refresh_strava_token_if_needed(request.user)

        headers = {'Authorization': f'Bearer {strava_token.access_token}'}
        try:
            response = requests.get(f'https://www.strava.com/api/v3/activities/{activity_id}', headers=headers, timeout=STRAVA_REQUEST_TIMEOUT)
            if response.status_code != 200:
                raise APIError('Failed to fetch activity from Strava.', code='strava.fetch_failed', status=status.HTTP_502_BAD_GATEWAY, details=response.json().get('message', 'Unknown error'))

            activity = response.json()
            essential_activity = self.extract_essential_activity_info(activity)
            return Response(essential_activity, status=status.HTTP_200_OK)

        except requests.RequestException as e:
            logger.error(f"Error fetching Strava activity: {str(e)}")
            raise APIError('Failed to connect to Strava.', code='strava.connection_failed', status=status.HTTP_502_BAD_GATEWAY)