import os
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from integrations.models import ImmichIntegration, StravaToken, WandererIntegration
from django.conf import settings


class IntegrationView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    def list(self, request):
        """
        RESTful GET method for listing all integrations.
        """
        immich_integrations = ImmichIntegration.objects.filter(user=request.user)
        google_map_integration = settings.GOOGLE_MAPS_API_KEY != ''
        strava_integration_global = settings.STRAVA_CLIENT_ID != '' and settings.STRAVA_CLIENT_SECRET != ''
        strava_integration_user = StravaToken.objects.filter(user=request.user).exists()
        wanderer_integration = WandererIntegration.objects.filter(user=request.user).exists()

        return Response(
            {
                'immich': immich_integrations.exists(),
                'google_maps': google_map_integration,
                'strava': {
                    'global': strava_integration_global,
                    'user': strava_integration_user
                },
                'wanderer': wanderer_integration
            },
            status=status.HTTP_200_OK
        )
