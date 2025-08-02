from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
import requests
import logging
import time
from django.shortcuts import redirect
from django.conf import settings
from integrations.models import StravaToken

logger = logging.getLogger(__name__)

class StravaIntegrationView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='authorize')
    def authorize(self, request):
        """
        Redirects the user to Strava's OAuth authorization page.
        """
        client_id = settings.STRAVA_CLIENT_ID
        redirect_uri = f"{settings.PUBLIC_URL}/api/integrations/strava/callback/"
        scope = 'activity:read_all'

        auth_url = (
            f'https://www.strava.com/oauth/authorize?client_id={client_id}'
            f'&response_type=code'
            f'&redirect_uri={redirect_uri}'
            f'&approval_prompt=auto'
            f'&scope={scope}'
        )

        return Response({'auth_url': auth_url}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='callback')
    def callback(self, request):
        """
        Handles the OAuth callback from Strava and exchanges the code for an access token.
        Saves or updates the StravaToken model instance for the authenticated user.
        """
        code = request.query_params.get('code')
        if not code:
            return Response(
                {
                    'message': 'Missing authorization code from Strava.',
                    'error': True,
                    'code': 'strava.missing_code'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        token_url = 'https://www.strava.com/oauth/token'
        payload = {
            'client_id': int(settings.STRAVA_CLIENT_ID),
            'client_secret': settings.STRAVA_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code'
        }

        try:
            response = requests.post(token_url, data=payload)
            response_data = response.json()

            if response.status_code != 200:
                logger.warning("Strava token exchange failed: %s", response_data)
                return Response(
                    {
                        'message': 'Failed to exchange code for access token.',
                        'error': True,
                        'code': 'strava.exchange_failed',
                        'details': response_data.get('message', 'Unknown error')
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

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

            # redirect to frontend url / setttigns
            frontend_url = settings.FRONTEND_URL
            if not frontend_url.endswith('/'):
                frontend_url += '/'
            return redirect(f"{frontend_url}settings?tab=integrations")


        except requests.RequestException as e:
            logger.error("Error during Strava OAuth token exchange: %s", str(e))
            return Response(
                {
                    'message': 'Failed to connect to Strava.',
                    'error': True,
                    'code': 'strava.connection_failed',
                    'details': str(e)
                },
                status=status.HTTP_502_BAD_GATEWAY
            )
        
    @action(detail=False, methods=['post'], url_path='disable')
    def disable(self, request):
        """
        Disables the Strava integration for the authenticated user by deleting their StravaToken.
        """
        strava_token = StravaToken.objects.filter(user=request.user).first()
        if not strava_token:
            return Response(
                {
                    'message': 'Strava integration is not enabled for this user.',
                    'error': True,
                    'code': 'strava.not_enabled'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        strava_token.delete()
        return Response(
            {'message': 'Strava integration disabled successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )
        
    def refresh_strava_token_if_needed(self, user):
        strava_token = StravaToken.objects.filter(user=user).first()
        if not strava_token:
            return None, Response({
                'message': 'You need to authorize Strava first.',
                'error': True,
                'code': 'strava.not_authorized'
            }, status=status.HTTP_403_FORBIDDEN)

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
                response = requests.post(refresh_url, data=payload)
                data = response.json()
                if response.status_code == 200:
                    # Update token info
                    strava_token.access_token = data['access_token']
                    strava_token.refresh_token = data['refresh_token']
                    strava_token.expires_at = data['expires_at']
                    strava_token.save()
                    return strava_token, None
                else:
                    logger.error(f"Failed to refresh Strava token: {data}")
                    return None, Response({
                        'message': 'Failed to refresh Strava token.',
                        'error': True,
                        'code': 'strava.refresh_failed',
                        'details': data.get('message', 'Unknown error')
                    }, status=status.HTTP_400_BAD_REQUEST)
            except requests.RequestException as e:
                logger.error(f"Error refreshing Strava token: {str(e)}")
                return None, Response({
                    'message': 'Failed to connect to Strava for token refresh.',
                    'error': True,
                    'code': 'strava.connection_failed',
                    'details': str(e)
                }, status=status.HTTP_502_BAD_GATEWAY)

        return strava_token, None

    def extract_essential_activity_info(self,activity):
    # Pick only essential fields from a single activity dict
        return {
            "id": activity.get("id"),
            "name": activity.get("name"),
            "type": activity.get("type"),
            "distance": activity.get("distance"),
            "moving_time": activity.get("moving_time"),
            "elapsed_time": activity.get("elapsed_time"),
            "total_elevation_gain": activity.get("total_elevation_gain"),
            "start_date": activity.get("start_date"),
            "start_date_local": activity.get("start_date_local"),
            "timezone": activity.get("timezone"),
            "average_speed": activity.get("average_speed"),
            "max_speed": activity.get("max_speed"),
            "average_cadence": activity.get("average_cadence"),
            "average_watts": activity.get("average_watts"),
            "max_watts": activity.get("max_watts"),
            "kilojoules": activity.get("kilojoules"),
            "calories": activity.get("calories"),
            "gear_id": activity.get("gear_id"),
            "device_name": activity.get("device_name"),
            "start_latlng": activity.get("start_latlng"),
            "end_latlng": activity.get("end_latlng"),
            'export_original': f'https://www.strava.com/activities/{activity.get("id")}/export_original',
            'export_gpx': f'https://www.strava.com/activities/{activity.get("id")}/export_gpx',
        }

    @action(detail=False, methods=['get'], url_path='activities')
    def activities(self, request):
        strava_token, error_response = self.refresh_strava_token_if_needed(request.user)
        if error_response:
            return error_response

        # Get date parameters from query string
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Build query parameters for Strava API
        params = {}
        
        if start_date:
            try:
                # Parse the date string and convert to Unix timestamp
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                params['after'] = int(start_dt.timestamp())
            except ValueError:
                return Response({
                    'message': 'Invalid start_date format. Use ISO format (e.g., 2024-01-01T00:00:00Z)',
                    'error': True,
                    'code': 'strava.invalid_start_date'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if end_date:
            try:
                # Parse the date string and convert to Unix timestamp
                from datetime import datetime
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                params['before'] = int(end_dt.timestamp())
            except ValueError:
                return Response({
                    'message': 'Invalid end_date format. Use ISO format (e.g., 2024-12-31T23:59:59Z)',
                    'error': True,
                    'code': 'strava.invalid_end_date'
                }, status=status.HTTP_400_BAD_REQUEST)

        headers = {'Authorization': f'Bearer {strava_token.access_token}'}
        try:
            response = requests.get('https://www.strava.com/api/v3/athlete/activities', 
                                headers=headers, params=params)
            if response.status_code != 200:
                return Response({
                    'message': 'Failed to fetch activities from Strava.',
                    'error': True,
                    'code': 'strava.fetch_failed',
                    'details': response.json().get('message', 'Unknown error')
                }, status=status.HTTP_400_BAD_REQUEST)

            activities = response.json()
            essential_activities = [self.extract_essential_activity_info(act) for act in activities]

            return Response(essential_activities, status=status.HTTP_200_OK)

        except requests.RequestException as e:
            logger.error(f"Error fetching Strava activities: {str(e)}")
            return Response({
                'message': 'Failed to connect to Strava.',
                'error': True,
                'code': 'strava.connection_failed',
                'details': str(e)
            }, status=status.HTTP_502_BAD_GATEWAY)

    @action(detail=False, methods=['get'], url_path='activities/(?P<activity_id>[^/.]+)')
    def activity(self, request, activity_id=None):
        if not activity_id:
            return Response({
                'message': 'Activity ID is required.',
                'error': True,
                'code': 'strava.activity_id_required'
            }, status=status.HTTP_400_BAD_REQUEST)

        strava_token, error_response = self.refresh_strava_token_if_needed(request.user)
        if error_response:
            return error_response

        headers = {'Authorization': f'Bearer {strava_token.access_token}'}
        try:
            response = requests.get(f'https://www.strava.com/api/v3/activities/{activity_id}', headers=headers)
            if response.status_code != 200:
                return Response({
                    'message': 'Failed to fetch activity from Strava.',
                    'error': True,
                    'code': 'strava.fetch_failed',
                    'details': response.json().get('message', 'Unknown error')
                }, status=status.HTTP_400_BAD_REQUEST)

            activity = response.json()
            essential_activity = self.extract_essential_activity_info(activity)
            return Response(essential_activity, status=status.HTTP_200_OK)

        except requests.RequestException as e:
            logger.error(f"Error fetching Strava activity: {str(e)}")
            return Response({
                'message': 'Failed to connect to Strava.',
                'error': True,
                'code': 'strava.connection_failed',
                'details': str(e)
            }, status=status.HTTP_502_BAD_GATEWAY)