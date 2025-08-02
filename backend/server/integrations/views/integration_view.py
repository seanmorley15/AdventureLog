import os
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from integrations.models import ImmichIntegration
from django.conf import settings


class IntegrationView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    def list(self, request):
        """
        RESTful GET method for listing all integrations.
        """
        immich_integrations = ImmichIntegration.objects.filter(user=request.user)
        google_map_integration = settings.GOOGLE_MAPS_API_KEY != ''
        strava_integration = settings.STRAVA_CLIENT_ID != '' and settings.STRAVA_CLIENT_SECRET != ''

        return Response(
            {
                'immich': immich_integrations.exists(),
                'google_maps': google_map_integration,
                'strava': strava_integration
            },
            status=status.HTTP_200_OK
        )
